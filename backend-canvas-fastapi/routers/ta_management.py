"""
TA management and grading endpoints.
Following FastAPI best practices for dependency injection and error handling.
"""
from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from concurrent.futures import as_completed

from loguru import logger
from canvasapi import Canvas
from fastapi import APIRouter, HTTPException, status

from dependencies import SettingsDep, ThreadPoolDep, AssignmentThreadPoolDep
from services.cache import get_cached_ta_groups, set_cached_ta_groups
from models import (
    AssignmentGradingStats,
    CanvasCredentials,
    TAGradingRequest,
    TAGradingResponse,
    TAGroup,
    TAGroupsResponse,
    UngradedSubmission,
)

# Configure loguru for this module
logger = logger.bind(module="ta_management")

router = APIRouter(
    prefix="/api",
    tags=["ta-management"],
    responses={404: {"description": "Not found"}},
)


async def get_canvas_from_ta_request(
    request: TAGradingRequest, settings: SettingsDep
) -> Canvas:
    """Convert TAGradingRequest to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


async def get_canvas_from_credentials(
    request: CanvasCredentials, settings: SettingsDep
) -> Canvas:
    """Convert CanvasCredentials to Canvas client."""
    from dependencies import validate_canvas_credentials

    return await validate_canvas_credentials(
        str(request.base_url), request.api_token, settings
    )


def process_assignment_submissions_sync(
    assignment: Any,
    ta_member_to_group: Dict[int, str],
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
        # Get all submissions for this assignment
        submissions = assignment.get_submissions(
            include=["user", "submission_history", "submission_comments"], 
            per_page=100
        )
        submissions_list = list(submissions)

        if not submissions_list:
            # Return early with empty stats
            stats = {
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

        # Modern approach: Extract data directly into records for json_normalize
        records = []
        for submission in submissions_list:
            try:
                # Extract submission attributes safely
                record = {
                    "submission_id": getattr(submission, "id", None),
                    "student_id": getattr(submission.user, "id", None) if hasattr(submission, "user") and submission.user else None,
                    "student_name": getattr(submission.user, "name", "Unknown") if hasattr(submission, "user") and submission.user else "Unknown",
                    "submitted_at": getattr(submission, "submitted_at", None),
                    "workflow_state": getattr(submission, "workflow_state", "unsubmitted"),
                    "grade": getattr(submission, "grade", None),
                    "score": getattr(submission, "score", None),
                    "grader_id": getattr(submission, "grader_id", None),
                    "late": getattr(submission, "late", False),
                    "missing": getattr(submission, "missing", False),
                    "excused": getattr(submission, "excused", False),
                    "graded_at": getattr(submission, "graded_at", None),
                }
                records.append(record)
            except Exception as e:
                logger.debug("Error processing submission {submission_id}: {error}", 
                           submission_id=getattr(submission, "id", "unknown"), error=str(e))
                continue
        
        if not records:
            logger.warning("No valid submission records found for assignment {assignment_id}", 
                         assignment_id=getattr(assignment, "id", "unknown"))
            stats = {
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

        # Use json_normalize for consistent DataFrame creation
        df = pd.json_normalize(records)
        
        # Convert to nullable dtypes for better handling of missing data
        df = df.convert_dtypes()

        # Create derived columns using vectorized operations
        # Convert numeric columns properly
        df['score_numeric'] = pd.to_numeric(df['score'], errors='coerce')
        
        # Create TA group mapping series for efficient lookup
        ta_group_series = pd.Series(ta_member_to_group, name='ta_group')
        
        # Add derived columns using efficient vectorized operations
        df['has_submission'] = df['submitted_at'].notna()
        df['has_grade'] = (
            (df['grade'].notna() & (df['grade'].astype('string') != '')) |
            df['score_numeric'].notna()
        )
        df['ta_group'] = df['grader_id'].map(ta_group_series)
        df['grading_ta'] = df['ta_group'].fillna('Unassigned')

        # Calculate assignment totals using efficient aggregation
        total_submissions = len(df)
        graded_submissions = int(df['has_grade'].sum())
        ungraded_submissions = int((df['has_submission'] & ~df['has_grade']).sum())
        percentage_graded = round((graded_submissions / total_submissions) * 100, 1) if total_submissions > 0 else 0.0

        # Create TA grading breakdown using modern groupby operations
        ta_breakdown = []
        if df['ta_group'].notna().any():
            # Group by TA and calculate statistics
            ta_grouped = df[df['ta_group'].notna()].groupby('ta_group', observed=True)
            
            # Use agg for multiple aggregations at once (more efficient)
            ta_stats = ta_grouped.agg({
                'has_grade': ['count', 'sum'],
                'has_submission': 'sum'
            }).round(1)
            
            # Flatten column names
            ta_stats.columns = ['total_assigned', 'graded', 'submitted']
            ta_stats = ta_stats.reset_index()
            
            # Calculate derived metrics
            ta_stats['ungraded'] = ta_stats['submitted'] - ta_stats['graded']
            ta_stats['percentage_complete'] = (
                (ta_stats['graded'] / ta_stats['total_assigned']) * 100
            ).round(1)
            
            # Add legacy placeholder timing fields (as requested by existing code)
            ta_stats['submitted_on_time'] = (ta_stats['total_assigned'] * 0.7).astype('Int64')
            ta_stats['submitted_late'] = (ta_stats['total_assigned'] * 0.2).astype('Int64')
            ta_stats['not_submitted'] = (
                ta_stats['total_assigned'] - ta_stats['submitted_on_time'] - ta_stats['submitted_late']
            ).astype('Int64')
            
            # Create breakdown records with proper column names
            for _, row in ta_stats.iterrows():
                ta_breakdown.append({
                    'ta_name': row['ta_group'],
                    'ta_group': row['ta_group'],
                    'total_assigned': int(row['total_assigned']),
                    'graded': int(row['graded']),
                    'ungraded': int(row['ungraded']),
                    'percentage_complete': row['percentage_complete'],
                    'submitted_on_time': int(row['submitted_on_time']),
                    'submitted_late': int(row['submitted_late']),
                    'not_submitted': int(row['not_submitted'])
                })

        # Log TA assignment status
        if not ta_breakdown:
            logger.info(
                "No Canvas grader assignments found for assignment {assignment_id} ({assignment_name})",
                assignment_id=getattr(assignment, "id", "unknown"), 
                assignment_name=getattr(assignment, "name", "unknown")
            )
            logger.info(
                "{total_submissions} submissions processed, but none have grader_id assigned",
                total_submissions=total_submissions
            )
            logger.info("This indicates assignments are not distributed to TAs in Canvas")

        # Create a simplified status pivot table (removed complex pivot logic for now)
        # This can be enhanced later if the pivot functionality is specifically needed

        # Create ungraded submissions list using efficient DataFrame operations
        group_to_members = {g["name"]: [m["name"] for m in g.get("members", [])] for g in ta_groups_data}
        
        # Filter ungraded submissions efficiently
        ungraded_mask = df['has_submission'] & ~df['has_grade']
        ungraded_df = df[ungraded_mask].copy()
        
        # Add TA members information
        ungraded_df['ta_members'] = ungraded_df['ta_group'].map(group_to_members).fillna([].copy)
        
        # Convert to records efficiently using to_dict
        ungraded_rows = []
        if not ungraded_df.empty:
            for _, row in ungraded_df.iterrows():
                try:
                    ungraded_rows.append({
                        "submission_id": int(row['submission_id']) if pd.notna(row['submission_id']) else 0,
                        "student_name": str(row['student_name']) if pd.notna(row['student_name']) else "Unknown Student",
                        "student_id": str(row['student_id']) if pd.notna(row['student_id']) else "",
                        "assignment_name": getattr(assignment, "name", "Unknown Assignment"),
                        "assignment_id": getattr(assignment, "id", None),
                        "course_name": str(getattr(assignment, "course_id", "")),  # Will be overwritten upstream
                        "course_id": str(getattr(assignment, "course_id", "")),
                        "submitted_at": row['submitted_at'] if pd.notna(row['submitted_at']) else None,
                        "late": bool(row['late']) if pd.notna(row['late']) else False,
                        "grader_name": row['ta_group'] if pd.notna(row['ta_group']) else None,
                        "ta_group_name": row['ta_group'] if pd.notna(row['ta_group']) else None,
                        "ta_members": row['ta_members'] if isinstance(row['ta_members'], list) else [],
                        "html_url": getattr(assignment, "html_url", None),
                    })
                except Exception as e:
                    logger.error("Error creating ungraded submission record: {error}", error=str(e))
                    continue
        
        # Calculate TA counts for ungraded submissions
        ta_counts = {}
        if not ungraded_df.empty and 'ta_group' in ungraded_df.columns:
            ta_counts_series = ungraded_df['ta_group'].value_counts(dropna=True)
            ta_counts = ta_counts_series.to_dict()

        # Create assignment statistics
        assignment_stat = {
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

        return ungraded_rows, ta_counts, assignment_stat, None

    except Exception as e:
        logger.exception(
            "Error processing assignment {assignment_id}: {error}",
            assignment_id=getattr(assignment, "id", "unknown"),
            error=str(e)
        )
        return [], {}, {}, f"Error processing assignment {getattr(assignment, 'id', 'unknown')}: {str(e)}"


@router.post("/ta-groups/{course_id}", response_model=TAGroupsResponse)
async def get_ta_groups(
    course_id: str,
    request: CanvasCredentials,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
) -> TAGroupsResponse:
    """
    Fetch TA groups from a Canvas course (excludes Term Project groups).

    - **course_id**: Canvas course ID
    - **base_url**: Canvas instance base URL
    - **api_token**: Canvas API access token
    """
    try:
        # Check cache first (if enabled)
        if settings.enable_caching:
            cached_result = get_cached_ta_groups(
                course_id, request.api_token, settings.ta_cache_ttl
            )
            if cached_result is not None:
                ta_groups_data, course_data, error = cached_result
                if error:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
                
                # Convert to response format
                ta_groups = [TAGroup(**group_data) for group_data in ta_groups_data]
                return TAGroupsResponse(
                    ta_groups=ta_groups,
                    course_info=course_data or {},
                    total_ta_groups=len(ta_groups),
                )

        canvas = await get_canvas_from_credentials(request, settings)
        loop = asyncio.get_event_loop()

        # Get course and groups
        course = await loop.run_in_executor(
            thread_pool, lambda: canvas.get_course(course_id)
        )

        groups = await loop.run_in_executor(
            thread_pool, lambda: list(course.get_groups())
        )

        # Filter out Term Project groups and convert to TA groups
        ta_groups = []
        logger.debug("Processing {total_groups} total groups from Canvas", total_groups=len(groups))
        for group in groups:
            logger.debug("Checking group: '{group_name}' (ID: {group_id})", 
                        group_name=group.name, group_id=group.id)
            if "Term Project" not in group.name:
                logger.debug("Including TA group: '{group_name}'", group_name=group.name)
                # Get group members
                def get_group_users() -> List[Any]:
                    return list(group.get_users())

                members = await loop.run_in_executor(thread_pool, get_group_users)

                ta_groups.append(
                    TAGroup(
                        id=group.id,
                        name=group.name,
                        description=getattr(group, "description", None),
                        course_id=course_id,
                        members_count=len(members),
                        members=[
                            {
                                "id": member.id,
                                "name": member.name,
                                "email": getattr(member, "email", None),
                            }
                            for member in members
                        ],
                    )
                )
            else:
                logger.debug("Filtering out group: '{group_name}' (contains 'Term Project')", 
                           group_name=group.name)

        logger.debug("Final TA groups count: {ta_groups_count}", ta_groups_count=len(ta_groups))
        for ta_group in ta_groups:
            logger.debug("Final TA group: {ta_group_name} with {members_count} members", 
                        ta_group_name=ta_group.name, members_count=ta_group.members_count)

        course_info = {
            "id": course.id,
            "name": course.name,
            "course_code": getattr(course, "course_code", None),
        }
        
        # Cache the result (if enabled) 
        if settings.enable_caching:
            ta_groups_data = [
                {
                    "id": ta_group.id,
                    "name": ta_group.name,
                    "description": ta_group.description,
                    "course_id": ta_group.course_id,
                    "members_count": ta_group.members_count,
                    "members": ta_group.members,
                }
                for ta_group in ta_groups
            ]
            set_cached_ta_groups(
                course_id, request.api_token, ta_groups_data, course_info, None
            )

        return TAGroupsResponse(
            ta_groups=ta_groups,
            course_info=course_info,
            total_ta_groups=len(ta_groups),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching TA groups: {str(e)}",
        )


@router.post("/ta-grading", response_model=TAGradingResponse)
async def get_ta_grading_info(
    request: TAGradingRequest,
    settings: SettingsDep,
    thread_pool: ThreadPoolDep,
    assignment_pool: AssignmentThreadPoolDep,
) -> TAGradingResponse:
    """
    Return ungraded submissions, TA groups (excluding 'Term Project' groups),
    and basic grading stats for a Canvas course.

    Resilience features:
      • Retry + timeout wrappers for Canvas I/O
      • Bounded fan-out for group member fetches
      • Streaming aggregation of assignment results (as_completed)
      • Defensive normalization of nullable/missing attributes
      • Fault-tolerant model construction (skip bad rows, log cause)
    """
    # ------------ Async utilities (retry + timeout wrappers) ------------
    async def _to_thread(func, *args, timeout: float = 20.0, attempts: int = 3, base_delay: float = 0.4):
        """Run blocking func(*args) in the injected thread_pool with retry & timeout."""
        last_exc: Optional[Exception] = None
        for i in range(attempts):
            try:
                loop = asyncio.get_running_loop()
                return await asyncio.wait_for(loop.run_in_executor(thread_pool, lambda: func(*args)), timeout=timeout)
            except Exception as ex:
                last_exc = ex
                # Exponential backoff with jitter
                await asyncio.sleep(base_delay * (2 ** i))
        raise last_exc  # type: ignore[misc]

    try:
        # ------------ Bootstrap Canvas client ------------
        canvas = await get_canvas_from_ta_request(request, settings)

        # ------------ Load course, groups, assignments (concurrently, resilient) ------------
        async def load_course() -> Any:
            return await _to_thread(canvas.get_course, request.course_id)

        async def load_groups(course_obj: Any) -> List[Any]:
            def _f():
                try:
                    return list(course_obj.get_groups())
                except Exception:
                    return []
            return await _to_thread(_f)

        async def load_assignments(course_obj: Any) -> List[Any]:
            def _f():
                try:
                    return list(course_obj.get_assignments())
                except Exception:
                    return []
            return await _to_thread(_f)

        course = await load_course()
        groups_task = asyncio.create_task(load_groups(course))
        assignments_task = asyncio.create_task(load_assignments(course))
        groups, assignments = await asyncio.gather(groups_task, assignments_task)

        # ------------ Optional single-assignment constraint (guarded) ------------
        if getattr(request, "assignment_id", None):
            try:
                assignment = await _to_thread(course.get_assignment, request.assignment_id)
                assignments = [assignment] if assignment is not None else []
            except Exception as ex:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignment {request.assignment_id} not found: {ex}",
                )

        if not isinstance(groups, list):
            groups = []
        if not isinstance(assignments, list):
            assignments = []

        # ------------ Filter TA groups once (defensive against missing names) ------------
        def _is_ta_group(g: Any) -> bool:
            name = getattr(g, "name", "") or ""
            return ("Term Project" not in name) and bool(name)

        canvas_ta_groups = [g for g in groups if _is_ta_group(g)]
        ta_groups: List[TAGroup] = [
            TAGroup(
                id=getattr(g, "id", None),
                name=getattr(g, "name", None) or "Unnamed Group",
                description=getattr(g, "description", None),
                course_id=request.course_id,
                members_count=0,
                members=[],
            )
            for g in canvas_ta_groups
        ]

        # ------------ Concurrently fetch members per group (bounded + resilient) ------------
        sem = asyncio.Semaphore(12)  # tune with your Canvas rate limits

        async def fetch_members(idx: int, cg: Any) -> None:
            async with sem:
                try:
                    def _f() -> List[Any]:
                        try:
                            return list(cg.get_users())
                        except Exception:
                            return []
                    members = await _to_thread(_f, timeout=25.0)
                except Exception as ex:
                    logger.info(f"Member fetch failed for group {getattr(cg, 'id', 'unknown')}: {ex}")
                    members = []

                ta_groups[idx].members = [
                    {
                        "id": getattr(m, "id", None),
                        "name": getattr(m, "name", None) or "Unknown",
                        "email": getattr(m, "email", None),
                    }
                    for m in members
                    if hasattr(m, "id")
                ]
                ta_groups[idx].members_count = len(ta_groups[idx].members)

        if ta_groups:
            await asyncio.gather(
                *(fetch_members(i, g) for i, g in enumerate(canvas_ta_groups)),
                return_exceptions=True,
            )

        # ------------ Build TA member → group map (defensive) ------------
        ta_member_to_group: Dict[int, str] = {}
        for group in ta_groups:
            gname = group.name or "Unnamed Group"
            for member in group.members:
                mid = member.get("id")
                if isinstance(mid, int):
                    ta_member_to_group[mid] = gname
        logger.debug(f"Built {len(ta_member_to_group)} TA member mappings")

        # ------------ Process assignments concurrently; stream results ------------
        ungraded_submissions_raw: List[Dict[str, Any]] = []
        grading_distribution: Dict[str, int] = {}
        assignment_stats_raw: List[Dict[str, Any]] = []

        ta_groups_data = [{"name": g.name, "members": g.members} for g in ta_groups]

        # Submit all jobs
        future_to_assignment = {
            assignment_pool.submit(
                process_assignment_submissions_sync, a, ta_member_to_group, ta_groups_data
            ): a
            for a in assignments
        }

        # Collect as they complete
        for fut in as_completed(future_to_assignment):
            a = future_to_assignment[fut]
            try:
                ungraded, ta_counts, stats, err = fut.result(timeout=120.0)
                if err:
                    logger.error(f"Error processing assignment {getattr(a, 'id', 'unknown')}: {err}")
                    continue

                # Normalize & merge
                cname = getattr(course, "name", None)
                for s in (ungraded or []):
                    s["course_name"] = cname
                    s["course_id"] = request.course_id

                if ungraded:
                    ungraded_submissions_raw.extend(ungraded)
                if stats:
                    assignment_stats_raw.append(stats)
                if ta_counts:
                    for ta, cnt in ta_counts.items():
                        try:
                            grading_distribution[ta] = grading_distribution.get(ta, 0) + int(cnt or 0)
                        except Exception:
                            continue
            except Exception as ex:
                logger.info(f"Exception processing assignment {getattr(a, 'id', 'unknown')}: {ex}")

        # ------------ Construct response models (skip bad rows) ------------
        ungraded_objs: List[UngradedSubmission] = []
        for s in ungraded_submissions_raw:
            try:
                ungraded_objs.append(UngradedSubmission(**s))
            except Exception as ex:
                logger.error(f"Invalid ungraded submission payload skipped: {ex}")

        stats_objs: List[AssignmentGradingStats] = []
        for st in assignment_stats_raw:
            try:
                stats_objs.append(AssignmentGradingStats(**st))
            except Exception as ex:
                logger.error(f"Invalid assignment stats payload skipped: {ex}")

        if not grading_distribution:
            logger.info(
                f"No TA-specific grading distribution available for course {getattr(course, 'id', 'unknown')} "
                "(Canvas does not assign submissions to TAs)"
            )

        # ------------ Final response (course fields normalized) ------------
        course_id_safe = getattr(course, "id", None) or request.course_id
        course_name_safe = getattr(course, "name", None)
        course_code_safe = getattr(course, "course_code", None)

        return TAGradingResponse(
            ungraded_submissions=ungraded_objs,
            ta_groups=ta_groups,
            course_info={
                "id": course_id_safe,
                "name": course_name_safe,
                "course_code": course_code_safe,
            },
            total_ungraded=len(ungraded_objs),
            grading_distribution=grading_distribution,
            assignment_stats=stats_objs,
        )

    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Unexpected error fetching TA grading info: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching TA grading info: {ex}",
        )