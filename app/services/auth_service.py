#!/usr/bin/env python3
"""
Authentication service for modular FastAPI architecture
"""

import json
import os
import logging
import traceback
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from db_service import get_database_service

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET', 'ai-news-jwt-secret-2025-default')
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
        logger.info(f"🔐 AuthService initialized - JWT secret length: {len(self.jwt_secret)}, Google Client ID: {'✅' if self.google_client_id else '❌'}")
        
        if self.DEBUG:
            logger.debug(f"🔍 Debug mode enabled in AuthService")
            logger.debug(f"🔍 JWT secret set: {'✅' if self.jwt_secret else '❌'}")
            logger.debug(f"🔍 Google Client ID: {self.google_client_id[:20]}..." if self.google_client_id else "🔍 No Google Client ID set")
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT token with HMAC-SHA256 signature"""
        try:
            user_email = user_data.get('email', 'unknown')
            logger.info(f"🔐 Creating JWT token for user: {user_email}")
            
            if self.DEBUG:
                logger.debug(f"🔍 User data for JWT: {user_data}")
            
            # Create JWT header
            header = {
                "alg": "HS256",
                "typ": "JWT"
            }
            
            # Create JWT payload with expiration
            payload = {
                "sub": user_data.get('sub', ''),
                "email": user_data.get('email', ''),
                "name": user_data.get('name', ''),
                "picture": user_data.get('picture', ''),
                "is_admin": user_data.get('is_admin', False),
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            }
            
            if self.DEBUG:
                logger.debug(f"🔍 JWT payload created: {payload}")
                logger.debug(f"🔍 JWT header: {header}")
            
            # Encode header and payload
            header_encoded = base64.urlsafe_b64encode(
                json.dumps(header, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            payload_encoded = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(',', ':')).encode()
            ).decode().rstrip('=')
            
            # Create signature
            message = f"{header_encoded}.{payload_encoded}"
            signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
            
            # Create final JWT token
            jwt_token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
            
            if self.DEBUG:
                logger.debug(f"🔍 JWT token structure: {len(header_encoded)}.{len(payload_encoded)}.{len(signature_encoded)}")
                logger.debug(f"🔍 JWT token first 50 chars: {jwt_token[:50]}...")
            
            logger.info(f"✅ JWT token created successfully for: {user_data.get('email', 'unknown')}")
            return jwt_token
            
        except Exception as e:
            logger.error(f"❌ JWT token creation failed: {str(e)}")
            if self.DEBUG:
                logger.debug(f"🔍 JWT creation error details: {traceback.format_exc()}")
            raise Exception(f"Token creation failed: {str(e)}")
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and extract user data"""
        try:
            logger.info("🔐 Verifying JWT token...")
            
            if self.DEBUG:
                logger.debug(f"🔍 Token length: {len(token)}")
                logger.debug(f"🔍 Token first 50 chars: {token[:50]}...")
            
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("❌ Invalid JWT token format")
                if self.DEBUG:
                    logger.debug(f"🔍 Token parts count: {len(parts)}")
                return None
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            if self.DEBUG:
                logger.debug(f"🔍 Token parts lengths: {len(header_encoded)}.{len(payload_encoded)}.{len(signature_encoded)}")
            
            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
            
            # Add padding if needed
            signature_to_verify = signature_encoded
            while len(signature_to_verify) % 4:
                signature_to_verify += '='
            
            expected_with_padding = expected_signature_encoded
            while len(expected_with_padding) % 4:
                expected_with_padding += '='
            
            if signature_to_verify != expected_with_padding:
                logger.warning("❌ JWT token signature verification failed")
                if self.DEBUG:
                    logger.debug(f"🔍 Expected signature: {expected_with_padding[:20]}...")
                    logger.debug(f"🔍 Received signature: {signature_to_verify[:20]}...")
                return None
            
            if self.DEBUG:
                logger.debug(f"🔍 JWT signature verification successful")
            
            # Decode payload
            payload_with_padding = payload_encoded
            while len(payload_with_padding) % 4:
                payload_with_padding += '='
            
            payload_decoded = base64.urlsafe_b64decode(payload_with_padding.encode())
            payload_data = json.loads(payload_decoded.decode())
            
            if self.DEBUG:
                logger.debug(f"🔍 Decoded payload: {payload_data}")
            
            # Check expiration
            current_time = int(datetime.utcnow().timestamp())
            if payload_data.get('exp', 0) < current_time:
                logger.warning("❌ JWT token has expired")
                if self.DEBUG:
                    logger.debug(f"🔍 Token exp: {payload_data.get('exp', 0)}, Current: {current_time}")
                return None
            
            if self.DEBUG:
                logger.debug(f"🔍 JWT token expiration check passed")
            
            logger.info(f"✅ JWT token verified successfully for: {payload_data.get('email', 'unknown')}")
            return payload_data
            
        except Exception as e:
            logger.error(f"❌ JWT token verification failed: {str(e)}")
            if self.DEBUG:
                logger.debug(f"🔍 JWT verification error details: {traceback.format_exc()}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from PostgreSQL database"""
        try:
            if self.DEBUG:
                logger.debug(f"🔍 Looking up user by email: {email}")
            
            db = get_database_service()
            
            query = """
                SELECT id, email, name, profile_image, subscription_tier, preferences, 
                       created_at, last_login_at, verified_email, is_admin
                FROM users 
                WHERE email = %s
            """
            
            if self.DEBUG:
                logger.debug(f"🔍 Executing user lookup query")
            
            result = db.execute_query(query, (email,), fetch_one=True)
            
            if self.DEBUG:
                logger.debug(f"🔍 User lookup result: {'Found' if result else 'Not found'}")
            
            if result:
                user_dict = dict(result)
                # Parse preferences JSON
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                
                # Ensure admin flag defaults to False if column doesn't exist yet
                if 'is_admin' not in user_dict or user_dict['is_admin'] is None:
                    user_dict['is_admin'] = email == 'admin@vidyagam.com'
                
                logger.info(f"✅ User found: {email} (Admin: {user_dict.get('is_admin', False)})")
                return user_dict
            else:
                logger.info(f"👤 User not found: {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get user by email: {str(e)}")
            # If column doesn't exist, try without is_admin column
            if 'is_admin' in str(e):
                try:
                    query = """
                        SELECT id, email, name, profile_image, subscription_tier, preferences, 
                               created_at, last_login_at, verified_email
                        FROM users 
                        WHERE email = %s
                    """
                    result = db.execute_query(query, (email,), fetch_one=True)
                    if result:
                        user_dict = dict(result)
                        if user_dict.get('preferences'):
                            if isinstance(user_dict['preferences'], str):
                                user_dict['preferences'] = json.loads(user_dict['preferences'])
                        user_dict['is_admin'] = email == 'admin@vidyagam.com'
                        logger.info(f"✅ User found (fallback): {email} (Admin: {user_dict.get('is_admin', False)})")
                        return user_dict
                except Exception:
                    pass
            return None
    
    def create_or_update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user in PostgreSQL database"""
        try:
            db = get_database_service()
            
            # First, ensure is_admin column exists
            try:
                db.execute_query("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE
                """)
                logger.info("✅ Ensured is_admin column exists")
            except Exception as col_error:
                logger.warning(f"⚠️ Could not ensure is_admin column: {str(col_error)}")
            
            # Check if user exists
            existing_user = self.get_user_by_email(user_data['email'])
            
            # Check if this is an admin user
            is_admin = user_data.get('email') == 'admin@vidyagam.com'
            
            if existing_user:
                # Update existing user with admin flag
                query = """
                    UPDATE users 
                    SET name = %s, profile_image = %s, is_admin = %s, last_login_at = CURRENT_TIMESTAMP
                    WHERE email = %s
                    RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email, is_admin
                """
                
                result = db.execute_query(
                    query, 
                    (user_data.get('name'), user_data.get('picture'), is_admin, user_data['email']),
                    fetch_one=True
                )
                
                logger.info(f"✅ User updated: {user_data['email']} (Admin: {is_admin})")
                
            else:
                # Create new user with admin flag
                user_id = user_data.get('sub', f"user_{int(datetime.utcnow().timestamp())}")
                
                query = """
                    INSERT INTO users (id, email, name, profile_image, verified_email, is_admin, created_at, last_login_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email, is_admin
                """
                
                result = db.execute_query(
                    query,
                    (user_id, user_data['email'], user_data.get('name'), user_data.get('picture'), True, is_admin),
                    fetch_one=True
                )
                
                logger.info(f"✅ New user created: {user_data['email']} (Admin: {is_admin})")
            
            if result:
                user_dict = dict(result)
                # Parse preferences JSON
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                else:
                    user_dict['preferences'] = {}
                
                # Ensure is_admin flag is properly set from database
                user_dict['is_admin'] = user_dict.get('is_admin', is_admin)
                
                if user_dict['is_admin']:
                    logger.info(f"🔑 Admin user confirmed from database: {user_dict.get('email')}")
                
                return user_dict
            else:
                raise Exception("Failed to create/update user")
                
        except Exception as e:
            logger.error(f"❌ Failed to create/update user: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user preferences in PostgreSQL database"""
        try:
            db = get_database_service()
            
            query = """
                UPDATE users 
                SET preferences = %s
                WHERE id = %s
                RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email, is_admin
            """
            
            result = db.execute_query(
                query,
                (json.dumps(preferences), user_id),
                fetch_one=True
            )
            
            if result:
                user_dict = dict(result)
                if user_dict.get('preferences'):
                    if isinstance(user_dict['preferences'], str):
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                
                # Ensure admin flag is preserved
                if 'is_admin' not in user_dict or user_dict['is_admin'] is None:
                    user_dict['is_admin'] = user_dict.get('email') == 'admin@vidyagam.com'
                
                logger.info(f"✅ User preferences updated: {user_id} (Admin: {user_dict.get('is_admin', False)})")
                return user_dict
            else:
                raise Exception("Failed to update user preferences")
                
        except Exception as e:
            logger.error(f"❌ Failed to update user preferences: {str(e)}")
            # If column doesn't exist, try without is_admin column
            if 'is_admin' in str(e):
                try:
                    query = """
                        UPDATE users 
                        SET preferences = %s
                        WHERE id = %s
                        RETURNING id, email, name, profile_image, subscription_tier, preferences, verified_email
                    """
                    result = db.execute_query(
                        query,
                        (json.dumps(preferences), user_id),
                        fetch_one=True
                    )
                    if result:
                        user_dict = dict(result)
                        if user_dict.get('preferences'):
                            if isinstance(user_dict['preferences'], str):
                                user_dict['preferences'] = json.loads(user_dict['preferences'])
                        user_dict['is_admin'] = user_dict.get('email') == 'admin@vidyagam.com'
                        logger.info(f"✅ User preferences updated (fallback): {user_id}")
                        return user_dict
                except Exception:
                    pass
            raise e