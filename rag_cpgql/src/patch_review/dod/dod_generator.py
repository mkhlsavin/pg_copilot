"""
DoD Generator - LLM-based Definition of Done generation

Generates DoD when not found in any source:
- Analyzes task description
- Examines tests in the commit
- Creates appropriate DoD items by category
"""

import logging
import re
from typing import Dict, List, Optional, Any

from ..models import (
    DefinitionOfDone,
    DoDItem,
    DoDSource,
    DoDFormat,
    DoDCriterionType,
    PatchContext,
    FileDiff,
)

logger = logging.getLogger(__name__)


# Default DoD generation prompt
DOD_GENERATION_PROMPT = """You are a code review expert. Based on the task description and code changes, generate a Definition of Done (DoD) checklist.

Task Description:
{task_description}

Files Changed:
{files_changed}

Tests in Commit:
{tests_info}

Generate a DoD checklist with 4-8 items covering:
1. Functional requirements (what the code should do)
2. Security requirements (if applicable to changes)
3. Test requirements (unit tests, coverage)
4. Documentation requirements (if applicable)
5. Code quality requirements

Output format (JSON):
```json
{{
  "dod": [
    {{"description": "...", "type": "functional"}},
    {{"description": "...", "type": "test"}},
    ...
  ]
}}
```

Only output the JSON block, no additional text."""


