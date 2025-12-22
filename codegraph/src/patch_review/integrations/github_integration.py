"""
GitHub Integration for Patch Review System.

Provides integration with GitHub PRs:
- Fetch PR diff and metadata
- Post review comments
- Update check status
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..models import PatchContext, ReviewVerdict, Recommendation
from ..formatters import PRCommentFormatter, InlineComment, ReviewComment

logger = logging.getLogger(__name__)


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""
    token: str
    owner: str
    repo: str
    api_base: str = "https://api.github.com"
    app_name: str = "CPG Code Review"


class GitHubIntegration:
    """
    Integration with GitHub Pull Requests.

    Provides:
    - PR diff fetching
    - Review submission
    - Check run updates
    - Inline comment posting
    """

    def __init__(self, config: GitHubConfig):
        """
        Initialize GitHub integration.

        Args:
            config: GitHub configuration
        """
        self.config = config
        self.formatter = PRCommentFormatter()

        # Import requests lazily
        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.warning("requests not installed; GitHub integration limited")
            self.requests = None

    @classmethod
    def from_env(cls) -> 'GitHubIntegration':
        """Create integration from environment variables."""
        config = GitHubConfig(
            token=os.environ.get('GITHUB_TOKEN', ''),
            owner=os.environ.get('GITHUB_OWNER', ''),
            repo=os.environ.get('GITHUB_REPO', ''),
        )
        return cls(config)

    def _headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            'Authorization': f'token {self.config.token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

    def fetch_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """
        Fetch pull request metadata.

        Args:
            pr_number: PR number

        Returns:
            PR metadata dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def fetch_pr_diff(self, pr_number: int) -> str:
        """
        Fetch pull request diff.

        Args:
            pr_number: PR number

        Returns:
            Diff string in unified format
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}"
        headers = self._headers()
        headers['Accept'] = 'application/vnd.github.v3.diff'

        response = self.requests.get(url, headers=headers)
        response.raise_for_status()

        return response.text

    def fetch_pr_files(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Fetch list of files changed in PR.

        Args:
            pr_number: PR number

        Returns:
            List of file change dictionaries
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}/files"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def create_patch_context(self, pr_number: int) -> PatchContext:
        """
        Create PatchContext from a GitHub PR.

        Args:
            pr_number: PR number

        Returns:
            PatchContext for the PR
        """
        pr_data = self.fetch_pull_request(pr_number)
        diff = self.fetch_pr_diff(pr_number)
        files = self.fetch_pr_files(pr_number)

        # Import patch parser
        from ..patch_parser import PatchParser
        parser = PatchParser()

        # Parse the diff
        patch = parser.parse_github_pr({
            'diff': diff,
            'base_sha': pr_data['base']['sha'],
            'head_sha': pr_data['head']['sha'],
            'pr_number': pr_number,
            'title': pr_data.get('title', ''),
            'author': pr_data['user']['login'] if pr_data.get('user') else None,
            'files': files
        })

        return patch

    def submit_review(
        self,
        pr_number: int,
        verdict: ReviewVerdict,
        commit_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a review on the PR.

        Args:
            pr_number: PR number
            verdict: The review verdict
            commit_id: Optional commit SHA to review

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        # Format the review
        review_comment = self.formatter.format_github_review(verdict)

        # Build review payload
        payload = {
            'body': review_comment.body,
            'event': review_comment.event
        }

        if commit_id:
            payload['commit_id'] = commit_id

        # Add inline comments
        if review_comment.comments:
            payload['comments'] = [
                {
                    'path': c.filepath,
                    'line': c.line_number,
                    'body': c.body,
                    'side': c.side
                }
                for c in review_comment.comments
            ]

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}/reviews"
        response = self.requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        logger.info(f"Submitted review on PR #{pr_number}: {review_comment.event}")
        return response.json()

    def create_check_run(
        self,
        verdict: ReviewVerdict,
        head_sha: str
    ) -> Dict[str, Any]:
        """
        Create a GitHub Check Run.

        Args:
            verdict: The review verdict
            head_sha: Commit SHA

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        check_data = self.formatter.format_check_run_summary(verdict)
        check_data['head_sha'] = head_sha

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/check-runs"
        response = self.requests.post(url, headers=self._headers(), json=check_data)
        response.raise_for_status()

        logger.info(f"Created check run for {head_sha}")
        return response.json()

    def update_check_run(
        self,
        check_run_id: int,
        verdict: ReviewVerdict
    ) -> Dict[str, Any]:
        """
        Update an existing Check Run.

        Args:
            check_run_id: Check run ID
            verdict: The review verdict

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        check_data = self.formatter.format_check_run_summary(verdict)

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/check-runs/{check_run_id}"
        response = self.requests.patch(url, headers=self._headers(), json=check_data)
        response.raise_for_status()

        return response.json()

    def add_pr_comment(
        self,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Add a general comment to a PR.

        Args:
            pr_number: PR number
            body: Comment body

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/issues/{pr_number}/comments"
        response = self.requests.post(
            url,
            headers=self._headers(),
            json={'body': body}
        )
        response.raise_for_status()

        return response.json()

    def add_line_comment(
        self,
        pr_number: int,
        commit_id: str,
        filepath: str,
        line: int,
        body: str,
        side: str = 'RIGHT'
    ) -> Dict[str, Any]:
        """
        Add an inline comment on a specific line.

        Args:
            pr_number: PR number
            commit_id: Commit SHA
            filepath: File path
            line: Line number
            body: Comment body
            side: 'LEFT' or 'RIGHT'

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        payload = {
            'body': body,
            'commit_id': commit_id,
            'path': filepath,
            'line': line,
            'side': side
        }

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}/comments"
        response = self.requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        return response.json()

    def get_pr_commits(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get list of commits in a PR.

        Args:
            pr_number: PR number

        Returns:
            List of commit dictionaries
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/pulls/{pr_number}/commits"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def set_commit_status(
        self,
        sha: str,
        state: str,
        description: str,
        context: str = "CPG Code Review"
    ) -> Dict[str, Any]:
        """
        Set commit status.

        Args:
            sha: Commit SHA
            state: 'pending', 'success', 'failure', 'error'
            description: Status description
            context: Status context name

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        payload = {
            'state': state,
            'description': description[:140],  # GitHub limit
            'context': context
        }

        url = f"{self.config.api_base}/repos/{self.config.owner}/{self.config.repo}/statuses/{sha}"
        response = self.requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        return response.json()
