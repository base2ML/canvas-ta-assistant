#!/usr/bin/env python3
"""
User Management CLI for Canvas TA Dashboard
Simple script to add, remove, and list users in S3
"""

import sys
import os
import argparse
from getpass import getpass

# Add parent directory to path to import auth module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import user_manager
from loguru import logger

def add_user(email: str, name: str, role: str = "ta", password: str = None):
    """Add a new user"""
    logger.info(f"Adding user: {email}")

    if not password:
        password = getpass("Enter password: ")
        password_confirm = getpass("Confirm password: ")

        if password != password_confirm:
            logger.error("Passwords do not match")
            return False

    success = user_manager.add_user(email, password, name, role)

    if success:
        logger.success(f"✅ User added successfully: {email}")
        print(f"\n✅ User created:")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Role: {role}")
        return True
    else:
        logger.error(f"❌ Failed to add user: {email}")
        return False


def remove_user(email: str):
    """Remove a user"""
    logger.info(f"Removing user: {email}")

    # Confirm deletion
    confirm = input(f"Are you sure you want to remove {email}? (yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("Deletion cancelled")
        return False

    success = user_manager.remove_user(email)

    if success:
        logger.success(f"✅ User removed successfully: {email}")
        return True
    else:
        logger.error(f"❌ Failed to remove user: {email}")
        return False


def list_users():
    """List all users"""
    users = user_manager.list_users()

    if not users:
        print("\nNo users found.")
        return

    print(f"\n📋 Total users: {len(users)}\n")
    print(f"{'Email':<35} {'Name':<25} {'Role':<10} {'Created':<20}")
    print("-" * 90)

    for user in users:
        email = user.get('email', 'N/A')
        name = user.get('name', 'N/A')
        role = user.get('role', 'N/A')
        created = user.get('created_at', 'N/A')[:10]  # Show only date

        print(f"{email:<35} {name:<25} {role:<10} {created:<20}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage users for Canvas TA Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a new user (interactive password prompt)
  python scripts/manage_users.py add ta1@gatech.edu "John Smith"

  # Add a user with specific role
  python scripts/manage_users.py add admin@gatech.edu "Admin User" --role admin

  # Remove a user
  python scripts/manage_users.py remove ta1@gatech.edu

  # List all users
  python scripts/manage_users.py list
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('email', help='User email address')
    add_parser.add_argument('name', help='User full name')
    add_parser.add_argument('--role', default='ta', choices=['ta', 'admin'],
                           help='User role (default: ta)')
    add_parser.add_argument('--password', help='User password (if not provided, will prompt)')

    # Remove user command
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('email', help='User email address to remove')

    # List users command
    list_parser = subparsers.add_parser('list', help='List all users')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check S3 configuration
    s3_bucket = os.getenv('S3_BUCKET_NAME', '')
    if not s3_bucket:
        print("\n⚠️  Warning: S3_BUCKET_NAME environment variable not set")
        print("Using local configuration or default bucket")
        print()

    # Execute command
    try:
        if args.command == 'add':
            add_user(args.email, args.name, args.role, args.password)
        elif args.command == 'remove':
            remove_user(args.email)
        elif args.command == 'list':
            list_users()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
