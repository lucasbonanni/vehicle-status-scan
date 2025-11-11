"""Authentication service for inspector login.

Implements JWT-based authentication following FastAPI OAuth2 security best practices.
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
"""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from uuid import UUID
import os

from src.vehicle_inspection.domain.value_objects.auth import (
    LoginCredentials,
    LoginResult,
    PasswordHasher,
    TokenGenerator,
)
from src.vehicle_inspection.infrastructure.logging import (
    get_logger,
    log_authentication_attempt,
)

if TYPE_CHECKING:
    from src.vehicle_inspection.application.ports.repositories import (
        InspectorRepository,
        AuthTokenRepository,
    )
    from src.vehicle_inspection.domain.entities.inspector import Inspector


class AuthenticationService:
    """Service for inspector authentication and authorization using JWT."""

    # Account lockout settings
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_HOURS = 1

    # JWT configuration from environment
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "your-super-secret-key-change-in-production"
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    TOKEN_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))

    def __init__(
        self,
        inspector_repository: "InspectorRepository",
        token_repository: "AuthTokenRepository",
    ):
        self._inspector_repository = inspector_repository
        self._token_repository = token_repository
        self._logger = get_logger(__name__)

    async def login(self, credentials: LoginCredentials) -> LoginResult:
        """Authenticate inspector and return JWT token.

        Returns a LoginResult containing a JWT token if authentication is successful.
        """
        email = credentials.email.lower().strip()
        self._logger.info(f"Login attempt for email: {email}")

        try:
            # Find inspector by email
            inspector = await self._inspector_repository.find_by_email(email)

            if not inspector:
                log_authentication_attempt(
                    self._logger, email, False, failure_reason="inspector_not_found"
                )
                return LoginResult(
                    success=False, error_message="Invalid email or password"
                )

            # Check if account is locked
            if await self._is_account_locked(inspector):
                log_authentication_attempt(
                    self._logger,
                    email,
                    False,
                    failure_reason="account_locked",
                    inspector_id=str(inspector.id),
                )
                return LoginResult(
                    success=False,
                    error_message="Account is temporarily locked due to too many failed login attempts",
                    locked_until=await self._get_lockout_expiry(inspector),
                )

            # Check if inspector is active
            if not inspector.can_perform_inspections():
                log_authentication_attempt(
                    self._logger,
                    email,
                    False,
                    failure_reason="account_inactive",
                    inspector_id=str(inspector.id),
                )
                return LoginResult(success=False, error_message="Account is not active")

            # Get stored password hash from database
            password_hash = await self._get_password_hash(inspector.id)

            if not password_hash:
                self._logger.error(
                    f"No password hash found for inspector {inspector.id}"
                )
                log_authentication_attempt(
                    self._logger,
                    email,
                    False,
                    failure_reason="no_password_hash",
                    inspector_id=str(inspector.id),
                )
                return LoginResult(success=False, error_message="Authentication error")

            # Verify password
            if not PasswordHasher.verify_password_hash(
                credentials.password, password_hash
            ):
                # Record failed attempt
                await self._record_failed_login(inspector)

                failed_attempts = await self._get_failed_attempts(inspector.id)

                if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                    lockout_expiry = await self._lock_account(inspector.id)
                    self._logger.warning(
                        f"Account locked for inspector {inspector.id} after {failed_attempts} failed attempts"
                    )
                    log_authentication_attempt(
                        self._logger,
                        email,
                        False,
                        failure_reason="account_locked_after_failures",
                        inspector_id=str(inspector.id),
                        failed_attempts=failed_attempts,
                    )
                    return LoginResult(
                        success=False,
                        error_message="Account locked due to too many failed login attempts",
                        locked_until=lockout_expiry,
                        failed_attempts=failed_attempts,
                    )

                log_authentication_attempt(
                    self._logger,
                    email,
                    False,
                    failure_reason="invalid_password",
                    inspector_id=str(inspector.id),
                    failed_attempts=failed_attempts,
                )
                return LoginResult(
                    success=False,
                    error_message="Invalid email or password",
                    failed_attempts=failed_attempts,
                )

            # Successful login - reset failed attempts and record login
            await self._inspector_repository.update_login_info(
                inspector.id, failed_attempts=0
            )
            await self._inspector_repository.record_login(inspector.id)

            # Generate JWT token following FastAPI best practices
            auth_token = TokenGenerator.generate_jwt_token(
                inspector_id=inspector.id,
                secret_key=self.JWT_SECRET_KEY,
                algorithm=self.JWT_ALGORITHM,
                expires_in_hours=self.TOKEN_EXPIRY_HOURS,
            )

            # Save token metadata to repository (optional, for audit trail)
            await self._token_repository.save_token(auth_token)

            self._logger.info(
                f"Successful login for inspector {inspector.id} with JWT token expiry {auth_token.expires_at}"
            )
            log_authentication_attempt(
                self._logger,
                email,
                True,
                inspector_id=str(inspector.id),
                token_expires_at=auth_token.expires_at.isoformat(),
            )

            return LoginResult(
                success=True, inspector_id=inspector.id, token=auth_token
            )

        except Exception as e:
            self._logger.error(f"Login error for {email}: {str(e)}", exc_info=True)
            log_authentication_attempt(
                self._logger, email, False, failure_reason="service_error", error=str(e)
            )
            return LoginResult(
                success=False, error_message="Authentication service error"
            )

    async def validate_token(self, token: str) -> Optional["Inspector"]:
        """Validate JWT token and return inspector if valid."""
        try:
            # Verify and decode JWT token
            payload = TokenGenerator.verify_jwt_token(
                token=token,
                secret_key=self.JWT_SECRET_KEY,
                algorithm=self.JWT_ALGORITHM,
            )

            # Extract inspector ID from token
            inspector_id_str = payload.get("sub")
            if not inspector_id_str:
                self._logger.debug("Token missing subject (inspector ID)")
                return None

            # Convert string UUID back to UUID
            try:
                inspector_id = UUID(inspector_id_str)
            except ValueError:
                self._logger.debug(f"Invalid inspector ID in token: {inspector_id_str}")
                return None

            # Find inspector in repository
            inspector = await self._inspector_repository.find_by_id(inspector_id)

            if not inspector:
                self._logger.warning(
                    f"Inspector {inspector_id} not found for valid JWT token"
                )
                return None

            if not inspector.can_perform_inspections():
                self._logger.debug(
                    f"Inspector {inspector_id} cannot perform inspections"
                )
                return None

            self._logger.debug(
                f"JWT token validated successfully for inspector {inspector.id}"
            )
            return inspector

        except ValueError as e:
            self._logger.debug(f"JWT token validation failed: {str(e)}")
            return None
        except Exception as e:
            self._logger.error(
                f"Unexpected error during token validation: {str(e)}", exc_info=True
            )
            return None

        except Exception as e:
            self._logger.error(f"Token validation error: {str(e)}", exc_info=True)
            return None

    async def logout(self, token: str) -> bool:
        """Logout inspector by invalidating token."""
        try:
            success = await self._token_repository.invalidate_token(token)
            if success:
                self._logger.info("Inspector logged out successfully")
            else:
                self._logger.warning(
                    "Logout failed - token not found or already invalid"
                )
            return success
        except Exception as e:
            self._logger.error(f"Logout error: {str(e)}", exc_info=True)
            return False

    async def change_password(
        self, inspector_id: UUID, old_password: str, new_password: str
    ) -> bool:
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
            if not current_hash or not PasswordHasher.verify_password_hash(
                old_password, current_hash
            ):
                return False

            # Create new password hash
            new_hash = PasswordHasher.create_password_hash(new_password)

            # Update password
            return await self._inspector_repository.update_password_hash(
                inspector_id, new_hash
            )

        except Exception:
            return False

    async def reset_password(self, inspector_id: UUID, new_password: str) -> bool:
        """Reset inspector password (admin function)."""
        try:
            if len(new_password) < 8:
                return False

            new_hash = PasswordHasher.create_password_hash(new_password)
            return await self._inspector_repository.update_password_hash(
                inspector_id, new_hash
            )

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
            lockout_expiry = await self._inspector_repository.get_lockout_expiry(
                inspector.id
            )
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
            inspector.id, failed_attempts=failed_attempts + 1
        )

    async def _get_failed_attempts(self, inspector_id: UUID) -> int:
        """Get number of failed login attempts."""
        try:
            return await self._inspector_repository.get_failed_attempts(inspector_id)
        except Exception:
            return 0

    async def _lock_account(self, inspector_id: UUID) -> datetime:
        """Lock inspector account."""
        lockout_expiry = datetime.utcnow() + timedelta(
            hours=self.LOCKOUT_DURATION_HOURS
        )
        await self._inspector_repository.update_login_info(
            inspector_id,
            failed_attempts=self.MAX_FAILED_ATTEMPTS,
            locked_until=lockout_expiry,
        )
        return lockout_expiry
