"""
Multi-Source Patch Parser

Parses patches from multiple sources into a unified PatchContext:
- Git diff (unified diff format)
- GitHub Pull Request API
- GitLab Merge Request API

Phase: Core Infrastructure (Phase 1)
"""

import logging
import re
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.patch_review.models import (
    ChangeType,
    ChangedMethod,
    FileDiff,
    HunkChange,
    PatchContext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LANGUAGE DETECTION
# =============================================================================

# File extension to language mapping
EXTENSION_TO_LANGUAGE = {
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cxx': 'cpp',
    '.cc': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.py': 'python',
    '.java': 'java',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.scala': 'scala',
    '.kt': 'kotlin',
    '.swift': 'swift',
    '.cs': 'csharp',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bash': 'shell',
}


def detect_language(filepath: str) -> str:
    """Detect programming language from file extension"""
    ext = Path(filepath).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, 'unknown')


# =============================================================================
# BASE ADAPTER
# =============================================================================

class PatchAdapter(ABC):
    """Abstract base class for patch source adapters"""

    @abstractmethod
    def parse(self, data: Any) -> PatchContext:
        """Parse patch data into PatchContext"""
        pass

    @abstractmethod
    def can_handle(self, data: Any) -> bool:
        """Check if this adapter can handle the given data"""
        pass


# =============================================================================
# GIT DIFF ADAPTER
# =============================================================================

