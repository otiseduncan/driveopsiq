"""
Authentication-related Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserLogin(BaseModel):
    """Schema for user login request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
            }
        }
    }


class UserRegister(BaseModel):
    """Schema for user registration request."""
    
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    
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
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "password": "SecurePassword123!",
            }
        }
    }


class Token(BaseModel):
    """Schema for authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    
    sub: str = Field(..., description="Subject (user ID)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    type: str = Field(..., description="Token type (access/refresh)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sub": "123",
                "exp": "2024-01-01T01:00:00Z",
                "iat": "2024-01-01T00:00:00Z",
                "type": "access",
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    
    refresh_token: str = Field(..., description="JWT refresh token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="User email address")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
            }
        }
    }


class PasswordReset(BaseModel):
    """Schema for password reset confirmation."""
    
    token: str = Field(..., description="Password reset token")
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
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "reset_token_here",
                "new_password": "NewSecurePassword123!",
            }
        }
    }


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""
    
    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    scopes: Optional[list[str]] = Field(None, description="API key scopes")
    expires_at: Optional[datetime] = Field(None, description="API key expiration date")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My API Key",
                "scopes": ["read:users", "write:users"],
                "expires_at": "2024-12-31T23:59:59Z",
            }
        }
    }


class APIKeyResponse(BaseModel):
    """Schema for API key response."""
    
    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key_prefix: str = Field(..., description="API key prefix (first 8 characters)")
    scopes: Optional[list[str]] = Field(None, description="API key scopes")
    is_active: bool = Field(..., description="Whether API key is active")
    usage_count: int = Field(..., description="Number of times the key has been used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "My API Key",
                "key_prefix": "sk_test_",
                "scopes": ["read:users", "write:users"],
                "is_active": True,
                "usage_count": 42,
                "last_used_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-12-31T23:59:59Z",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }


class APIKeyWithSecret(APIKeyResponse):
    """Schema for API key response with secret (only returned on creation)."""
    
    key: str = Field(..., description="Full API key (only shown once)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "My API Key",
                "key_prefix": "sk_test_",
                "key": "sk_test_abcdefghijklmnopqrstuvwxyz123456",
                "scopes": ["read:users", "write:users"],
                "is_active": True,
                "usage_count": 0,
                "last_used_at": None,
                "expires_at": "2024-12-31T23:59:59Z",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }