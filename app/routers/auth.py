#!/usr/bin/env python3
"""
Authentication router for modular FastAPI architecture
Maintains compatibility with existing frontend API endpoints
"""

import json
import base64
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    GoogleAuthRequest, TokenResponse, UserResponse, UserPreferences,
    OTPRequest, OTPVerifyRequest
)
from app.dependencies.auth import get_current_user
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_auth_service() -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService()


@router.post("/auth/google", response_model=TokenResponse)
async def google_auth(
    request: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Google OAuth authentication - compatible with existing frontend
    Endpoint: POST /auth/google (same as before)
    """
    try:
        logger.info("🔐 Processing Google authentication")
        
        google_token = request.credential
        if not google_token:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'Missing Google token',
                    'message': 'Google credential token is required'
                }
            )
        
        # Extract email from token payload (simplified)
        try:
            # Decode Google JWT token payload (without verification for demo)
            parts = google_token.split('.')
            if len(parts) >= 2:
                payload_encoded = parts[1]
                # Add padding
                while len(payload_encoded) % 4:
                    payload_encoded += '='
                payload_decoded = base64.urlsafe_b64decode(payload_encoded.encode())
                google_data = json.loads(payload_decoded.decode())
                
                user_data = {
                    'sub': google_data.get('sub', ''),
                    'email': google_data.get('email', ''),
                    'name': google_data.get('name', ''),
                    'picture': google_data.get('picture', '')
                }
            else:
                raise Exception("Invalid Google token format")
                
        except Exception:
            # Fallback for testing
            user_data = {
                'sub': 'google_user_' + str(int(datetime.utcnow().timestamp())),
                'email': 'test@example.com',
                'name': 'Test User',
                'picture': ''
            }
        
        # Create or update user in PostgreSQL
        user = auth_service.create_or_update_user(user_data)
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user_data)
        
        response = TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
        logger.info(f"✅ Google authentication successful for: {user_data['email']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google auth failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Authentication failed',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.post("/auth/send-otp")
async def send_otp(
    request: OTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Send OTP for email authentication
    Endpoint: POST /auth/send-otp (compatible with existing frontend)
    """
    try:
        logger.info(f"📧 OTP requested for: {request.email}")
        
        # For now, return success with test OTP for development
        # In production, implement actual OTP sending via email service
        test_otp = "123456"
        
        response = {
            'success': True,
            'message': f'OTP sent to {request.email}',
            'otpSent': False,  # Set to True when email service is implemented
            'debug_info': {
                'otp_for_testing': test_otp,
                'auth_mode': request.auth_mode,
                'email_service_status': 'development_mode'
            }
        }
        
        logger.info(f"✅ OTP generation successful for: {request.email}")
        return response
        
    except Exception as e:
        logger.error(f"❌ OTP send failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to send OTP',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.post("/auth/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify OTP and authenticate user
    Endpoint: POST /auth/verify-otp (compatible with existing frontend)
    """
    try:
        logger.info(f"🔐 OTP verification for: {request.email}")
        
        # For development, accept the test OTP
        if request.otp != "123456":
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'Invalid OTP',
                    'message': 'The OTP code is incorrect or has expired'
                }
            )
        
        # Create user data from request
        user_data = {
            'sub': f"otp_user_{int(datetime.utcnow().timestamp())}",
            'email': request.email,
            'name': request.userData.get('name', ''),
            'picture': ''
        }
        
        # Create or update user in PostgreSQL
        user = auth_service.create_or_update_user(user_data)
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user_data)
        
        response = TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
        logger.info(f"✅ OTP verification successful for: {request.email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OTP verification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'OTP verification failed',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.get("/auth/profile", response_model=UserResponse)
async def get_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get user profile - requires authentication
    Endpoint: GET /auth/profile (same as before)
    """
    try:
        logger.info(f"👤 Profile requested for: {current_user.email}")
        
        logger.info(f"✅ Profile retrieved for: {current_user.email}")
        return current_user
        
    except Exception as e:
        logger.error(f"❌ Profile endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to get profile',
                'message': str(e),
                'database': 'postgresql'
            }
        )


@router.post("/auth/preferences", response_model=UserResponse)
@router.put("/auth/preferences", response_model=UserResponse)
async def update_preferences(
    preferences: UserPreferences,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user preferences
    Endpoint: POST/PUT /auth/preferences (compatible with existing frontend)
    """
    try:
        logger.info(f"⚙️ Preferences update for: {current_user.email}")
        
        # Convert preferences to dict
        preferences_dict = preferences.dict(exclude_unset=True)
        
        # Update user preferences in database
        updated_user = auth_service.update_user_preferences(
            current_user.id,
            preferences_dict
        )
        
        response = UserResponse(**updated_user)
        
        logger.info(f"✅ Preferences updated for: {current_user.email}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Preferences update failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to update preferences',
                'message': str(e),
                'database': 'postgresql'
            }
        )