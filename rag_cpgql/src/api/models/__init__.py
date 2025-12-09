"""
Pydantic Models Package.

Provides request/response models for API endpoints.
"""

from src.api.models.common import (
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse,
    PaginationParams,
)
from src.api.models.auth import (
    TokenRequest,
    TokenResponse,
    TokenRefreshRequest,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    PasswordChange,
    PasswordReset,
    OAuthProviderInfo,
    OAuthLoginResponse,
    LDAPLoginRequest,
)
from src.api.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ScenarioInfo,
    ScenarioListResponse,
    ScenarioQueryRequest,
    Evidence,
)
from src.api.models.review import (
    PatchReviewRequest,
    GitHubPRReviewRequest,
    GitLabMRReviewRequest,
    ReviewResponse,
    Finding,
)
from src.api.models.sessions import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionSummary,
    SessionListResponse,
    DialogueTurnResponse,
    HistoryResponse,
    ExportRequest,
    JobCreate,
    JobResponse,
    JobListResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    "SuccessResponse",
    "PaginatedResponse",
    "PaginationParams",
    # Auth
    "TokenRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "PasswordChange",
    "PasswordReset",
    "OAuthProviderInfo",
    "OAuthLoginResponse",
    "LDAPLoginRequest",
    # Chat
    "ChatRequest",
    "ChatResponse",
    "ChatStreamEvent",
    "ScenarioInfo",
    "ScenarioListResponse",
    "ScenarioQueryRequest",
    "Evidence",
    # Review
    "PatchReviewRequest",
    "GitHubPRReviewRequest",
    "GitLabMRReviewRequest",
    "ReviewResponse",
    "Finding",
    # Sessions
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionSummary",
    "SessionListResponse",
    "DialogueTurnResponse",
    "HistoryResponse",
    "ExportRequest",
    "JobCreate",
    "JobResponse",
    "JobListResponse",
]
