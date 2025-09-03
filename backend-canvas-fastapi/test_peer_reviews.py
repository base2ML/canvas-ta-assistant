#!/usr/bin/env python3
"""
Debug script to test peer review functionality with your actual Canvas data.
This will show detailed logging about what's happening with peer review detection.
"""

import sys
from loguru import logger

from main import get_peer_review_data_sync


def test_peer_reviews():
    logger.info("=== Canvas Peer Review Debug Test ===")

    # You'll need to fill these in with your actual values
    base_url = input(
        "Enter your Canvas base URL (e.g., https://gatech.instructure.com): "
    ).strip()
    if not base_url:
        base_url = "https://gatech.instructure.com"  # Default from your .env

    api_token = input("Enter your Canvas API token: ").strip()
    if not api_token:
        logger.error("API token is required")
        return

    course_id = input("Enter course ID: ").strip()
    if not course_id:
        logger.error("Course ID is required")
        return

    assignment_id = input("Enter assignment ID (the project proposal): ").strip()
    if not assignment_id:
        logger.error("Assignment ID is required")
        return

    deadline = input(
        "Enter deadline (YYYY-MM-DDTHH:MM:SS format, e.g., 2024-03-15T23:59:59): "
    ).strip()
    if not deadline:
        deadline = "2024-03-15T23:59:59"

    logger.info("Testing Peer Review Detection")
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Course ID: {course_id}")
    logger.info(f"Assignment ID: {assignment_id}")
    logger.info(f"Deadline: {deadline}")

    try:
        # Call the function with debugging
        peer_events_data, peer_summary_data, assignment_data, course_data, error = (
            get_peer_review_data_sync(
                base_url=base_url,
                api_token=api_token,
                course_id=course_id,
                assignment_id=int(assignment_id),
                deadline=deadline,
                penalty_per_review=4,
            )
        )

        logger.info("=== RESULTS ===")
        if error:
            logger.error(f"Error: {error}")
        else:
            logger.success("Success!")
            logger.info(f"Found {len(peer_events_data)} peer review events")
            logger.info(f"Found {len(peer_summary_data)} students with penalties")

            if assignment_data:
                logger.info(f"Assignment: {assignment_data.get('name')}")

            if peer_events_data:
                logger.info("Peer Review Events:")
                for i, event in enumerate(peer_events_data[:5]):  # Show first 5
                    logger.info(
                        f"  {i+1}. {event.get('reviewer_name', f'ID:{event.get('reviewer_id')}')} -> "
                        f"{event.get('assessed_name', f'ID:{event.get('assessed_user_id')}')} "
                        f"[{event.get('status')}] ({event.get('penalty_points')} pts)"
                    )

                if len(peer_events_data) > 5:
                    logger.info(f"  ... and {len(peer_events_data) - 5} more")
            else:
                logger.warning("No peer review events found")

    except Exception as e:
        logger.exception(f"Exception occurred: {str(e)}")
        logger.error(f"Exception type: {type(e)}")


if __name__ == "__main__":
    test_peer_reviews()
