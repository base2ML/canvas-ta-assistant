"""
TA processing services for Canvas assignment and grading operations.
Extracted from ta_management.py to follow Single Responsibility Principle.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from dependencies import SettingsDep
from models import TAGradingRequest, CanvasCredentials

# Configure loguru for this module
logger = logger.bind(module="ta_processing")


async def get_canvas_from_ta_request(
    request: TAGradingRequest, settings: SettingsDep
) -> Any:
    """Convert TAGradingRequest to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


async def get_canvas_from_credentials(
    request: CanvasCredentials, settings: SettingsDep
) -> Any:
    """Convert CanvasCredentials to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


def process_assignment_submissions_sync(
    assignment: Any,
    student_to_ta_group: Dict[int, str],
    ta_groups_data: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, Any], Optional[str]]:
    """
    Process assignment submissions using modern pandas best practices.

    Following pandas best practices:
    - Use efficient vectorized operations
    - Proper json_normalize usage for nested data
    - Modern DataFrame construction and manipulation
    - Efficient groupby operations
    - Proper nullable dtype handling

    Returns:
        (ungraded_rows, ta_counts, assignment_stats, error_msg)
    """
    try:
        # Get all submissions for this assignment (including unsubmitted)
        submissions = assignment.get_submissions(
            include=["user"],
            per_page=100,
        )

        # Use pandas json_normalize for proper Canvas API object handling
        submission_df = pd.concat(
            [
                pd.json_normalize(
                    [vars(submission) for submission in submissions]
                )
            ],
            ignore_index=True
        )
        submission_df = submission_df.loc[:, ~submission_df.columns.str.startswith("turnitin")]
        
        # Debug: Log submission count and workflow states to verify fix
        logger.info(
            "Assignment {assignment_id} has {count} total submissions",
            assignment_id=getattr(assignment, "id", "unknown"),
            count=len(submission_df),
        )
        if not submission_df.empty:
            workflow_states = submission_df['workflow_state'].value_counts().to_dict()
            user_count = submission_df['user.id'].notna().sum()
            
            # Debug: Show actual DataFrame columns to understand structure
            logger.info(
                "DataFrame columns: {columns}",
                columns=list(submission_df.columns),
            )
            
            logger.info(
                "Workflow states distribution: {states}, Submissions with users: {user_count}",
                states=workflow_states,
                user_count=user_count,
            )

        if submission_df.empty:
            # Return early with empty stats
            stats: Dict[str, Any] = {
                "assignment_id": getattr(assignment, "id", None),
                "assignment_name": getattr(assignment, "name", "Unknown"),
                "total_submissions": 0,
                "graded_submissions": 0,
                "ungraded_submissions": 0,
                "percentage_graded": 100.0,
                "due_at": getattr(assignment, "due_at", None),
                "html_url": getattr(assignment, "html_url", None),
                "ta_grading_breakdown": [],
            }
            return [], {}, stats, None

        # Rename columns to match expected format
        df = submission_df.rename(columns={
            'id': 'submission_id',
            'user.id': 'student_id',
            'user.name': 'student_name'
        })

        # Convert to nullable dtypes for better handling of missing data
        df = df.convert_dtypes()

        # Ensure student_id is integer type for consistent mapping
        if 'student_id' in df.columns:
            df["student_id"] = pd.to_numeric(df["student_id"], errors="coerce").astype(int)

        # Create derived columns using vectorized operations
        # Convert numeric columns properly
        df["score_numeric"] = pd.to_numeric(df["score"], errors="coerce")

        # Use the provided student-to-TA-group mapping from function parameter
        # Create TA group mapping series for efficient lookup based on student assignment
        ta_group_series = pd.Series(student_to_ta_group, name="ta_group")

        # Debug: Log mapping information
        logger.debug(
            "Processing assignment {assignment_id}: {total_students} students in mapping, {total_submissions} submissions",
            assignment_id=getattr(assignment, "id", "unknown"),
            total_students=len(student_to_ta_group),
            total_submissions=len(df),
        )

        # Add derived columns using efficient vectorized operations
        df["has_submission"] = df["submitted_at"].notna()
        df["has_grade"] = (
            df["grade"].notna() & (df["grade"].astype("string") != "")
        ) | df["score_numeric"].notna()

        # Map students to their TA groups (students are group members)
        df["ta_group"] = df["student_id"].map(ta_group_series)
        df["grading_ta"] = df["ta_group"].fillna("Unassigned")

        # Debug: Check mapping success and identify mismatches
        mapped_students = df["ta_group"].notna().sum()
        unmapped_students = df[df["ta_group"].isna()]
        
        logger.info(
            "TA group mapping results: {mapped}/{total} students mapped to TA groups",
            mapped=mapped_students,
            total=len(df),
        )
        
        # Log unmapped student IDs for debugging
        if not unmapped_students.empty:
            unmapped_ids = unmapped_students["student_id"].tolist()
            logger.warning(
                "Unmapped student IDs: {unmapped_ids} not found in TA group members",
                unmapped_ids=unmapped_ids,
            )
            
        # Log sample of mapped vs available student IDs for debugging
        submission_student_ids = set(df["student_id"].dropna().astype(int).tolist())
        ta_group_student_ids = set(student_to_ta_group.keys())
        
        logger.info(
            "Student ID analysis: {submission_count} from submissions, {ta_count} in TA groups",
            submission_count=len(submission_student_ids),
            ta_count=len(ta_group_student_ids),
        )
        logger.debug(
            "Submission student IDs: {submission_ids}",
            submission_ids=sorted(list(submission_student_ids))[:10],  # First 10 for brevity
        )
        logger.debug(
            "TA group student IDs: {ta_ids}",
            ta_ids=sorted(list(ta_group_student_ids))[:10],  # First 10 for brevity
        )

        # Calculate assignment totals using efficient aggregation
        total_submissions = len(df)
        graded_submissions = int(df["has_grade"].sum())
        ungraded_submissions = int((df["has_submission"] & ~df["has_grade"]).sum())
        percentage_graded = (
            round((graded_submissions / total_submissions) * 100, 1)
            if total_submissions > 0
            else 0.0
        )

        # Create TA grading breakdown using modern groupby operations
        ta_breakdown = []
        
        # Debug: Show DataFrame structure for troubleshooting mapping issues
        logger.info(
            "DataFrame analysis for assignment {assignment_id}:",
            assignment_id=getattr(assignment, "id", "unknown"),
        )
        logger.info(
            "Student IDs in submissions: {submission_ids}",
            submission_ids=sorted(df["student_id"].dropna().astype(int).tolist()),
        )
        logger.info(
            "Student IDs in TA groups: {ta_group_ids}",
            ta_group_ids=sorted(list(student_to_ta_group.keys())),
        )
        
        if df["ta_group"].notna().any():
            # Group by TA and calculate statistics
            ta_grouped = df[df["ta_group"].notna()].groupby("ta_group", observed=True)

            # Use agg for multiple aggregations at once (more efficient)
            ta_stats = ta_grouped.agg(
                {
                    "has_grade": ["count", "sum"],
                    "has_submission": "sum",
                    "late": "sum",  # Include late submissions count
                }
            ).round(1)

            # Flatten column names properly
            ta_stats.columns = [
                "total_assigned",
                "graded",
                "submitted",
                "submitted_late",
            ]
            ta_stats = ta_stats.reset_index()

            # Calculate derived metrics
            ta_stats["ungraded"] = ta_stats["submitted"] - ta_stats["graded"]
            ta_stats["percentage_complete"] = (
                (ta_stats["graded"] / ta_stats["total_assigned"]) * 100
            ).round(1)

            # Calculate submission timing breakdown
            ta_stats["submitted_on_time"] = (
                ta_stats["submitted"] - ta_stats["submitted_late"]
            )
            ta_stats["not_submitted"] = (
                ta_stats["total_assigned"] - ta_stats["submitted"]
            )

            # Create breakdown records with proper column names and safe type conversion
            for _, row in ta_stats.iterrows():
                ta_breakdown.append(
                    {
                        "ta_name": str(row["ta_group"]),
                        "ta_group": str(row["ta_group"]),
                        "total_assigned": (
                            int(row["total_assigned"])
                            if pd.notna(row["total_assigned"])
                            else 0
                        ),
                        "graded": int(row["graded"]) if pd.notna(row["graded"]) else 0,
                        "ungraded": (
                            int(row["ungraded"]) if pd.notna(row["ungraded"]) else 0
                        ),
                        "percentage_complete": (
                            float(row["percentage_complete"])
                            if pd.notna(row["percentage_complete"])
                            else 0.0
                        ),
                        "submitted_on_time": (
                            int(row["submitted_on_time"])
                            if pd.notna(row["submitted_on_time"])
                            else 0
                        ),
                        "submitted_late": (
                            int(row["submitted_late"])
                            if pd.notna(row["submitted_late"])
                            else 0
                        ),
                        "not_submitted": (
                            int(row["not_submitted"])
                            if pd.notna(row["not_submitted"])
                            else 0
                        ),
                    }
                )

        # Ensure all TA groups are represented, even if they have no assigned students
        ta_groups_in_breakdown = {ta["ta_group"] for ta in ta_breakdown}
        for group in ta_groups_data:
            group_name = group.get("name", "Unknown TA Group")
            if group_name not in ta_groups_in_breakdown:
                ta_breakdown.append(
                    {
                        "ta_name": group_name,
                        "ta_group": group_name,
                        "total_assigned": 0,
                        "graded": 0,
                        "ungraded": 0,
                        "percentage_complete": 0.0,
                        "submitted_on_time": 0,
                        "submitted_late": 0,
                        "not_submitted": 0,
                    }
                )

        # Log TA group assignment status
        logger.debug(
            "Assignment {assignment_id} TA assignments: {students_mapped}/{total_submissions} students mapped to TA groups",
            assignment_id=getattr(assignment, "id", "unknown"),
            students_mapped=(
                df["ta_group"].notna().sum() if "ta_group" in df.columns else 0
            ),
            total_submissions=total_submissions,
        )

        # Create ungraded submissions list using efficient DataFrame operations
        group_to_members = {
            g["name"]: [m["name"] for m in g.get("members", [])] for g in ta_groups_data
        }

        # Filter ungraded submissions efficiently
        ungraded_mask = df["has_submission"] & ~df["has_grade"]
        ungraded_df = df[ungraded_mask].copy()

        # Add TA members information
        ungraded_df["ta_members"] = (
            ungraded_df["ta_group"].map(group_to_members).fillna([].copy)
        )

        # Convert to records efficiently using to_dict
        ungraded_rows = []
        if not ungraded_df.empty:
            for _, row in ungraded_df.iterrows():
                try:
                    ungraded_rows.append(
                        {
                            "submission_id": (
                                int(row["submission_id"])
                                if pd.notna(row["submission_id"])
                                else 0
                            ),
                            "student_name": (
                                str(row["student_name"])
                                if pd.notna(row["student_name"])
                                else "Unknown Student"
                            ),
                            "student_id": (
                                str(row["student_id"])
                                if pd.notna(row["student_id"])
                                else ""
                            ),
                            "assignment_name": getattr(
                                assignment, "name", "Unknown Assignment"
                            ),
                            "assignment_id": getattr(assignment, "id", None),
                            "course_name": str(
                                getattr(assignment, "course_id", "")
                            ),  # Will be overwritten upstream
                            "course_id": str(getattr(assignment, "course_id", "")),
                            "submitted_at": (
                                row["submitted_at"]
                                if pd.notna(row["submitted_at"])
                                else None
                            ),
                            "late": (
                                bool(row["late"]) if pd.notna(row["late"]) else False
                            ),
                            "grader_name": (
                                row["ta_group"] if pd.notna(row["ta_group"]) else None
                            ),
                            "ta_group_name": (
                                row["ta_group"] if pd.notna(row["ta_group"]) else None
                            ),
                            "ta_members": (
                                row["ta_members"]
                                if isinstance(row["ta_members"], list)
                                else []
                            ),
                            "html_url": getattr(assignment, "html_url", None),
                        }
                    )
                except Exception as e:
                    logger.error(
                        "Error creating ungraded submission record: {error}",
                        error=str(e),
                    )
                    continue

        # Calculate TA counts for ungraded submissions
        ta_counts = {}
        if not ungraded_df.empty and "ta_group" in ungraded_df.columns:
            ta_counts_series = ungraded_df["ta_group"].value_counts(dropna=True)
            ta_counts = ta_counts_series.to_dict()

        # Create assignment statistics with TA breakdown
        assignment_stat: Dict[str, Any] = {
            "assignment_id": getattr(assignment, "id", None),
            "assignment_name": getattr(assignment, "name", "Unknown Assignment"),
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
            "ungraded_submissions": ungraded_submissions,
            "percentage_graded": percentage_graded,
            "due_at": getattr(assignment, "due_at", None),
            "html_url": getattr(assignment, "html_url", None),
            "ta_grading_breakdown": ta_breakdown,
        }

        # Log final TA breakdown for debugging
        logger.debug(
            "Assignment {assignment_id} final TA breakdown: {breakdown_count} TAs, breakdown={ta_breakdown}",
            assignment_id=getattr(assignment, "id", "unknown"),
            breakdown_count=len(ta_breakdown),
            ta_breakdown=ta_breakdown,
        )

        return ungraded_rows, ta_counts, assignment_stat, None

    except Exception as e:
        logger.exception(
            "Error processing assignment {assignment_id}: {error}",
            assignment_id=getattr(assignment, "id", "unknown"),
            error=str(e),
        )
        return (
            [],
            {},
            {},
            f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {str(e)}",
        )


async def get_group_members_with_memberships_original(
    group: Any, thread_pool: Any
) -> List[Dict[str, Any]]:
    """
    Get group members using CanvasAPI best practices.

    Uses group.get_memberships() which returns GroupMembership objects
    containing both user information and membership details.

    Args:
        group: Canvas Group object
        thread_pool: ThreadPoolExecutor for async execution

    Returns:
        List of member dictionaries with enhanced membership information
    """
    try:

        def get_memberships() -> List[Any]:
            """Get group memberships using CanvasAPI best practices."""
            group_id = getattr(group, 'id', 'unknown')
            group_name = getattr(group, 'name', 'unknown')
            
            try:
                # Use get_memberships() with per_page for optimal performance
                logger.debug(f"Attempting get_memberships() for group {group_id} '{group_name}'")
                memberships = list(group.get_memberships(per_page=100))
                logger.info(f"SUCCESS: get_memberships() for group {group_id} returned {len(memberships)} memberships")
                return memberships
            except Exception as e:
                # Fallback to get_users() with optimization if get_memberships() fails
                logger.warning(
                    f"get_memberships() failed for group {group_id} '{group_name}' with error: {e}, falling back to get_users()"
                )
                # CRITICAL: Use group.get_users() to get group-specific users, not course users
                users = list(
                    group.get_users(
                        per_page=100,
                        include=["email"],  # Include email for comprehensive user data
                        # Note: enrollment_state might not apply to group users
                    )
                )
                logger.info(f"FALLBACK: group.get_users() for group {group_id} returned {len(users)} users")
                return users

        loop = asyncio.get_event_loop()
        memberships = await loop.run_in_executor(thread_pool, get_memberships)
        
        # Debug: Log group-specific membership info
        group_id = getattr(group, 'id', 'unknown')
        group_name = getattr(group, 'name', 'unknown')
        logger.info(
            "Group {group_id} '{group_name}' has {count} memberships",
            group_id=group_id,
            group_name=group_name,
            count=len(memberships),
        )

        members = []
        for membership in memberships:
            try:
                # Handle both GroupMembership and User objects
                if hasattr(membership, "user"):
                    # GroupMembership object - extract user and membership info
                    user = membership.user
                    member_data = {
                        "id": getattr(user, "id", None),
                        "name": getattr(user, "name", "Unknown"),
                        "email": getattr(user, "email", None),
                        "workflow_state": getattr(
                            membership, "workflow_state", "active"
                        ),
                        "moderator": getattr(membership, "moderator", False),
                    }
                else:
                    # User object - direct access (fallback case)
                    member_data = {
                        "id": getattr(membership, "id", None),
                        "name": getattr(membership, "name", "Unknown"),
                        "email": getattr(membership, "email", None),
                        "workflow_state": "active",  # Default for User objects
                        "moderator": False,  # Default for User objects
                    }

                if member_data["id"] is not None:
                    members.append(member_data)

            except Exception as e:
                logger.debug(f"Error processing group member: {e}")
                continue

        # Debug: Log the specific student IDs for this group
        student_ids = [m.get('id') for m in members if m.get('id')]
        logger.info(
            "Group {group_id} '{group_name}' retrieved {count} members: {member_ids}",
            group_id=group_id,
            group_name=group_name,
            count=len(members),
            member_ids=student_ids[:10],  # Show first 10 to avoid log spam
        )
        
        return members

    except Exception as e:
        logger.error(
            f"Error getting group members for group {getattr(group, 'id', 'unknown')}: {e}"
        )
        return []


async def get_group_members_with_memberships(
    group: Any, thread_pool: Any
) -> List[Dict[str, Any]]:
    """
    Get group members using pandas pattern provided by user.
    Uses group.get_memberships() with pandas json_normalize for accurate group-specific membership retrieval.
    """
    try:
        def get_memberships_sync() -> List[Dict[str, Any]]:
            """Synchronous function to get group memberships using pandas pattern."""
            group_id = getattr(group, 'id', 'unknown')
            group_name = getattr(group, 'name', 'unknown')
            
            try:
                # Use user's pandas pattern for group memberships
                logger.debug(f"Using pandas pattern for group {group_id} '{group_name}'")
                memberships = list(group.get_memberships())
                
                if not memberships:
                    logger.info(f"Group {group_id} '{group_name}' has no memberships")
                    return []
                
                # Apply user's pandas pattern exactly as provided
                membership_df = pd.json_normalize(
                    [vars(member) for member in memberships]
                ).assign(grading_TA=group_name)
                
                # Debug: Log the DataFrame structure and user IDs
                logger.debug(f"Group {group_id} membership DataFrame columns: {list(membership_df.columns)}")
                logger.debug(f"Group {group_id} membership DataFrame shape: {membership_df.shape}")
                
                if 'user_id' in membership_df.columns:
                    user_ids = membership_df['user_id'].dropna().astype(int).tolist()
                    logger.info(
                        f"Group {group_id} '{group_name}' has {len(user_ids)} unique user_ids: {sorted(user_ids)[:10]}..."
                    )
                    
                    # CRITICAL DEBUG: Check if group_id column exists and varies
                    if 'group_id' in membership_df.columns:
                        group_ids_in_data = membership_df['group_id'].dropna().unique()
                        logger.info(f"Group {group_id} memberships contain group_ids: {group_ids_in_data}")
                        if len(group_ids_in_data) > 1:
                            logger.warning(f"UNEXPECTED: Group {group_id} memberships contain multiple group_ids: {group_ids_in_data}")
                    else:
                        logger.warning(f"Group {group_id} memberships missing group_id column")
                    
                    # Convert to expected member dictionary format
                    members = []
                    for _, row in membership_df.iterrows():
                        if pd.notna(row.get('user_id')):
                            members.append({
                                "id": int(row['user_id']),
                                "name": f"Student_{int(row['user_id'])}",
                                "email": None,
                                "workflow_state": row.get('workflow_state', 'active'),
                                "moderator": row.get('moderator', False),
                            })
                    return members
                else:
                    logger.error(f"Group {group_id} memberships missing user_id column: {list(membership_df.columns)}")
                    return []
                    
            except Exception as e:
                logger.error(f"Failed to get memberships for group {group_id} '{group_name}': {e}")
                return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(thread_pool, get_memberships_sync)
        
    except Exception as e:
        logger.error(f"Error in pandas group membership retrieval: {e}")
        return []


def build_ta_member_mapping(ta_groups: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Build mapping from student ID (group member) to TA group name.

    In Canvas TA workflow, TA groups contain students as members,
    and TAs are responsible for grading their group members' assignments.

    Args:
        ta_groups: List of TA group data with student members

    Returns:
        Dictionary mapping student ID to TA group name
    """
    student_to_ta_group: Dict[int, str] = {}
    for group in ta_groups:
        group_name = group.get("name", "Unnamed Group")
        group_members = group.get("members", [])
        logger.debug(
            "Processing TA group '{group_name}' with {member_count} members",
            group_name=group_name,
            member_count=len(group_members),
        )
        
        for member in group_members:
            student_id = member.get("id")
            student_name = member.get("name", "Unknown")
            
            if isinstance(student_id, int):
                student_to_ta_group[student_id] = group_name
                logger.debug(
                    "Mapped student {student_id} ({student_name}) to TA group '{group_name}'",
                    student_id=student_id,
                    student_name=student_name,
                    group_name=group_name,
                )
            else:
                logger.warning(
                    "Invalid student ID {student_id} for member {student_name} in group '{group_name}'",
                    student_id=student_id,
                    student_name=student_name,
                    group_name=group_name,
                )
    
    logger.info(f"Built {len(student_to_ta_group)} student-to-TA-group mappings")
    return student_to_ta_group
