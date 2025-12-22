"""
Tests for API Key Repository.

Tests for ApiKeyRepository CRUD operations.
"""

import pytest
import uuid
from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import User, ApiKey
from src.api.database.repositories.api_key_repo import ApiKeyRepository


class TestApiKeyCreate:
    """Tests for ApiKeyRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating a new API key."""
        repo = ApiKeyRepository(db_session)

        api_key = await repo.create(
            user_id=test_user.id,
            name="Test API Key",
            key_hash="hashed_key_value_123",
            prefix="sk_test",
            scopes=["scenarios:read", "query:execute"],
        )

        assert api_key is not None
        assert api_key.user_id == test_user.id
        assert api_key.name == "Test API Key"
        assert api_key.prefix == "sk_test"
        assert api_key.is_revoked is False

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating API key with expiration date."""
        repo = ApiKeyRepository(db_session)
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)

        api_key = await repo.create(
            user_id=test_user.id,
            name="Expiring Key",
            key_hash="hashed_key",
            prefix="sk_exp",
            expires_at=expires_at,
        )

        assert api_key.expires_at is not None
        assert api_key.expires_at > datetime.now(UTC).replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_create_api_key_default_scopes(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating API key with default scopes."""
        repo = ApiKeyRepository(db_session)

        api_key = await repo.create(
            user_id=test_user.id,
            name="Default Scopes Key",
            key_hash="hashed_key",
            prefix="sk_def",
        )

        assert api_key.scopes == ["scenarios:read", "query:execute"]


class TestApiKeyGetById:
    """Tests for ApiKeyRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test getting existing API key by ID."""
        repo = ApiKeyRepository(db_session)

        result = await repo.get_by_id(test_api_key.id)

        assert result is not None
        assert result.id == test_api_key.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent API key."""
        repo = ApiKeyRepository(db_session)

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestApiKeyGetByPrefix:
    """Tests for ApiKeyRepository.get_by_prefix()."""

    @pytest.mark.asyncio
    async def test_get_by_prefix_existing(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test getting API key by prefix."""
        repo = ApiKeyRepository(db_session)

        result = await repo.get_by_prefix(test_api_key.prefix)

        assert result is not None
        assert result.prefix == test_api_key.prefix

    @pytest.mark.asyncio
    async def test_get_by_prefix_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent prefix."""
        repo = ApiKeyRepository(db_session)

        result = await repo.get_by_prefix("nonexistent_prefix")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_prefix_excludes_revoked(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test that revoked keys are not found by prefix."""
        repo = ApiKeyRepository(db_session)

        # Revoke the key
        await repo.revoke(test_api_key.id)
        await db_session.commit()

        result = await repo.get_by_prefix(test_api_key.prefix)

        assert result is None


