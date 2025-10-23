"""
AWS Lambda function for fetching Canvas data and caching it in S3.
Multi-tenant architecture - fetches data for all courses with active users.
"""

import json
import os
import boto3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

# Canvas API
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Environment variables
USERS_TABLE = os.environ['USERS_TABLE']
USER_COURSES_TABLE = os.environ['USER_COURSES_TABLE']
CACHE_METADATA_TABLE = os.environ['CACHE_METADATA_TABLE']
COURSE_DATA_BUCKET = os.environ['COURSE_DATA_BUCKET']
CANVAS_TOKENS_SECRET = os.environ['CANVAS_TOKENS_SECRET']


class CanvasDataFetcher:
    """Fetches Canvas data for multiple courses and caches in S3."""

    def __init__(self):
        self.users_table = dynamodb.Table(USERS_TABLE)
        self.user_courses_table = dynamodb.Table(USER_COURSES_TABLE)
        self.cache_metadata_table = dynamodb.Table(CACHE_METADATA_TABLE)
        self.thread_pool = ThreadPoolExecutor(max_workers=5)

    async def fetch_all_course_data(self) -> Dict[str, Any]:
        """Main entry point - fetch data for all active courses."""
        results = {
            'processed_courses': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'errors': []
        }

        try:
            # Get all unique courses with active users
            active_courses = await self._get_active_courses()
            logger.info(f"Found {len(active_courses)} active courses to process")

            # Process each course
            for course_info in active_courses:
                try:
                    success = await self._process_course(course_info)
                    results['processed_courses'] += 1

                    if success:
                        results['successful_updates'] += 1
                    else:
                        results['failed_updates'] += 1

                except Exception as e:
                    logger.error(f"Error processing course {course_info['course_key']}: {e}")
                    results['failed_updates'] += 1
                    results['errors'].append(f"{course_info['course_key']}: {str(e)}")

            logger.info(f"Processing complete: {results}")
            return results

        except Exception as e:
            logger.error(f"Error in fetch_all_course_data: {e}")
            results['errors'].append(f"Fatal error: {str(e)}")
            return results

    async def _get_active_courses(self) -> List[Dict[str, Any]]:
        """Get all courses with active users."""
        try:
            # Scan user_courses_table for active courses
            response = self.user_courses_table.scan(
                FilterExpression='is_active = :active',
                ExpressionAttributeValues={':active': True}
            )

            # Group by course_key to avoid duplicates
            courses_map = {}
            for item in response['Items']:
                course_key = f"{item['canvas_base_url']}#{item['course_id']}"

                if course_key not in courses_map:
                    courses_map[course_key] = {
                        'course_key': course_key,
                        'course_id': item['course_id'],
                        'canvas_base_url': item['canvas_base_url'],
                        'user_count': 0,
                        'sample_token': None
                    }

                courses_map[course_key]['user_count'] += 1

                # Store one token for API calls (all users of same course should have same access)
                if not courses_map[course_key]['sample_token']:
                    courses_map[course_key]['sample_token'] = item.get('encrypted_token')

            return list(courses_map.values())

        except Exception as e:
            logger.error(f"Error getting active courses: {e}")
            return []

    async def _process_course(self, course_info: Dict[str, Any]) -> bool:
        """Process a single course and update its cached data."""
        try:
            course_key = course_info['course_key']
            course_id = course_info['course_id']
            canvas_base_url = course_info['canvas_base_url']

            logger.info(f"Processing course: {course_key}")

            # Check if we need to update (every 15 minutes or on demand)
            if not await self._should_update_course(course_key):
                logger.info(f"Skipping {course_key} - recently updated")
                return True

            # Get Canvas API token for this course
            api_token = await self._get_course_api_token(course_key)
            if not api_token:
                logger.warning(f"No API token found for course: {course_key}")
                return False

            # Fetch Canvas data
            canvas_data = await self._fetch_canvas_course_data(
                canvas_base_url, api_token, course_id
            )

            if not canvas_data:
                logger.error(f"Failed to fetch Canvas data for: {course_key}")
                return False

            # Store in S3
            await self._store_course_data_s3(course_key, canvas_data)

            # Update cache metadata
            await self._update_cache_metadata(
                course_key, course_id, canvas_base_url,
                course_info['user_count'], len(json.dumps(canvas_data))
            )

            logger.info(f"Successfully updated course: {course_key}")
            return True

        except Exception as e:
            logger.error(f"Error processing course {course_info['course_key']}: {e}")
            return False

    async def _should_update_course(self, course_key: str) -> bool:
        """Check if course data should be updated."""
        try:
            response = self.cache_metadata_table.get_item(
                Key={'course_key': course_key}
            )

            if 'Item' not in response:
                return True  # No cache metadata, need to update

            item = response['Item']
            last_updated = datetime.fromisoformat(item['last_updated'])

            # Update every 15 minutes
            if datetime.utcnow() - last_updated < timedelta(minutes=15):
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking update status for {course_key}: {e}")
            return True  # If in doubt, update

    async def _get_course_api_token(self, course_key: str) -> Optional[str]:
        """Get Canvas API token for a course."""
        try:
            # In a real implementation, you'd decrypt the token from the user record
            # For now, we'll use a placeholder from Secrets Manager
            response = secrets_client.get_secret_value(SecretId=CANVAS_TOKENS_SECRET)
            secret_data = json.loads(response['SecretString'])

            # This is a simplified approach - in production, you'd have proper token management
            return secret_data.get('default_token')

        except Exception as e:
            logger.error(f"Error getting API token for {course_key}: {e}")
            return None

    async def _fetch_canvas_course_data(self, canvas_base_url: str, api_token: str, course_id: str) -> Optional[Dict[str, Any]]:
        """Fetch Canvas course data (metadata only)."""
        try:
            loop = asyncio.get_event_loop()

            def fetch_data():
                canvas = Canvas(canvas_base_url, api_token)
                course = canvas.get_course(course_id)

                # Get TA groups
                groups_data = []
                groups = list(course.get_groups(per_page=100, include=["users"]))

                for group in groups:
                    if "Term Project" not in getattr(group, "name", ""):
                        group_info = {
                            "id": group.id,
                            "name": group.name,
                            "members": [
                                {"id": user.id, "name": user.name}
                                for user in getattr(group, "users", [])
                            ]
                        }
                        groups_data.append(group_info)

                # Get assignments with metadata only
                assignments_data = []
                assignments = list(course.get_assignments(per_page=100))

                for assignment in assignments:
                    # Get submission stats
                    submissions = list(assignment.get_submissions())
                    total_submissions = len(submissions)
                    graded_submissions = len([s for s in submissions if hasattr(s, 'score') and s.score is not None])

                    assignment_info = {
                        "id": assignment.id,
                        "name": assignment.name,
                        "due_at": getattr(assignment, "due_at", None),
                        "points_possible": getattr(assignment, "points_possible", None),
                        "html_url": getattr(assignment, "html_url", None),
                        "total_submissions": total_submissions,
                        "graded_submissions": graded_submissions,
                        "ungraded_submissions": total_submissions - graded_submissions,
                        "percentage_graded": (graded_submissions / total_submissions * 100) if total_submissions > 0 else 0
                    }
                    assignments_data.append(assignment_info)

                # Calculate TA grading breakdown
                ta_breakdown = {}
                for group_info in groups_data:
                    group_name = group_info["name"]
                    # Simple distribution for now - in practice, you'd analyze actual assignments
                    ungraded_count = sum(a["ungraded_submissions"] for a in assignments_data) // len(groups_data) if groups_data else 0
                    ta_breakdown[group_name] = ungraded_count

                return {
                    "course_id": course_id,
                    "canvas_base_url": canvas_base_url,
                    "last_updated": datetime.utcnow().isoformat(),
                    "ta_groups": groups_data,
                    "assignments": assignments_data,
                    "statistics": {
                        "total_assignments": len(assignments_data),
                        "total_submissions": sum(a["total_submissions"] for a in assignments_data),
                        "total_graded": sum(a["graded_submissions"] for a in assignments_data),
                        "total_ungraded": sum(a["ungraded_submissions"] for a in assignments_data),
                        "ta_breakdown": ta_breakdown
                    }
                }

            # Run in thread pool to avoid blocking
            canvas_data = await loop.run_in_executor(self.thread_pool, fetch_data)
            return canvas_data

        except CanvasException as e:
            logger.error(f"Canvas API error for {course_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Canvas data for {course_id}: {e}")
            return None

    async def _store_course_data_s3(self, course_key: str, data: Dict[str, Any]):
        """Store course data in S3."""
        try:
            # Create S3 key
            course_id = data["course_id"]
            s3_key = f"courses/{course_id}/data.json"

            # Store data
            s3_client.put_object(
                Bucket=COURSE_DATA_BUCKET,
                Key=s3_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )

            logger.info(f"Stored course data in S3: {s3_key}")

        except Exception as e:
            logger.error(f"Error storing course data in S3 for {course_key}: {e}")
            raise

    async def _update_cache_metadata(self, course_key: str, course_id: str,
                                   canvas_base_url: str, user_count: int, data_size: int):
        """Update cache metadata in DynamoDB."""
        try:
            now = datetime.utcnow()
            ttl = int((now + timedelta(days=90)).timestamp())

            self.cache_metadata_table.put_item(
                Item={
                    'course_key': course_key,
                    'course_id': course_id,
                    'canvas_base_url': canvas_base_url,
                    'last_updated': now.isoformat(),
                    'data_size': data_size,
                    'user_count': user_count,
                    'is_active': True,
                    'error_count': 0,
                    'last_error': None,
                    'ttl': ttl
                }
            )

        except Exception as e:
            logger.error(f"Error updating cache metadata for {course_key}: {e}")


def lambda_handler(event, context):
    """Lambda handler function."""
    logger.info(f"Lambda triggered with event: {json.dumps(event)}")

    try:
        # Create fetcher and run
        fetcher = CanvasDataFetcher()

        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        results = loop.run_until_complete(fetcher.fetch_all_course_data())

        logger.info(f"Lambda execution completed: {results}")

        return {
            'statusCode': 200,
            'body': json.dumps(results)
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
    finally:
        if 'loop' in locals():
            loop.close()