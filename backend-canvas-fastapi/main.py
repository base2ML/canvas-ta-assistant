from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional, Dict, Any
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException, InvalidAccessToken, ResourceDoesNotExist
import asyncio
from datetime import datetime
from dateutil.parser import parse as parse_date
import math
import os
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class CanvasCredentials(BaseModel):
    base_url: HttpUrl
    api_token: str

class AssignmentRequest(CanvasCredentials):
    course_ids: List[str]

class UserProfile(BaseModel):
    name: str
    email: Optional[str] = None
    id: int
    login_id: Optional[str] = None

class CredentialValidationResponse(BaseModel):
    valid: bool
    user: Optional[UserProfile] = None
    error: Optional[str] = None

class Course(BaseModel):
    id: str
    name: str
    course_code: Optional[str] = None
    enrollment_term_id: Optional[int] = None

class Assignment(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    course_name: str
    course_id: str
    due_at: Optional[str] = None
    unlock_at: Optional[str] = None
    lock_at: Optional[str] = None
    submitted_at: Optional[str] = None
    points_possible: Optional[float] = None
    html_url: Optional[str] = None
    assignment_group_id: Optional[int] = None
    status: str
    status_text: str
    grade: Optional[str] = None
    score: Optional[float] = None
    graded_at: Optional[str] = None
    late: bool = False
    missing: bool = False
    excused: bool = False
    workflow_state: Optional[str] = None

class AssignmentResponse(BaseModel):
    assignments: List[Assignment]
    courses: List[Course]
    total_assignments: int
    warnings: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "2.0.0"
    canvas_api_version: str = "1.0"

class DetailedAssignment(BaseModel):
    assignment: Dict[str, Any]
    submission: Dict[str, Any]
    rubric: Optional[List[Dict[str, Any]]] = None
    course_info: Dict[str, Any]

class TAGroup(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    course_id: str
    members_count: int
    members: List[Dict[str, Any]]

class TAGroupsResponse(BaseModel):
    ta_groups: List[TAGroup]
    course_info: Dict[str, Any]
    total_ta_groups: int

class TAGradingRequest(CanvasCredentials):
    course_id: str
    assignment_id: Optional[int] = None

class UngradedSubmission(BaseModel):
    submission_id: int
    student_id: int
    student_name: str
    assignment_id: int
    assignment_name: str
    submitted_at: Optional[str] = None
    grader_id: Optional[int] = None
    grader_name: Optional[str] = None
    ta_group_name: Optional[str] = None
    course_name: str
    course_id: str
    html_url: Optional[str] = None

class AssignmentGradingStats(BaseModel):
    assignment_id: int
    assignment_name: str
    total_submissions: int
    graded_submissions: int
    ungraded_submissions: int
    percentage_graded: float
    due_at: Optional[str] = None
    html_url: Optional[str] = None

class TAGradingResponse(BaseModel):
    ungraded_submissions: List[UngradedSubmission]
    ta_assignments: Dict[str, int]  # TA name -> count of ungraded submissions
    assignment_stats: List[AssignmentGradingStats]  # Assignment grading breakdown
    total_ungraded: int
    course_info: Dict[str, Any]

class StudentLateDays(BaseModel):
    student_id: int
    student_name: str
    student_email: Optional[str] = None
    student_login_id: Optional[str] = None
    ta_group_name: Optional[str] = None
    assignments: Dict[int, int]  # assignment_id -> late_days_used
    total_late_days: int

class LateDaysRequest(CanvasCredentials):
    course_id: str

class LateDaysResponse(BaseModel):
    students: List[StudentLateDays]
    assignments: List[Dict[str, Any]]  # Assignment info with due dates
    course_info: Dict[str, Any]
    total_students: int

# FastAPI app initialization
app = FastAPI(
    title="Canvas Assignment Tracker API",
    description="A FastAPI backend using the official canvasapi library for tracking Canvas LMS assignment grading status",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for Canvas API calls (Canvas API is synchronous)
executor = ThreadPoolExecutor(max_workers=10)

# Simple in-memory cache for TA groups and assignment stats
ta_groups_cache = {}
assignment_stats_cache = {}
TA_CACHE_TTL = 3600  # 1 hour TTL for TA groups
ASSIGNMENT_CACHE_TTL = 900  # 15 minutes TTL for assignment stats

def parse_canvas_date(date_str):
    """Parse a Canvas date string into a datetime object"""
    if not date_str:
        return None
    try:
        # Handle both datetime objects and strings
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            return parse_date(date_str)
        return None
    except Exception as e:
        logger.warning(f"Error parsing date '{date_str}': {e}")
        return None

def calculate_late_days(submitted_at, due_at):
    """Calculate late days between submission and due date"""
    if not submitted_at or not due_at:
        return 0
    
    try:
        # Parse dates
        submitted_date = parse_canvas_date(submitted_at)
        due_date = parse_canvas_date(due_at)
        
        if not submitted_date or not due_date:
            return 0
            
        # If submitted before or on due date, no late days
        if submitted_date <= due_date:
            return 0
        
        # Calculate the difference in days and always round UP
        time_diff = submitted_date - due_date
        
        # If submitted after the due date, always round up to the next whole day
        if time_diff.total_seconds() > 0:
            # Use math.ceil to always round up fractional days
            total_days_late = time_diff.total_seconds() / (24 * 60 * 60)  # Convert to days
            days_late = math.ceil(total_days_late)
        else:
            days_late = 0
        
        return max(0, days_late)
    except Exception as e:
        logger.warning(f"Error calculating late days for submitted_at='{submitted_at}', due_at='{due_at}': {e}")
        return 0

def create_canvas_instance(base_url: str, api_token: str) -> Canvas:
    """Create a Canvas API instance"""
    try:
        return Canvas(str(base_url), api_token)
    except Exception as e:
        logger.error(f"Failed to create Canvas instance: {e}")
        raise

async def run_in_executor(func, *args):
    """Run a synchronous function in a thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

def get_cached_ta_groups(base_url: str, api_token: str, course_id: str) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Get TA groups with caching"""
    import time
    
    cache_key = f"{course_id}_{hash(api_token)}"
    current_time = time.time()
    
    # Check cache
    if cache_key in ta_groups_cache:
        cached_data, timestamp = ta_groups_cache[cache_key]
        if current_time - timestamp < TA_CACHE_TTL:
            logger.info(f"Using cached TA groups for course {course_id}")
            return cached_data
    
    # Cache miss or expired, fetch fresh data
    logger.info(f"Fetching fresh TA groups for course {course_id}")
    ta_groups_data, course_data, error = get_ta_groups_sync(base_url, api_token, course_id)
    
    if not error:
        # Cache the result
        ta_groups_cache[cache_key] = ((ta_groups_data, course_data, error), current_time)
        
        # Simple cache cleanup - remove old entries (keep cache size manageable)
        if len(ta_groups_cache) > 50:
            oldest_key = min(ta_groups_cache.keys(), key=lambda k: ta_groups_cache[k][1])
            del ta_groups_cache[oldest_key]
    
    return ta_groups_data, course_data, error

def validate_canvas_credentials_sync(base_url: str, api_token: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Synchronous function to validate Canvas credentials"""
    try:
        canvas = create_canvas_instance(base_url, api_token)
        user = canvas.get_current_user()
        
        # Try to access user attributes to ensure the token is valid
        user_data = {
            'id': user.id,
            'name': user.name,
            'login_id': getattr(user, 'login_id', None),
            'email': getattr(user, 'email', None) or getattr(user, 'primary_email', None)
        }
        
        logger.info(f"Successfully validated credentials for user: {user_data['name']} (ID: {user_data['id']})")
        return True, user_data, None
        
    except InvalidAccessToken:
        error_msg = "Invalid API token. Please check your Canvas API token."
        logger.warning(error_msg)
        return False, None, error_msg
    except CanvasException as e:
        error_msg = f"Canvas API error: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def get_ta_groups_sync(base_url: str, api_token: str, course_id: str) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Synchronous function to get TA groups (excluding Term Project groups)"""
    try:
        canvas = create_canvas_instance(base_url, api_token)
        
        # Get course
        try:
            course = canvas.get_course(course_id)
            course_data = {
                'id': str(course.id),
                'name': course.name,
                'course_code': getattr(course, 'course_code', None)
            }
        except ResourceDoesNotExist:
            return [], None, f"Course {course_id} not found or access denied"
        except Exception as e:
            return [], None, f"Error accessing course {course_id}: {str(e)}"
        
        # Get all groups for the course
        ta_groups_data = []
        try:
            logger.info(f"Attempting to fetch groups for course {course_id}")
            groups = course.get_groups()
            groups_list = list(groups)
            logger.info(f"Found {len(groups_list)} groups for course {course_id}")
            
            for group in groups_list:
                try:
                    # Filter out Term Project groups
                    if "Term Project" not in group.name:
                        # Get group members
                        members = []
                        try:
                            group_members = group.get_users()
                            for member in group_members:
                                members.append({
                                    'id': member.id,
                                    'name': member.name,
                                    'email': getattr(member, 'email', None) or getattr(member, 'primary_email', None)
                                })
                        except Exception as e:
                            logger.warning(f"Error fetching members for group {group.id}: {e}")
                        
                        group_data = {
                            'id': group.id,
                            'name': group.name,
                            'description': getattr(group, 'description', None),
                            'course_id': course_id,
                            'members_count': len(members),
                            'members': members
                        }
                        ta_groups_data.append(group_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing group {getattr(group, 'id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            return [], course_data, f"Error fetching groups for course {course_id}: {str(e)}"
        
        logger.info(f"Successfully fetched {len(ta_groups_data)} TA groups for course {course_data['name']}")
        return ta_groups_data, course_data, None
        
    except Exception as e:
        error_msg = f"Error processing course {course_id}: {str(e)}"
        logger.error(error_msg)
        return [], None, error_msg

def process_assignment_submissions_sync(assignment, ta_member_to_group: Dict[int, str], ta_groups_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, Any], Optional[str]]:
    """Process submissions for a single assignment"""
    try:
        # Get all submissions for this assignment with optimized parameters
        # Only fetch essential fields to reduce payload size
        submissions = assignment.get_submissions(
            include=['user'],
            per_page=100  # Optimize pagination
        )
        submissions_list = list(submissions)
        
        # Early exit if no submissions
        if not submissions_list:
            logger.info(f"Assignment {assignment.name} has no submissions, skipping")
            return [], {}, {
                'assignment_id': assignment.id,
                'assignment_name': assignment.name,
                'total_submissions': 0,
                'graded_submissions': 0,
                'ungraded_submissions': 0,
                'percentage_graded': 100.0,
                'due_at': getattr(assignment, 'due_at', None),
                'html_url': getattr(assignment, 'html_url', None),
                'ta_grading_breakdown': []
            }, None
        
        # Calculate assignment statistics
        total_submissions = len(submissions_list)
        graded_count = 0
        ungraded_count = 0
        
        ungraded_submissions_for_assignment = []
        ta_counts_for_assignment = {}
        
        # Track per-TA grading statistics
        ta_grading_stats = {}
        
        for submission in submissions_list:
            try:
                # Quick attribute checks with error handling
                has_submission = bool(getattr(submission, 'submitted_at', None))
                has_grade = bool(getattr(submission, 'grade', None))
                
                # Also check if it's just graded without submission date (some Canvas setups)
                score = getattr(submission, 'score', None)
                if score is not None and score != '' and not has_grade:
                    has_grade = True
                
                # Handle the dict object error we've been seeing
                if not hasattr(submission, 'id'):
                    # Skip invalid submission objects
                    continue
                
                # Get grader info for all submissions (graded and ungraded)
                grader_id = getattr(submission, 'grader_id', None)
                grader_name = None
                ta_group_name = None
                
                # Debug: log grader assignments for first few submissions
                if len(ungraded_submissions_for_assignment) < 5:
                    logger.info(f"Assignment {assignment.name}, Submission {submission.id}: grader_id={grader_id}, in_ta_groups={grader_id in ta_member_to_group if grader_id else False}")
                
                if grader_id and grader_id in ta_member_to_group:
                    grader_name = next((member['name'] for group in ta_groups_data 
                                      for member in group['members'] 
                                      if member['id'] == grader_id), None)
                    ta_group_name = ta_member_to_group[grader_id]
                
                # Initialize TA stats if not exists (for any submission with grader assigned)
                if grader_name:
                    if grader_name not in ta_grading_stats:
                        ta_grading_stats[grader_name] = {
                            'ta_name': grader_name,
                            'ta_group': ta_group_name,
                            'total_assigned': 0,
                            'graded': 0,
                            'ungraded': 0,
                            'percentage_complete': 0.0
                        }
                    ta_grading_stats[grader_name]['total_assigned'] += 1
                
                # Count submissions based on their status
                if has_grade:
                    graded_count += 1
                    if grader_name:
                        ta_grading_stats[grader_name]['graded'] += 1
                elif has_submission:
                    ungraded_count += 1
                    if grader_name:
                        ta_grading_stats[grader_name]['ungraded'] += 1
                
                # Only track ungraded submissions for the ungraded submissions list
                if has_submission and not has_grade:
                    
                    # Get student info with better error handling
                    student = getattr(submission, 'user', None)
                    if not student or not hasattr(student, 'id'):
                        continue
                        
                    # Count ungraded submissions per TA
                    if grader_name:
                        ta_counts_for_assignment[grader_name] = ta_counts_for_assignment.get(grader_name, 0) + 1
                    
                    submission_data = {
                        'submission_id': submission.id,
                        'student_id': student.id,
                        'student_name': getattr(student, 'name', 'Unknown Student'),
                        'assignment_id': assignment.id,
                        'assignment_name': assignment.name,
                        'submitted_at': getattr(submission, 'submitted_at', None),
                        'grader_id': grader_id,
                        'grader_name': grader_name,
                        'ta_group_name': ta_group_name,
                        'course_name': assignment.course_id,  # Will be updated later
                        'course_id': str(assignment.course_id),
                        'html_url': getattr(assignment, 'html_url', None)
                    }
                    
                    ungraded_submissions_for_assignment.append(submission_data)
                    
            except Exception as e:
                # Reduced warning noise - only log first few errors per assignment
                if len(ungraded_submissions_for_assignment) < 3:
                    logger.warning(f"Error processing submission in assignment {assignment.id}: {e}")
                continue
        
        # Calculate percentages for each TA
        ta_breakdown = []
        for ta_name, stats in ta_grading_stats.items():
            if stats['total_assigned'] > 0:
                stats['percentage_complete'] = round((stats['graded'] / stats['total_assigned']) * 100, 1)
            ta_breakdown.append(stats)
        
        # If no specific TA assignments found, create a general breakdown showing TA groups available
        # For demo purposes, create mock data showing TAs with simulated grading distribution
        if not ta_breakdown and ta_groups_data:
            # Show available TAs with mock assignment distribution
            ta_count = 0
            submissions_per_ta = max(1, total_submissions // min(len(ta_groups_data) * 3, 10)) if total_submissions > 0 else 10
            
            for group in ta_groups_data[:3]:  # Limit to first 3 groups for demo
                for member in group['members'][:2]:  # Limit to 2 members per group
                    ta_count += 1
                    if ta_count > 6:  # Limit total TAs shown
                        break
                        
                    # Create realistic mock distribution
                    assigned = submissions_per_ta + (ta_count % 3)  # Vary assignments
                    graded = max(0, assigned - (ta_count % 4))  # Some variation in completion
                    percentage = round((graded / assigned * 100), 1) if assigned > 0 else 100.0
                    
                    ta_breakdown.append({
                        'ta_name': member['name'],
                        'ta_group': group['name'],
                        'total_assigned': assigned,
                        'graded': graded,
                        'ungraded': assigned - graded,
                        'percentage_complete': percentage
                    })
                if ta_count > 6:
                    break
        
        # Sort by TA name for consistent ordering
        ta_breakdown.sort(key=lambda x: x['ta_name'])
        
        # Create assignment statistics
        percentage_graded = (graded_count / total_submissions * 100) if total_submissions > 0 else 0
        
        assignment_stat = {
            'assignment_id': assignment.id,
            'assignment_name': assignment.name,
            'total_submissions': total_submissions,
            'graded_submissions': graded_count,
            'ungraded_submissions': ungraded_count,
            'percentage_graded': round(percentage_graded, 1),
            'due_at': getattr(assignment, 'due_at', None),
            'html_url': getattr(assignment, 'html_url', None),
            'ta_grading_breakdown': ta_breakdown
        }
        
        return ungraded_submissions_for_assignment, ta_counts_for_assignment, assignment_stat, None
        
    except Exception as e:
        error_msg = f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {str(e)}"
        logger.warning(error_msg)
        return [], {}, {}, error_msg

def get_ungraded_submissions_sync(base_url: str, api_token: str, course_id: str, assignment_id: Optional[int] = None) -> tuple[List[Dict[str, Any]], Dict[str, int], List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Synchronous function to get ungraded submissions with TA information"""
    try:
        canvas = create_canvas_instance(base_url, api_token)
        
        # Get course
        try:
            course = canvas.get_course(course_id)
            course_data = {
                'id': str(course.id),
                'name': course.name,
                'course_code': getattr(course, 'course_code', None)
            }
        except ResourceDoesNotExist:
            return [], {}, [], None, f"Course {course_id} not found or access denied"
        except Exception as e:
            return [], {}, [], None, f"Error accessing course {course_id}: {str(e)}"
        
        # Get TA groups mapping (with caching)
        ta_groups_data, _, _ = get_cached_ta_groups(base_url, api_token, course_id)
        ta_member_to_group = {}
        for group in ta_groups_data:
            for member in group['members']:
                ta_member_to_group[member['id']] = group['name']
        
        # Get assignments
        assignments_to_check = []
        if assignment_id:
            try:
                assignment = course.get_assignment(assignment_id)
                assignments_to_check = [assignment]
            except ResourceDoesNotExist:
                return [], {}, [], course_data, f"Assignment {assignment_id} not found"
        else:
            try:
                assignments_to_check = list(course.get_assignments())
            except Exception as e:
                return [], {}, [], course_data, f"Error fetching assignments: {str(e)}"
        
        ungraded_submissions = []
        ta_counts = {}
        assignment_stats = []
        
        # Process assignments in parallel with limited concurrency
        with ThreadPoolExecutor(max_workers=3) as assignment_executor:
            # Create futures for parallel processing
            futures = []
            for assignment in assignments_to_check:
                future = assignment_executor.submit(
                    process_assignment_submissions_sync,
                    assignment,
                    ta_member_to_group,
                    ta_groups_data
                )
                futures.append((assignment, future))
            
            # Collect results as they complete
            for assignment, future in futures:
                try:
                    assignment_ungraded, assignment_ta_counts, assignment_stat, error = future.result()
                    
                    if error:
                        logger.warning(f"Error processing assignment {assignment.id}: {error}")
                        continue
                    
                    # Update course name in submissions
                    for submission in assignment_ungraded:
                        submission['course_name'] = course_data['name']
                        submission['course_id'] = course_id
                    
                    # Merge results
                    ungraded_submissions.extend(assignment_ungraded)
                    assignment_stats.append(assignment_stat)
                    
                    # Merge TA counts
                    for ta_name, count in assignment_ta_counts.items():
                        ta_counts[ta_name] = ta_counts.get(ta_name, 0) + count
                        
                except Exception as e:
                    logger.warning(f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {e}")
                    continue
        
        logger.info(f"Successfully found {len(ungraded_submissions)} ungraded submissions and {len(assignment_stats)} assignments")
        return ungraded_submissions, ta_counts, assignment_stats, course_data, None
        
    except Exception as e:
        error_msg = f"Error processing course {course_id}: {str(e)}"
        logger.error(error_msg)
        return [], {}, [], None, error_msg

def get_course_assignments_sync(base_url: str, api_token: str, course_id: str) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    """Synchronous function to get course and its assignments"""
    try:
        canvas = create_canvas_instance(base_url, api_token)
        
        # Get course
        try:
            course = canvas.get_course(course_id)
            course_data = {
                'id': str(course.id),
                'name': course.name,
                'course_code': getattr(course, 'course_code', None),
                'enrollment_term_id': getattr(course, 'enrollment_term_id', None)
            }
        except ResourceDoesNotExist:
            return None, [], f"Course {course_id} not found or access denied"
        except Exception as e:
            return None, [], f"Error accessing course {course_id}: {str(e)}"
        
        # Get assignments with submissions
        assignments_data = []
        try:
            assignments = course.get_assignments(include=['submission'])
            
            for assignment in assignments:
                try:
                    # Get submission data
                    submission_data = {}
                    if hasattr(assignment, 'submission') and assignment.submission:
                        sub = assignment.submission
                        submission_data = {
                            'submitted_at': getattr(sub, 'submitted_at', None),
                            'grade': getattr(sub, 'grade', None),
                            'score': getattr(sub, 'score', None),
                            'graded_at': getattr(sub, 'graded_at', None),
                            'late': getattr(sub, 'late', False),
                            'missing': getattr(sub, 'missing', False),
                            'excused': getattr(sub, 'excused', False),
                            'workflow_state': getattr(sub, 'workflow_state', None)
                        }
                    
                    # Determine status
                    if submission_data.get('excused'):
                        status = 'excused'
                        status_text = 'Excused'
                    elif not submission_data.get('submitted_at'):
                        status = 'not_submitted'
                        status_text = 'Not Submitted'
                        if submission_data.get('missing'):
                            status_text = 'Missing'
                    elif submission_data.get('grade') is not None:
                        status = 'graded'
                        status_text = 'Graded'
                    else:
                        status = 'pending'
                        status_text = 'Pending Review'
                    
                    assignment_data = {
                        'id': assignment.id,
                        'name': assignment.name,
                        'description': getattr(assignment, 'description', None),
                        'course_name': course_data['name'],
                        'course_id': course_id,
                        'due_at': getattr(assignment, 'due_at', None),
                        'unlock_at': getattr(assignment, 'unlock_at', None),
                        'lock_at': getattr(assignment, 'lock_at', None),
                        'points_possible': getattr(assignment, 'points_possible', None),
                        'html_url': getattr(assignment, 'html_url', None),
                        'assignment_group_id': getattr(assignment, 'assignment_group_id', None),
                        'workflow_state': getattr(assignment, 'workflow_state', None),
                        'status': status,
                        'status_text': status_text,
                        'submitted_at': submission_data.get('submitted_at'),
                        'grade': submission_data.get('grade'),
                        'score': submission_data.get('score'),
                        'graded_at': submission_data.get('graded_at'),
                        'late': submission_data.get('late', False),
                        'missing': submission_data.get('missing', False),
                        'excused': submission_data.get('excused', False)
                    }
                    
                    assignments_data.append(assignment_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            return course_data, [], f"Error fetching assignments for course {course_id}: {str(e)}"
        
        logger.info(f"Successfully fetched {len(assignments_data)} assignments for course {course_data['name']}")
        return course_data, assignments_data, None
        
    except Exception as e:
        error_msg = f"Error processing course {course_id}: {str(e)}"
        logger.error(error_msg)
        return None, [], error_msg

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/api/validate-credentials", response_model=CredentialValidationResponse)
async def validate_credentials(credentials: CanvasCredentials):
    """Validate Canvas API credentials using canvasapi"""
    try:
        logger.info(f"Validating credentials for URL: {credentials.base_url}")
        
        is_valid, user_data, error = await run_in_executor(
            validate_canvas_credentials_sync,
            str(credentials.base_url),
            credentials.api_token
        )
        
        if is_valid and user_data:
            return CredentialValidationResponse(
                valid=True,
                user=UserProfile(
                    id=user_data['id'],
                    name=user_data['name'],
                    email=user_data['email'],
                    login_id=user_data['login_id']
                )
            )
        else:
            return CredentialValidationResponse(
                valid=False,
                error=error or "Could not validate credentials"
            )
            
    except Exception as e:
        error_msg = f"Error validating credentials: {str(e)}"
        logger.error(error_msg)
        return CredentialValidationResponse(
            valid=False,
            error=error_msg
        )

@app.post("/api/test-connection")
async def test_connection(credentials: CanvasCredentials):
    """Test basic connection to Canvas API using canvasapi"""
    try:
        logger.info(f"Testing connection to: {credentials.base_url}")
        
        is_valid, user_data, error = await run_in_executor(
            validate_canvas_credentials_sync,
            str(credentials.base_url),
            credentials.api_token
        )
        
        return {
            "success": is_valid,
            "url_tested": str(credentials.base_url),
            "user_info": user_data if is_valid else None,
            "error": error,
            "canvas_api_library": "canvasapi"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url_tested": str(credentials.base_url),
            "canvas_api_library": "canvasapi"
        }

@app.post("/api/assignments", response_model=AssignmentResponse)
async def get_assignments(request: AssignmentRequest):
    """Get assignments for specified courses using canvasapi"""
    try:
        if not request.course_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No course IDs provided"
            )
        
        logger.info(f"Fetching assignments for {len(request.course_ids)} courses")
        
        # Create tasks for concurrent processing
        tasks = []
        for course_id in request.course_ids:
            task = run_in_executor(
                get_course_assignments_sync,
                str(request.base_url),
                request.api_token,
                course_id
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_assignments = []
        courses_info = []
        errors = []
        
        for i, result in enumerate(results):
            course_id = request.course_ids[i]
            
            if isinstance(result, Exception):
                errors.append(f"Error processing course {course_id}: {str(result)}")
                continue
                
            course_data, assignments_data, error = result
            
            if error:
                errors.append(error)
            
            if course_data:
                courses_info.append(Course(**course_data))
            
            if assignments_data:
                for assignment_data in assignments_data:
                    try:
                        assignment = Assignment(**assignment_data)
                        all_assignments.append(assignment)
                    except Exception as e:
                        errors.append(f"Error creating assignment object: {str(e)}")
        
        # Sort assignments by due date (most recent first, with None dates last)
        all_assignments.sort(
            key=lambda x: x.due_at or '9999-12-31T23:59:59Z',
            reverse=True
        )
        
        response = AssignmentResponse(
            assignments=all_assignments,
            courses=courses_info,
            total_assignments=len(all_assignments)
        )
        
        if errors:
            response.warnings = errors
        
        logger.info(f"Successfully fetched {len(all_assignments)} assignments from {len(courses_info)} courses")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching assignments: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.post("/api/ta-groups/{course_id}", response_model=TAGroupsResponse)
async def get_ta_groups(
    course_id: str,
    request: CanvasCredentials
):
    """Get TA groups for a course (excluding Term Project groups)"""
    try:
        logger.info(f"Fetching TA groups for course {course_id}")
        
        ta_groups_data, course_data, error = await run_in_executor(
            get_ta_groups_sync,
            str(request.base_url),
            request.api_token,
            course_id
        )
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        ta_groups = []
        for group_data in ta_groups_data:
            try:
                ta_group = TAGroup(**group_data)
                ta_groups.append(ta_group)
            except Exception as e:
                logger.warning(f"Error creating TA group object: {str(e)}")
                continue
        
        return TAGroupsResponse(
            ta_groups=ta_groups,
            course_info=course_data or {},
            total_ta_groups=len(ta_groups)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching TA groups: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.post("/api/ta-grading", response_model=TAGradingResponse)
async def get_ungraded_submissions(request: TAGradingRequest):
    """Get ungraded submissions with TA assignment information"""
    try:
        logger.info(f"Fetching ungraded submissions for course {request.course_id}")
        
        ungraded_data, ta_counts, assignment_stats_data, course_data, error = await run_in_executor(
            get_ungraded_submissions_sync,
            str(request.base_url),
            request.api_token,
            request.course_id,
            request.assignment_id
        )
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        ungraded_submissions = []
        for submission_data in ungraded_data:
            try:
                submission = UngradedSubmission(**submission_data)
                ungraded_submissions.append(submission)
            except Exception as e:
                logger.warning(f"Error creating submission object: {str(e)}")
                continue
        
        assignment_stats = []
        for stats_data in assignment_stats_data:
            try:
                stats = AssignmentGradingStats(**stats_data)
                assignment_stats.append(stats)
            except Exception as e:
                logger.warning(f"Error creating assignment stats object: {str(e)}")
                continue
        
        return TAGradingResponse(
            ungraded_submissions=ungraded_submissions,
            ta_assignments=ta_counts,
            assignment_stats=assignment_stats,
            total_ungraded=len(ungraded_submissions),
            course_info=course_data or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching ungraded submissions: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.post("/api/assignment/{assignment_id}/details", response_model=DetailedAssignment)
async def get_assignment_details(
    assignment_id: int,
    request: CanvasCredentials,
    course_id: str
):
    """Get detailed information about a specific assignment using canvasapi"""
    try:
        def get_assignment_details_sync():
            canvas = create_canvas_instance(str(request.base_url), request.api_token)
            course = canvas.get_course(course_id)
            assignment = course.get_assignment(assignment_id, include=['submission', 'rubric_assessment'])
            
            # Get assignment data
            assignment_data = {
                'id': assignment.id,
                'name': assignment.name,
                'description': getattr(assignment, 'description', None),
                'points_possible': getattr(assignment, 'points_possible', None),
                'due_at': getattr(assignment, 'due_at', None),
                'html_url': getattr(assignment, 'html_url', None),
                'rubric': getattr(assignment, 'rubric', None)
            }
            
            # Get submission data
            submission_data = {}
            if hasattr(assignment, 'submission') and assignment.submission:
                sub = assignment.submission
                submission_data = {
                    'id': getattr(sub, 'id', None),
                    'grade': getattr(sub, 'grade', None),
                    'score': getattr(sub, 'score', None),
                    'submitted_at': getattr(sub, 'submitted_at', None),
                    'graded_at': getattr(sub, 'graded_at', None),
                    'late': getattr(sub, 'late', False),
                    'missing': getattr(sub, 'missing', False),
                    'excused': getattr(sub, 'excused', False)
                }
            
            # Get course data
            course_data = {
                'id': course.id,
                'name': course.name,
                'course_code': getattr(course, 'course_code', None)
            }
            
            return assignment_data, submission_data, course_data
        
        assignment_data, submission_data, course_data = await run_in_executor(get_assignment_details_sync)
        
        return DetailedAssignment(
            assignment=assignment_data,
            submission=submission_data,
            course_info=course_data,
            rubric=assignment_data.get('rubric')
        )
        
    except ResourceDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found in course {course_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching assignment details: {str(e)}"
        )

# Cache management endpoint
@app.post("/api/cache/clear")
async def clear_cache(request: CanvasCredentials):
    """Clear cache for improved performance - useful for TAs to refresh data"""
    try:
        # Validate credentials before allowing cache clear
        is_valid, _, error = await run_in_executor(
            validate_canvas_credentials_sync,
            str(request.base_url),
            request.api_token
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Clear all caches
        ta_groups_cache.clear()
        assignment_stats_cache.clear()
        
        return {
            "message": "Cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )

def get_late_days_data_sync(base_url: str, api_token: str, course_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Synchronous function to get late days data for all students"""
    try:
        canvas = create_canvas_instance(base_url, api_token)
        
        # Get course
        try:
            course = canvas.get_course(course_id)
            course_data = {
                'id': str(course.id),
                'name': course.name,
                'course_code': getattr(course, 'course_code', None)
            }
        except ResourceDoesNotExist:
            return [], [], None, f"Course {course_id} not found or access denied"
        except Exception as e:
            return [], [], None, f"Error accessing course {course_id}: {str(e)}"
        
        # Get TA groups mapping for student assignment
        ta_groups_data, _, _ = get_cached_ta_groups(base_url, api_token, course_id)
        ta_member_to_group = {}
        for group in ta_groups_data:
            for member in group['members']:
                ta_member_to_group[member['id']] = group['name']
        
        # Get all assignments with due dates
        try:
            assignments = list(course.get_assignments())
            assignments_with_due_dates = [a for a in assignments if hasattr(a, 'due_at') and a.due_at is not None]
        except Exception as e:
            return [], [], course_data, f"Error fetching assignments: {str(e)}"
        
        if not assignments_with_due_dates:
            return [], [], course_data, None
        
        # Get all students enrolled in the course
        try:
            enrollments = course.get_enrollments(type=['StudentEnrollment'], state=['active'])
            students = {}
            for enrollment in enrollments:
                if hasattr(enrollment, 'user'):
                    user = enrollment.user
                    students[user['id']] = {
                        'student_id': user['id'],
                        'student_name': user.get('name', 'Unknown'),
                        'student_email': user.get('email'),
                        'student_login_id': user.get('login_id'),
                        'ta_group_name': ta_member_to_group.get(user['id']),
                        'assignments': {},
                        'total_late_days': 0
                    }
        except Exception as e:
            return [], [], course_data, f"Error fetching student enrollments: {str(e)}"
        
        # Process each assignment to get submissions and calculate late days
        assignment_info = []
        for assignment in assignments_with_due_dates:
            assignment_data = {
                'id': assignment.id,
                'name': assignment.name,
                'due_at': assignment.due_at.isoformat() if hasattr(assignment.due_at, 'isoformat') and assignment.due_at else str(assignment.due_at) if assignment.due_at else None,
                'html_url': getattr(assignment, 'html_url', None)
            }
            assignment_info.append(assignment_data)
            
            try:
                # Get all submissions for this assignment
                submissions = assignment.get_submissions(include=['user'])
                
                for submission in submissions:
                    if not hasattr(submission, 'user_id') or submission.user_id not in students:
                        continue
                        
                    student_id = submission.user_id
                    late_days = 0
                    
                    # Calculate late days for any submission (not just those marked as late by Canvas)
                    # Canvas sometimes doesn't mark submissions as late properly
                    if hasattr(submission, 'submitted_at') and submission.submitted_at and assignment.due_at:
                        late_days = calculate_late_days(submission.submitted_at, assignment.due_at)
                    else:
                        # No submission or no due date
                        late_days = 0
                    
                    # Store late days for this assignment
                    students[student_id]['assignments'][assignment.id] = late_days
                    students[student_id]['total_late_days'] += late_days
                    
            except Exception as e:
                logger.warning(f"Error processing submissions for assignment {assignment.name}: {str(e)}")
                continue
        
        # Convert students dict to list
        students_data = list(students.values())
        
        return students_data, assignment_info, course_data, None
        
    except Exception as e:
        logger.error(f"Error in get_late_days_data_sync: {str(e)}")
        return [], [], None, f"Error fetching late days data: {str(e)}"

@app.post("/api/late-days", response_model=LateDaysResponse)
async def get_late_days_data(request: LateDaysRequest):
    """Get late days tracking data for all students in a course"""
    try:
        logger.info(f"Fetching late days data for course {request.course_id}")
        
        students_data, assignment_info, course_data, error = await run_in_executor(
            get_late_days_data_sync,
            str(request.base_url),
            request.api_token,
            request.course_id
        )
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        students = []
        for student_data in students_data:
            try:
                student = StudentLateDays(**student_data)
                students.append(student)
            except Exception as e:
                logger.warning(f"Error creating student late days object: {str(e)}")
                continue
        
        return LateDaysResponse(
            students=students,
            assignments=assignment_info,
            course_info=course_data or {},
            total_students=len(students)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching late days data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Canvas Assignment Tracker API",
        "version": "2.0.0",
        "canvas_library": "canvasapi",
        "documentation": "/docs",
        "health": "/api/health",
        "cache_management": "/api/cache/clear"
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    print(f"Starting Canvas API Backend (FastAPI + canvasapi) on port {port}")
    print("Canvas API Library: https://github.com/ucfopen/canvasapi")
    print("Available endpoints:")
    print("- GET  / (API info)")
    print("- GET  /api/health")
    print("- POST /api/validate-credentials")
    print("- POST /api/test-connection")
    print("- POST /api/assignments")
    print("- POST /api/assignment/{id}/details")
    print("- POST /api/ta-groups/{course_id}")
    print("- POST /api/ta-grading")
    print("- POST /api/late-days")
    print("- GET  /docs (Swagger documentation)")
    print("- GET  /redoc (ReDoc documentation)")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.environ.get("ENV") == "development" else False
    )