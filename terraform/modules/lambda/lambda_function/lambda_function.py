"""
Canvas Data Fetcher Lambda Function

This function fetches data from Canvas API and stores it in S3.
Designed to run every 15 minutes via EventBridge.
"""

import json
import os
import boto3
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """
    Main Lambda handler function
    """
    try:
        logger.info("Starting Canvas data fetch process")

        # Get environment variables
        s3_bucket = os.environ['S3_BUCKET_NAME']
        canvas_api_url = os.environ['CANVAS_API_URL']
        canvas_course_id = os.environ['CANVAS_COURSE_ID']
        environment = os.environ['ENVIRONMENT']

        # Get Canvas API token from Secrets Manager
        canvas_token = get_canvas_api_token(environment)

        # Initialize Canvas API client
        canvas_api = CanvasAPIClient(canvas_api_url, canvas_token)

        # Fetch data from Canvas
        canvas_data = fetch_canvas_data(canvas_api, canvas_course_id)

        # Store data in S3
        store_data_in_s3(s3_bucket, canvas_data, canvas_course_id)

        logger.info("Canvas data fetch completed successfully")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Canvas data fetch completed successfully',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'course_id': canvas_course_id,
                'records_processed': len(canvas_data.get('assignments', [])) + len(canvas_data.get('submissions', []))
            })
        }

    except Exception as e:
        logger.error(f"Error in Canvas data fetch: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def get_canvas_api_token(environment: str) -> str:
    """
    Retrieve Canvas API token from Secrets Manager
    """
    try:
        secret_name = f"canvas-ta-dashboard-canvas-api-token-{environment}"
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret['canvas_api_token']
    except Exception as e:
        logger.error(f"Failed to retrieve Canvas API token: {str(e)}")
        raise

class CanvasAPIClient:
    """
    Canvas API client for fetching course data
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Make GET request to Canvas API
        """
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_paginated(self, endpoint: str, params: Dict = None) -> List[Dict[str, Any]]:
        """
        Get all pages of a paginated Canvas API response
        """
        all_items = []
        params = params or {}
        params['per_page'] = 100  # Max items per page

        while True:
            data = self.get(endpoint, params)
            if isinstance(data, list):
                all_items.extend(data)
                # Check if there are more pages
                if len(data) < params['per_page']:
                    break
                params['page'] = params.get('page', 1) + 1
            else:
                return data  # Single object response

        return all_items

def fetch_canvas_data(canvas_api: CanvasAPIClient, course_id: str) -> Dict[str, Any]:
    """
    Fetch all relevant Canvas data for the dashboard
    """
    logger.info(f"Fetching Canvas data for course {course_id}")

    canvas_data = {
        'course_id': course_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'course': {},
        'assignments': [],
        'submissions': [],
        'users': [],
        'enrollments': [],
        'groups': []
    }

    try:
        # Fetch course information
        canvas_data['course'] = canvas_api.get(f"courses/{course_id}")
        logger.info(f"Fetched course: {canvas_data['course'].get('name', 'Unknown')}")

        # Fetch assignments
        assignments = canvas_api.get_paginated(f"courses/{course_id}/assignments")
        canvas_data['assignments'] = assignments
        logger.info(f"Fetched {len(assignments)} assignments")

        # Fetch users (students and TAs)
        users = canvas_api.get_paginated(f"courses/{course_id}/users")
        canvas_data['users'] = users
        logger.info(f"Fetched {len(users)} users")

        # Skip enrollments - not needed for dashboard and very slow for large courses
        canvas_data['enrollments'] = []
        logger.info("Skipped enrollments fetch (not needed for dashboard)")

        # Fetch submissions per assignment (matching notebook approach)
        try:
            import time
            start_time = time.time()
            max_fetch_time = 240  # 4 minutes max for submissions (longer since per-assignment)

            logger.info(f"Starting per-assignment submissions fetch for {len(assignments)} assignments with time limit")
            all_submissions = []
            assignments_processed = 0

            for assignment in assignments:
                # Check if we've exceeded time limit
                elapsed = time.time() - start_time
                if elapsed > max_fetch_time:
                    logger.warning(f"Submissions fetch timed out after {elapsed:.1f}s, processed {assignments_processed}/{len(assignments)} assignments, collected {len(all_submissions)} submissions")
                    break

                try:
                    assignment_id = assignment.get('id')
                    assignment_name = assignment.get('name', 'Unknown')

                    # Fetch submissions for this assignment
                    assignment_submissions = canvas_api.get_paginated(
                        f"courses/{course_id}/assignments/{assignment_id}/submissions"
                    )

                    if isinstance(assignment_submissions, list):
                        all_submissions.extend(assignment_submissions)
                        assignments_processed += 1
                        logger.info(f"Fetched {len(assignment_submissions)} submissions for assignment '{assignment_name}' ({assignments_processed}/{len(assignments)}, total: {len(all_submissions)})")

                except Exception as assignment_error:
                    logger.warning(f"Error fetching submissions for assignment {assignment.get('name', 'Unknown')}: {str(assignment_error)}")
                    continue

            canvas_data['submissions'] = all_submissions
            logger.info(f"Fetched {len(all_submissions)} submissions across {assignments_processed} assignments in {time.time() - start_time:.1f}s")

        except Exception as e:
            logger.warning(f"Failed to fetch submissions: {str(e)}")
            canvas_data['submissions'] = []

        # Fetch groups with memberships (for TA assignments)
        try:
            groups = canvas_api.get_paginated(f"courses/{course_id}/groups")
            logger.info(f"Fetched {len(groups)} groups")

            # Fetch memberships for each group (matching notebook approach)
            groups_with_members = []
            for group in groups:
                try:
                    group_id = group.get('id')
                    group_name = group.get('name', 'Unknown')

                    # Fetch memberships for this group
                    memberships = canvas_api.get_paginated(f"groups/{group_id}/memberships")

                    # Add members array to group
                    group['members'] = memberships
                    groups_with_members.append(group)

                    logger.info(f"Fetched {len(memberships)} members for group '{group_name}'")

                except Exception as group_error:
                    logger.warning(f"Error fetching memberships for group {group.get('name', 'Unknown')}: {str(group_error)}")
                    # Keep group without members rather than failing completely
                    group['members'] = []
                    groups_with_members.append(group)

            canvas_data['groups'] = groups_with_members
            logger.info(f"Completed fetching memberships for {len(groups_with_members)} groups")
        except Exception as e:
            logger.warning(f"Failed to fetch groups: {str(e)}")
            canvas_data['groups'] = []

    except Exception as e:
        logger.error(f"Error fetching Canvas data: {str(e)}")
        raise

    return canvas_data

def store_data_in_s3(bucket_name: str, canvas_data: Dict[str, Any], course_id: str):
    """
    Store Canvas data in S3 bucket under both long and short course ID formats
    """
    try:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        # Generate both long and short form course IDs
        course_ids = [course_id]
        if len(course_id) > 10:
            # Extract short form (last 6 digits)
            short_id = course_id[-6:]
            course_ids.append(short_id)
            logger.info(f"Storing data for both course IDs: {course_id} and {short_id}")

        # Store data under both course ID formats
        for cid in course_ids:
            # Store complete data dump
            complete_data_key = f"canvas_data/course_{cid}/complete/canvas_data_{timestamp}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=complete_data_key,
                Body=json.dumps(canvas_data, default=str, indent=2),
                ContentType='application/json'
            )

            # Store latest data (for dashboard to consume)
            latest_data_key = f"canvas_data/course_{cid}/latest.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=latest_data_key,
                Body=json.dumps(canvas_data, default=str, indent=2),
                ContentType='application/json'
            )

            # Store individual data types for easier access
            data_types = ['assignments', 'submissions', 'users', 'enrollments', 'groups']
            for data_type in data_types:
                if data_type in canvas_data and canvas_data[data_type]:
                    data_key = f"canvas_data/course_{cid}/latest_{data_type}.json"
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=data_key,
                        Body=json.dumps({
                            'timestamp': canvas_data['timestamp'],
                            'course_id': cid,
                            data_type: canvas_data[data_type]
                        }, default=str, indent=2),
                        ContentType='application/json'
                    )

        logger.info(f"Stored Canvas data in S3 for course IDs: {', '.join(course_ids)}")

    except Exception as e:
        logger.error(f"Error storing data in S3: {str(e)}")
        raise