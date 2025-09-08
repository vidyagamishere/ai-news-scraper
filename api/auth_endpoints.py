"""
Authentication endpoints for AI News Scraper API
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List

from auth_models import (
    User, UserCreate, UserLogin, GoogleAuthRequest, 
    PreferencesUpdate, AuthResponse, AITopic
)
from auth_service import AuthService

# Initialize router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Global auth service (will be initialized in main.py)
auth_service: Optional[AuthService] = None

def init_auth_service(service: AuthService):
    """Initialize the auth service"""
    global auth_service
    auth_service = service

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    user = auth_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

@auth_router.post("/signup", response_model=AuthResponse)
async def signup(user_data: UserCreate):
    """Create a new user account"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        print(f"Signup attempt: {user_data.email}, {user_data.name}")  # Debug logging
        user = auth_service.create_user(user_data)
        response = auth_service.generate_auth_response(user)
        return AuthResponse(**response)
    except ValueError as e:
        print(f"Signup validation error: {str(e)}")  # Debug logging
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Signup unexpected error: {str(e)}")  # Debug logging
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@auth_router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    """Authenticate user with email and password"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    user = auth_service.authenticate_user(login_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    response = auth_service.generate_auth_response(user)
    return AuthResponse(**response)

@auth_router.post("/google", response_model=AuthResponse)
async def google_auth(auth_data: GoogleAuthRequest):
    """Authenticate user with Google OAuth"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    try:
        user = auth_service.google_authenticate(auth_data.id_token)
        if not user:
            raise HTTPException(status_code=401, detail="Google authentication failed")
        
        response = auth_service.generate_auth_response(user)
        return AuthResponse(**response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")

@auth_router.get("/profile", response_model=User)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@auth_router.put("/preferences", response_model=User)
async def update_preferences(
    preferences: PreferencesUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user preferences"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    # Convert Pydantic model to dict, excluding None values
    preferences_dict = preferences.model_dump(exclude_none=True)
    
    updated_user = auth_service.update_user_preferences(current_user.id, preferences_dict)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

@auth_router.get("/topics", response_model=List[AITopic])
async def get_topics():
    """Get all available AI topics"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    return auth_service.get_available_topics()

# Subscription endpoints
subscription_router = APIRouter(prefix="/subscription", tags=["Subscription"])

@subscription_router.post("/upgrade", response_model=User)
async def upgrade_subscription(current_user: User = Depends(get_current_user)):
    """Upgrade user to premium subscription"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    if current_user.subscription_tier.value == "premium":
        raise HTTPException(status_code=400, detail="User is already on premium plan")
    
    updated_user = auth_service.upgrade_user_subscription(current_user.id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

@subscription_router.get("/preferences", response_model=User)
async def get_subscription_preferences(current_user: User = Depends(get_current_user)):
    """Get user's subscription and preferences"""
    return current_user

@subscription_router.post("/preferences", response_model=User)
async def update_subscription_preferences(
    preferences: PreferencesUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user's subscription preferences"""
    return await update_preferences(preferences, current_user)

# Admin endpoints
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.get("/subscribers")
async def get_subscribers(current_user: User = Depends(get_current_user)):
    """Get all subscribers (admin only)"""
    # For now, this is a placeholder - you would implement proper admin role checking
    if not auth_service:
        raise HTTPException(status_code=500, detail="Authentication service not initialized")
    
    # This is a basic implementation - you would add proper admin authorization
    return {"message": "Admin endpoint - implement proper authorization"}

@admin_router.get("/subscribers/stats")
async def get_subscriber_stats(current_user: User = Depends(get_current_user)):
    """Get subscriber statistics (admin only)"""
    # Placeholder for subscriber statistics
    return {
        "total_users": 0,
        "premium_users": 0,
        "free_users": 0,
        "active_users": 0
    }