"""
Canvas TA Dashboard FastAPI Application
Simple authentication with S3 data storage
"""

import os
import json
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from mangum import Mangum

# Import our simple authentication system
from auth import (
    auth_service,
    user_manager,
    LoginRequest,
    LoginResponse,
    User
)

# Configure loguru - in Lambda, logs go to CloudWatch
# Only write to file if not in Lambda environment (which has read-only filesystem)
if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is None:
    logger.add("logs/app.log", rotation="500 MB", retention="10 days", level="INFO")
else:
    # In Lambda, loguru will output to stdout which goes to CloudWatch Logs
    logger.info("Running in AWS Lambda - logs will go to CloudWatch")

# AWS clients - with error handling for local development
try:
    s3_client = boto3.client('s3')
    aws_available = True
    logger.info("AWS S3 client initialized successfully")
except Exception as e:
    logger.warning(f"AWS S3 client not available: {e}")
    s3_client = None
    aws_available = False

# Environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# FastAPI app
app = FastAPI(
    title="Canvas TA Dashboard API",
    description="Simple Canvas TA Dashboard with S3 data storage and JWT authentication",
    version="4.0.0",
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def validate_environment():
    """Validate required environment variables on startup"""
    required_vars = {
        'S3_BUCKET_NAME': 'S3 bucket for Canvas data storage',
        'JWT_SECRET_KEY': 'JWT signing secret',  # pragma: allowlist secret
        'AWS_REGION': 'AWS region for services',
    }

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing and os.getenv('ENVIRONMENT', 'dev') != 'dev':
        error_msg = "Missing required environment variables:\n"
        for var in missing:
            error_msg += f"  - {var}: {required_vars[var]}\n"
        raise ValueError(error_msg)

# CORS middleware - production configured
# Development CORS - permissive for local testing
DEV_CORS_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:8000',
    'https://ta-dashboard-isye6740-dev.base2ml.com'  # CloudFront dev domain
]

# Production CORS - strict domain whitelist
PROD_CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []

CORS_ORIGINS = DEV_CORS_ORIGINS if ENVIRONMENT == 'dev' else PROD_CORS_ORIGINS

if ENVIRONMENT != 'dev' and not PROD_CORS_ORIGINS:
    raise ValueError("CORS_ORIGINS environment variable required in production")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if ENVIRONMENT == 'dev' else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str
    services: Dict[str, str]

class UserInfo(BaseModel):
    email: str
    name: str
    role: str

class CanvasData(BaseModel):
    course_id: str
    timestamp: str
    assignments: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]
    users: List[Dict[str, Any]]
    enrollments: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]

class SubmissionStatusMetrics(BaseModel):
    on_time: int
    late: int
    missing: int
    on_time_percentage: float
    late_percentage: float
    missing_percentage: float
    total_expected: int

class AssignmentStatusBreakdown(BaseModel):
    assignment_id: str
    assignment_name: str
    due_date: Optional[str]
    metrics: SubmissionStatusMetrics

class TAStatusMetrics(BaseModel):
    ta_name: str
    student_count: int
    on_time: int
    late: int
    missing: int
    on_time_percentage: float
    late_percentage: float
    missing_percentage: float

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """
    Validate JWT token and return user information
    Simple JWT validation without Cognito
    """
    token_payload = auth_service.verify_token(credentials.credentials)

    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInfo(
        email=token_payload.get('email', ''),
        name=token_payload.get('name', ''),
        role=token_payload.get('role', 'ta')
    )

