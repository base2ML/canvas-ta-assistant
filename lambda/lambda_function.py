"""
AWS Lambda entry point for Canvas data fetcher.
"""

import asyncio
from canvas_data_fetcher import CanvasDataFetcher


def lambda_handler(event, context):
    """Lambda entry point for Canvas data fetching."""

    # Create fetcher instance
    fetcher = CanvasDataFetcher()

    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(fetcher.fetch_all_course_data())
        return {
            'statusCode': 200,
            'body': result
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'processed_courses': 0,
                'successful_updates': 0,
                'failed_updates': 1,
                'errors': [str(e)]
            }
        }
    finally:
        loop.close()