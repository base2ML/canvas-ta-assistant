"""
Cognito Pre-Signup Lambda Trigger
Validates that the user's email is in the allowed list before allowing signup
"""
import json
import os

# Load allowed emails from environment variable
ALLOWED_EMAILS_STR = os.environ.get('ALLOWED_EMAILS', '')
ALLOWED_EMAILS = set(email.strip().lower() for email in ALLOWED_EMAILS_STR.split(',') if email.strip())

def lambda_handler(event, context):
    """
    Pre-signup trigger to validate email against allowed list

    Event structure:
    {
        "request": {
            "userAttributes": {
                "email": "user@example.com"
            }
        },
        "response": {
            "autoConfirmUser": false,
            "autoVerifyEmail": false
        }
    }
    """
    print(f"Pre-signup event: {json.dumps(event)}")

    # Get the user's email from the event
    user_email = event['request']['userAttributes'].get('email', '').lower()

    print(f"Checking email: {user_email}")
    print(f"Allowed emails: {ALLOWED_EMAILS}")

    # Check if email is in allowed list
    if user_email not in ALLOWED_EMAILS:
        print(f"REJECTED: Email {user_email} is not in the allowed list")
        raise Exception(f"Email {user_email} is not authorized to create an account. Please contact the administrator.")

    # Email is allowed - auto-confirm the user
    event['response']['autoConfirmUser'] = True
    event['response']['autoVerifyEmail'] = True

    print(f"APPROVED: Email {user_email} is authorized")

    return event