# S3 data access functions
class S3DataManager:
    """
    Manager class for S3 data operations
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a pre-signed URL for S3 object access
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
        Returns:
            Pre-signed URL string or None if error
        """
        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated pre-signed URL for key: {key}")
            return url
        except Exception as e:
            logger.error(f"Error generating pre-signed URL for {key}: {str(e)}")
            return None

    def get_latest_canvas_data(self, course_id: str) -> Optional[CanvasData]:
        """
        Retrieve the latest Canvas data for a course from S3
        Handles both short form (516212) and long form (20960000000516212) course IDs
        """
        # Try both short and long form course IDs
        course_ids_to_try = [course_id]

        # If it's a long form ID, also try extracting the short form (last 6 digits)
        if len(course_id) > 10:
            short_id = course_id[-6:]
            course_ids_to_try.append(short_id)
        # If it's a short form, construct the long form
        elif len(course_id) <= 6:
            long_id = f"20960000000{course_id}"
            course_ids_to_try.append(long_id)

        for cid in course_ids_to_try:
            try:
                key = f"canvas_data/course_{cid}/latest.json"
                response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
                data = json.loads(response['Body'].read())
                logger.info(f"Found course data using ID: {cid}")
                return CanvasData(**data)
            except s3_client.exceptions.NoSuchKey:
                logger.debug(f"No data found for course ID variant: {cid}")
                continue
            except Exception as e:
                logger.error(f"Error retrieving Canvas data for {cid}: {str(e)}")
                continue

        logger.warning(f"No data found for course {course_id} or its variants")
        return None

    def get_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get assignments for a course
        Handles both short form (516212) and long form (20960000000516212) course IDs
        """
        # Try both short and long form course IDs
        course_ids_to_try = [course_id]

        if len(course_id) > 10:
            short_id = course_id[-6:]
            course_ids_to_try.append(short_id)
        elif len(course_id) <= 6:
            long_id = f"20960000000{course_id}"
            course_ids_to_try.append(long_id)

        for cid in course_ids_to_try:
            try:
                key = f"canvas_data/course_{cid}/latest_assignments.json"
                response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
                data = json.loads(response['Body'].read())
                # Handle both list format and dict format
                if isinstance(data, list):
                    return data
                return data.get('assignments', [])
            except s3_client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                logger.error(f"Error retrieving assignments for {cid}: {str(e)}")
                continue

        logger.warning(f"No assignments found for course {course_id} or its variants")
        return []

    def get_submissions(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get submissions for a course
        """
        try:
            key = f"canvas_data/course_{course_id}/latest_submissions.json"
            response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response['Body'].read())
            # Handle both list format and dict format
            if isinstance(data, list):
                return data
            return data.get('submissions', [])
        except Exception as e:
            logger.error(f"Error retrieving submissions: {str(e)}")
            return []

    def get_users(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get users for a course
        """
        try:
            key = f"canvas_data/course_{course_id}/latest_users.json"
            response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response['Body'].read())
            # Handle both list format and dict format
            if isinstance(data, list):
                return data
            return data.get('users', [])
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            return []

    def get_groups(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get groups for a course
        """
        try:
            key = f"canvas_data/course_{course_id}/latest_groups.json"
            response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response['Body'].read())
            # Handle both list format and dict format
            if isinstance(data, list):
                return data
            return data.get('groups', [])
        except Exception as e:
            logger.error(f"Error retrieving groups: {str(e)}")
            return []

# Submission status helper functions
def classify_submission_status(submission: Dict, assignment: Dict) -> str:
    """
    Classify submission as on_time, late, or missing

    Args:
        submission: Submission data from Canvas
        assignment: Assignment data from Canvas

    Returns:
        Status string: 'on_time', 'late', or 'missing'
    """
    workflow_state = submission.get('workflow_state', '')
    submitted_at = submission.get('submitted_at')
    due_at = assignment.get('due_at')
    late = submission.get('late', False)

    # Missing: not submitted or pending review
    if workflow_state in ['unsubmitted', 'pending_review'] or not submitted_at:
        return 'missing'

    # Late: explicit late flag or submitted after due date
    if late:
        return 'late'

    if submitted_at and due_at:
        try:
            from dateutil import parser
            submitted_datetime = parser.parse(submitted_at)
            due_datetime = parser.parse(due_at)
            if submitted_datetime > due_datetime:
                return 'late'
        except Exception as e:
            logger.debug(f"Error parsing dates: {e}")

    return 'on_time'