class GitDiffAdapter(PatchAdapter):
    """
    Adapter for parsing unified diff format (git diff output).

    Supports:
    - Standard unified diff format
    - Git extended diff headers
    - Binary file markers
    - Rename detection
    """

    # Regex patterns for parsing
    DIFF_HEADER = re.compile(r'^diff --git a/(.+) b/(.+)$')
    OLD_FILE = re.compile(r'^--- (.+)$')
    NEW_FILE = re.compile(r'^\+\+\+ (.+)$')
    HUNK_HEADER = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
    RENAME_FROM = re.compile(r'^rename from (.+)$')
    RENAME_TO = re.compile(r'^rename to (.+)$')
    NEW_FILE_MODE = re.compile(r'^new file mode \d+$')
    DELETED_FILE_MODE = re.compile(r'^deleted file mode \d+$')
    INDEX_LINE = re.compile(r'^index ([a-f0-9]+)\.\.([a-f0-9]+)')

    def can_handle(self, data: Any) -> bool:
        """Check if data looks like a unified diff"""
        if not isinstance(data, str):
            return False
        return data.strip().startswith('diff --git') or data.strip().startswith('---')

    def parse(self, data: str) -> PatchContext:
        """
        Parse unified diff format into PatchContext.

        Args:
            data: Unified diff string (from git diff)

        Returns:
            PatchContext with parsed file diffs and hunks
        """
        lines = data.split('\n')
        files: List[FileDiff] = []
        current_file: Optional[FileDiff] = None
        current_hunk: Optional[HunkChange] = None

        # State tracking
        old_path = None
        new_path = None
        is_new_file = False
        is_deleted = False
        is_rename = False
        rename_from = None

        # Hunk state
        in_hunk = False
        hunk_old_line = 0
        hunk_new_line = 0
        context_phase = 'before'  # 'before', 'changes', 'after'

        # Extract commit hashes if present
        base_commit = None
        head_commit = None

        i = 0
        while i < len(lines):
            line = lines[i]

            # Match diff header
            diff_match = self.DIFF_HEADER.match(line)
            if diff_match:
                # Save previous file if exists
                if current_file is not None:
                    if current_hunk is not None:
                        current_file.hunks.append(current_hunk)
                    files.append(current_file)

                # Reset state
                old_path = diff_match.group(1)
                new_path = diff_match.group(2)
                is_new_file = False
                is_deleted = False
                is_rename = False
                rename_from = None
                current_file = None
                current_hunk = None
                in_hunk = False
                context_phase = 'before'
                i += 1
                continue

            # Match index line for commit hashes
            index_match = self.INDEX_LINE.match(line)
            if index_match:
                if base_commit is None:
                    base_commit = index_match.group(1)
                head_commit = index_match.group(2)
                i += 1
                continue

            # Match new/deleted file mode
            if self.NEW_FILE_MODE.match(line):
                is_new_file = True
                i += 1
                continue
            if self.DELETED_FILE_MODE.match(line):
                is_deleted = True
                i += 1
                continue

            # Match rename
            rename_from_match = self.RENAME_FROM.match(line)
            if rename_from_match:
                is_rename = True
                rename_from = rename_from_match.group(1)
                i += 1
                continue

            # Match old file header
            old_match = self.OLD_FILE.match(line)
            if old_match:
                old_file_path = old_match.group(1)
                if old_file_path.startswith('a/'):
                    old_file_path = old_file_path[2:]
                elif old_file_path == '/dev/null':
                    is_new_file = True
                i += 1
                continue

            # Match new file header
            new_match = self.NEW_FILE.match(line)
            if new_match:
                new_file_path = new_match.group(1)
                if new_file_path.startswith('b/'):
                    new_file_path = new_file_path[2:]
                elif new_file_path == '/dev/null':
                    is_deleted = True

                # Create FileDiff
                if is_new_file:
                    change_type = ChangeType.ADDED
                    path = new_file_path if new_file_path != '/dev/null' else new_path
                elif is_deleted:
                    change_type = ChangeType.DELETED
                    path = old_path
                elif is_rename:
                    change_type = ChangeType.RENAMED
                    path = new_file_path
                else:
                    change_type = ChangeType.MODIFIED
                    path = new_file_path

                current_file = FileDiff(
                    path=path,
                    change_type=change_type,
                    language=detect_language(path),
                    old_path=rename_from if is_rename else None
                )
                i += 1
                continue

            # Match hunk header
            hunk_match = self.HUNK_HEADER.match(line)
            if hunk_match:
                # Save previous hunk
                if current_hunk is not None and current_file is not None:
                    current_file.hunks.append(current_hunk)

                old_start = int(hunk_match.group(1))
                old_lines = int(hunk_match.group(2) or 1)
                new_start = int(hunk_match.group(3))
                new_lines = int(hunk_match.group(4) or 1)

                current_hunk = HunkChange(
                    old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines
                )

                in_hunk = True
                hunk_old_line = 0
                hunk_new_line = 0
                context_phase = 'before'
                i += 1
                continue

            # Process hunk content
            if in_hunk and current_hunk is not None:
                if line.startswith('-') and not line.startswith('---'):
                    # Removed line
                    if context_phase == 'before':
                        context_phase = 'changes'
                    elif context_phase == 'after':
                        # Context after changes - this is a new change block
                        # Move after context to before of next change
                        pass
                    current_hunk.removed_lines.append(line[1:])
                    hunk_old_line += 1
                elif line.startswith('+') and not line.startswith('+++'):
                    # Added line
                    if context_phase == 'before':
                        context_phase = 'changes'
                    current_hunk.added_lines.append(line[1:])
                    hunk_new_line += 1
                elif line.startswith(' ') or line == '':
                    # Context line
                    context_line = line[1:] if line.startswith(' ') else ''
                    if context_phase == 'before':
                        current_hunk.context_before.append(context_line)
                    elif context_phase == 'changes':
                        context_phase = 'after'
                        current_hunk.context_after.append(context_line)
                    else:
                        current_hunk.context_after.append(context_line)
                    hunk_old_line += 1
                    hunk_new_line += 1
                elif line.startswith('\\'):
                    # No newline at end of file marker
                    pass

            i += 1

        # Save last file and hunk
        if current_file is not None:
            if current_hunk is not None:
                current_file.hunks.append(current_hunk)
            files.append(current_file)

        # Generate patch ID
        patch_id = f"PATCH_{uuid.uuid4().hex[:12].upper()}"

        return PatchContext(
            patch_id=patch_id,
            source='git_diff',
            base_commit=base_commit or 'unknown',
            head_commit=head_commit or 'unknown',
            files=files,
            metadata={
                'format': 'unified_diff',
                'total_files': len(files)
            }
        )


