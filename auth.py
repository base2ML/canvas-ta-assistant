"""
Simple authentication system for Canvas TA Dashboard
Uses bcrypt password hashing and JWT tokens stored in S3
"""

import os
import json
import boto3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException, status
from loguru import logger

# Environment configuration
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', '')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    if os.getenv('ENVIRONMENT', 'dev') == 'dev':
        logger.warning("Using development JWT secret")
        JWT_SECRET_KEY = 'dev-only-secret-key'  # pragma: allowlist secret
    else:
        raise ValueError("JWT_SECRET_KEY environment variable required in production")
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 7

# S3 client
s3_client = None
try:
    s3_client = boto3.client('s3')
    logger.info("S3 client initialized for authentication")
except Exception as e:
    logger.warning(f"S3 client initialization failed: {e}")


class User(BaseModel):
    """User model for authentication"""
    email: EmailStr
    name: str
    role: str = "ta"
    created_at: str
    password_hash: Optional[str] = None  # Only used internally


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT token"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class TokenPayload(BaseModel):
    """JWT token payload"""
    email: str
    name: str
    role: str
    exp: datetime


class UserManager:
    """Manages users stored in S3"""

    USERS_FILE_KEY = "auth/users.json"

    def __init__(self, s3_bucket: str):
        self.s3_bucket = s3_bucket
        self.s3_client = s3_client

    def _load_users(self) -> Dict[str, Any]:
        """Load users from S3 or local file"""
        if not self.s3_client or not self.s3_bucket:
            logger.info("S3 not configured, checking local users.json")
            if os.path.exists("users.json"):
                try:
                    with open("users.json", "r") as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading local users.json: {e}")
                    return {"users": []}
            return {"users": []}

        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self.USERS_FILE_KEY
            )
            users_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Loaded {len(users_data.get('users', []))} users from S3")
            return users_data
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning("Users file not found in S3, creating empty file")
            # Create empty users file
            empty_data = {"users": []}
            self._save_users(empty_data)
            return empty_data
        except Exception as e:
            logger.error(f"Error loading users from S3: {e}")
            return {"users": []}

    def _save_users(self, users_data: Dict[str, Any]) -> bool:
        """Save users to S3 or local file"""
        if not self.s3_client or not self.s3_bucket:
            logger.info("S3 not configured, saving to local users.json")
            try:
                with open("users.json", "w") as f:
                    json.dump(users_data, f, indent=2)
                return True
            except Exception as e:
                logger.error(f"Error saving local users.json: {e}")
                return False

        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=self.USERS_FILE_KEY,
                Body=json.dumps(users_data, indent=2).encode('utf-8'),
                ContentType='application/json',
                ServerSideEncryption='AES256'  # Encrypt at rest
            )
            logger.info(f"Saved {len(users_data.get('users', []))} users to S3")
            return True
        except Exception as e:
            logger.error(f"Error saving users to S3: {e}")
            return False

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        users_data = self._load_users()

        for user_dict in users_data.get('users', []):
            if user_dict.get('email', '').lower() == email.lower():
                return User(**user_dict)

        return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def add_user(self, email: str, password: str, name: str, role: str = "ta") -> bool:
        """Add a new user with hashed password"""
        users_data = self._load_users()

        # Check if user already exists
        if any(u.get('email', '').lower() == email.lower() for u in users_data['users']):
            logger.warning(f"User {email} already exists")
            return False

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Create new user
        new_user = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        users_data['users'].append(new_user)

        if self._save_users(users_data):
            logger.info(f"Successfully added user: {email}")
            return True
        else:
            logger.error(f"Failed to save user: {email}")
            return False

    def remove_user(self, email: str) -> bool:
        """Remove a user by email"""
        users_data = self._load_users()

        original_count = len(users_data['users'])
        users_data['users'] = [
            u for u in users_data['users']
            if u.get('email', '').lower() != email.lower()
        ]

        if len(users_data['users']) < original_count:
            if self._save_users(users_data):
                logger.info(f"Successfully removed user: {email}")
                return True

        logger.warning(f"User not found or failed to remove: {email}")
        return False

    def list_users(self) -> list:
        """List all users (without password hashes)"""
        users_data = self._load_users()
        return [
            {k: v for k, v in u.items() if k != 'password_hash'}
            for u in users_data.get('users', [])
        ]


class AuthService:
    """Authentication service for JWT token management"""

    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager

    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)

        payload = {
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "exp": expires_at
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.user_manager.get_user_by_email(email)

        if not user:
            logger.warning(f"User not found: {email}")
            return None

        if not user.password_hash:
            logger.error(f"User {email} has no password hash")
            return None

        if not self.user_manager.verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for user: {email}")
            return None

        logger.info(f"User authenticated successfully: {email}")
        return user

    def login(self, login_request: LoginRequest) -> LoginResponse:
        """Login user and return JWT token"""
        user = self.authenticate(login_request.email, login_request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = self.create_access_token(user)

        return LoginResponse(
            access_token=access_token,
            user={
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        )


# Global instances
user_manager = UserManager(S3_BUCKET_NAME)
auth_service = AuthService(user_manager)