def calculate_submission_status_metrics(
    assignments: List[Dict],
    submissions: List[Dict],
    users: List[Dict],
    groups: List[Dict],
    assignment_filter: Optional[str] = None,
    ta_group_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive submission status metrics

    Args:
        assignments: List of assignment data
        submissions: List of submission data
        users: List of user data
        groups: List of group data
        assignment_filter: Optional assignment ID to filter by
        ta_group_filter: Optional TA group name to filter by

    Returns:
        Dict with overall_metrics, by_assignment, and by_ta breakdowns
    """
    # Filter assignments if specified
    if assignment_filter and assignment_filter != 'all':
        assignments = [a for a in assignments if str(a.get('id')) == assignment_filter]

    # Pre-compute user to TA group mapping - O(Users)
    user_to_ta_group = {}
    for group in groups:
        group_name = group.get('name')
        for member in group.get('members', []):
            # Handle both 'id' and 'user_id' formats
            user_id = member.get('user_id') or member.get('id')
            if user_id:
                user_to_ta_group[user_id] = group_name

    # Filter users by TA group if specified
    if ta_group_filter and ta_group_filter != 'all':
        users = [u for u in users if user_to_ta_group.get(u.get('id')) == ta_group_filter]

    # Create submission lookup by user and assignment - O(Submissions)
    submission_lookup = {}
    for sub in submissions:
        key = (sub.get('user_id'), sub.get('assignment_id'))
        submission_lookup[key] = sub

    # Initialize counters
    overall_on_time = 0
    overall_late = 0
    overall_missing = 0

    # Metrics by assignment
    assignment_metrics = {}

    # Metrics by TA - Initialize with all groups
    ta_metrics = {}
    for group in groups:
        group_name = group.get('name')
        if ta_group_filter and ta_group_filter != 'all' and group_name != ta_group_filter:
            continue

        ta_metrics[group_name] = {
            'ta_name': group_name,
            'student_count': 0, # Will be calculated based on active students
            'on_time': 0,
            'late': 0,
            'missing': 0
        }

    # Calculate metrics - O(Assignments * Users)
    # This is the dominant term, but much faster than previous O(A*U*G*M)
    for assignment in assignments:
        assignment_id = assignment.get('id')
        assignment_name = assignment.get('name', 'Unnamed Assignment')
        due_date = assignment.get('due_at')

        # Initialize assignment metrics
        assignment_on_time = 0
        assignment_late = 0
        assignment_missing = 0

        for user in users:
            user_id = user.get('id')
            key = (user_id, assignment_id)

            # Get submission or create missing entry - O(1)
            submission = submission_lookup.get(key, {
                'workflow_state': 'unsubmitted',
                'user_id': user_id,
                'assignment_id': assignment_id
            })

            # Classify status
            status = classify_submission_status(submission, assignment)

            # Update counters
            if status == 'on_time':
                overall_on_time += 1
                assignment_on_time += 1
            elif status == 'late':
                overall_late += 1
                assignment_late += 1
            else:  # missing
                overall_missing += 1
                assignment_missing += 1

            # Update TA metrics - O(1) lookup
            user_ta_group = user_to_ta_group.get(user_id)
            if user_ta_group and user_ta_group in ta_metrics:
                # We only increment student count once per user, but here we are inside assignment loop
                # So we don't increment student_count here to avoid multiplication
                # Instead we just update status counts
                if status == 'on_time':
                    ta_metrics[user_ta_group]['on_time'] += 1
                elif status == 'late':
                    ta_metrics[user_ta_group]['late'] += 1
                else:
                    ta_metrics[user_ta_group]['missing'] += 1

        # Calculate assignment percentages
        total_assignment_submissions = len(users)
        assignment_metrics[str(assignment_id)] = {
            'assignment_id': str(assignment_id),
            'assignment_name': assignment_name,
            'due_date': due_date,
            'metrics': {
                'on_time': assignment_on_time,
                'late': assignment_late,
                'missing': assignment_missing,
                'on_time_percentage': (assignment_on_time / total_assignment_submissions * 100) if total_assignment_submissions > 0 else 0,
                'late_percentage': (assignment_late / total_assignment_submissions * 100) if total_assignment_submissions > 0 else 0,
                'missing_percentage': (assignment_missing / total_assignment_submissions * 100) if total_assignment_submissions > 0 else 0,
                'total_expected': total_assignment_submissions
            }
        }

    # Fix student counts in TA metrics
    # We need to count unique students per TA group
    for user in users:
        user_id = user.get('id')
        user_ta_group = user_to_ta_group.get(user_id)
        if user_ta_group and user_ta_group in ta_metrics:
            ta_metrics[user_ta_group]['student_count'] += 1

    # Calculate overall percentages
    total_expected = len(assignments) * len(users)

    # Calculate TA percentages
    for ta_name, metrics in ta_metrics.items():
        total = metrics['on_time'] + metrics['late'] + metrics['missing']
        if total > 0:
            metrics['on_time_percentage'] = metrics['on_time'] / total * 100
            metrics['late_percentage'] = metrics['late'] / total * 100
            metrics['missing_percentage'] = metrics['missing'] / total * 100
        else:
            metrics['on_time_percentage'] = 0
            metrics['late_percentage'] = 0
            metrics['missing_percentage'] = 0

    return {
        'overall_metrics': {
            'on_time': overall_on_time,
            'late': overall_late,
            'missing': overall_missing,
            'on_time_percentage': (overall_on_time / total_expected * 100) if total_expected > 0 else 0,
            'late_percentage': (overall_late / total_expected * 100) if total_expected > 0 else 0,
            'missing_percentage': (overall_missing / total_expected * 100) if total_expected > 0 else 0,
            'total_expected': total_expected
        },
        'by_assignment': list(assignment_metrics.values()),
        'by_ta': list(ta_metrics.values())
    }

# Initialize S3 data manager
s3_manager = S3DataManager(S3_BUCKET_NAME) if S3_BUCKET_NAME and s3_client else None

# Mock data loader for local development
def load_mock_data() -> Dict[str, Any]:
    """Load mock Canvas data from JSON file for local testing"""
    mock_file_path = Path("mock_canvas_data.json")
    if mock_file_path.exists():
        try:
            with open(mock_file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mock data: {e}")
            return {}
    return {}

# Load mock data if available
MOCK_DATA = load_mock_data()


# Authentication endpoints
@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    """
    Login endpoint - validates email/password and returns JWT token
    """
    logger.info(f"Login attempt for user: {login_request.email}")
    return auth_service.login(login_request)


@app.post("/api/auth/logout")
async def logout(user: UserInfo = Depends(get_current_user)):
    """
    Logout endpoint - currently just validates token
    Client should discard the JWT token
    """
    logger.info(f"User logged out: {user.email}")
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me")
async def get_current_user_info(user: UserInfo = Depends(get_current_user)):
    """Get current user information from JWT token"""
    return user


# Health check endpoint
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with service status"""
    services = {
        "s3": "not_configured",
        "authentication": "simple_jwt",
        "aws_client": "available" if aws_available else "unavailable"
    }

    # Check S3 status
    if S3_BUCKET_NAME and s3_client:
        services["s3"] = "configured"
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            services["s3"] = "healthy"
        except Exception as e:
            logger.warning(f"S3 health check failed: {e}")
            services["s3"] = "unhealthy"

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="4.0.0",
        environment=ENVIRONMENT,
        services=services
    )