# =============================================================================
# GITHUB ADAPTER
# =============================================================================

class GitHubAdapter(PatchAdapter):
    """
    Adapter for GitHub Pull Request API.

    Fetches PR diff via GitHub API and parses it.
    Requires PyGithub library.
    """

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize GitHub adapter.

        Args:
            token: GitHub personal access token
            repo: Repository in format "owner/repo"
        """
        self.token = token
        self.repo = repo
        self._gh = None
        self._repo_obj = None

    def _ensure_client(self):
        """Ensure GitHub client is initialized"""
        if self._gh is None:
            try:
                from github import Github
                self._gh = Github(self.token) if self.token else Github()
                if self.repo:
                    self._repo_obj = self._gh.get_repo(self.repo)
            except ImportError:
                raise ImportError(
                    "PyGithub is required for GitHub integration. "
                    "Install with: pip install PyGithub"
                )

    def can_handle(self, data: Any) -> bool:
        """Check if data is a GitHub PR number or PR object"""
        if isinstance(data, int):
            return True
        if isinstance(data, dict) and 'pull_request' in data:
            return True
        return False

    def parse(self, data: Any) -> PatchContext:
        """
        Parse GitHub PR into PatchContext.

        Args:
            data: PR number (int) or PR event payload (dict)

        Returns:
            PatchContext with parsed PR diff
        """
        self._ensure_client()

        if self._repo_obj is None:
            raise ValueError("Repository not set. Initialize with repo='owner/repo'")

        # Get PR number
        if isinstance(data, int):
            pr_number = data
        elif isinstance(data, dict):
            pr_number = data.get('pull_request', {}).get('number')
            if pr_number is None:
                raise ValueError("Could not extract PR number from payload")
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Fetch PR
        pr = self._repo_obj.get_pull(pr_number)

        # Get diff
        diff_url = pr.diff_url
        import requests
        headers = {}
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        response = requests.get(diff_url, headers=headers)
        response.raise_for_status()
        diff_text = response.text

        # Parse diff using GitDiffAdapter
        git_adapter = GitDiffAdapter()
        patch = git_adapter.parse(diff_text)

        # Update with GitHub-specific metadata
        patch.source = 'github_pr'
        patch.base_commit = pr.base.sha
        patch.head_commit = pr.head.sha
        patch.metadata.update({
            'pr_number': pr_number,
            'pr_title': pr.title,
            'pr_url': pr.html_url,
            'author': pr.user.login,
            'base_branch': pr.base.ref,
            'head_branch': pr.head.ref,
            'state': pr.state,
            'mergeable': pr.mergeable,
            'additions': pr.additions,
            'deletions': pr.deletions,
            'changed_files': pr.changed_files,
        })

        return patch

    def set_repo(self, repo: str):
        """Set or change the repository"""
        self.repo = repo
        self._repo_obj = None  # Force re-initialization

    def set_token(self, token: str):
        """Set or change the access token"""
        self.token = token
        self._gh = None  # Force re-initialization


# =============================================================================
# GITLAB ADAPTER
# =============================================================================

class GitLabAdapter(PatchAdapter):
    """
    Adapter for GitLab Merge Request API.

    Fetches MR diff via GitLab API and parses it.
    Requires python-gitlab library.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        project_id: Optional[str] = None,
        url: str = "https://gitlab.com"
    ):
        """
        Initialize GitLab adapter.

        Args:
            token: GitLab personal access token
            project_id: Project ID or path
            url: GitLab instance URL
        """
        self.token = token
        self.project_id = project_id
        self.url = url
        self._gl = None
        self._project = None

    def _ensure_client(self):
        """Ensure GitLab client is initialized"""
        if self._gl is None:
            try:
                import gitlab
                self._gl = gitlab.Gitlab(self.url, private_token=self.token)
                if self.project_id:
                    self._project = self._gl.projects.get(self.project_id)
            except ImportError:
                raise ImportError(
                    "python-gitlab is required for GitLab integration. "
                    "Install with: pip install python-gitlab"
                )

    def can_handle(self, data: Any) -> bool:
        """Check if data is a GitLab MR number or MR object"""
        if isinstance(data, int):
            return True
        if isinstance(data, dict) and 'merge_request' in data:
            return True
        return False

    def parse(self, data: Any) -> PatchContext:
        """
        Parse GitLab MR into PatchContext.

        Args:
            data: MR IID (int) or MR webhook payload (dict)

        Returns:
            PatchContext with parsed MR diff
        """
        self._ensure_client()

        if self._project is None:
            raise ValueError("Project not set. Initialize with project_id")

        # Get MR IID
        if isinstance(data, int):
            mr_iid = data
        elif isinstance(data, dict):
            mr_iid = data.get('merge_request', {}).get('iid')
            if mr_iid is None:
                raise ValueError("Could not extract MR IID from payload")
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Fetch MR
        mr = self._project.mergerequests.get(mr_iid)

        # Get diff
        changes = mr.changes()
        diff_text = self._build_diff_from_changes(changes)

        # Parse diff
        git_adapter = GitDiffAdapter()
        patch = git_adapter.parse(diff_text)

        # Update with GitLab-specific metadata
        patch.source = 'gitlab_mr'
        patch.base_commit = changes.get('diff_refs', {}).get('base_sha', 'unknown')
        patch.head_commit = changes.get('diff_refs', {}).get('head_sha', 'unknown')
        patch.metadata.update({
            'mr_iid': mr_iid,
            'mr_title': mr.title,
            'mr_url': mr.web_url,
            'author': mr.author.get('username', 'unknown'),
            'source_branch': mr.source_branch,
            'target_branch': mr.target_branch,
            'state': mr.state,
            'merge_status': mr.merge_status,
        })

        return patch

    def _build_diff_from_changes(self, changes: Dict[str, Any]) -> str:
        """Build unified diff string from GitLab changes object"""
        lines = []
        for change in changes.get('changes', []):
            old_path = change.get('old_path', '')
            new_path = change.get('new_path', '')
            diff = change.get('diff', '')

            lines.append(f"diff --git a/{old_path} b/{new_path}")
            if change.get('new_file'):
                lines.append('new file mode 100644')
            elif change.get('deleted_file'):
                lines.append('deleted file mode 100644')
            elif change.get('renamed_file'):
                lines.append(f'rename from {old_path}')
                lines.append(f'rename to {new_path}')

            lines.append(f"--- a/{old_path}")
            lines.append(f"+++ b/{new_path}")
            lines.append(diff)

        return '\n'.join(lines)


