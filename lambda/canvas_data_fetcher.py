"""
AWS Lambda function for fetching Canvas data and caching it in S3.
Single-tenant architecture - fetches data for configured course.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Canvas API
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Environment variables
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
CANVAS_API_URL = os.environ['CANVAS_API_URL']
CANVAS_COURSE_ID = os.environ['CANVAS_COURSE_ID']
# Optional: Get token from env var or Secrets Manager
CANVAS_API_TOKEN = os.environ.get('CANVAS_API_TOKEN')
CANVAS_TOKENS_SECRET = os.environ.get('CANVAS_TOKENS_SECRET')


def lambda_handler(event, context):
    """Lambda handler function."""
    logger.info(f"Lambda triggered with event: {json.dumps(event)}")

    try:
        # Get API token
        api_token = get_api_token()
        if not api_token:
            raise ValueError("No Canvas API token found")

        # Initialize Canvas API
        canvas = Canvas(CANVAS_API_URL, api_token)
        course = canvas.get_course(CANVAS_COURSE_ID)
        logger.info(f"Fetching data for course: {course.name} ({CANVAS_COURSE_ID})")

        # Fetch data
        data = fetch_course_data(course)

        # Store in S3
        store_course_data(CANVAS_COURSE_ID, data)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data fetched successfully',
                'course_id': CANVAS_COURSE_ID,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Canvas data fetching failed'
            })
        }

def get_api_token() -> Optional[str]:
    """Get Canvas API token from env var or Secrets Manager."""
    if CANVAS_API_TOKEN:
        return CANVAS_API_TOKEN

    if CANVAS_TOKENS_SECRET:
        try:
            response = secrets_client.get_secret_value(SecretId=CANVAS_TOKENS_SECRET)
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('canvas_api_token')
        except Exception as e:
            logger.error(f"Error getting secret: {e}")
            return None

    return None

def fetch_course_data(course) -> Dict[str, Any]:
    """Fetch all required data from Canvas."""

    # Get assignments
    assignments = []
    for assignment in course.get_assignments(per_page=100):
        assignments.append({
            'id': assignment.id,
            'name': assignment.name,
            'due_at': getattr(assignment, 'due_at', None),
            'points_possible': getattr(assignment, 'points_possible', None),
            'html_url': getattr(assignment, 'html_url', None)
        })

    # Get submissions
    submissions = []
    for assignment in course.get_assignments(per_page=100):
        for submission in assignment.get_submissions(include=['submission_history']):
            submissions.append({
                'id': submission.id,
                'user_id': submission.user_id,
                'assignment_id': assignment.id,
                'submitted_at': getattr(submission, 'submitted_at', None),
                'workflow_state': submission.workflow_state,
                'late': getattr(submission, 'late', False),
                'score': getattr(submission, 'score', None)
            })

    # Get users
    users = []
    for user in course.get_users(enrollment_type=['student']):
        users.append({
            'id': user.id,
            'name': user.name,
            'email': getattr(user, 'email', None)
        })

    # Get groups
    groups = []
    for group in course.get_groups(per_page=100, include=['users']):
        if "Term Project" not in getattr(group, 'name', ''):  # Filter out project groups if needed
            members = []
            for member in getattr(group, 'users', []):
                members.append({
                    'id': member.id,
                    'user_id': member.id,
                    'name': member.name
                })

            groups.append({
                'id': group.id,
                'name': group.name,
                'members': members
            })

    return {
        'assignments': assignments,
        'submissions': submissions,
        'users': users,
        'enrollments': [],  # Can add if needed
        'groups': groups
    }

def store_course_data(course_id, data):
    """Store data in S3 with structure main.py expects."""
    timestamp = datetime.utcnow().isoformat()

    # Store complete data
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=f'canvas_data/course_{course_id}/latest.json',
        Body=json.dumps({
            'course_id': course_id,
            'timestamp': timestamp,
            **data
        }, indent=2),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )

    # Store individual components (for backwards compatibility/performance)
    for component_name, component_data in data.items():
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=f'canvas_data/course_{course_id}/latest_{component_name}.json',
            Body=json.dumps(component_data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )

    logger.info(f"Stored data for course {course_id} in {S3_BUCKET_NAME}")
