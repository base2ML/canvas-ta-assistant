#!/usr/bin/env python3
"""
Canvas Data Extraction Test Script

Tests Canvas API connectivity and data fetching without uploading to S3.
Useful for local development and CI/CD validation.

Usage:
    python scripts/test-canvas-extraction.py [--dry-run] [--output-dir DIR]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from canvasapi import Canvas
    from canvasapi.exceptions import CanvasException
except ImportError:
    print("❌ Error: canvasapi not installed. Run: pip install canvasapi")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.NC}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.NC}")


def get_env_var(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation"""
    value = os.getenv(name)
    if required and not value:
        print_error(f"Missing required environment variable: {name}")
        return None
    return value


def test_canvas_connection(canvas_url: str, api_token: str) -> Optional[Canvas]:
    """Test Canvas API connection"""
    print_info(f"Testing connection to: {canvas_url}")

    try:
        canvas = Canvas(canvas_url, api_token)
        # Test by getting current user
        user = canvas.get_current_user()
        print_success(f"Connected as: {user.name}")
        return canvas
    except CanvasException as e:
        print_error(f"Canvas API error: {e}")
        return None
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return None


def fetch_course_data(canvas: Canvas, course_id: str, dry_run: bool = False) -> Optional[Dict[str, Any]]:
    """Fetch course data from Canvas"""

    try:
        print_info(f"Fetching course: {course_id}")
        course = canvas.get_course(course_id)

        course_data = {
            'id': course.id,
            'name': course.name,
            'course_code': getattr(course, 'course_code', 'N/A'),
        }

        print_success(f"Course: {course.name} ({course.course_code})")

        if dry_run:
            print_info("Dry-run mode: Skipping full data fetch")
            return {
                'course': course_data,
                'dry_run': True,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Fetch assignments
        print_info("Fetching assignments...")
        assignments = []
        for assignment in course.get_assignments(per_page=100):
            assignments.append({
                'id': assignment.id,
                'name': assignment.name,
                'due_at': getattr(assignment, 'due_at', None),
                'points_possible': getattr(assignment, 'points_possible', None),
            })
        print_success(f"Found {len(assignments)} assignments")

        # Fetch users (students)
        print_info("Fetching users...")
        users = []
        for user in course.get_users(enrollment_type=['student'], per_page=100):
            users.append({
                'id': user.id,
                'name': user.name,
                'sortable_name': getattr(user, 'sortable_name', user.name),
            })
        print_success(f"Found {len(users)} users")

        # Fetch submissions (sample from first assignment)
        print_info("Fetching submissions (sample)...")
        submissions = []
        if assignments:
            try:
                first_assignment = course.get_assignment(assignments[0]['id'])
                for submission in first_assignment.get_submissions():
                    submissions.append({
                        'id': submission.id,
                        'assignment_id': first_assignment.id,
                        'user_id': submission.user_id,
                        'workflow_state': submission.workflow_state,
                        'submitted_at': getattr(submission, 'submitted_at', None),
                    })
                print_success(f"Found {len(submissions)} submissions (from first assignment)")
            except Exception as e:
                print_warning(f"Could not fetch submissions: {e}")

        # Fetch groups
        print_info("Fetching groups...")
        groups = []
        try:
            for group in course.get_groups():
                members = []
                try:
                    for member in group.get_users():
                        members.append(member.id)
                except: # noqa: E722
                    pass

                groups.append({
                    'id': group.id,
                    'name': group.name,
                    'members_count': len(members),
                })
            print_success(f"Found {len(groups)} groups")
        except Exception as e:
            print_warning(f"Could not fetch groups: {e}")

        return {
            'course': course_data,
            'assignments': assignments,
            'users': users,
            'submissions': submissions,
            'groups': groups,
            'timestamp': datetime.utcnow().isoformat(),
        }

    except CanvasException as e:
        print_error(f"Canvas API error: {e}")
        return None
    except Exception as e:
        print_error(f"Error fetching course data: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_output(data: Dict[str, Any], output_dir: str):
    """Save test output to JSON file"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"canvas_data_{timestamp}.json"
    filepath = output_path / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print_success(f"Data saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Test Canvas API data extraction')
    parser.add_argument('--dry-run', action='store_true', help='Only test connection, skip full data fetch')
    parser.add_argument('--output-dir', default='test_output', help='Output directory for test results')
    args = parser.parse_args()

    print("=" * 60)
    print("🧪 Canvas Data Extraction Test")
    print("=" * 60)
    print()

    # Get environment variables
    canvas_url = get_env_var('CANVAS_API_URL')
    api_token = get_env_var('CANVAS_API_TOKEN')
    course_id = get_env_var('CANVAS_COURSE_ID')

    if not all([canvas_url, api_token, course_id]):
        print_error("Missing required environment variables:")
        print("  - CANVAS_API_URL")
        print("  - CANVAS_API_TOKEN")
        print("  - CANVAS_COURSE_ID")
        print()
        print("Set these in your .env file or export them.")
        return 1

    # Test connection
    canvas = test_canvas_connection(canvas_url, api_token)
    if not canvas:
        return 1

    print()

    # Fetch course data
    data = fetch_course_data(canvas, course_id, dry_run=args.dry_run)
    if not data:
        return 1

    print()

    # Save output
    if not args.dry_run:
        save_output(data, args.output_dir)

    print()
    print("=" * 60)
    print(f"{Colors.GREEN}✅ Canvas Data Extraction Test Passed{Colors.NC}")
    print("=" * 60)

    if not args.dry_run:
        print()
        print("Summary:")
        print(f"  Course: {data['course']['name']}")
        print(f"  Assignments: {len(data.get('assignments', []))}")
        print(f"  Users: {len(data.get('users', []))}")
        print(f"  Submissions (sample): {len(data.get('submissions', []))}")
        print(f"  Groups: {len(data.get('groups', []))}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
