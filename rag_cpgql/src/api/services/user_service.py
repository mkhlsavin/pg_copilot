"""
User Service Module.

Provides business logic for user management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from passlib.context import CryptContext

from src.api.database.repositories.user_repo import UserRepository
from src.api.database.models import User, AuthProvider, UserRole

logger = logging.getLogger("api.services.user")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """
    User management service.

    Provides high-level operations for user management.
    """

    def __init__(self, user_repo: UserRepository):
        """
        Initialize the user service.

        Args:
            user_repo: User repository
        """
        self.repo = user_repo

    def hash_password(self, password: str) -> str:
        """
        Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    async def create_user(
        self,
        username: str,
        password: Optional[str] = None,
        email: Optional[str] = None,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        external_id: Optional[str] = None,
        role: UserRole = UserRole.ANALYST,
    ) -> User:
        """
        Create a new user.

        Args:
            username: Username
            password: Password (for local auth)
            email: Email address
            auth_provider: Authentication provider
            external_id: External provider user ID
            role: User role

        Returns:
            Created user
        """
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = self.hash_password(password)

        return await self.repo.create(
            username=username,
            email=email,
            password_hash=password_hash,
            auth_provider=auth_provider,
            external_id=external_id,
            role=role,
        )

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            User if authenticated, None otherwise
        """
        # Try to find user by username
        user = await self.repo.get_by_username(username)

        # Also try by email
        if not user:
            user = await self.repo.get_by_email(username)

        if not user:
            logger.info(f"Authentication failed: user not found: {username}")
            return None

        # Check if user is active
        if not user.is_active:
            logger.info(f"Authentication failed: user inactive: {username}")
            return None

        # Verify password
        if not user.password_hash:
            logger.info(f"Authentication failed: no password set: {username}")
            return None

        if not self.verify_password(password, user.password_hash):
            logger.info(f"Authentication failed: invalid password: {username}")
            return None

        logger.info(f"Authentication successful: {username}")
        return user

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None
        """
        return await self.repo.get_by_id(user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: Username

        Returns:
            User or None
        """
        return await self.repo.get_by_username(username)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.

        Args:
            email: Email address

        Returns:
            User or None
        """
        return await self.repo.get_by_email(email)

    async def get_or_create_oauth_user(
        self,
        external_id: str,
        auth_provider: AuthProvider,
        username: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> User:
        """
        Get or create a user from OAuth provider.

        Args:
            external_id: External provider user ID
            auth_provider: Authentication provider
            username: Username
            email: Email address
            name: Display name

        Returns:
            User
        """
        # Try to find existing user
        user = await self.repo.get_by_external_id(external_id, auth_provider)

        if user:
            logger.info(f"Found existing OAuth user: {username}")
            return user

        # Create new user
        logger.info(f"Creating new OAuth user: {username}")
        return await self.create_user(
            username=username,
            email=email,
            auth_provider=auth_provider,
            external_id=external_id,
        )

    async def get_or_create_ldap_user(
        self,
        username: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ) -> User:
        """
        Get or create a user from LDAP.

        Args:
            username: Username
            email: Email address
            display_name: Display name
            groups: LDAP group memberships

        Returns:
            User
        """
        # Try to find existing user
        user = await self.repo.get_by_username(username)

        if user:
            logger.info(f"Found existing LDAP user: {username}")
            return user

        # Determine role from groups
        role = self._map_ldap_groups_to_role(groups or [])

        # Create new user
        logger.info(f"Creating new LDAP user: {username} with role: {role}")
        return await self.create_user(
            username=username,
            email=email,
            auth_provider=AuthProvider.LDAP,
            role=role,
        )

    def _map_ldap_groups_to_role(self, groups: List[str]) -> UserRole:
        """
        Map LDAP groups to user role.

        Args:
            groups: LDAP group names

        Returns:
            User role
        """
        # Simple group to role mapping
        # Can be customized based on configuration
        admin_groups = {"Admins", "Domain Admins", "api-admins"}
        reviewer_groups = {"Code Reviewers", "api-reviewers"}

        for group in groups:
            if group in admin_groups:
                return UserRole.ADMIN
            if group in reviewer_groups:
                return UserRole.REVIEWER

        return UserRole.ANALYST

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = True,
    ) -> List[User]:
        """
        List all users.

        Args:
            limit: Maximum users
            offset: Skip count
            active_only: Only return active users

        Returns:
            List of users
        """
        return await self.repo.list_all(
            limit=limit,
            offset=offset,
            active_only=active_only,
        )

    async def count_users(self, active_only: bool = True) -> int:
        """
        Count users.

        Args:
            active_only: Only count active users

        Returns:
            User count
        """
        return await self.repo.count(active_only=active_only)

    async def update_user(
        self,
        user_id: UUID,
        email: Optional[str] = None,
        role: Optional[UserRole] = None,
    ) -> Optional[User]:
        """
        Update user profile.

        Args:
            user_id: User ID
            email: New email
            role: New role

        Returns:
            Updated user or None
        """
        updates = {}
        if email is not None:
            updates["email"] = email
        if role is not None:
            updates["role"] = role

        if not updates:
            return await self.repo.get_by_id(user_id)

        return await self.repo.update(user_id, **updates)

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed
        """
        user = await self.repo.get_by_id(user_id)
        if not user or not user.password_hash:
            return False

        # Verify old password
        if not self.verify_password(old_password, user.password_hash):
            return False

        # Update password
        new_hash = self.hash_password(new_password)
        await self.repo.update_password(user_id, new_hash)

        logger.info(f"Password changed for user: {user_id}")
        return True

    async def reset_password(
        self,
        user_id: UUID,
        new_password: str,
    ) -> bool:
        """
        Reset user password (admin operation).

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            True if password reset
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False

        new_hash = self.hash_password(new_password)
        await self.repo.update_password(user_id, new_hash)

        logger.info(f"Password reset for user: {user_id}")
        return True

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            Deactivated user or None
        """
        user = await self.repo.deactivate(user_id)
        if user:
            logger.info(f"User deactivated: {user_id}")
        return user

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """
        Activate a user.

        Args:
            user_id: User ID

        Returns:
            Activated user or None
        """
        user = await self.repo.activate(user_id)
        if user:
            logger.info(f"User activated: {user_id}")
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        result = await self.repo.delete(user_id)
        if result:
            logger.info(f"User deleted: {user_id}")
        return result
