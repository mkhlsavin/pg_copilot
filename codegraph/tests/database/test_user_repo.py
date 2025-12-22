"""
Tests for User Repository.

Tests for UserRepository CRUD operations.
"""

import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.models import User, UserRole, AuthProvider
from src.api.database.repositories.user_repo import UserRepository


class TestUserCreate:
    """Tests for UserRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        db_session: AsyncSession,
    ):
        """Test creating a new user."""
        repo = UserRepository(db_session)

        user = await repo.create(
            username="newuser",
            email="newuser@example.com",
            password_hash="hashed_password",
        )

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.role == UserRole.ANALYST  # default
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_create_user_with_role(
        self,
        db_session: AsyncSession,
    ):
        """Test creating user with specific role."""
        repo = UserRepository(db_session)

        user = await repo.create(
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_create_user_with_external_auth(
        self,
        db_session: AsyncSession,
    ):
        """Test creating user with external auth provider."""
        repo = UserRepository(db_session)

        user = await repo.create(
            username="oauth_user",
            auth_provider=AuthProvider.OAUTH_GITHUB,
            external_id="github_12345",
        )

        assert user.auth_provider == AuthProvider.OAUTH_GITHUB
        assert user.external_id == "github_12345"


class TestUserGetById:
    """Tests for UserRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting existing user by ID."""
        repo = UserRepository(db_session)

        result = await repo.get_by_id(test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.username == test_user.username

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent user."""
        repo = UserRepository(db_session)

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestUserGetByUsername:
    """Tests for UserRepository.get_by_username()."""

    @pytest.mark.asyncio
    async def test_get_by_username_existing(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting user by username."""
        repo = UserRepository(db_session)

        result = await repo.get_by_username(test_user.username)

        assert result is not None
        assert result.username == test_user.username

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent username."""
        repo = UserRepository(db_session)

        result = await repo.get_by_username("nonexistent")

        assert result is None


class TestUserGetByEmail:
    """Tests for UserRepository.get_by_email()."""

    @pytest.mark.asyncio
    async def test_get_by_email_existing(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting user by email."""
        repo = UserRepository(db_session)

        result = await repo.get_by_email(test_user.email)

        assert result is not None
        assert result.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test getting non-existent email."""
        repo = UserRepository(db_session)

        result = await repo.get_by_email("nonexistent@example.com")

        assert result is None


class TestUserGetByExternalId:
    """Tests for UserRepository.get_by_external_id()."""

    @pytest.mark.asyncio
    async def test_get_by_external_id_success(
        self,
        db_session: AsyncSession,
    ):
        """Test getting user by external ID."""
        repo = UserRepository(db_session)

        # Create user with external auth
        user = await repo.create(
            username="github_user",
            auth_provider=AuthProvider.OAUTH_GITHUB,
            external_id="gh_123456",
        )
        await db_session.commit()

        result = await repo.get_by_external_id("gh_123456", AuthProvider.OAUTH_GITHUB)

        assert result is not None
        assert result.external_id == "gh_123456"

    @pytest.mark.asyncio
    async def test_get_by_external_id_wrong_provider(
        self,
        db_session: AsyncSession,
    ):
        """Test that external ID lookup requires correct provider."""
        repo = UserRepository(db_session)

        await repo.create(
            username="github_user",
            auth_provider=AuthProvider.OAUTH_GITHUB,
            external_id="gh_123456",
        )
        await db_session.commit()

        # Wrong provider should not find the user
        result = await repo.get_by_external_id("gh_123456", AuthProvider.OAUTH_GITLAB)

        assert result is None


class TestUserListAll:
    """Tests for UserRepository.list_all()."""

    @pytest.mark.asyncio
    async def test_list_all_users(
        self,
        db_session: AsyncSession,
    ):
        """Test listing all users."""
        repo = UserRepository(db_session)

        for i in range(5):
            await repo.create(username=f"user{i}", email=f"user{i}@example.com")
        await db_session.commit()

        users = await repo.list_all()

        assert len(users) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_limit(
        self,
        db_session: AsyncSession,
    ):
        """Test listing users with limit."""
        repo = UserRepository(db_session)

        for i in range(10):
            await repo.create(username=f"user{i}", email=f"user{i}@example.com")
        await db_session.commit()

        users = await repo.list_all(limit=5)

        assert len(users) == 5

    @pytest.mark.asyncio
    async def test_list_all_active_only(
        self,
        db_session: AsyncSession,
    ):
        """Test listing only active users."""
        repo = UserRepository(db_session)

        # Create active users
        for i in range(3):
            await repo.create(username=f"active{i}", email=f"active{i}@example.com")

        # Create and deactivate users
        inactive = await repo.create(username="inactive", email="inactive@example.com")
        await db_session.commit()
        await repo.deactivate(inactive.id)
        await db_session.commit()

        users = await repo.list_all(active_only=True)

        assert len(users) == 3
        assert all(u.is_active for u in users)

    @pytest.mark.asyncio
    async def test_list_all_include_inactive(
        self,
        db_session: AsyncSession,
    ):
        """Test listing all users including inactive."""
        repo = UserRepository(db_session)

        user = await repo.create(username="user1", email="user1@example.com")
        await db_session.commit()
        await repo.deactivate(user.id)
        await db_session.commit()

        users = await repo.list_all(active_only=False)

        assert len(users) == 1
        assert users[0].is_active is False


class TestUserCount:
    """Tests for UserRepository.count()."""

    @pytest.mark.asyncio
    async def test_count_users(
        self,
        db_session: AsyncSession,
    ):
        """Test counting users."""
        repo = UserRepository(db_session)

        for i in range(5):
            await repo.create(username=f"user{i}", email=f"user{i}@example.com")
        await db_session.commit()

        count = await repo.count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_active_only(
        self,
        db_session: AsyncSession,
    ):
        """Test counting only active users."""
        repo = UserRepository(db_session)

        for i in range(3):
            await repo.create(username=f"user{i}", email=f"user{i}@example.com")

        inactive = await repo.create(username="inactive", email="inactive@example.com")
        await db_session.commit()
        await repo.deactivate(inactive.id)
        await db_session.commit()

        active_count = await repo.count(active_only=True)
        total_count = await repo.count(active_only=False)

        assert active_count == 3
        assert total_count == 4


class TestUserUpdate:
    """Tests for UserRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_email(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating user email."""
        repo = UserRepository(db_session)

        updated = await repo.update(test_user.id, email="newemail@example.com")

        assert updated is not None
        assert updated.email == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating multiple fields."""
        repo = UserRepository(db_session)

        updated = await repo.update(
            test_user.id,
            username="updated_username",
            email="updated@example.com",
        )

        assert updated is not None
        assert updated.username == "updated_username"
        assert updated.email == "updated@example.com"


class TestUserUpdateRole:
    """Tests for UserRepository.update_role()."""

    @pytest.mark.asyncio
    async def test_update_role_to_admin(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test promoting user to admin."""
        repo = UserRepository(db_session)

        updated = await repo.update_role(test_user.id, UserRole.ADMIN)

        assert updated is not None
        assert updated.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_update_role_to_viewer(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test changing user to viewer."""
        repo = UserRepository(db_session)

        updated = await repo.update_role(test_user.id, UserRole.VIEWER)

        assert updated is not None
        assert updated.role == UserRole.VIEWER


class TestUserActivation:
    """Tests for UserRepository.activate() and deactivate()."""

    @pytest.mark.asyncio
    async def test_deactivate_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deactivating a user."""
        repo = UserRepository(db_session)

        deactivated = await repo.deactivate(test_user.id)

        assert deactivated is not None
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_activate_user(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test activating a deactivated user."""
        repo = UserRepository(db_session)

        # First deactivate
        await repo.deactivate(test_user.id)
        await db_session.commit()

        # Then activate
        activated = await repo.activate(test_user.id)

        assert activated is not None
        assert activated.is_active is True


class TestUserDelete:
    """Tests for UserRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_user(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting a user."""
        repo = UserRepository(db_session)

        user = await repo.create(username="to_delete", email="delete@example.com")
        await db_session.commit()

        result = await repo.delete(user.id)

        assert result is True

        # Verify deleted
        deleted = await repo.get_by_id(user.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting non-existent user."""
        repo = UserRepository(db_session)

        result = await repo.delete(uuid.uuid4())

        assert result is False


class TestUserUpdatePassword:
    """Tests for UserRepository.update_password()."""

    @pytest.mark.asyncio
    async def test_update_password(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating user password."""
        repo = UserRepository(db_session)

        updated = await repo.update_password(test_user.id, "new_hashed_password")

        assert updated is not None
        assert updated.password_hash == "new_hashed_password"
