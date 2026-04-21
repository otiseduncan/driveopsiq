"""
Security utilities for authentication and authorization.
Enhanced with production-grade security measures.
"""
import logging
import secrets
import structlog
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union, Dict, List
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

# Security logger for audit trails
security_logger = structlog.get_logger("security")

@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    password_schemes: Optional[list[str]] = None
    argon2_rounds: int = 16
    token_expire_minutes: int = 15
    max_token_payload_size: int = 1024
    enforce_argon2_only: bool = True

    def __post_init__(self):
        if self.password_schemes is None:
            self.password_schemes = ["argon2"] if self.enforce_argon2_only else ["argon2", "bcrypt"]

# Global security configuration
security_config = SecurityConfig()

# Enhanced password context - Argon2 only for maximum security
pwd_context = CryptContext(
    schemes=security_config.password_schemes,
    deprecated="auto",
    argon2__memory_cost=102400,  # ~100 MB
    argon2__time_cost=security_config.argon2_rounds,
    argon2__parallelism=8,       # tune to your CPU
    bcrypt__rounds=12,  # Only used if backward compatibility enabled
)

def log_security_event(event_type: str, **kwargs):
    """Centralized security event logging."""
    security_logger.info(
        "Security event",
        event_type=event_type,
        timestamp=datetime.utcnow().isoformat(),
        **kwargs
    )

# Security scheme for bearer token
security = HTTPBearer(
    scheme_name="Bearer",
    description="Enter JWT Bearer token",
)


def verify_password(plain_password: str, hashed_password: str, user_id: Optional[str] = None) -> bool:
    """
    Verify that a given plain password matches the stored hash.
    Enforces Argon2-only policy and logs security events.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        user_id: Optional user ID for audit logging
        
    Returns:
        bool: True if password is correct
        
    Raises:
        TypeError: If inputs are not strings
        ValueError: If hash format is unsupported
    """
    # Validate input types
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        raise TypeError("Password arguments must be strings")
    
    # Enforce Argon2-only policy if configured
    if security_config.enforce_argon2_only and not hashed_password.startswith("$argon2"):
        log_security_event(
            "legacy_password_hash_detected", 
            hash_prefix=hashed_password[:10],
            user_id=user_id
        )
        raise ValueError("Unsupported password hash format - Argon2 required")
    
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        
        if not result:
            log_security_event("password_verification_failed", user_id=user_id)
        
        return result
    except Exception as e:
        log_security_event("password_verification_error", error=str(e), user_id=user_id)
        raise


def get_password_hash(password: str) -> str:
    """
    Always hash new passwords with Argon2 for maximum security.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password using Argon2
        
    Raises:
        TypeError: If password is not a string
        ValueError: If password is empty or too long
    """
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    
    if not password:
        raise ValueError("Password cannot be empty")
    
    if len(password) > 256:  # Reasonable password length limit
        raise ValueError("Password too long (max 256 characters)")
    
    hash_result = pwd_context.hash(password)
    
    # Verify the hash was created with Argon2
    if not hash_result.startswith("$argon2"):
        raise RuntimeError("Failed to create Argon2 hash")
    
    return hash_result


def needs_rehash(hashed_password: str) -> bool:
    """
    Check whether an existing hash needs upgrade to Argon2.
    
    Args:
        hashed_password: The stored password hash
        
    Returns:
        bool: True if the hash should be upgraded to Argon2
    """
    if not isinstance(hashed_password, str):
        return True  # Invalid hash needs replacement
    
    # If enforcing Argon2-only, any non-Argon2 hash needs rehashing
    if security_config.enforce_argon2_only:
        return not hashed_password.startswith("$argon2")
    
    return pwd_context.needs_update(hashed_password)

def verify_and_upgrade_password(plain_password: str, hashed_password: str) -> tuple[bool, Optional[str]]:
    """
    Verify password and return new hash if upgrade needed.
    
    Args:
        plain_password: Plain text password
        hashed_password: Stored hash
        
    Returns:
        tuple: (is_valid, new_hash_or_none)
    """
    try:
        is_valid = verify_password(plain_password, hashed_password)
        
        if is_valid and needs_rehash(hashed_password):
            new_hash = get_password_hash(plain_password)
            log_security_event("password_hash_upgraded", old_prefix=hashed_password[:10])
            return True, new_hash
        
        return is_valid, None
    except (TypeError, ValueError):
        return False, None


