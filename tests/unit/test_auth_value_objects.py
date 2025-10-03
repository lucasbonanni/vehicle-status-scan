"""Unit tests for authentication value objects."""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.vehicle_inspection.domain.value_objects.auth import (
    LoginCredentials,
    AuthToken,
    LoginResult,
    PasswordHasher,
    TokenGenerator
)


class TestLoginCredentials:
    """Test cases for LoginCredentials value object."""

    def test_valid_credentials_creation(self):
        """Test creation of valid login credentials."""
        credentials = LoginCredentials(
            email="test@example.com",
            password="testpassword123"
        )

        assert credentials.email == "test@example.com"
        assert credentials.password == "testpassword123"

    def test_empty_email_raises_error(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            LoginCredentials(email="", password="testpassword123")

    def test_whitespace_only_email_raises_error(self):
        """Test that whitespace-only email raises ValueError."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            LoginCredentials(email="   ", password="testpassword123")

    def test_invalid_email_format_raises_error(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            LoginCredentials(email="notanemail", password="testpassword123")

    def test_short_password_raises_error(self):
        """Test that password shorter than 8 characters raises ValueError."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            LoginCredentials(email="test@example.com", password="short")

    def test_empty_password_raises_error(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            LoginCredentials(email="test@example.com", password="")


class TestAuthToken:
    """Test cases for AuthToken value object."""

    def test_auth_token_creation(self):
        """Test creation of authentication token."""
        inspector_id = uuid4()
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=8)

        token = AuthToken(
            token="test_token_123",
            inspector_id=inspector_id,
            expires_at=expires_at,
            created_at=created_at
        )

        assert token.token == "test_token_123"
        assert token.inspector_id == inspector_id
        assert token.expires_at == expires_at
        assert token.created_at == created_at

    def test_is_expired_with_future_expiry(self):
        """Test is_expired property with future expiry date."""
        token = AuthToken(
            token="test_token",
            inspector_id=uuid4(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )

        assert token.is_expired is False

    def test_is_expired_with_past_expiry(self):
        """Test is_expired property with past expiry date."""
        token = AuthToken(
            token="test_token",
            inspector_id=uuid4(),
            expires_at=datetime.utcnow() - timedelta(hours=1),
            created_at=datetime.utcnow() - timedelta(hours=2)
        )

        assert token.is_expired is True

    def test_time_until_expiry_positive(self):
        """Test time_until_expiry with future expiry."""
        expires_at = datetime.utcnow() + timedelta(hours=2)
        token = AuthToken(
            token="test_token",
            inspector_id=uuid4(),
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )

        time_remaining = token.time_until_expiry
        assert time_remaining.total_seconds() > 0
        assert time_remaining.total_seconds() <= 7200  # 2 hours in seconds

    def test_time_until_expiry_negative(self):
        """Test time_until_expiry with past expiry."""
        token = AuthToken(
            token="test_token",
            inspector_id=uuid4(),
            expires_at=datetime.utcnow() - timedelta(hours=1),
            created_at=datetime.utcnow() - timedelta(hours=2)
        )

        time_remaining = token.time_until_expiry
        assert time_remaining.total_seconds() < 0


class TestLoginResult:
    """Test cases for LoginResult value object."""

    def test_successful_login_result(self):
        """Test creation of successful login result."""
        inspector_id = uuid4()
        auth_token = AuthToken(
            token="success_token",
            inspector_id=inspector_id,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            created_at=datetime.utcnow()
        )

        result = LoginResult(
            success=True,
            inspector_id=inspector_id,
            token=auth_token
        )

        assert result.success is True
        assert result.inspector_id == inspector_id
        assert result.token == auth_token
        assert result.error_message is None
        assert result.locked_until is None
        assert result.failed_attempts == 0

    def test_failed_login_result(self):
        """Test creation of failed login result."""
        result = LoginResult(
            success=False,
            error_message="Invalid credentials",
            failed_attempts=3
        )

        assert result.success is False
        assert result.inspector_id is None
        assert result.token is None
        assert result.error_message == "Invalid credentials"
        assert result.locked_until is None
        assert result.failed_attempts == 3

    def test_locked_account_result(self):
        """Test creation of locked account result."""
        locked_until = datetime.utcnow() + timedelta(hours=1)

        result = LoginResult(
            success=False,
            error_message="Account locked",
            locked_until=locked_until,
            failed_attempts=5
        )

        assert result.success is False
        assert result.error_message == "Account locked"
        assert result.locked_until == locked_until
        assert result.failed_attempts == 5


class TestPasswordHasher:
    """Test cases for PasswordHasher service."""

    def test_hash_password_with_salt(self):
        """Test password hashing with provided salt."""
        password = "testpassword123"
        salt = "test_salt"

        hashed, returned_salt = PasswordHasher.hash_password(password, salt)

        assert returned_salt == salt
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_generates_salt(self):
        """Test password hashing generates salt when not provided."""
        password = "testpassword123"

        hashed, salt = PasswordHasher.hash_password(password)

        assert salt is not None
        assert len(salt) > 0
        assert hashed != password

    def test_same_password_same_salt_same_hash(self):
        """Test that same password and salt produce same hash."""
        password = "testpassword123"
        salt = "test_salt"

        hash1, _ = PasswordHasher.hash_password(password, salt)
        hash2, _ = PasswordHasher.hash_password(password, salt)

        assert hash1 == hash2

    def test_same_password_different_salt_different_hash(self):
        """Test that same password with different salts produce different hashes."""
        password = "testpassword123"

        hash1, salt1 = PasswordHasher.hash_password(password)
        hash2, salt2 = PasswordHasher.hash_password(password)

        assert salt1 != salt2
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        salt = "test_salt"

        hashed, _ = PasswordHasher.hash_password(password, salt)

        assert PasswordHasher.verify_password(password, hashed, salt) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        correct_password = "testpassword123"
        wrong_password = "wrongpassword"
        salt = "test_salt"

        hashed, _ = PasswordHasher.hash_password(correct_password, salt)

        assert PasswordHasher.verify_password(wrong_password, hashed, salt) is False

    def test_create_password_hash(self):
        """Test creation of complete password hash."""
        password = "testpassword123"

        password_hash = PasswordHasher.create_password_hash(password)

        assert ":" in password_hash
        assert len(password_hash.split(":")) == 2

    def test_verify_password_hash_correct(self):
        """Test verification with complete password hash - correct password."""
        password = "testpassword123"

        password_hash = PasswordHasher.create_password_hash(password)

        assert PasswordHasher.verify_password_hash(password, password_hash) is True

    def test_verify_password_hash_incorrect(self):
        """Test verification with complete password hash - incorrect password."""
        correct_password = "testpassword123"
        wrong_password = "wrongpassword"

        password_hash = PasswordHasher.create_password_hash(correct_password)

        assert PasswordHasher.verify_password_hash(wrong_password, password_hash) is False

    def test_verify_password_hash_invalid_format(self):
        """Test verification with invalid hash format."""
        password = "testpassword123"
        invalid_hash = "invalid_hash_format"

        assert PasswordHasher.verify_password_hash(password, invalid_hash) is False


class TestTokenGenerator:
    """Test cases for TokenGenerator service."""

    def test_create_auth_token(self):
        """Test creation of authentication token."""
        inspector_id = uuid4()

        token = TokenGenerator.create_auth_token(inspector_id, expires_in_hours=8)

        assert token.inspector_id == inspector_id
        assert len(token.token) > 0
        assert token.expires_at > token.created_at

        # Check that expiry is approximately 8 hours from creation
        expected_expiry = token.created_at + timedelta(hours=8)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

    def test_create_auth_token_default_expiry(self):
        """Test creation of auth token with default expiry."""
        inspector_id = uuid4()

        token = TokenGenerator.create_auth_token(inspector_id)

        assert token.inspector_id == inspector_id
        assert token.expires_at > token.created_at

    def test_tokens_are_unique(self):
        """Test that generated tokens are unique."""
        inspector_id = uuid4()

        token1 = TokenGenerator.create_auth_token(inspector_id)
        token2 = TokenGenerator.create_auth_token(inspector_id)

        assert token1.token != token2.token

    def test_token_format(self):
        """Test that token has expected format."""
        inspector_id = uuid4()

        token = TokenGenerator.create_auth_token(inspector_id)

        # Token should be a non-empty string
        assert isinstance(token.token, str)
        assert len(token.token) > 0
        # Should be URL-safe (no special characters that need encoding)
        assert all(c.isalnum() or c in '-_' for c in token.token)
