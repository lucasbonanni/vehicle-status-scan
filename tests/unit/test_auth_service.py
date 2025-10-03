"""Unit tests for authentication service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.vehicle_inspection.application.services.auth_service import AuthenticationService
from src.vehicle_inspection.domain.value_objects.auth import LoginCredentials, LoginResult, AuthToken, PasswordHasher
from src.vehicle_inspection.domain.entities.inspector import Inspector, InspectorRole, InspectorStatus

# Mark all async tests in this module
pytestmark = pytest.mark.asyncio


class MockInspectorRepository:
    """Mock inspector repository for testing."""

    def __init__(self):
        self.inspectors = {}
        self.login_info = {}
        self.password_hashes = {}

    async def find_by_email(self, email: str) -> Inspector | None:
        """Find inspector by email."""
        for inspector in self.inspectors.values():
            if inspector.email.lower() == email.lower():
                return inspector
        return None

    async def find_by_id(self, inspector_id: UUID) -> Inspector | None:
        """Find inspector by ID."""
        return self.inspectors.get(inspector_id)

    async def update_login_info(self, inspector_id: UUID, **kwargs):
        """Update login information."""
        if inspector_id not in self.login_info:
            self.login_info[inspector_id] = {}
        self.login_info[inspector_id].update(kwargs)

    async def record_login(self, inspector_id: UUID):
        """Record successful login."""
        if inspector_id not in self.login_info:
            self.login_info[inspector_id] = {}
        self.login_info[inspector_id]['last_login'] = datetime.now()

    async def get_password_hash(self, inspector_id: UUID) -> str | None:
        """Get password hash for inspector."""
        return self.password_hashes.get(inspector_id)

    async def get_failed_attempts(self, inspector_id: UUID) -> int:
        """Get failed login attempts."""
        return self.login_info.get(inspector_id, {}).get('failed_attempts', 0)

    async def get_lockout_expiry(self, inspector_id: UUID) -> datetime | None:
        """Get account lockout expiry."""
        return self.login_info.get(inspector_id, {}).get('locked_until')

    async def update_password_hash(self, inspector_id: UUID, password_hash: str) -> bool:
        """Update password hash for inspector."""
        if inspector_id in self.inspectors:
            self.password_hashes[inspector_id] = password_hash
            return True
        return False


class MockAuthTokenRepository:
    """Mock auth token repository for testing."""

    def __init__(self):
        self.tokens = {}

    async def save_token(self, token: AuthToken):
        """Save authentication token."""
        self.tokens[token.token] = token

    async def find_token(self, token: str) -> AuthToken | None:
        """Find authentication token."""
        return self.tokens.get(token)

    async def invalidate_token(self, token: str) -> bool:
        """Invalidate authentication token."""
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens."""
        expired_tokens = [
            token for token, auth_token in self.tokens.items()
            if auth_token.is_expired
        ]
        count = len(expired_tokens)
        for token in expired_tokens:
            del self.tokens[token]
        return count


@pytest.fixture
def mock_inspector_repo():
    """Create mock inspector repository."""
    return MockInspectorRepository()


@pytest.fixture
def mock_token_repo():
    """Create mock token repository."""
    return MockAuthTokenRepository()


@pytest.fixture
def auth_service(mock_inspector_repo, mock_token_repo):
    """Create authentication service with mocked dependencies."""
    return AuthenticationService(mock_inspector_repo, mock_token_repo)


@pytest.fixture
def active_inspector():
    """Create an active inspector for testing."""
    inspector_id = UUID("11111111-1111-1111-1111-111111111111")
    return Inspector(
        inspector_id=inspector_id,
        email="test@example.com",
        first_name="John",
        last_name="Inspector",
        phone="+1234567890",
        role=InspectorRole.SENIOR,
        license_number="INS001",
        status=InspectorStatus.ACTIVE,
        hire_date=datetime.now() - timedelta(days=365)
    )


@pytest.fixture
def inactive_inspector():
    """Create an inactive inspector for testing."""
    inspector_id = UUID("22222222-2222-2222-2222-222222222222")
    return Inspector(
        inspector_id=inspector_id,
        email="inactive@example.com",
        first_name="Jane",
        last_name="Inactive",
        phone="+1234567891",
        role=InspectorRole.JUNIOR,
        license_number="INS002",
        status=InspectorStatus.INACTIVE,
        hire_date=datetime.now() - timedelta(days=100)
    )


