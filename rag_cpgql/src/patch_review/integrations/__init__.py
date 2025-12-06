"""
External Integrations for Patch Review

Integrations with external services:
- GitHubIntegration: GitHub PR API integration
- GitLabIntegration: GitLab MR API integration
- CI hooks for various CI/CD platforms
"""

from .github_integration import GitHubIntegration, GitHubConfig
from .gitlab_integration import GitLabIntegration, GitLabConfig

__all__ = [
    'GitHubIntegration',
    'GitHubConfig',
    'GitLabIntegration',
    'GitLabConfig',
]