# Simple health check for Docker/ECS
@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint for Docker/ECS health checks"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Canvas data endpoints
@app.get("/api/canvas/courses")
async def get_available_courses(
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get list of available courses from S3 data or return demo data for local testing
    """
    if not s3_manager:
        # Return demo/mock courses for local development
        logger.info("S3 not configured, returning demo courses for local testing")
        return {
            'courses': [
                {
                    'id': 'demo-001',
                    'name': 'Demo Course - Introduction to Computer Science',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                },
                {
                    'id': 'demo-002',
                    'name': 'Demo Course - Data Structures and Algorithms',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
            ],
            'total': 2,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'demo_mode': True
        }

    try:
        # List all course data in S3 bucket
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix="canvas_data/course_",
            Delimiter="/"
        )

        courses = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                course_prefix = prefix['Prefix']
                # Extract course ID from prefix like "canvas_data/course_12345/"
                course_id = course_prefix.split('course_')[1].rstrip('/')

                # Try to get course info from latest data
                try:
                    course_data = s3_manager.get_latest_canvas_data(course_id)
                    if course_data:
                        courses.append({
                            'id': course_id,
                            'name': f"Course {course_id}",  # Could be enhanced with actual course name
                            'last_updated': course_data.timestamp
                        })
                except Exception as e:
                    logger.warning(f"Could not load data for course {course_id}: {e}")
                    courses.append({
                        'id': course_id,
                        'name': f"Course {course_id}",
                        'last_updated': None
                    })

        return {
            'courses': courses,
            'total': len(courses),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load courses: {str(e)}"
        )

@app.get("/api/canvas/data/{course_id}")
async def get_canvas_data(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get complete Canvas data for a course (from S3 or mock data)
    """
    if not s3_manager:
        # Return mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Returning mock data for course {course_id}")
            return MOCK_DATA[course_id]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data found for course {course_id}"
        )

    data = s3_manager.get_latest_canvas_data(course_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for course {course_id}"
        )

    return data.dict()