class TestApiKeyGetByUser:
    """Tests for ApiKeyRepository.get_by_user()."""

    @pytest.mark.asyncio
    async def test_get_by_user_success(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting all API keys for a user."""
        repo = ApiKeyRepository(db_session)

        # Create multiple keys
        for i in range(3):
            await repo.create(
                user_id=test_user.id,
                name=f"Key {i}",
                key_hash=f"hash_{i}",
                prefix=f"sk_{i}",
            )
        await db_session.commit()

        keys = await repo.get_by_user(test_user.id)

        assert len(keys) == 3

    @pytest.mark.asyncio
    async def test_get_by_user_excludes_revoked(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that revoked keys are excluded by default."""
        repo = ApiKeyRepository(db_session)

        # Create keys
        key1 = await repo.create(
            user_id=test_user.id,
            name="Active Key",
            key_hash="hash_1",
            prefix="sk_1",
        )
        key2 = await repo.create(
            user_id=test_user.id,
            name="Revoked Key",
            key_hash="hash_2",
            prefix="sk_2",
        )
        await db_session.commit()

        # Revoke one
        await repo.revoke(key2.id)
        await db_session.commit()

        keys = await repo.get_by_user(test_user.id)

        assert len(keys) == 1
        assert keys[0].id == key1.id

    @pytest.mark.asyncio
    async def test_get_by_user_include_revoked(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test including revoked keys."""
        repo = ApiKeyRepository(db_session)

        key1 = await repo.create(
            user_id=test_user.id,
            name="Key 1",
            key_hash="hash_1",
            prefix="sk_1",
        )
        key2 = await repo.create(
            user_id=test_user.id,
            name="Key 2",
            key_hash="hash_2",
            prefix="sk_2",
        )
        await db_session.commit()

        await repo.revoke(key2.id)
        await db_session.commit()

        keys = await repo.get_by_user(test_user.id, include_revoked=True)

        assert len(keys) == 2


class TestApiKeyUpdateLastUsed:
    """Tests for ApiKeyRepository.update_last_used()."""

    @pytest.mark.asyncio
    async def test_update_last_used(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test updating last used timestamp."""
        repo = ApiKeyRepository(db_session)

        # Initially last_used_at should be None
        assert test_api_key.last_used_at is None

        await repo.update_last_used(test_api_key.id)
        await db_session.commit()

        # Refresh to get updated value
        updated = await repo.get_by_id(test_api_key.id)

        assert updated is not None
        assert updated.last_used_at is not None


class TestApiKeyRevoke:
    """Tests for ApiKeyRepository.revoke()."""

    @pytest.mark.asyncio
    async def test_revoke_key(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test revoking an API key."""
        repo = ApiKeyRepository(db_session)

        result = await repo.revoke(test_api_key.id)

        assert result is True

        # Verify revoked
        key = await repo.get_by_id(test_api_key.id)
        assert key is not None
        assert key.is_revoked is True

    @pytest.mark.asyncio
    async def test_revoke_already_revoked(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test revoking already revoked key returns False."""
        repo = ApiKeyRepository(db_session)

        # First revoke
        await repo.revoke(test_api_key.id)
        await db_session.commit()

        # Second revoke should return False
        result = await repo.revoke(test_api_key.id)

        assert result is False


class TestApiKeyDelete:
    """Tests for ApiKeyRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_key(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an API key."""
        repo = ApiKeyRepository(db_session)

        key = await repo.create(
            user_id=test_user.id,
            name="To Delete",
            key_hash="hash",
            prefix="sk_del",
        )
        await db_session.commit()

        result = await repo.delete(key.id)

        assert result is True

        # Verify deleted
        deleted = await repo.get_by_id(key.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting non-existent key."""
        repo = ApiKeyRepository(db_session)

        result = await repo.delete(uuid.uuid4())

        assert result is False


class TestApiKeyDeleteByUser:
    """Tests for ApiKeyRepository.delete_by_user()."""

    @pytest.mark.asyncio
    async def test_delete_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting all API keys for a user."""
        repo = ApiKeyRepository(db_session)

        for i in range(3):
            await repo.create(
                user_id=test_user.id,
                name=f"Key {i}",
                key_hash=f"hash_{i}",
                prefix=f"sk_{i}",
            )
        await db_session.commit()

        deleted_count = await repo.delete_by_user(test_user.id)

        assert deleted_count == 3

        # Verify all deleted
        remaining = await repo.get_by_user(test_user.id, include_revoked=True)
        assert len(remaining) == 0


class TestApiKeyCountByUser:
    """Tests for ApiKeyRepository.count_by_user()."""

    @pytest.mark.asyncio
    async def test_count_by_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test counting API keys for a user."""
        repo = ApiKeyRepository(db_session)

        for i in range(5):
            await repo.create(
                user_id=test_user.id,
                name=f"Key {i}",
                key_hash=f"hash_{i}",
                prefix=f"sk_{i}",
            )
        await db_session.commit()

        count = await repo.count_by_user(test_user.id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_by_user_active_only(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test counting only active keys."""
        repo = ApiKeyRepository(db_session)

        key1 = await repo.create(
            user_id=test_user.id,
            name="Active",
            key_hash="hash_1",
            prefix="sk_1",
        )
        key2 = await repo.create(
            user_id=test_user.id,
            name="Revoked",
            key_hash="hash_2",
            prefix="sk_2",
        )
        await db_session.commit()

        await repo.revoke(key2.id)
        await db_session.commit()

        active_count = await repo.count_by_user(test_user.id, active_only=True)
        total_count = await repo.count_by_user(test_user.id, active_only=False)

        assert active_count == 1
        assert total_count == 2


class TestApiKeyIsValid:
    """Tests for ApiKeyRepository.is_valid()."""

    @pytest.mark.asyncio
    async def test_is_valid_active_key(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test that active key is valid."""
        repo = ApiKeyRepository(db_session)

        is_valid = await repo.is_valid(test_api_key.id)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_is_valid_revoked_key(
        self,
        db_session: AsyncSession,
        test_api_key: ApiKey,
    ):
        """Test that revoked key is invalid."""
        repo = ApiKeyRepository(db_session)

        await repo.revoke(test_api_key.id)
        await db_session.commit()

        is_valid = await repo.is_valid(test_api_key.id)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_is_valid_expired_key(
        self,
        db_session: AsyncSession,
        expired_api_key: ApiKey,
    ):
        """Test that expired key is invalid."""
        repo = ApiKeyRepository(db_session)

        is_valid = await repo.is_valid(expired_api_key.id)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_is_valid_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test that non-existent key is invalid."""
        repo = ApiKeyRepository(db_session)

        is_valid = await repo.is_valid(uuid.uuid4())

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_is_valid_no_expiration(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that key without expiration is valid."""
        repo = ApiKeyRepository(db_session)

        key = await repo.create(
            user_id=test_user.id,
            name="No Expiry",
            key_hash="hash",
            prefix="sk_noexp",
            expires_at=None,
        )
        await db_session.commit()

        is_valid = await repo.is_valid(key.id)

        assert is_valid is True
