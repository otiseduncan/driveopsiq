"""
User database model with enhanced security and validation.
"""
import re
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.exc import StatementError

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.auth import APIKey, RefreshToken, PasswordResetToken


class User(Base):
    """
    User database model with enhanced security and data integrity.
    
    Security Features:
    - Email format validation
    - Password hash format validation  
    - URL validation for profile fields
    - Input sanitization for text fields
    - Database constraints for data integrity
    """
    
    __tablename__ = "users"
    
    # Table constraints for data integrity and security
    __table_args__ = (
        # Ensure email is valid format
        CheckConstraint(
            "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="valid_email_format"
        ),
        # Ensure password hash is from a secure algorithm
        CheckConstraint(
            "hashed_password ~ '^\\$argon2|^\\$bcrypt|^\\$scrypt'",
            name="secure_password_hash"
        ),
        # Ensure full name is not empty and reasonable length
        CheckConstraint(
            "length(trim(full_name)) >= 2 AND length(full_name) <= 255",
            name="valid_full_name"
        ),
        # Composite index for common query patterns
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_created_at", "created_at"),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic user information with enhanced validation
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False,
        comment="User email address (validated format)"
    )
    full_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="User full name (sanitized, 2-255 chars)"
    )
    hashed_password: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Secure password hash (Argon2/bcrypt/scrypt only)"
    )
    
    # User status and permissions with explicit defaults
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False,
        server_default="true",
        comment="Account active status"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        server_default="false",
        comment="Superuser privileges"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        server_default="false",
        comment="Email verification status"
    )
    
    # Optional profile information with validation
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        comment="Avatar image URL (validated)"
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="User biography (sanitized)"
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True,
        comment="User location (sanitized)"
    )
    website_url: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        comment="Personal website URL (validated)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # Validation methods for enhanced security
    @validates('email')
    def validate_email(self, key: str, address: str) -> str:
        """Validate and normalize email address."""
        if not address or not isinstance(address, str):
            raise ValueError("Email address is required and must be a string")
        
        # Normalize email
        normalized = address.lower().strip()
        
        # Basic format validation
        if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', normalized):
            raise ValueError("Invalid email format")
        
        # Length check
        if len(normalized) > 255:
            raise ValueError("Email address too long")
        
        return normalized

    @validates('full_name')
    def validate_full_name(self, key: str, name: str) -> str:
        """Validate and sanitize full name."""
        if not name or not isinstance(name, str):
            raise ValueError("Full name is required and must be a string")
        
        # Sanitize: remove extra whitespace and potentially dangerous characters
        sanitized = re.sub(r'\s+', ' ', name.strip())
        
        # Security check for dangerous characters
        if re.search(r'[<>"\'/\\&;]', sanitized):
            raise ValueError("Full name contains invalid characters")
        
        # Length validation
        if len(sanitized) < 2 or len(sanitized) > 255:
            raise ValueError("Full name must be between 2 and 255 characters")
        
        return sanitized

    @validates('hashed_password')
    def validate_hashed_password(self, key: str, password_hash: str) -> str:
        """Validate password hash format for security."""
        if not password_hash or not isinstance(password_hash, str):
            raise ValueError("Password hash is required and must be a string")
        
        # Ensure hash is from a secure algorithm
        secure_prefixes = ['$argon2', '$bcrypt', '$scrypt']
        if not any(password_hash.startswith(prefix) for prefix in secure_prefixes):
            raise ValueError("Password hash must be from a secure algorithm (Argon2, bcrypt, or scrypt)")
        
        return password_hash

    @validates('avatar_url', 'website_url')
    def validate_url(self, key: str, url: Optional[str]) -> Optional[str]:
        """Validate URL fields."""
        if url is None or url == '':
            return None
        
        if not isinstance(url, str):
            raise ValueError(f"{key} must be a string")
        
        url = url.strip()
        
        # Basic URL format validation
        if not re.match(r'^https?://[^\s<>"\'{|}\\^`[\]]+$', url):
            raise ValueError(f"Invalid {key} format")
        
        # Length check
        if len(url) > 500:
            raise ValueError(f"{key} too long")
        
        return url

    @validates('bio', 'location')
    def validate_text_fields(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate and sanitize text fields."""
        if value is None or value == '':
            return None
        
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        
        # Sanitize and normalize whitespace
        sanitized = re.sub(r'\s+', ' ', value.strip())
        
        # Security check for dangerous characters (more lenient for bio)
        if re.search(r'[<>"\'/\\]', sanitized):
            raise ValueError(f"{key} contains potentially unsafe characters")
        
        # Length limits
        max_length = 1000 if key == 'bio' else 255
        if len(sanitized) > max_length:
            raise ValueError(f"{key} too long (max {max_length} characters)")
        
        return sanitized

    @validates('is_active', 'is_superuser', 'is_verified')
    def validate_boolean_fields(self, key: str, value: bool) -> bool:
        """Validate boolean fields with type checking."""
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean value")
        return value

    def is_password_hash_secure(self) -> bool:
        """Check if the current password hash uses a secure algorithm."""
        return self.hashed_password.startswith('$argon2')

    def needs_password_upgrade(self) -> bool:
        """Check if password needs upgrading to more secure hash."""
        return not self.is_password_hash_secure()

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', active={self.is_active})>"