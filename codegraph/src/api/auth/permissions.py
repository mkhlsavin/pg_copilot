"""
RBAC Permissions Module.

Defines roles and permissions for access control.
"""

from enum import Enum
from typing import List, Optional, Set


class Permission(str, Enum):
    """Available permissions in the system."""

    # Scenario permissions
    SCENARIOS_READ = "scenarios:read"
    SCENARIOS_EXECUTE = "scenarios:execute"

    # Query permissions
    QUERY_EXECUTE = "query:execute"
    QUERY_VALIDATE = "query:validate"

    # Review permissions
    REVIEW_EXECUTE = "review:execute"
    REVIEW_GITHUB = "review:github"
    REVIEW_GITLAB = "review:gitlab"

    # Session permissions
    SESSIONS_READ = "sessions:read"
    SESSIONS_WRITE = "sessions:write"
    SESSIONS_DELETE = "sessions:delete"

    # History permissions
    HISTORY_READ = "history:read"
    HISTORY_EXPORT = "history:export"

    # User management permissions
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"

    # API key permissions
    API_KEYS_READ = "api_keys:read"
    API_KEYS_WRITE = "api_keys:write"
    API_KEYS_DELETE = "api_keys:delete"

    # Stats and metrics permissions
    STATS_READ = "stats:read"
    METRICS_READ = "metrics:read"

    # Admin permissions
    ADMIN_ALL = "admin:all"


class Role(str, Enum):
    """User roles with predefined permission sets."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.SCENARIOS_READ,
        Permission.HISTORY_READ,
        Permission.SESSIONS_READ,
        Permission.STATS_READ,
    },
    Role.ANALYST: {
        # Viewer permissions
        Permission.SCENARIOS_READ,
        Permission.HISTORY_READ,
        Permission.SESSIONS_READ,
        Permission.STATS_READ,
        # Additional analyst permissions
        Permission.SCENARIOS_EXECUTE,
        Permission.QUERY_EXECUTE,
        Permission.QUERY_VALIDATE,
        Permission.SESSIONS_WRITE,
        Permission.SESSIONS_DELETE,
        Permission.HISTORY_EXPORT,
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
    },
    Role.REVIEWER: {
        # Analyst permissions
        Permission.SCENARIOS_READ,
        Permission.HISTORY_READ,
        Permission.SESSIONS_READ,
        Permission.STATS_READ,
        Permission.SCENARIOS_EXECUTE,
        Permission.QUERY_EXECUTE,
        Permission.QUERY_VALIDATE,
        Permission.SESSIONS_WRITE,
        Permission.SESSIONS_DELETE,
        Permission.HISTORY_EXPORT,
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
        # Additional reviewer permissions
        Permission.REVIEW_EXECUTE,
        Permission.REVIEW_GITHUB,
        Permission.REVIEW_GITLAB,
    },
    Role.ADMIN: {
        # All permissions
        Permission.ADMIN_ALL,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """
    Get all permissions for a role.

    Args:
        role: User role

    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(
    role: Optional[Role],
    required_permission: Permission,
    user_scopes: Optional[List[str]] = None,
) -> bool:
    """
    Check if a role/user has a specific permission.

    Args:
        role: User role (can be None)
        required_permission: Permission to check
        user_scopes: Additional scopes from JWT token

    Returns:
        True if permission is granted
    """
    # Admin has all permissions
    if role == Role.ADMIN:
        return True

    # Check role-based permissions
    if role:
        role_perms = get_role_permissions(role)
        if Permission.ADMIN_ALL in role_perms:
            return True
        if required_permission in role_perms:
            return True

    # Check explicit scopes from token
    if user_scopes:
        if required_permission.value in user_scopes:
            return True
        if Permission.ADMIN_ALL.value in user_scopes:
            return True

    return False


def has_any_permission(
    role: Optional[Role],
    required_permissions: List[Permission],
    user_scopes: Optional[List[str]] = None,
) -> bool:
    """
    Check if a role/user has any of the specified permissions.

    Args:
        role: User role
        required_permissions: List of permissions (any one is sufficient)
        user_scopes: Additional scopes from JWT token

    Returns:
        True if any permission is granted
    """
    return any(
        has_permission(role, perm, user_scopes)
        for perm in required_permissions
    )


def has_all_permissions(
    role: Optional[Role],
    required_permissions: List[Permission],
    user_scopes: Optional[List[str]] = None,
) -> bool:
    """
    Check if a role/user has all of the specified permissions.

    Args:
        role: User role
        required_permissions: List of permissions (all required)
        user_scopes: Additional scopes from JWT token

    Returns:
        True if all permissions are granted
    """
    return all(
        has_permission(role, perm, user_scopes)
        for perm in required_permissions
    )


def get_default_scopes_for_api_key() -> List[str]:
    """
    Get default scopes for new API keys.

    Returns:
        List of default permission scopes
    """
    return [
        Permission.SCENARIOS_READ.value,
        Permission.SCENARIOS_EXECUTE.value,
        Permission.QUERY_EXECUTE.value,
        Permission.SESSIONS_READ.value,
        Permission.SESSIONS_WRITE.value,
        Permission.HISTORY_READ.value,
    ]


def validate_scopes(scopes: List[str]) -> List[str]:
    """
    Validate and filter scopes to only valid permissions.

    Args:
        scopes: List of scope strings

    Returns:
        List of valid scope strings
    """
    valid_permissions = {p.value for p in Permission}
    return [s for s in scopes if s in valid_permissions]
