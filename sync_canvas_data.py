#!/usr/bin/env python3
"""
Canvas Data Sync Script
Fetches data from Canvas API and uploads to S3
"""
import json
import boto3
from datetime import datetime
from canvasapi import Canvas

# Configuration
CANVAS_URL = "https://gatech.instructure.com"
CANVAS_COURSE_ID = "516212"  # Actual Canvas course ID (not the full ID)
S3_BUCKET = "canvas-ta-dashboard-prod-canvas-data"

def get_canvas_token():
    """Retrieve Canvas API token from Secrets Manager"""
    secretsmanager = boto3.client('secretsmanager', region_name='us-east-1')
    response = secretsmanager.get_secret_value(SecretId='canvas-ta-dashboard-prod-canvas-api-token')
    return response['SecretString']

def fetch_canvas_data():
    """Fetch course data from Canvas API"""
    print("🔍 Fetching Canvas API token from Secrets Manager...")
    canvas_token = get_canvas_token()
    
    print(f"📚 Connecting to Canvas: {CANVAS_URL}")
    canvas = Canvas(CANVAS_URL, canvas_token)
    
    print(f"📖 Fetching course: {CANVAS_COURSE_ID}")
    course = canvas.get_course(CANVAS_COURSE_ID)
    
    # Fetch course data
    course_data = {
        'id': course.id,
        'name': course.name,
        'course_code': course.course_code,
        'enrollment_term_id': getattr(course, 'enrollment_term_id', None),
        'start_at': getattr(course, 'start_at', None),
        'end_at': getattr(course, 'end_at', None),
    }
    
    print(f"✅ Course: {course.name} ({course.course_code})")
    
    # Fetch assignments
    print("📝 Fetching assignments...")
    assignments = []
    for assignment in course.get_assignments():
        assignments.append({
            'id': assignment.id,
            'name': assignment.name,
            'due_at': assignment.due_at,
            'points_possible': assignment.points_possible,
            'submission_types': assignment.submission_types,
            'published': assignment.published,
        })
    print(f"✅ Found {len(assignments)} assignments")
    
    # Fetch users (students)
    print("👥 Fetching users...")
    users = []
    for user in course.get_users(enrollment_type=['student']):
        users.append({
            'id': user.id,
            'name': user.name,
            'sortable_name': getattr(user, 'sortable_name', user.name),
            'email': getattr(user, 'email', None),
        })
    print(f"✅ Found {len(users)} users")

    # Fetch submissions
    print("📥 Fetching submissions...")
    submissions = []
    for assignment in course.get_assignments():
        try:
            for submission in assignment.get_submissions():
                submissions.append({
                    'id': submission.id,
                    'assignment_id': assignment.id,
                    'user_id': submission.user_id,
                    'workflow_state': submission.workflow_state,
                    'grade': getattr(submission, 'grade', None),
                    'score': getattr(submission, 'score', None),
                    'submitted_at': getattr(submission, 'submitted_at', None),
                    'graded_at': getattr(submission, 'graded_at', None),
                    'late': getattr(submission, 'late', False),
                })
        except Exception as e:
            print(f"⚠️  Could not fetch submissions for assignment {assignment.id}: {e}")
    print(f"✅ Found {len(submissions)} submissions")

    # Fetch enrollments
    print("📋 Fetching enrollments...")
    enrollments = []
    for enrollment in course.get_enrollments():
        enrollments.append({
            'id': enrollment.id,
            'user_id': enrollment.user_id,
            'course_id': enrollment.course_id,
            'type': enrollment.type,
            'enrollment_state': enrollment.enrollment_state,
        })
    print(f"✅ Found {len(enrollments)} enrollments")

    # Fetch groups with members
    print("👥 Fetching groups and members...")
    groups = []
    group_memberships = {}  # group_id -> [student_ids]

    try:
        for group in course.get_groups():
            group_id = group.id
            group_name = group.name

            # Fetch group members
            members = []
            try:
                for user in group.get_users():
                    members.append(user.id)
            except Exception as e:
                print(f"⚠️  Could not fetch members for group {group_name}: {e}")

            groups.append({
                'id': group_id,
                'name': group_name,
                'members_count': len(members),
                'members': members  # Add member list
            })

            group_memberships[group_id] = members

    except Exception as e:
        print(f"⚠️  Could not fetch groups: {e}")
    print(f"✅ Found {len(groups)} groups with member data")

    return {
        'course': course_data,
        'assignments': assignments,
        'users': users,
        'submissions': submissions,
        'enrollments': enrollments,
        'groups': groups,
        'last_updated': datetime.utcnow().isoformat(),
    }

