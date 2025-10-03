"""Authentication-related value objects and services."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import hashlib
import secrets


@dataclass(frozen=True)
class LoginCredentials:
    """Value object for login credentials."""
    email: str
    password: str

    def __post_init__(self) -> None:
        """Validate credentials."""
        if not self.email or not self.email.strip():
            raise ValueError("Email cannot be empty")
        if not self.password or len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if "@" not in self.email:
            raise ValueError("Invalid email format")


@dataclass(frozen=True)
class AuthToken:
    """Value object for authentication token."""
    token: str
    inspector_id: UUID
    expires_at: datetime
    created_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def time_until_expiry(self) -> timedelta:
        """Get time until token expires."""
        return self.expires_at - datetime.utcnow()


@dataclass(frozen=True)
class LoginResult:
    """Value object for login operation result."""
    success: bool
    inspector_id: Optional[UUID] = None
    token: Optional[AuthToken] = None
    error_message: Optional[str] = None
    locked_until: Optional[datetime] = None
    failed_attempts: int = 0


class PasswordHasher:
    """Service for password hashing and verification."""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(32)

        # Using PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )

        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash."""
        new_hash, _ = PasswordHasher.hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed_password)

    @staticmethod
    def create_password_hash(password: str) -> str:
        """Create a complete password hash with embedded salt."""
        hashed, salt = PasswordHasher.hash_password(password)
        return f"{salt}:{hashed}"

    @staticmethod
    def verify_password_hash(password: str, password_hash: str) -> bool:
        """Verify password against complete hash."""
        try:
            salt, hashed = password_hash.split(':', 1)
            return PasswordHasher.verify_password(password, hashed, salt)
        except ValueError:
            return False


class TokenGenerator:
    """Service for generating authentication tokens."""

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_auth_token(inspector_id: UUID, expires_in_hours: int = 8) -> AuthToken:
        """Create an authentication token."""
        token = TokenGenerator.generate_token()
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=expires_in_hours)

        return AuthToken(
            token=token,
            inspector_id=inspector_id,
            expires_at=expires_at,
            created_at=created_at
        )
