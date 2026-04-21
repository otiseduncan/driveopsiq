"""
User-related Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, constr


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    is_active: bool = Field(default=True, description="Whether user is active")


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    email: EmailStr = Field(..., description="User email address")
    full_name: constr(min_length=2, max_length=255) = Field(..., description="User full name")
    password: constr(min_length=8, max_length=128) = Field(..., description="User password")
    is_active: bool = Field(default=True, description="Whether user is active")
    is_superuser: bool = Field(default=False, description="Whether user is a superuser")
    roles: Optional[str] = Field(None, description="Comma-separated list of user roles")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[constr(min_length=2, max_length=255)] = Field(None, description="User full name")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    bio: Optional[str] = Field(None, max_length=1000, description="User biography")
    location: Optional[str] = Field(None, max_length=255, description="User location")
    website_url: Optional[str] = Field(None, max_length=500, description="Website URL")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    is_superuser: Optional[bool] = Field(None, description="Whether user is a superuser")
    roles: Optional[str] = Field(None, description="Comma-separated list of user roles")


class UserResponse(BaseModel):
    """Schema for user response data."""
    
    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="User full name")
    is_active: bool = Field(..., description="Whether user is active")
    is_superuser: bool = Field(..., description="Whether user is a superuser")
    is_verified: bool = Field(..., description="Whether user is verified")
    roles: Optional[str] = Field(None, description="Comma-separated list of user roles")
    
    # Optional profile fields
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    bio: Optional[str] = Field(None, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website_url: Optional[str] = Field(None, description="Website URL")
    
    # Timestamps
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "is_verified": True,
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "Software developer passionate about AI",
                "location": "San Francisco, CA",
                "website_url": "https://johndoe.dev",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-01T12:00:00Z",
            }
        }
    }


class UsersListResponse(BaseModel):
    """Schema for paginated user list response."""
    
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of users skipped")
    limit: int = Field(..., description="Maximum number of users returned")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                        "is_verified": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                ],
                "total": 100,
                "skip": 0,
                "limit": 50,
            }
        }
    }


class PasswordChange(BaseModel):
    """Schema for password change request."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v
