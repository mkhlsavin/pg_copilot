"""
GitLab Integration for Patch Review System.

Provides integration with GitLab Merge Requests:
- Fetch MR diff and metadata
- Post review comments
- Add discussions
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import quote

from ..models import PatchContext, ReviewVerdict, Recommendation
from ..formatters import PRCommentFormatter

logger = logging.getLogger(__name__)


@dataclass
class GitLabConfig:
    """Configuration for GitLab integration."""
    token: str
    project_id: str  # Can be 'group/project' or numeric ID
    api_base: str = "https://gitlab.com/api/v4"
    app_name: str = "CPG Code Review"


class GitLabIntegration:
    """
    Integration with GitLab Merge Requests.

    Provides:
    - MR diff fetching
    - Note/discussion posting
    - Pipeline status updates
    - Inline comment posting
    """

    def __init__(self, config: GitLabConfig):
        """
        Initialize GitLab integration.

        Args:
            config: GitLab configuration
        """
        self.config = config
        self.formatter = PRCommentFormatter()

        # URL-encode the project ID if it's a path
        self.project_id_encoded = quote(config.project_id, safe='')

        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.warning("requests not installed; GitLab integration limited")
            self.requests = None

    @classmethod
    def from_env(cls) -> 'GitLabIntegration':
        """Create integration from environment variables."""
        config = GitLabConfig(
            token=os.environ.get('GITLAB_TOKEN', ''),
            project_id=os.environ.get('GITLAB_PROJECT_ID', ''),
            api_base=os.environ.get('GITLAB_API_BASE', 'https://gitlab.com/api/v4'),
        )
        return cls(config)

    def _headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            'PRIVATE-TOKEN': self.config.token,
            'Content-Type': 'application/json'
        }

    def fetch_merge_request(self, mr_iid: int) -> Dict[str, Any]:
        """
        Fetch merge request metadata.

        Args:
            mr_iid: MR internal ID

        Returns:
            MR metadata dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def fetch_mr_diff(self, mr_iid: int) -> str:
        """
        Fetch merge request diff.

        Args:
            mr_iid: MR internal ID

        Returns:
            Diff string
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        # Get diff versions
        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/diffs"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        diffs = response.json()

        # Combine diffs into unified format
        diff_lines = []
        for diff in diffs:
            diff_lines.append(f"diff --git a/{diff['old_path']} b/{diff['new_path']}")
            if diff.get('new_file'):
                diff_lines.append("new file mode 100644")
            elif diff.get('deleted_file'):
                diff_lines.append("deleted file mode 100644")
            diff_lines.append(f"--- a/{diff['old_path']}")
            diff_lines.append(f"+++ b/{diff['new_path']}")
            diff_lines.append(diff.get('diff', ''))

        return '\n'.join(diff_lines)

    def fetch_mr_changes(self, mr_iid: int) -> Dict[str, Any]:
        """
        Fetch merge request changes with full context.

        Args:
            mr_iid: MR internal ID

        Returns:
            Changes dictionary including file changes
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/changes"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def create_patch_context(self, mr_iid: int) -> PatchContext:
        """
        Create PatchContext from a GitLab MR.

        Args:
            mr_iid: MR internal ID

        Returns:
            PatchContext for the MR
        """
        mr_data = self.fetch_merge_request(mr_iid)
        changes = self.fetch_mr_changes(mr_iid)

        # Import patch parser
        from ..patch_parser import PatchParser
        parser = PatchParser()

        # Construct diff from changes
        diff_lines = []
        for change in changes.get('changes', []):
            diff_lines.append(f"diff --git a/{change['old_path']} b/{change['new_path']}")
            diff_lines.append(f"--- a/{change['old_path']}")
            diff_lines.append(f"+++ b/{change['new_path']}")
            diff_lines.append(change.get('diff', ''))

        diff = '\n'.join(diff_lines)

        patch = parser.parse_gitlab_mr({
            'diff': diff,
            'base_sha': mr_data.get('diff_refs', {}).get('base_sha', ''),
            'head_sha': mr_data.get('diff_refs', {}).get('head_sha', ''),
            'mr_iid': mr_iid,
            'title': mr_data.get('title', ''),
            'author': mr_data.get('author', {}).get('username'),
            'changes': changes.get('changes', [])
        })

        return patch

    def submit_review(
        self,
        mr_iid: int,
        verdict: ReviewVerdict
    ) -> Dict[str, Any]:
        """
        Submit a review on the MR.

        Args:
            mr_iid: MR internal ID
            verdict: The review verdict

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        # Format the review
        gitlab_review = self.formatter.format_gitlab_review(verdict)

        # Post the main review note
        note_response = self.add_note(mr_iid, gitlab_review['body'])

        # Post inline discussions
        for discussion in gitlab_review.get('discussions', []):
            try:
                self.create_discussion(
                    mr_iid,
                    discussion['body'],
                    discussion['position']
                )
            except Exception as e:
                logger.warning(f"Failed to create discussion: {e}")

        # Approve or unapprove based on verdict
        if verdict.recommendation == Recommendation.APPROVE:
            try:
                self.approve_mr(mr_iid)
            except Exception as e:
                logger.warning(f"Failed to approve MR: {e}")

        logger.info(f"Submitted review on MR !{mr_iid}")
        return note_response

    def add_note(self, mr_iid: int, body: str) -> Dict[str, Any]:
        """
        Add a note/comment to an MR.

        Args:
            mr_iid: MR internal ID
            body: Note body

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/notes"
        response = self.requests.post(
            url,
            headers=self._headers(),
            json={'body': body}
        )
        response.raise_for_status()

        return response.json()

    def create_discussion(
        self,
        mr_iid: int,
        body: str,
        position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a discussion thread on specific code.

        Args:
            mr_iid: MR internal ID
            body: Discussion body
            position: Position dictionary with file/line info

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        # Get the diff refs
        mr_data = self.fetch_merge_request(mr_iid)
        diff_refs = mr_data.get('diff_refs', {})

        payload = {
            'body': body,
            'position': {
                'base_sha': diff_refs.get('base_sha'),
                'head_sha': diff_refs.get('head_sha'),
                'start_sha': diff_refs.get('start_sha'),
                'new_path': position.get('new_path'),
                'new_line': position.get('new_line'),
                'position_type': position.get('position_type', 'text')
            }
        }

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/discussions"
        response = self.requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        return response.json()

    def approve_mr(self, mr_iid: int) -> Dict[str, Any]:
        """
        Approve a merge request.

        Args:
            mr_iid: MR internal ID

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/approve"
        response = self.requests.post(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def unapprove_mr(self, mr_iid: int) -> Dict[str, Any]:
        """
        Remove approval from a merge request.

        Args:
            mr_iid: MR internal ID

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/unapprove"
        response = self.requests.post(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def set_pipeline_status(
        self,
        sha: str,
        state: str,
        name: str = "CPG Code Review",
        description: str = "",
        target_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set commit/pipeline status.

        Args:
            sha: Commit SHA
            state: 'pending', 'running', 'success', 'failed', 'canceled'
            name: Status name
            description: Status description
            target_url: Optional URL to link

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        payload = {
            'state': state,
            'name': name,
            'description': description[:140]
        }
        if target_url:
            payload['target_url'] = target_url

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/statuses/{sha}"
        response = self.requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        return response.json()

    def get_mr_commits(self, mr_iid: int) -> List[Dict[str, Any]]:
        """
        Get list of commits in an MR.

        Args:
            mr_iid: MR internal ID

        Returns:
            List of commit dictionaries
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}/commits"
        response = self.requests.get(url, headers=self._headers())
        response.raise_for_status()

        return response.json()

    def add_mr_label(self, mr_iid: int, labels: List[str]) -> Dict[str, Any]:
        """
        Add labels to an MR.

        Args:
            mr_iid: MR internal ID
            labels: List of label names

        Returns:
            API response dictionary
        """
        if not self.requests:
            raise RuntimeError("requests library not available")

        url = f"{self.config.api_base}/projects/{self.project_id_encoded}/merge_requests/{mr_iid}"
        response = self.requests.put(
            url,
            headers=self._headers(),
            json={'add_labels': ','.join(labels)}
        )
        response.raise_for_status()

        return response.json()
