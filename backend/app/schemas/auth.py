"""
Authentication-related Pydantic schemas for request/response validation.
Enhanced with security best practices and input validation.
"""
import re
from datetime import datetime
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

# Common password validation utility
class PasswordValidatorMixin:
    """Mixin for consistent password validation across schemas."""
    
    @staticmethod
    def validate_password_strength(password: str, field_name: str = "password") -> str:
        """
        Validate password strength with comprehensive security checks.
        
        Args:
            password: Password to validate
            field_name: Name of the field for error messages
            
        Returns:
            str: Validated password
            
        Raises:
            ValueError: If password doesn't meet security requirements
        """
        if not isinstance(password, str):
            raise ValueError(f"{field_name} must be a string")
        
        # Length requirements
        if len(password) < 8:
            raise ValueError(f"{field_name} must be at least 8 characters long")
        
        if len(password) > 128:
            raise ValueError(f"{field_name} must not exceed 128 characters")
        
        # Character class requirements
        if not re.search(r'[A-Z]', password):
            raise ValueError(f"{field_name} must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValueError(f"{field_name} must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValueError(f"{field_name} must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError(f"{field_name} must contain at least one special character")
        
        # Security checks
        if password.lower() in ['password', '12345678', 'qwerty123', 'admin123']:
            raise ValueError(f"{field_name} is too common and insecure")
        
        # Check for repeated characters (simple pattern detection)
        if re.search(r'(.)\1{3,}', password):
            raise ValueError(f"{field_name} cannot contain more than 3 consecutive identical characters")
        
        return password


class UserLogin(BaseModel, PasswordValidatorMixin):
    """Schema for user login request with enhanced validation."""
    
    email: EmailStr = Field(
        ..., 
        description="User email address",
        max_length=255
    )
    password: str = Field(
        ..., 
        description="User password",
        min_length=1,  # Basic check, full validation in validator
        max_length=128
    )
    
    @field_validator("password")
    @classmethod
    def validate_login_password(cls, v: str) -> str:
        """Validate login password format (basic check only)."""
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")
        return v.strip()
    
    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: EmailStr) -> EmailStr:
        """Additional email validation."""
        email_str = str(v).lower().strip()
        if len(email_str) > 255:
            raise ValueError("Email address too long")
        return EmailStr(email_str)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
            }
        }
    )


class UserRegister(BaseModel, PasswordValidatorMixin):
    """Schema for user registration request with comprehensive validation."""
    
    email: EmailStr = Field(
        ..., 
        description="User email address",
        max_length=255
    )
    full_name: str = Field(
        ..., 
        min_length=2, 
        max_length=255, 
        description="User full name"
    )
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="User password with strength requirements"
    )
    
    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name format and security."""
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        
        # Remove extra whitespace and validate
        name = re.sub(r'\s+', ' ', v.strip())
        
        # Basic security check - no special characters that could cause issues
        if re.search(r'[<>"\'/\\&;]', name):
            raise ValueError("Full name contains invalid characters")
        
        # Length check after normalization
        if len(name) < 2:
            raise ValueError("Full name must be at least 2 characters")
        
        return name
    
    @field_validator("password")
    @classmethod
    def validate_registration_password(cls, v: str) -> str:
        """Validate password with full strength requirements."""
        return cls.validate_password_strength(v, "password")
    
    @field_validator("email")
    @classmethod  
    def validate_registration_email(cls, v: EmailStr) -> EmailStr:
        """Enhanced email validation for registration."""
        email_str = str(v).lower().strip()
        
        # Additional security checks
        if len(email_str) > 255:
            raise ValueError("Email address too long")
        
        # Check for potentially malicious patterns
        if re.search(r'[<>"\'/\\]', email_str):
            raise ValueError("Email contains invalid characters")
        
        return EmailStr(email_str)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "password": "SecurePassword123!",
            }
        }
    )


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
    """Schema for JWT token payload with enhanced validation."""
    
    sub: str = Field(..., description="Subject (user ID)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    type: str = Field(..., description="Token type (access/refresh)")
    iss: Optional[str] = Field(None, description="Issuer")
    
    @field_validator("sub")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        """Validate token subject."""
        if not v or not v.strip():
            raise ValueError("Token subject cannot be empty")
        return v.strip()
    
    @field_validator("type")
    @classmethod
    def validate_token_type(cls, v: str) -> str:
        """Validate token type."""
        if v not in ["access", "refresh"]:
            raise ValueError("Token type must be 'access' or 'refresh'")
        return v
    
    @field_validator("iss")
    @classmethod
    def validate_issuer(cls, v: Optional[str]) -> Optional[str]:
        """Validate token issuer."""
        if v is not None:
            if not v.strip():
                raise ValueError("Issuer cannot be empty if provided")
            return v.strip()
        return v
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "sub": "123",
                "exp": "2024-01-01T01:00:00Z",
                "iat": "2024-01-01T00:00:00Z",
                "type": "access",
                "iss": "SyferStackV2"
            }
        }
    )


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
    """Schema for password reset request with validation."""
    
    email: EmailStr = Field(
        ..., 
        description="User email address",
        max_length=255
    )
    
    @field_validator("email")
    @classmethod
    def validate_reset_email(cls, v: EmailStr) -> EmailStr:
        """Validate email for password reset."""
        email_str = str(v).lower().strip()
        
        if len(email_str) > 255:
            raise ValueError("Email address too long")
        
        # Security check for malicious patterns
        if re.search(r'[<>"\'/\\]', email_str):
            raise ValueError("Email contains invalid characters")
        
        return EmailStr(email_str)
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
            }
        }
    )


class PasswordReset(BaseModel, PasswordValidatorMixin):
    """Schema for password reset confirmation with enhanced security."""
    
    token: str = Field(
        ..., 
        description="Password reset token",
        min_length=1,
        max_length=512
    )
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="New password with strength requirements"
    )
    
    @field_validator("token")
    @classmethod
    def validate_reset_token(cls, v: str) -> str:
        """Validate reset token format."""
        if not v or not v.strip():
            raise ValueError("Reset token cannot be empty")
        
        # Basic format validation (alphanumeric and common token characters)
        if not re.match(r'^[A-Za-z0-9_\-\.]+$', v.strip()):
            raise ValueError("Invalid reset token format")
        
        return v.strip()
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password with full strength requirements."""
        return cls.validate_password_strength(v, "new_password")
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "token": "reset_token_here",
                "new_password": "NewSecurePassword123!",
            }
        }
    )


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