def upgrade_password_if_needed(plain_password: str, hashed_password: str) -> str:
    """
    Optionally called during login: verify and upgrade legacy hashes transparently.
    
    Args:
        plain_password: The plain text password from login
        hashed_password: The stored hash from database
        
    Returns:
        str: Either the original hash or a new Argon2 hash if upgrade needed
    """
    if verify_password(plain_password, hashed_password) and needs_rehash(hashed_password):
        return get_password_hash(plain_password)
    return hashed_password


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create JWT access token with enhanced security validation.
    
    Args:
        subject: Token subject (user ID - must be string or int)
        expires_delta: Token expiration time
        additional_claims: Additional claims to include
        
    Returns:
        str: JWT token
        
    Raises:
        ValueError: If inputs are invalid
        TypeError: If subject is wrong type
    """
    # Validate subject
    if not isinstance(subject, (str, int)):
        raise TypeError("Token subject must be string or int")
    
    if isinstance(subject, str) and not subject.strip():
        raise ValueError("Token subject cannot be empty")
    
    # Validate additional claims
    if additional_claims is not None:
        if not isinstance(additional_claims, dict):
            raise ValueError("Additional claims must be a dictionary")
        
        # Prevent token stuffing attacks
        payload_size = len(str(additional_claims))
        if payload_size > security_config.max_token_payload_size:
            raise ValueError(f"Token payload too large: {payload_size} > {security_config.max_token_payload_size}")
    
    # Calculate expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=security_config.token_expire_minutes
        )
    
    # Build token payload
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "iss": "SyferStackV2",  # Add issuer for verification
    }
    
    if additional_claims:
        # Validate no reserved claims are overwritten
        reserved = {"exp", "sub", "iat", "type", "iss"}
        if any(key in reserved for key in additional_claims.keys()):
            raise ValueError(f"Cannot override reserved JWT claims: {reserved}")
        to_encode.update(additional_claims)
    
    try:
        token = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        
        log_security_event("access_token_created", subject=str(subject))
        return token
        
    except Exception as e:
        log_security_event("token_creation_failed", error=str(e), subject=str(subject))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token with enhanced validation.
    
    Args:
        subject: Token subject (user ID - must be string or int)
        expires_delta: Token expiration time (default: 7 days)
        
    Returns:
        str: JWT refresh token
        
    Raises:
        ValueError: If subject is invalid
        TypeError: If subject is wrong type
    """
    # Validate subject (same as access token)
    if not isinstance(subject, (str, int)):
        raise TypeError("Token subject must be string or int")
    
    if isinstance(subject, str) and not subject.strip():
        raise ValueError("Token subject cannot be empty")
    
    # Calculate expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "iss": "SyferStackV2",
    }
    
    try:
        token = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        
        log_security_event("refresh_token_created", subject=str(subject))
        return token
        
    except Exception as e:
        log_security_event("refresh_token_creation_failed", error=str(e), subject=str(subject))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refresh token"
        )


def verify_token(token: str) -> TokenPayload:
    """
    Verify and decode JWT token with enhanced security checks.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenPayload: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    if not isinstance(token, str) or not token.strip():
        log_security_event("token_verification_failed", reason="empty_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        
        # Validate issuer if present
        if "iss" in payload and payload["iss"] != "SyferStackV2":
            log_security_event("token_verification_failed", reason="invalid_issuer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenPayload(**payload)
        
        # Check if token has expired (additional check)
        if datetime.now(timezone.utc) > token_data.exp:
            log_security_event("token_verification_failed", reason="token_expired", subject=token_data.sub)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token_data
        
    except JWTError as e:
        log_security_event("token_verification_failed", reason="jwt_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        log_security_event("token_verification_failed", reason="unexpected_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Get current authenticated user.
    
    Args:
        db: Database session
        credentials: HTTP authorization credentials
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If user not found or token invalid
    """
    token_data = verify_token(credentials.credentials)
    
    # Import here to avoid circular imports
    from app.models.user import User
    from sqlalchemy import select, or_
    
    # Try to find user by email first (new tokens), then by ID (old tokens) for compatibility
    result = await db.execute(
        select(User).where(
            or_(
                User.email == token_data.sub,
                User.id == (int(token_data.sub) if token_data.sub.isdigit() else None)
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active superuser.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current superuser
        
    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        str: Generated API key
    """
    import secrets
    return secrets.token_urlsafe(32)


class RateLimiter:
    """Simple rate limiter for API endpoints."""
    
    def __init__(self, calls: int, period: int):
        """
        Initialize rate limiter.
        
        Args:
            calls: Maximum number of calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the request
            
        Returns:
            bool: True if request is allowed
        """
        now = datetime.now(timezone.utc).timestamp()
        
        # Clean old requests
        cutoff = now - self.period
        self.requests = {
            k: v for k, v in self.requests.items()
            if v and v[-1] > cutoff
        }
        
        # Check rate limit
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests for this key
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > cutoff
        ]
        
        if len(self.requests[key]) >= self.calls:
            return False
        
        self.requests[key].append(now)
        return True
