"""
Review Service Module.

Provides business logic for code review operations.
Integrates with PatchReviewWorkflow.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger("api.services.review")


class Finding(BaseModel):
    """Code review finding."""

    severity: str  # critical, major, minor, info
    category: str  # security, performance, style, logic, etc.
    description: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


class ReviewResult(BaseModel):
    """Result of code review."""

    recommendation: str  # APPROVE, REQUEST_CHANGES, COMMENT, BLOCK
    score: float  # 0.0 to 1.0
    findings: List[Finding] = []
    summary: str
    processing_time_ms: float
    dod_compliance: Optional[Dict[str, bool]] = None
    metadata: Dict[str, Any] = {}


class ReviewService:
    """
    Code review service.

    Integrates with PatchReviewWorkflow for analyzing patches.
    """

    def __init__(self):
        """Initialize the review service."""
        self._workflow = None

    async def initialize(self) -> None:
        """
        Initialize the review service.

        This is called lazily on first use.
        """
        if self._workflow is not None:
            return

        try:
            from src.patch_review.workflow.review_workflow import PatchReviewWorkflow

            self._workflow = PatchReviewWorkflow()
            logger.info("Review service initialized with PatchReviewWorkflow")
        except Exception as e:
            logger.error(f"Failed to initialize PatchReviewWorkflow: {e}")
            raise

    async def review_patch(
        self,
        patch_content: str,
        task_description: Optional[str] = None,
        dod_items: Optional[List[str]] = None,
        output_format: str = "json",
    ) -> ReviewResult:
        """
        Review a git patch/diff.

        Args:
            patch_content: Git diff content
            task_description: Description of the task being implemented
            dod_items: Definition of Done items to check
            output_format: Output format (json, markdown, yaml)

        Returns:
            Review result
        """
        await self.initialize()

        start_time = time.time()

        try:
            if self._workflow:
                result = await self._process_with_workflow(
                    patch_content=patch_content,
                    task_description=task_description,
                    dod_items=dod_items,
                )
            else:
                result = self._generate_fallback_result()

            processing_time_ms = (time.time() - start_time) * 1000

            return ReviewResult(
                recommendation=result.get("recommendation", "COMMENT"),
                score=result.get("score", 0.5),
                findings=[Finding(**f) for f in result.get("findings", [])],
                summary=result.get("summary", ""),
                processing_time_ms=processing_time_ms,
                dod_compliance=result.get("dod_compliance"),
                metadata=result.get("metadata", {}),
            )

        except Exception as e:
            logger.exception(f"Error reviewing patch: {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return ReviewResult(
                recommendation="COMMENT",
                score=0.0,
                findings=[
                    Finding(
                        severity="critical",
                        category="error",
                        description=f"Review failed: {str(e)}",
                    )
                ],
                summary="Review failed due to an error.",
                processing_time_ms=processing_time_ms,
            )

    async def review_github_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        github_token: str,
        task_description: Optional[str] = None,
        dod_items: Optional[List[str]] = None,
    ) -> ReviewResult:
        """
        Review a GitHub pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            github_token: GitHub access token
            task_description: Task description
            dod_items: DoD items

        Returns:
            Review result
        """
        start_time = time.time()

        try:
            # Fetch PR diff
            patch_content = await self._fetch_github_pr_diff(
                owner, repo, pr_number, github_token
            )

            # Get PR description as task description if not provided
            if not task_description:
                pr_info = await self._fetch_github_pr_info(
                    owner, repo, pr_number, github_token
                )
                task_description = pr_info.get("body", "")

            result = await self.review_patch(
                patch_content=patch_content,
                task_description=task_description,
                dod_items=dod_items,
            )

            # Add GitHub-specific metadata
            result.metadata["source"] = "github"
            result.metadata["pr_url"] = f"https://github.com/{owner}/{repo}/pull/{pr_number}"

            return result

        except Exception as e:
            logger.exception(f"Error reviewing GitHub PR: {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return ReviewResult(
                recommendation="COMMENT",
                score=0.0,
                findings=[
                    Finding(
                        severity="critical",
                        category="error",
                        description=f"Failed to fetch GitHub PR: {str(e)}",
                    )
                ],
                summary="Review failed - could not fetch PR.",
                processing_time_ms=processing_time_ms,
                metadata={"source": "github", "error": str(e)},
            )

    async def review_gitlab_mr(
        self,
        project_id: str,
        mr_iid: int,
        gitlab_token: str,
        gitlab_url: str = "https://gitlab.com",
        task_description: Optional[str] = None,
        dod_items: Optional[List[str]] = None,
    ) -> ReviewResult:
        """
        Review a GitLab merge request.

        Args:
            project_id: Project ID or path
            mr_iid: MR internal ID
            gitlab_token: GitLab access token
            gitlab_url: GitLab server URL
            task_description: Task description
            dod_items: DoD items

        Returns:
            Review result
        """
        start_time = time.time()

        try:
            # Fetch MR diff
            patch_content = await self._fetch_gitlab_mr_diff(
                project_id, mr_iid, gitlab_token, gitlab_url
            )

            # Get MR description as task description if not provided
            if not task_description:
                mr_info = await self._fetch_gitlab_mr_info(
                    project_id, mr_iid, gitlab_token, gitlab_url
                )
                task_description = mr_info.get("description", "")

            result = await self.review_patch(
                patch_content=patch_content,
                task_description=task_description,
                dod_items=dod_items,
            )

            # Add GitLab-specific metadata
            result.metadata["source"] = "gitlab"
            result.metadata["mr_url"] = f"{gitlab_url}/{project_id}/-/merge_requests/{mr_iid}"

            return result

        except Exception as e:
            logger.exception(f"Error reviewing GitLab MR: {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return ReviewResult(
                recommendation="COMMENT",
                score=0.0,
                findings=[
                    Finding(
                        severity="critical",
                        category="error",
                        description=f"Failed to fetch GitLab MR: {str(e)}",
                    )
                ],
                summary="Review failed - could not fetch MR.",
                processing_time_ms=processing_time_ms,
                metadata={"source": "gitlab", "error": str(e)},
            )

    async def _process_with_workflow(
        self,
        patch_content: str,
        task_description: Optional[str],
        dod_items: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Process patch using PatchReviewWorkflow."""
        try:
            result = await self._workflow.review(
                patch=patch_content,
                task_description=task_description,
                dod_items=dod_items,
            )

            return {
                "recommendation": self._map_recommendation(result),
                "score": self._calculate_score(result),
                "findings": self._extract_findings(result),
                "summary": self._generate_summary(result),
                "dod_compliance": self._extract_dod_compliance(result),
                "metadata": {},
            }
        except Exception as e:
            logger.error(f"Workflow processing error: {e}")
            return self._generate_fallback_result()

    def _map_recommendation(self, result: Any) -> str:
        """Map workflow result to recommendation."""
        if hasattr(result, "recommendation"):
            return result.recommendation

        # Infer from findings
        if hasattr(result, "findings"):
            critical_count = sum(
                1 for f in result.findings
                if getattr(f, "severity", "").lower() in ["critical", "blocker"]
            )
            major_count = sum(
                1 for f in result.findings
                if getattr(f, "severity", "").lower() == "major"
            )

            if critical_count > 0:
                return "BLOCK"
            elif major_count > 2:
                return "REQUEST_CHANGES"
            elif major_count > 0:
                return "COMMENT"

        return "APPROVE"

    def _calculate_score(self, result: Any) -> float:
        """Calculate review score."""
        if hasattr(result, "score"):
            return result.score

        # Calculate from findings
        if hasattr(result, "findings"):
            findings = result.findings
            if not findings:
                return 1.0

            weights = {"critical": 0.3, "major": 0.15, "minor": 0.05, "info": 0.01}
            total_penalty = sum(
                weights.get(getattr(f, "severity", "minor").lower(), 0.05)
                for f in findings
            )
            return max(0.0, 1.0 - total_penalty)

        return 0.5

    def _extract_findings(self, result: Any) -> List[Dict[str, Any]]:
        """Extract findings from workflow result."""
        findings = []

        if hasattr(result, "findings"):
            for f in result.findings:
                findings.append({
                    "severity": getattr(f, "severity", "minor"),
                    "category": getattr(f, "category", "general"),
                    "description": getattr(f, "description", str(f)),
                    "file_path": getattr(f, "file_path", None),
                    "line_start": getattr(f, "line_start", None),
                    "line_end": getattr(f, "line_end", None),
                    "suggestion": getattr(f, "suggestion", None),
                    "code_snippet": getattr(f, "code_snippet", None),
                })

        return findings

    def _generate_summary(self, result: Any) -> str:
        """Generate review summary."""
        if hasattr(result, "summary"):
            return result.summary

        if hasattr(result, "findings"):
            count = len(result.findings)
            if count == 0:
                return "No issues found. Code looks good!"
            elif count == 1:
                return "Found 1 issue that should be addressed."
            else:
                return f"Found {count} issues that should be addressed."

        return "Review completed."

    def _extract_dod_compliance(self, result: Any) -> Optional[Dict[str, bool]]:
        """Extract DoD compliance from result."""
        if hasattr(result, "dod_compliance"):
            return result.dod_compliance
        return None

    def _generate_fallback_result(self) -> Dict[str, Any]:
        """Generate fallback result when workflow is unavailable."""
        return {
            "recommendation": "COMMENT",
            "score": 0.5,
            "findings": [
                {
                    "severity": "info",
                    "category": "system",
                    "description": "Review system is currently unavailable. Manual review recommended.",
                }
            ],
            "summary": "Automated review unavailable. Please perform manual review.",
            "dod_compliance": None,
            "metadata": {"fallback": True},
        }

    async def _fetch_github_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        token: str,
    ) -> str:
        """Fetch PR diff from GitHub."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3.diff",
                },
            )
            response.raise_for_status()
            return response.text

    async def _fetch_github_pr_info(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        token: str,
    ) -> Dict[str, Any]:
        """Fetch PR info from GitHub."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            response.raise_for_status()
            return response.json()

    async def _fetch_gitlab_mr_diff(
        self,
        project_id: str,
        mr_iid: int,
        token: str,
        gitlab_url: str,
    ) -> str:
        """Fetch MR diff from GitLab."""
        import httpx
        from urllib.parse import quote

        project_encoded = quote(project_id, safe="")

        async with httpx.AsyncClient() as client:
            # Get MR changes
            response = await client.get(
                f"{gitlab_url}/api/v4/projects/{project_encoded}/merge_requests/{mr_iid}/changes",
                headers={"PRIVATE-TOKEN": token},
            )
            response.raise_for_status()
            data = response.json()

            # Construct diff from changes
            diff_lines = []
            for change in data.get("changes", []):
                diff_lines.append(f"diff --git a/{change['old_path']} b/{change['new_path']}")
                diff_lines.append(change.get("diff", ""))

            return "\n".join(diff_lines)

    async def _fetch_gitlab_mr_info(
        self,
        project_id: str,
        mr_iid: int,
        token: str,
        gitlab_url: str,
    ) -> Dict[str, Any]:
        """Fetch MR info from GitLab."""
        import httpx
        from urllib.parse import quote

        project_encoded = quote(project_id, safe="")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gitlab_url}/api/v4/projects/{project_encoded}/merge_requests/{mr_iid}",
                headers={"PRIVATE-TOKEN": token},
            )
            response.raise_for_status()
            return response.json()


# Global review service instance
_review_service: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """Get the global review service instance."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
