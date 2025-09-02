#!/usr/bin/env python3
"""
Debug script to test peer review functionality with your actual Canvas data.
This will show detailed logging about what's happening with peer review detection.
"""

import logging
import sys

from main import get_peer_review_data_sync

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def test_peer_reviews():
    print("=== Canvas Peer Review Debug Test ===")
    print()

    # You'll need to fill these in with your actual values
    base_url = input(
        "Enter your Canvas base URL (e.g., https://gatech.instructure.com): "
    ).strip()
    if not base_url:
        base_url = "https://gatech.instructure.com"  # Default from your .env

    api_token = input("Enter your Canvas API token: ").strip()
    if not api_token:
        print("❌ API token is required")
        return

    course_id = input("Enter course ID: ").strip()
    if not course_id:
        print("❌ Course ID is required")
        return

    assignment_id = input("Enter assignment ID (the project proposal): ").strip()
    if not assignment_id:
        print("❌ Assignment ID is required")
        return

    deadline = input(
        "Enter deadline (YYYY-MM-DDTHH:MM:SS format, e.g., 2024-03-15T23:59:59): "
    ).strip()
    if not deadline:
        deadline = "2024-03-15T23:59:59"

    print("\n=== Testing Peer Review Detection ===")
    print(f"Base URL: {base_url}")
    print(f"Course ID: {course_id}")
    print(f"Assignment ID: {assignment_id}")
    print(f"Deadline: {deadline}")
    print("\n" + "=" * 50)

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

        print("\n=== RESULTS ===")
        if error:
            print(f"❌ Error: {error}")
        else:
            print(f"✅ Success!")
            print(f"📊 Found {len(peer_events_data)} peer review events")
            print(f"👥 Found {len(peer_summary_data)} students with penalties")

            if assignment_data:
                print(f"📝 Assignment: {assignment_data.get('name')}")

            if peer_events_data:
                print("\n📋 Peer Review Events:")
                for i, event in enumerate(peer_events_data[:5]):  # Show first 5
                    print(
                        f"  {i+1}. {event.get('reviewer_name', f'ID:{event.get('reviewer_id')}')} -> "
                        f"{event.get('assessed_name', f'ID:{event.get('assessed_user_id')}')} "
                        f"[{event.get('status')}] ({event.get('penalty_points')} pts)"
                    )

                if len(peer_events_data) > 5:
                    print(f"  ... and {len(peer_events_data) - 5} more")
            else:
                print("📋 No peer review events found")

    except Exception as e:
        print(f"💥 Exception occurred: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_peer_reviews()