@app.get("/api/canvas/assignments/{course_id}")
async def get_assignments(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get assignments for a course - returns S3 pre-signed URL or mock data
    """
    if not s3_manager:
        # Return mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Returning mock assignments for course {course_id}")
            return {"assignments": MOCK_DATA[course_id]["assignments"]}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data found for course {course_id}"
        )

    # Try both short and long form course IDs
    course_ids_to_try = [course_id]
    if len(course_id) > 10:
        course_ids_to_try.append(course_id[-6:])
    elif len(course_id) <= 6:
        course_ids_to_try.append(f"20960000000{course_id}")

    for cid in course_ids_to_try:
        key = f"canvas_data/course_{cid}/latest.json"
        url = s3_manager.generate_presigned_url(key, expiration=3600)
        if url:
            return {"data_url": url, "course_id": cid, "data_type": "assignments"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No data found for course {course_id}"
    )

@app.get("/api/canvas/submissions/{course_id}")
async def get_submissions(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get submissions for a course - returns S3 pre-signed URL or mock data
    """
    if not s3_manager:
        # Return mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Returning mock submissions for course {course_id}")
            return {"submissions": MOCK_DATA[course_id]["submissions"]}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data found for course {course_id}"
        )

    # Try both short and long form course IDs
    course_ids_to_try = [course_id]
    if len(course_id) > 10:
        course_ids_to_try.append(course_id[-6:])
    elif len(course_id) <= 6:
        course_ids_to_try.append(f"20960000000{course_id}")

    for cid in course_ids_to_try:
        key = f"canvas_data/course_{cid}/latest.json"
        url = s3_manager.generate_presigned_url(key, expiration=3600)
        if url:
            return {"data_url": url, "course_id": cid, "data_type": "submissions"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No data found for course {course_id}"
    )

