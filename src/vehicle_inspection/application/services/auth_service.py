"""Authentication service for inspector login."""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from src.vehicle_inspection.domain.value_objects.auth import (
    LoginCredentials,
    LoginResult,
    AuthToken,
    PasswordHasher,
    TokenGenerator
)

if TYPE_CHECKING:
    from src.vehicle_inspection.application.ports.repositories import InspectorRepository, AuthTokenRepository
    from src.vehicle_inspection.domain.entities.inspector import Inspector


class AuthenticationService:
    """Service for inspector authentication and authorization."""

    # Account lockout settings
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_HOURS = 1
    TOKEN_EXPIRY_HOURS = 8

    def __init__(
        self,
        inspector_repository: "InspectorRepository",
        token_repository: "AuthTokenRepository"
    ):
        self._inspector_repository = inspector_repository
        self._token_repository = token_repository

    async def login(self, credentials: LoginCredentials) -> LoginResult:
        """Authenticate inspector and return login result."""
        try:
            # Find inspector by email
            inspector = await self._inspector_repository.find_by_email(credentials.email.lower().strip())

            if not inspector:
                return LoginResult(
                    success=False,
                    error_message="Invalid email or password"
                )

            # Check if account is locked
            if await self._is_account_locked(inspector):
                return LoginResult(
                    success=False,
                    error_message="Account is temporarily locked due to too many failed login attempts",
                    locked_until=await self._get_lockout_expiry(inspector)
                )

            # Check if inspector is active
            if not inspector.can_perform_inspections():
                return LoginResult(
                    success=False,
                    error_message="Account is not active"
                )

            # Get stored password hash from database
            password_hash = await self._get_password_hash(inspector.id)

            if not password_hash:
                return LoginResult(
                    success=False,
                    error_message="Authentication error"
                )

            # Verify password
            if not PasswordHasher.verify_password_hash(credentials.password, password_hash):
                # Record failed attempt
                await self._record_failed_login(inspector)

                failed_attempts = await self._get_failed_attempts(inspector.id)

                if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                    lockout_expiry = await self._lock_account(inspector.id)
                    return LoginResult(
                        success=False,
                        error_message="Account locked due to too many failed login attempts",
                        locked_until=lockout_expiry,
                        failed_attempts=failed_attempts
                    )

                return LoginResult(
                    success=False,
                    error_message="Invalid email or password",
                    failed_attempts=failed_attempts
                )

            # Successful login - reset failed attempts and record login
            await self._inspector_repository.update_login_info(inspector.id, failed_attempts=0)
            await self._inspector_repository.record_login(inspector.id)

            # Generate authentication token
            auth_token = TokenGenerator.create_auth_token(
                inspector.id,
                expires_in_hours=self.TOKEN_EXPIRY_HOURS
            )

            # Save token
            await self._token_repository.save_token(auth_token)

            return LoginResult(
                success=True,
                inspector_id=inspector.id,
                token=auth_token
            )

        except Exception as e:
            return LoginResult(
                success=False,
                error_message="Authentication service error"
            )

    async def validate_token(self, token: str) -> Optional["Inspector"]:
        """Validate authentication token and return inspector if valid."""
        try:
            # Find token
            auth_token = await self._token_repository.find_token(token)

            if not auth_token or auth_token.is_expired:
                return None

            # Find inspector
            inspector = await self._inspector_repository.find_by_id(auth_token.inspector_id)

            if not inspector or not inspector.can_perform_inspections():
                return None

            return inspector

        except Exception:
            return None

    async def logout(self, token: str) -> bool:
        """Logout inspector by invalidating token."""
        try:
            return await self._token_repository.invalidate_token(token)
        except Exception:
            return False

    async def change_password(self, inspector_id: UUID, old_password: str, new_password: str) -> bool:
        """Change inspector password."""
        try:
            # Validate new password
            if len(new_password) < 8:
                return False

            # Find inspector
            inspector = await self._inspector_repository.find_by_id(inspector_id)
            if not inspector:
                return False

            # Verify old password
            current_hash = await self._get_password_hash(inspector_id)
            if not current_hash or not PasswordHasher.verify_password_hash(old_password, current_hash):
                return False

            # Create new password hash
            new_hash = PasswordHasher.create_password_hash(new_password)

            # Update password
            return await self._inspector_repository.update_password_hash(inspector_id, new_hash)

        except Exception:
            return False

    async def reset_password(self, inspector_id: UUID, new_password: str) -> bool:
        """Reset inspector password (admin function)."""
        try:
            if len(new_password) < 8:
                return False

            new_hash = PasswordHasher.create_password_hash(new_password)
            return await self._inspector_repository.update_password_hash(inspector_id, new_hash)

        except Exception:
            return False

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired authentication tokens."""
        try:
            return await self._token_repository.cleanup_expired_tokens()
        except Exception:
            return 0

    async def _is_account_locked(self, inspector: "Inspector") -> bool:
        """Check if inspector account is locked."""
        try:
            lockout_expiry = await self._inspector_repository.get_lockout_expiry(inspector.id)
            if lockout_expiry and lockout_expiry > datetime.utcnow():
                return True
            return False
        except Exception:
            return False

    async def _get_lockout_expiry(self, inspector: "Inspector") -> Optional[datetime]:
        """Get account lockout expiry time."""
        try:
            return await self._inspector_repository.get_lockout_expiry(inspector.id)
        except Exception:
            return None

    async def _get_password_hash(self, inspector_id: UUID) -> Optional[str]:
        """Get password hash from database."""
        try:
            # We'll get this from the repository implementation
            return await self._inspector_repository.get_password_hash(inspector_id)
        except Exception:
            return None

    async def _record_failed_login(self, inspector: "Inspector") -> None:
        """Record failed login attempt."""
        failed_attempts = await self._get_failed_attempts(inspector.id)
        await self._inspector_repository.update_login_info(
            inspector.id,
            failed_attempts=failed_attempts + 1
        )

    async def _get_failed_attempts(self, inspector_id: UUID) -> int:
        """Get number of failed login attempts."""
        try:
            return await self._inspector_repository.get_failed_attempts(inspector_id)
        except Exception:
            return 0

    async def _lock_account(self, inspector_id: UUID) -> datetime:
        """Lock inspector account."""
        lockout_expiry = datetime.utcnow() + timedelta(hours=self.LOCKOUT_DURATION_HOURS)
        await self._inspector_repository.update_login_info(
            inspector_id,
            failed_attempts=self.MAX_FAILED_ATTEMPTS,
            locked_until=lockout_expiry
        )
        return lockout_expiry
