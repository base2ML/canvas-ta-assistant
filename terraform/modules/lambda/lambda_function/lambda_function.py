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

        # Fetch enrollments
        enrollments = canvas_api.get_paginated(f"courses/{course_id}/enrollments")
        canvas_data['enrollments'] = enrollments
        logger.info(f"Fetched {len(enrollments)} enrollments")

        # Fetch submissions for all assignments
        all_submissions = []
        for assignment in assignments:
            try:
                submissions = canvas_api.get_paginated(
                    f"courses/{course_id}/assignments/{assignment['id']}/submissions",
                    params={'include[]': ['submission_history', 'submission_comments', 'rubric_assessment']}
                )
                # Add assignment_id to each submission for easier processing
                for submission in submissions:
                    submission['assignment_id'] = assignment['id']
                all_submissions.extend(submissions)
            except Exception as e:
                logger.warning(f"Failed to fetch submissions for assignment {assignment['id']}: {str(e)}")

        canvas_data['submissions'] = all_submissions
        logger.info(f"Fetched {len(all_submissions)} submissions")

        # Fetch groups (for TA assignments)
        try:
            groups = canvas_api.get_paginated(f"courses/{course_id}/groups")
            canvas_data['groups'] = groups
            logger.info(f"Fetched {len(groups)} groups")
        except Exception as e:
            logger.warning(f"Failed to fetch groups: {str(e)}")
            canvas_data['groups'] = []

    except Exception as e:
        logger.error(f"Error fetching Canvas data: {str(e)}")
        raise

    return canvas_data

def store_data_in_s3(bucket_name: str, canvas_data: Dict[str, Any], course_id: str):
    """
    Store Canvas data in S3 bucket
    """
    try:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        # Store complete data dump
        complete_data_key = f"canvas_data/course_{course_id}/complete/canvas_data_{timestamp}.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=complete_data_key,
            Body=json.dumps(canvas_data, default=str, indent=2),
            ContentType='application/json'
        )

        # Store latest data (for dashboard to consume)
        latest_data_key = f"canvas_data/course_{course_id}/latest.json"
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
                data_key = f"canvas_data/course_{course_id}/latest_{data_type}.json"
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=data_key,
                    Body=json.dumps({
                        'timestamp': canvas_data['timestamp'],
                        'course_id': course_id,
                        data_type: canvas_data[data_type]
                    }, default=str, indent=2),
                    ContentType='application/json'
                )

        logger.info(f"Stored Canvas data in S3: {complete_data_key}")

    except Exception as e:
        logger.error(f"Error storing data in S3: {str(e)}")
        raise