# =============================================================================
# MAIN PATCH PARSER
# =============================================================================

class PatchParser:
    """
    Multi-source patch parser with pluggable adapters.

    Automatically selects the appropriate adapter based on input type,
    or allows explicit adapter selection.
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        gitlab_token: Optional[str] = None,
        gitlab_project: Optional[str] = None,
        gitlab_url: str = "https://gitlab.com"
    ):
        """
        Initialize parser with optional integration credentials.

        Args:
            github_token: GitHub personal access token
            github_repo: GitHub repository (owner/repo)
            gitlab_token: GitLab personal access token
            gitlab_project: GitLab project ID or path
            gitlab_url: GitLab instance URL
        """
        self.adapters: Dict[str, PatchAdapter] = {
            'git_diff': GitDiffAdapter(),
            'github_pr': GitHubAdapter(github_token, github_repo),
            'gitlab_mr': GitLabAdapter(gitlab_token, gitlab_project, gitlab_url),
        }

    def parse(self, source: str, data: Any) -> PatchContext:
        """
        Parse patch data using specified source adapter.

        Args:
            source: Adapter name ('git_diff', 'github_pr', 'gitlab_mr')
            data: Source-specific data (diff text, PR number, etc.)

        Returns:
            Parsed PatchContext
        """
        if source not in self.adapters:
            raise ValueError(f"Unknown source: {source}. Available: {list(self.adapters.keys())}")

        adapter = self.adapters[source]
        return adapter.parse(data)

    def parse_auto(self, data: Any) -> PatchContext:
        """
        Automatically detect source and parse.

        Tries each adapter until one can handle the data.

        Args:
            data: Patch data (will try to auto-detect format)

        Returns:
            Parsed PatchContext
        """
        for name, adapter in self.adapters.items():
            if adapter.can_handle(data):
                logger.info(f"Auto-detected patch source: {name}")
                return adapter.parse(data)

        raise ValueError("Could not detect patch format. Please specify source explicitly.")

    def parse_git_diff(self, diff_text: str) -> PatchContext:
        """Convenience method to parse git diff directly"""
        return self.adapters['git_diff'].parse(diff_text)

    def parse_github_pr(self, pr_number: int) -> PatchContext:
        """Convenience method to parse GitHub PR directly"""
        return self.adapters['github_pr'].parse(pr_number)

    def parse_gitlab_mr(self, mr_iid: int) -> PatchContext:
        """Convenience method to parse GitLab MR directly"""
        return self.adapters['gitlab_mr'].parse(mr_iid)

    def parse_local_changes(
        self,
        repo_path: str = ".",
        base_ref: str = "HEAD~1",
        head_ref: str = "HEAD"
    ) -> PatchContext:
        """
        Parse local git changes between two refs.

        Args:
            repo_path: Path to git repository
            base_ref: Base reference (default: HEAD~1)
            head_ref: Head reference (default: HEAD)

        Returns:
            PatchContext from git diff
        """
        try:
            result = subprocess.run(
                ['git', '-C', repo_path, 'diff', base_ref, head_ref],
                capture_output=True,
                text=True,
                check=True
            )
            diff_text = result.stdout

            # Get actual commit hashes
            base_sha = subprocess.run(
                ['git', '-C', repo_path, 'rev-parse', base_ref],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            head_sha = subprocess.run(
                ['git', '-C', repo_path, 'rev-parse', head_ref],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            patch = self.parse_git_diff(diff_text)
            patch.base_commit = base_sha
            patch.head_commit = head_sha
            patch.metadata['repo_path'] = repo_path
            patch.metadata['base_ref'] = base_ref
            patch.metadata['head_ref'] = head_ref

            return patch

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git diff failed: {e.stderr}")

    def extract_changed_methods(
        self,
        patch: PatchContext,
        language_parsers: Optional[Dict[str, Any]] = None
    ) -> List[ChangedMethod]:
        """
        Extract methods affected by the patch.

        Uses language-specific parsing to identify method boundaries
        within the changed hunks.

        Args:
            patch: Parsed patch context
            language_parsers: Optional custom language parsers

        Returns:
            List of ChangedMethod objects
        """
        changed_methods = []

        for file_diff in patch.files:
            # Skip non-code files
            if file_diff.language == 'unknown':
                continue

            # For now, use heuristic-based method detection
            # TODO: Integrate with tree-sitter for proper parsing
            methods = self._extract_methods_heuristic(file_diff)
            changed_methods.extend(methods)

        # Store in patch for later use
        patch.changed_methods = changed_methods

        return changed_methods

    def _extract_methods_heuristic(self, file_diff: FileDiff) -> List[ChangedMethod]:
        """
        Heuristic-based method extraction from diff.

        Uses regex patterns to identify function/method definitions
        in the changed lines. This is approximate - for production
        use, integrate with tree-sitter or language-specific parsers.
        """
        methods = []

        # Language-specific function patterns
        patterns = {
            'c': [
                # C function: return_type function_name(params)
                re.compile(r'^[\+\-]?\s*(\w+\s+\*?\s*)?(\w+)\s*\([^)]*\)\s*\{?'),
            ],
            'python': [
                # Python def
                re.compile(r'^[\+\-]?\s*def\s+(\w+)\s*\('),
                # Python class
                re.compile(r'^[\+\-]?\s*class\s+(\w+)'),
            ],
            'java': [
                # Java method
                re.compile(r'^[\+\-]?\s*(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\('),
            ],
            'javascript': [
                # JS function
                re.compile(r'^[\+\-]?\s*function\s+(\w+)'),
                # JS arrow/method
                re.compile(r'^[\+\-]?\s*(\w+)\s*[=:]\s*(async\s*)?\(?'),
            ],
        }

        lang_patterns = patterns.get(file_diff.language, patterns.get('c', []))

        for hunk in file_diff.hunks:
            # Check both added and removed lines
            all_lines = (
                [(line, 'removed', hunk.old_start + i)
                 for i, line in enumerate(hunk.removed_lines)] +
                [(line, 'added', hunk.new_start + i)
                 for i, line in enumerate(hunk.added_lines)]
            )

            for line, change_type, line_num in all_lines:
                for pattern in lang_patterns:
                    match = pattern.search(line)
                    if match:
                        # Extract method name (last group that's not None)
                        method_name = None
                        for g in reversed(match.groups()):
                            if g and not g.strip() in ('public', 'private', 'protected', 'static', 'async'):
                                method_name = g.strip()
                                break

                        if method_name:
                            methods.append(ChangedMethod(
                                method_name=method_name,
                                full_name=f"{file_diff.path}:{method_name}",
                                filepath=file_diff.path,
                                change_type=(ChangeType.DELETED if change_type == 'removed'
                                            else ChangeType.ADDED if file_diff.change_type == ChangeType.ADDED
                                            else ChangeType.MODIFIED),
                                line_start=line_num,
                                line_end=line_num,  # Unknown end without full parsing
                            ))

        return methods


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_patch_from_file(filepath: str) -> PatchContext:
    """
    Parse a patch from a .patch or .diff file.

    Args:
        filepath: Path to patch file

    Returns:
        Parsed PatchContext
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        diff_text = f.read()

    parser = PatchParser()
    patch = parser.parse_git_diff(diff_text)
    patch.metadata['source_file'] = filepath
    return patch


def summarize_patch(patch: PatchContext) -> Dict[str, Any]:
    """
    Generate a summary of a patch.

    Args:
        patch: Parsed patch context

    Returns:
        Dictionary with patch summary statistics
    """
    return {
        'patch_id': patch.patch_id,
        'source': patch.source,
        'base_commit': patch.base_commit[:8] if len(patch.base_commit) >= 8 else patch.base_commit,
        'head_commit': patch.head_commit[:8] if len(patch.head_commit) >= 8 else patch.head_commit,
        'files_changed': len(patch.files),
        'additions': patch.total_additions,
        'deletions': patch.total_deletions,
        'net_change': patch.total_additions - patch.total_deletions,
        'files_by_type': _count_files_by_type(patch),
        'affected_directories': patch.affected_directories,
        'methods_changed': len(patch.changed_methods),
    }


def _count_files_by_type(patch: PatchContext) -> Dict[str, int]:
    """Count files by change type"""
    counts = {'added': 0, 'modified': 0, 'deleted': 0, 'renamed': 0}
    for f in patch.files:
        counts[f.change_type.value] += 1
    return counts