@app.get("/api/canvas/users/{course_id}")
async def get_users(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get users for a course - returns S3 pre-signed URL or mock data
    """
    if not s3_manager:
        # Return mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Returning mock users for course {course_id}")
            return {"users": MOCK_DATA[course_id]["users"]}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data found for course {course_id}"
        )

    # Try both short and long form course IDs
    course_ids_to_try = [course_id]
    if len(course_id) > 10:
        course_ids_to_try.append(course_id[-6:])
    elif len(course_id) <= 6:
        course_ids_to_try.append(f"20960000000{course_id}")

    for cid in course_ids_to_try:
        key = f"canvas_data/course_{cid}/latest.json"
        url = s3_manager.generate_presigned_url(key, expiration=3600)
        if url:
            return {"data_url": url, "course_id": cid, "data_type": "users"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No data found for course {course_id}"
    )

@app.get("/api/canvas/groups/{course_id}")
async def get_groups(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get groups for a course - returns S3 pre-signed URL or mock data
    """
    if not s3_manager:
        # Return mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Returning mock groups for course {course_id}")
            return {"groups": MOCK_DATA[course_id]["groups"]}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data found for course {course_id}"
        )

    # Try both short and long form course IDs
    course_ids_to_try = [course_id]
    if len(course_id) > 10:
        course_ids_to_try.append(course_id[-6:])
    elif len(course_id) <= 6:
        course_ids_to_try.append(f"20960000000{course_id}")

    for cid in course_ids_to_try:
        key = f"canvas_data/course_{cid}/latest.json"
        url = s3_manager.generate_presigned_url(key, expiration=3600)
        if url:
            return {"data_url": url, "course_id": cid, "data_type": "groups"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No data found for course {course_id}"
    )

# Dashboard specific endpoints
@app.get("/api/dashboard/submission-status/{course_id}")
async def get_submission_status_metrics(
    course_id: str,
    assignment_id: Optional[str] = None,
    ta_group: Optional[str] = None,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get submission status metrics (on_time, late, missing)

    Query Parameters:
        assignment_id: Optional assignment ID to filter by
        ta_group: Optional TA group name to filter by

    Returns:
        Dict with overall_metrics, by_assignment, and by_ta breakdowns
    """
    if not s3_manager:
        # Use mock data for local testing
        if course_id in MOCK_DATA:
            logger.info(f"Calculating metrics from mock data for course {course_id}")
            course_data = MOCK_DATA[course_id]
            assignments = course_data.get("assignments", [])
            submissions = course_data.get("submissions", [])
            users = course_data.get("users", [])
            groups = course_data.get("groups", [])

            # Calculate metrics
            metrics = calculate_submission_status_metrics(
                assignments=assignments,
                submissions=submissions,
                users=users,
                groups=groups,
                assignment_filter=assignment_id,
                ta_group_filter=ta_group
            )
            return metrics
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No mock data found for course {course_id}"
            )

    try:
        # Get all data from S3
        assignments = s3_manager.get_assignments(course_id)
        submissions = s3_manager.get_submissions(course_id)
        users = s3_manager.get_users(course_id)
        groups = s3_manager.get_groups(course_id)

        # Calculate metrics
        metrics = calculate_submission_status_metrics(
            assignments=assignments,
            submissions=submissions,
            users=users,
            groups=groups,
            assignment_filter=assignment_id,
            ta_group_filter=ta_group
        )

        return metrics

    except Exception as e:
        logger.error(f"Error calculating submission status metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating metrics: {str(e)}"
        )

@app.get("/api/dashboard/ta-grading/{course_id}")
async def get_ta_grading_data(
    course_id: str,
    user: UserInfo = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get TA grading dashboard data
    """
    if not s3_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 not configured"
        )

    # Get all data
    assignments = s3_manager.get_assignments(course_id)
    submissions = s3_manager.get_submissions(course_id)
    users = s3_manager.get_users(course_id)

    # Process data for TA dashboard
    ta_grading_data = process_ta_grading_data(assignments, submissions, users)

    return ta_grading_data