class TestAuthenticationService:
    """Test cases for AuthenticationService."""

    @pytest.mark.asyncio
    async def test_successful_login(self, auth_service, mock_inspector_repo, active_inspector):
        """Test successful login with valid credentials."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        credentials = LoginCredentials(
            email=active_inspector.email,
            password=password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is True
        assert result.inspector_id == active_inspector.id
        assert result.token is not None
        assert result.token.inspector_id == active_inspector.id
        assert result.error_message is None
        assert result.failed_attempts == 0

    @pytest.mark.asyncio
    async def test_login_with_invalid_email(self, auth_service):
        """Test login with non-existent email."""
        credentials = LoginCredentials(
            email="nonexistent@example.com",
            password="testpassword123"
        )

        result = await auth_service.login(credentials)

        assert result.success is False
        assert result.error_message == "Invalid email or password"
        assert result.inspector_id is None
        assert result.token is None

    async def test_login_with_invalid_password(self, auth_service, mock_inspector_repo, active_inspector):
        """Test login with incorrect password."""
        # Setup
        correct_password = "testpassword123"
        wrong_password = "wrongpassword"
        password_hash = PasswordHasher.create_password_hash(correct_password)

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        credentials = LoginCredentials(
            email=active_inspector.email,
            password=wrong_password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is False
        assert result.error_message == "Invalid email or password"
        assert result.inspector_id is None
        assert result.token is None
        assert result.failed_attempts == 1

    async def test_login_with_inactive_inspector(self, auth_service, mock_inspector_repo, inactive_inspector):
        """Test login with inactive inspector account."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)

        mock_inspector_repo.inspectors[inactive_inspector.id] = inactive_inspector
        mock_inspector_repo.password_hashes[inactive_inspector.id] = password_hash

        credentials = LoginCredentials(
            email=inactive_inspector.email,
            password=password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is False
        assert result.error_message == "Account is not active"

    async def test_account_lockout_after_max_failed_attempts(self, auth_service, mock_inspector_repo, active_inspector):
        """Test account lockout after maximum failed login attempts."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)
        wrong_password = "wrongpassword"

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        credentials = LoginCredentials(
            email=active_inspector.email,
            password=wrong_password
        )

        # Execute multiple failed attempts
        for attempt in range(1, AuthenticationService.MAX_FAILED_ATTEMPTS):
            result = await auth_service.login(credentials)
            assert result.success is False
            assert result.failed_attempts == attempt

        # Final attempt should lock the account
        result = await auth_service.login(credentials)
        assert result.success is False
        assert result.error_message == "Account locked due to too many failed login attempts"
        assert result.locked_until is not None

    async def test_login_with_locked_account(self, auth_service, mock_inspector_repo, active_inspector):
        """Test login attempt with locked account."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        # Lock the account
        lockout_expiry = datetime.utcnow() + timedelta(hours=1)
        mock_inspector_repo.login_info[active_inspector.id] = {
            'failed_attempts': AuthenticationService.MAX_FAILED_ATTEMPTS,
            'locked_until': lockout_expiry
        }

        credentials = LoginCredentials(
            email=active_inspector.email,
            password=password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is False
        assert result.error_message == "Account is temporarily locked due to too many failed login attempts"
        assert result.locked_until == lockout_expiry

    async def test_successful_login_resets_failed_attempts(self, auth_service, mock_inspector_repo, active_inspector):
        """Test that successful login resets failed attempt counter."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        # Set some failed attempts
        mock_inspector_repo.login_info[active_inspector.id] = {'failed_attempts': 3}

        credentials = LoginCredentials(
            email=active_inspector.email,
            password=password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is True
        # Check that failed attempts were reset
        assert mock_inspector_repo.login_info[active_inspector.id]['failed_attempts'] == 0

    async def test_validate_valid_token(self, auth_service, mock_inspector_repo, mock_token_repo, active_inspector):
        """Test token validation with valid token."""
        # Setup
        auth_token = AuthToken(
            token="valid_token_123",
            inspector_id=active_inspector.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_token_repo.tokens[auth_token.token] = auth_token

        # Execute
        result = await auth_service.validate_token(auth_token.token)

        # Assert
        assert result is not None
        assert result.id == active_inspector.id

    async def test_validate_expired_token(self, auth_service, mock_token_repo, active_inspector):
        """Test token validation with expired token."""
        # Setup
        expired_token = AuthToken(
            token="expired_token_123",
            inspector_id=active_inspector.id,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            created_at=datetime.utcnow() - timedelta(hours=2)
        )

        mock_token_repo.tokens[expired_token.token] = expired_token

        # Execute
        result = await auth_service.validate_token(expired_token.token)

        # Assert
        assert result is None

    async def test_validate_nonexistent_token(self, auth_service):
        """Test token validation with non-existent token."""
        result = await auth_service.validate_token("nonexistent_token")
        assert result is None

    async def test_logout_success(self, auth_service, mock_token_repo, active_inspector):
        """Test successful logout."""
        # Setup
        auth_token = AuthToken(
            token="logout_token_123",
            inspector_id=active_inspector.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )

        mock_token_repo.tokens[auth_token.token] = auth_token

        # Execute
        await auth_service.logout(auth_token.token)

        # Assert - token should be removed
        assert auth_token.token not in mock_token_repo.tokens

    async def test_logout_with_invalid_token(self, auth_service):
        """Test logout with invalid token."""
        # This should not raise an exception
        await auth_service.logout("invalid_token")

    async def test_case_insensitive_email_login(self, auth_service, mock_inspector_repo, active_inspector):
        """Test that email login is case insensitive."""
        # Setup
        password = "testpassword123"
        password_hash = PasswordHasher.create_password_hash(password)

        mock_inspector_repo.inspectors[active_inspector.id] = active_inspector
        mock_inspector_repo.password_hashes[active_inspector.id] = password_hash

        # Test with uppercase email
        credentials = LoginCredentials(
            email=active_inspector.email.upper(),
            password=password
        )

        # Execute
        result = await auth_service.login(credentials)

        # Assert
        assert result.success is True
        assert result.inspector_id == active_inspector.id