def upload_to_s3(data):
    """Upload data to S3 bucket in Lambda-compatible format"""
    print(f"\n☁️  Uploading to S3 bucket: {S3_BUCKET}")
    s3 = boto3.client('s3', region_name='us-east-1')

    course_id = str(data['course']['id'])

    # Create Lambda-compatible data structure
    lambda_data = {
        'course_id': course_id,
        'timestamp': data['last_updated'],
        'assignments': data['assignments'],
        'submissions': data['submissions'],
        'users': data['users'],
        'enrollments': data['enrollments'],
        'groups': data['groups']
    }

    # Upload to canvas_data/course_{id}/latest.json (Lambda expects this path)
    latest_key = f"canvas_data/course_{course_id}/latest.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=latest_key,
        Body=json.dumps(lambda_data, indent=2),
        ContentType='application/json',
    )
    print(f"✅ Uploaded: {latest_key}")

    # Upload individual data files for separate endpoints
    files_to_upload = [
        (f"canvas_data/course_{course_id}/latest_assignments.json", data['assignments']),
        (f"canvas_data/course_{course_id}/latest_submissions.json", data['submissions']),
        (f"canvas_data/course_{course_id}/latest_users.json", data['users']),
        (f"canvas_data/course_{course_id}/latest_enrollments.json", data['enrollments']),
        (f"canvas_data/course_{course_id}/latest_groups.json", data['groups']),
    ]

    for key, file_data in files_to_upload:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(file_data, indent=2),
            ContentType='application/json',
        )
        print(f"✅ Uploaded: {key}")

    # Also create long form ID version for compatibility
    if len(course_id) <= 6:
        long_course_id = f"20960000000{course_id}"
        long_latest_key = f"canvas_data/course_{long_course_id}/latest.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=long_latest_key,
            Body=json.dumps(lambda_data, indent=2),
            ContentType='application/json',
        )
        print(f"✅ Uploaded: {long_latest_key}")

        # Upload individual files for long form too
        for key, file_data in files_to_upload:
            long_key = key.replace(f"course_{course_id}", f"course_{long_course_id}")
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=long_key,
                Body=json.dumps(file_data, indent=2),
                ContentType='application/json',
            )
            print(f"✅ Uploaded: {long_key}")

    # Upload metadata
    metadata = {
        'last_sync': data['last_updated'],
        'course_id': course_id,
        'course_name': data['course']['name'],
        'assignment_count': len(data['assignments']),
        'user_count': len(data['users']),
        'submission_count': len(data['submissions']),
        'enrollment_count': len(data['enrollments']),
        'group_count': len(data['groups']),
    }
    metadata_key = "metadata/sync_status.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType='application/json',
    )
    print(f"✅ Uploaded: {metadata_key}")

def main():
    """Main execution"""
    print("=" * 60)
    print("🚀 Canvas Data Sync - Production")
    print("=" * 60)
    
    try:
        # Fetch data from Canvas
        data = fetch_canvas_data()
        
        # Upload to S3
        upload_to_s3(data)
        
        print("\n" + "=" * 60)
        print("✅ SYNC COMPLETE!")
        print("=" * 60)
        print(f"Course: {data['course']['name']}")
        print(f"Assignments: {len(data['assignments'])}")
        print(f"Users: {len(data['users'])}")
        print(f"Submissions: {len(data['submissions'])}")
        print(f"Enrollments: {len(data['enrollments'])}")
        print(f"Groups: {len(data['groups'])}")
        print(f"Last Updated: {data['last_updated']}")
        print("\n🎉 Canvas data is now available in the dashboard!")
        print("🌐 Visit: https://d16kqfc205lnk5.cloudfront.net")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