class DoDGenerator:
    """
    Generates Definition of Done using LLM.

    Uses task description and commit information to generate
    appropriate DoD items when none are provided.
    """

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize DoD generator.

        Args:
            llm_provider: LLM provider for generation (optional, lazy-loaded)
            config: Configuration dictionary
        """
        self._llm_provider = llm_provider
        self.config = config or {}
        self.prompt_template = self.config.get('prompt', DOD_GENERATION_PROMPT)

    @property
    def llm_provider(self):
        """Lazy-load LLM provider if not provided."""
        if self._llm_provider is None:
            try:
                from ...llm.llm_interface_compat import get_llm_interface
                self._llm_provider = get_llm_interface()
            except ImportError:
                logger.warning("LLM provider not available")
        return self._llm_provider

    def generate(
        self,
        task_description: str,
        patch: Optional[PatchContext] = None,
    ) -> DefinitionOfDone:
        """
        Generate DoD based on task description and patch.

        Args:
            task_description: Task/issue description
            patch: Patch context with file changes

        Returns:
            Generated DefinitionOfDone
        """
        # Extract information for prompt
        files_changed = self._format_files_changed(patch)
        tests_info = self._extract_tests_info(patch)

        # Try LLM generation first
        if self.llm_provider:
            dod = self._generate_with_llm(
                task_description=task_description,
                files_changed=files_changed,
                tests_info=tests_info,
            )
            if dod:
                return dod

        # Fall back to rule-based generation
        return self._generate_rule_based(
            task_description=task_description,
            patch=patch,
        )

    def _generate_with_llm(
        self,
        task_description: str,
        files_changed: str,
        tests_info: str,
    ) -> Optional[DefinitionOfDone]:
        """
        Generate DoD using LLM.

        Args:
            task_description: Task description
            files_changed: Formatted list of changed files
            tests_info: Information about tests in commit

        Returns:
            DefinitionOfDone if successful, None otherwise
        """
        try:
            prompt = self.prompt_template.format(
                task_description=task_description,
                files_changed=files_changed,
                tests_info=tests_info or "No tests found in commit",
            )

            response = self.llm_provider.generate(prompt)

            # Parse JSON from response
            import json
            json_match = re.search(r'```json\s*\n(.*?)```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try parsing entire response as JSON
                data = json.loads(response)

            items = []
            dod_data = data.get('dod', data)
            if isinstance(dod_data, list):
                for item in dod_data:
                    if isinstance(item, dict):
                        desc = item.get('description', '')
                        type_str = item.get('type', 'functional')
                        ctype = self._parse_criterion_type(type_str)
                        items.append(DoDItem(
                            description=desc,
                            criterion_type=ctype,
                        ))
                    elif isinstance(item, str):
                        items.append(DoDItem(
                            description=item,
                            criterion_type=DoDCriterionType.FUNCTIONAL,
                        ))

            if items:
                return DefinitionOfDone(
                    items=items,
                    source=DoDSource.GENERATED,
                    format=DoDFormat.JSON,
                    generated_from=task_description,
                )

        except Exception as e:
            logger.warning(f"LLM DoD generation failed: {e}")

        return None

    def _generate_rule_based(
        self,
        task_description: str,
        patch: Optional[PatchContext] = None,
    ) -> DefinitionOfDone:
        """
        Generate DoD using rule-based approach.

        Creates standard DoD items based on task keywords and patch content.

        Args:
            task_description: Task description
            patch: Patch context

        Returns:
            DefinitionOfDone with rule-based items
        """
        items = []
        desc_lower = task_description.lower()

        # Always add functional requirement based on task
        items.append(DoDItem(
            description=self._generate_functional_item(task_description),
            criterion_type=DoDCriterionType.FUNCTIONAL,
        ))

        # Security items for security-related changes
        if any(kw in desc_lower for kw in ['security', 'vuln', 'auth', 'sanitize', 'validate', 'xss', 'sql', 'inject']):
            items.append(DoDItem(
                description="No new security vulnerabilities introduced",
                criterion_type=DoDCriterionType.SECURITY,
            ))
            items.append(DoDItem(
                description="Input validation implemented for user data",
                criterion_type=DoDCriterionType.SECURITY,
            ))

        # Test items based on changed files
        if patch:
            has_tests = any(
                'test' in f.path.lower() or 'spec' in f.path.lower()
                for f in patch.files
            )
            if has_tests:
                items.append(DoDItem(
                    description="All new tests pass",
                    criterion_type=DoDCriterionType.TEST,
                ))
            else:
                items.append(DoDItem(
                    description="Unit tests added for new functionality",
                    criterion_type=DoDCriterionType.TEST,
                ))
        else:
            items.append(DoDItem(
                description="Tests added or updated as needed",
                criterion_type=DoDCriterionType.TEST,
            ))

        # Documentation items for API/public changes
        if any(kw in desc_lower for kw in ['api', 'public', 'interface', 'endpoint']):
            items.append(DoDItem(
                description="API documentation updated",
                criterion_type=DoDCriterionType.DOCUMENTATION,
            ))

        # Performance items for performance-related changes
        if any(kw in desc_lower for kw in ['performance', 'optimize', 'speed', 'slow', 'fast']):
            items.append(DoDItem(
                description="Performance regression tests pass",
                criterion_type=DoDCriterionType.PERFORMANCE,
            ))

        # Code quality item
        items.append(DoDItem(
            description="Code follows project style guidelines",
            criterion_type=DoDCriterionType.CODE_QUALITY,
        ))

        return DefinitionOfDone(
            items=items,
            source=DoDSource.GENERATED,
            format=DoDFormat.CHECKLIST,
            generated_from=task_description,
        )

    def _generate_functional_item(self, task_description: str) -> str:
        """
        Generate functional DoD item from task description.

        Extracts the main action from task and converts to DoD format.
        """
        # Clean up task description
        desc = task_description.strip()

        # Remove common prefixes
        for prefix in ['implement', 'add', 'fix', 'update', 'create', 'refactor']:
            if desc.lower().startswith(prefix):
                desc = desc[len(prefix):].strip()
                break

        # Limit length
        if len(desc) > 100:
            desc = desc[:97] + "..."

        return f"Feature implemented: {desc}"

    def _format_files_changed(self, patch: Optional[PatchContext]) -> str:
        """
        Format changed files list for prompt.
        """
        if not patch or not patch.files:
            return "No files provided"

        lines = []
        for f in patch.files[:20]:  # Limit to 20 files
            change_symbol = {
                'added': '+',
                'modified': 'M',
                'deleted': '-',
                'renamed': 'R',
            }.get(f.change_type.value, '?')
            lines.append(f"  {change_symbol} {f.path}")

        if len(patch.files) > 20:
            lines.append(f"  ... and {len(patch.files) - 20} more files")

        return "\n".join(lines)

    def _extract_tests_info(self, patch: Optional[PatchContext]) -> str:
        """
        Extract test file information from patch.
        """
        if not patch or not patch.files:
            return ""

        test_files = [
            f for f in patch.files
            if 'test' in f.path.lower() or 'spec' in f.path.lower()
        ]

        if not test_files:
            return ""

        lines = ["Tests in commit:"]
        for f in test_files[:10]:
            lines.append(f"  - {f.path} ({f.total_additions} additions)")

        return "\n".join(lines)

    def _parse_criterion_type(self, type_str: str) -> DoDCriterionType:
        """
        Parse criterion type from string.
        """
        type_mapping = {
            'functional': DoDCriterionType.FUNCTIONAL,
            'security': DoDCriterionType.SECURITY,
            'test': DoDCriterionType.TEST,
            'documentation': DoDCriterionType.DOCUMENTATION,
            'doc': DoDCriterionType.DOCUMENTATION,
            'performance': DoDCriterionType.PERFORMANCE,
            'perf': DoDCriterionType.PERFORMANCE,
            'code_quality': DoDCriterionType.CODE_QUALITY,
            'quality': DoDCriterionType.CODE_QUALITY,
        }
        return type_mapping.get(type_str.lower(), DoDCriterionType.FUNCTIONAL)

    def suggest_additional_items(
        self,
        existing_dod: DefinitionOfDone,
        patch: PatchContext,
    ) -> List[DoDItem]:
        """
        Suggest additional DoD items based on patch analysis.

        Args:
            existing_dod: Current DoD
            patch: Patch context

        Returns:
            List of suggested additional items
        """
        suggestions = []
        existing_types = {item.criterion_type for item in existing_dod.items}

        # Suggest security item if not present and security-sensitive files changed
        if DoDCriterionType.SECURITY not in existing_types:
            security_paths = ['auth', 'security', 'crypto', 'password', 'token']
            if any(
                any(sp in f.path.lower() for sp in security_paths)
                for f in patch.files
            ):
                suggestions.append(DoDItem(
                    description="Security review completed",
                    criterion_type=DoDCriterionType.SECURITY,
                ))

        # Suggest test item if tests present but not in DoD
        if DoDCriterionType.TEST not in existing_types:
            has_tests = any(
                'test' in f.path.lower() for f in patch.files
            )
            if has_tests:
                suggestions.append(DoDItem(
                    description="All tests pass",
                    criterion_type=DoDCriterionType.TEST,
                ))

        return suggestions