def process_ta_grading_data(assignments, submissions, users):
    """
    Process Canvas data for TA grading dashboard
    """
    # Create lookup dictionaries
    assignment_dict = {str(a['id']): a for a in assignments}
    user_dict = {str(u['id']): u for u in users}

    # Process submissions
    ungraded_submissions = []
    ta_workload = {}

    for submission in submissions:
        # Skip if submission is already graded
        if submission.get('workflow_state') == 'graded':
            continue

        assignment_id = str(submission.get('assignment_id', ''))
        user_id = str(submission.get('user_id', ''))

        assignment = assignment_dict.get(assignment_id)
        student = user_dict.get(user_id)

        if assignment and student:
            ungraded_item = {
                'assignment_id': assignment_id,
                'assignment_name': assignment['name'],
                'student_id': user_id,
                'student_name': student['name'],
                'submitted_at': submission.get('submitted_at'),
                'due_date': assignment.get('due_at'),
                'submission_type': assignment.get('submission_types', []),
                'points_possible': assignment.get('points_possible'),
            }

            ungraded_submissions.append(ungraded_item)

            # Track TA workload (simplified - would need actual TA assignments)
            ta_name = "Unassigned"  # Would get from actual TA group data
            if ta_name not in ta_workload:
                ta_workload[ta_name] = 0
            ta_workload[ta_name] += 1

    return {
        'ungraded_submissions': ungraded_submissions,
        'ta_workload': ta_workload,
        'total_ungraded': len(ungraded_submissions),
        'last_updated': datetime.now(timezone.utc).isoformat()
    }

# Data sync endpoint
@app.post("/api/canvas/sync")
async def trigger_data_sync(user: UserInfo = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Trigger manual Canvas data sync
    Invokes the data fetcher Lambda function to refresh Canvas data
    """
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    data_fetcher_function = f'canvas-ta-dashboard-canvas-data-fetcher-{ENVIRONMENT}'

    try:
        logger.info(f"User {user.email} triggered manual data sync")

        # Invoke data fetcher Lambda asynchronously
        response = lambda_client.invoke(
            FunctionName=data_fetcher_function,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({
                'triggered_by': user.email,
                'trigger_type': 'manual',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        )

        return {
            'status': 'success',
            'message': 'Data sync triggered successfully',
            'triggered_by': user.email,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'lambda_status_code': response['StatusCode']
        }

    except Exception as e:
        logger.error(f"Error triggering data sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger data sync: {str(e)}"
        )

# User management endpoints
@app.get("/api/user/profile")
async def get_user_profile(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    Get current user profile
    """
    return user

@app.get("/api/config")
async def get_app_config() -> Dict[str, Any]:
    """
    Get application configuration for frontend
    """
    return {
        'cognito_user_pool_id': COGNITO_USER_POOL_ID,
        'cognito_user_pool_client_id': COGNITO_USER_POOL_CLIENT_ID,
        'aws_region': AWS_REGION,
        'environment': ENVIRONMENT,
        'version': '3.0.0',
        's3_bucket_name': S3_BUCKET_NAME,
        'data_refresh_interval': '15 minutes'
    }

# Canvas courses endpoint without authentication for initial setup
@app.get("/api/courses")
async def get_courses_public() -> Dict[str, Any]:
    """
    Public endpoint to get available courses (for initial setup)
    """
    if not s3_manager:
        return {
            'courses': [],
            'total': 0,
            'message': 'S3 not configured - data pipeline not yet active'
        }

    try:
        # List all course data in S3 bucket
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix="canvas_data/course_",
            Delimiter="/"
        )

        courses = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                course_prefix = prefix['Prefix']
                course_id = course_prefix.split('course_')[1].rstrip('/')
                courses.append({
                    'id': course_id,
                    'name': f"Course {course_id}",
                    'status': 'available'
                })

        return {
            'courses': courses,
            'total': len(courses),
            'message': f'Found {len(courses)} courses with Canvas data'
        }

    except Exception as e:
        logger.error(f"Error listing courses: {e}")
        return {
            'courses': [],
            'total': 0,
            'message': f'Error accessing S3 data: {str(e)}'
        }

# Mount static files for React frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Mounted static files from {static_dir}")
else:
    logger.warning(f"Static directory not found at {static_dir}")

# AWS Lambda handler
handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
