"""
DoD Extractor - Multi-source Definition of Done extraction

Extracts DoD from:
- PR Body (GitHub/GitLab)
- Jira tickets
- Commit messages
- Manual input

Supports formats:
- Markdown checklist (- [ ] item)
- YAML block
- Markdown section (## Definition of Done)
- JSON block
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any

import yaml

from ..models import (
    DefinitionOfDone,
    DoDItem,
    DoDSource,
    DoDFormat,
    DoDCriterionType,
    PatchContext,
)

logger = logging.getLogger(__name__)


class DoDExtractor:
    """
    Extracts Definition of Done from various sources.

    Supports multiple input sources and formats, with configurable
    priority order for source selection.
    """

    # Patterns for DoD section detection
    DOD_SECTION_PATTERNS = [
        r'##\s*definition\s*of\s*done',
        r'##\s*dod\b',
        r'##\s*acceptance\s*criteria',
        r'##\s*done\s*criteria',
        r'\*\*definition\s*of\s*done\*\*',
        r'\*\*dod\*\*',
    ]

    # Checklist item patterns
    CHECKLIST_PATTERNS = [
        r'^\s*-\s*\[\s*([xX ]?)\s*\]\s*(.+)$',  # - [ ] item or - [x] item
        r'^\s*\*\s*\[\s*([xX ]?)\s*\]\s*(.+)$',  # * [ ] item
    ]

    # Criterion type keywords (ordered by specificity - FUNCTIONAL last as fallback)
    CRITERION_KEYWORDS = {
        DoDCriterionType.TEST: ['test', 'coverage', 'unit', 'integration', 'spec'],
        DoDCriterionType.SECURITY: ['security', 'vuln', 'safe', 'sanitize', 'validate', 'auth'],
        DoDCriterionType.DOCUMENTATION: ['doc', 'comment', 'readme', 'changelog'],
        DoDCriterionType.PERFORMANCE: ['perf', 'speed', 'optimize', 'fast', 'slow'],
        DoDCriterionType.CODE_QUALITY: ['lint', 'style', 'format', 'clean', 'refactor'],
        DoDCriterionType.FUNCTIONAL: ['feature', 'function', 'work', 'implement', 'add'],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DoD extractor.

        Args:
            config: Configuration dictionary with:
                - sources: List of enabled sources
                - source_priority: Priority order for sources
                - formats: List of enabled formats
                - jira: Jira integration settings
        """
        self.config = config or {}
        self.enabled_sources = self.config.get('sources', [
            'pr_body', 'jira', 'commit_message', 'manual'
        ])
        self.source_priority = self.config.get('source_priority', [
            'pr_body', 'jira', 'commit_message'
        ])
        self.enabled_formats = self.config.get('formats', [
            'checklist', 'yaml', 'markdown', 'json'
        ])
        self.jira_config = self.config.get('jira', {})

    def extract(
        self,
        patch: PatchContext,
        pr_body: Optional[str] = None,
        jira_ticket: Optional[str] = None,
        manual_input: Optional[str] = None,
    ) -> Optional[DefinitionOfDone]:
        """
        Extract DoD from available sources in priority order.

        Args:
            patch: Patch context with commit information
            pr_body: PR/MR description text
            jira_ticket: Jira ticket ID
            manual_input: Manual DoD input

        Returns:
            DefinitionOfDone if found, None otherwise
        """
        for source in self.source_priority:
            if source not in self.enabled_sources:
                continue

            dod = None
            if source == 'pr_body' and pr_body:
                dod = self._extract_from_text(pr_body, DoDSource.PR_BODY)
            elif source == 'jira' and jira_ticket:
                dod = self._extract_from_jira(jira_ticket)
            elif source == 'commit_message':
                dod = self._extract_from_commit(patch)
            elif source == 'manual' and manual_input:
                dod = self._extract_from_text(manual_input, DoDSource.MANUAL)

            if dod and dod.items:
                logger.info(f"DoD extracted from {source}: {len(dod.items)} items")
                return dod

        logger.info("No DoD found in any source")
        return None

    def _extract_from_text(
        self,
        text: str,
        source: DoDSource,
    ) -> Optional[DefinitionOfDone]:
        """
        Extract DoD from text using multiple format parsers.

        Args:
            text: Text to parse
            source: Source type for metadata

        Returns:
            DefinitionOfDone if found, None otherwise
        """
        # Try YAML block first (most structured)
        if 'yaml' in self.enabled_formats:
            dod = self._parse_yaml_block(text, source)
            if dod:
                return dod

        # Try JSON block
        if 'json' in self.enabled_formats:
            dod = self._parse_json_block(text, source)
            if dod:
                return dod

        # Try Markdown section
        if 'markdown' in self.enabled_formats:
            dod = self._parse_markdown_section(text, source)
            if dod:
                return dod

        # Try checklist (most common)
        if 'checklist' in self.enabled_formats:
            dod = self._parse_checklist(text, source)
            if dod:
                return dod

        return None

    def _parse_checklist(
        self,
        text: str,
        source: DoDSource,
    ) -> Optional[DefinitionOfDone]:
        """
        Parse markdown checklist format.

        Example:
            - [ ] Feature works as expected
            - [x] Tests added
            - [ ] Documentation updated
        """
        items = []

        for line in text.split('\n'):
            for pattern in self.CHECKLIST_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    checked = match.group(1).lower() == 'x'
                    description = match.group(2).strip()
                    criterion_type = self._infer_criterion_type(description)
                    items.append(DoDItem(
                        description=description,
                        criterion_type=criterion_type,
                        is_satisfied=checked if checked else None,
                    ))
                    break

        if items:
            return DefinitionOfDone(
                items=items,
                source=source,
                format=DoDFormat.CHECKLIST,
                raw_text=text,
            )
        return None

    def _parse_yaml_block(
        self,
        text: str,
        source: DoDSource,
    ) -> Optional[DefinitionOfDone]:
        """
        Parse YAML block format.

        Example:
            ```yaml
            dod:
              - description: Feature works
                type: functional
              - description: Tests pass
                type: test
            ```
        """
        # Find YAML code block
        yaml_pattern = r'```ya?ml\s*\n(.*?)```'
        match = re.search(yaml_pattern, text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None

        yaml_text = match.group(1)
        try:
            data = yaml.safe_load(yaml_text)
            if not data:
                return None

            # Handle different YAML structures
            dod_data = data.get('dod') or data.get('definition_of_done') or data
            if isinstance(dod_data, list):
                items = []
                for item in dod_data:
                    if isinstance(item, str):
                        items.append(DoDItem(
                            description=item,
                            criterion_type=self._infer_criterion_type(item),
                        ))
                    elif isinstance(item, dict):
                        desc = item.get('description') or item.get('item') or str(item)
                        type_str = item.get('type', '')
                        items.append(DoDItem(
                            description=desc,
                            criterion_type=self._parse_criterion_type(type_str, desc),
                            is_satisfied=item.get('satisfied'),
                        ))
                if items:
                    return DefinitionOfDone(
                        items=items,
                        source=source,
                        format=DoDFormat.YAML,
                        raw_text=yaml_text,
                    )
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML DoD: {e}")

        return None

    def _parse_json_block(
        self,
        text: str,
        source: DoDSource,
    ) -> Optional[DefinitionOfDone]:
        """
        Parse JSON block format.

        Example:
            ```json
            {
              "dod": [
                {"description": "Feature works", "type": "functional"},
                {"description": "Tests pass", "type": "test"}
              ]
            }
            ```
        """
        # Find JSON code block
        json_pattern = r'```json\s*\n(.*?)```'
        match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None

        json_text = match.group(1)
        try:
            data = json.loads(json_text)
            if not data:
                return None

            dod_data = data.get('dod') or data.get('definition_of_done') or data
            if isinstance(dod_data, list):
                items = []
                for item in dod_data:
                    if isinstance(item, str):
                        items.append(DoDItem(
                            description=item,
                            criterion_type=self._infer_criterion_type(item),
                        ))
                    elif isinstance(item, dict):
                        desc = item.get('description') or item.get('item') or str(item)
                        type_str = item.get('type', '')
                        items.append(DoDItem(
                            description=desc,
                            criterion_type=self._parse_criterion_type(type_str, desc),
                            is_satisfied=item.get('satisfied'),
                        ))
                if items:
                    return DefinitionOfDone(
                        items=items,
                        source=source,
                        format=DoDFormat.JSON,
                        raw_text=json_text,
                    )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON DoD: {e}")

        return None

    def _parse_markdown_section(
        self,
        text: str,
        source: DoDSource,
    ) -> Optional[DefinitionOfDone]:
        """
        Parse markdown section format.

        Example:
            ## Definition of Done

            - Feature works as expected
            - Tests added and passing
            - Documentation updated
        """
        # Find DoD section
        section_start = None
        for pattern in self.DOD_SECTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section_start = match.end()
                break

        if section_start is None:
            return None

        # Extract content until next section or end
        remaining = text[section_start:]
        next_section = re.search(r'\n##\s', remaining)
        if next_section:
            section_text = remaining[:next_section.start()]
        else:
            section_text = remaining

        # Parse items from section (simple list)
        items = []
        for line in section_text.split('\n'):
            line = line.strip()
            # Skip empty lines and headers
            if not line or line.startswith('#'):
                continue

            # Remove list markers
            if line.startswith('- ') or line.startswith('* '):
                line = line[2:].strip()
            elif re.match(r'^\d+\.\s', line):
                line = re.sub(r'^\d+\.\s*', '', line).strip()
            else:
                continue  # Not a list item

            # Remove checkbox markers if present
            checkbox_match = re.match(r'^\[\s*([xX ]?)\s*\]\s*(.+)$', line)
            if checkbox_match:
                line = checkbox_match.group(2).strip()

            if line:
                items.append(DoDItem(
                    description=line,
                    criterion_type=self._infer_criterion_type(line),
                ))

        if items:
            return DefinitionOfDone(
                items=items,
                source=source,
                format=DoDFormat.MARKDOWN,
                raw_text=section_text,
            )
        return None

    def _extract_from_commit(
        self,
        patch: PatchContext,
    ) -> Optional[DefinitionOfDone]:
        """
        Extract DoD from commit message.

        Looks for DoD in the first commit message of the patch.
        """
        commit_msg = patch.metadata.get('commit_message', '')
        if not commit_msg:
            return None

        return self._extract_from_text(commit_msg, DoDSource.COMMIT_MESSAGE)

    def _extract_from_jira(
        self,
        ticket_id: str,
    ) -> Optional[DefinitionOfDone]:
        """
        Extract DoD from Jira ticket.

        Requires Jira integration configuration.
        """
        if not self.jira_config.get('url') or not self.jira_config.get('api_key'):
            logger.warning("Jira not configured, skipping Jira DoD extraction")
            return None

        try:
            # Import Jira client (optional dependency)
            from jira import JIRA

            jira = JIRA(
                server=self.jira_config['url'],
                token_auth=self.jira_config['api_key'],
            )

            issue = jira.issue(ticket_id)

            # Try DoD custom field first
            dod_field = self.jira_config.get('dod_field', 'customfield_10001')
            dod_text = getattr(issue.fields, dod_field, None)

            if dod_text:
                return self._extract_from_text(str(dod_text), DoDSource.JIRA)

            # Fall back to description
            if issue.fields.description:
                return self._extract_from_text(
                    issue.fields.description,
                    DoDSource.JIRA,
                )

        except ImportError:
            logger.warning("jira package not installed, skipping Jira extraction")
        except Exception as e:
            logger.warning(f"Failed to extract DoD from Jira: {e}")

        return None

    def _infer_criterion_type(self, description: str) -> DoDCriterionType:
        """
        Infer criterion type from description text.

        Uses keyword matching to determine the type.
        """
        desc_lower = description.lower()

        for ctype, keywords in self.CRITERION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return ctype

        return DoDCriterionType.FUNCTIONAL

    def _parse_criterion_type(
        self,
        type_str: str,
        fallback_desc: str,
    ) -> DoDCriterionType:
        """
        Parse criterion type from string or infer from description.
        """
        if type_str:
            type_str_lower = type_str.lower()
            for ctype in DoDCriterionType:
                if ctype.value == type_str_lower:
                    return ctype

        return self._infer_criterion_type(fallback_desc)

    def create_manual_dod(
        self,
        items: List[str],
        types: Optional[List[str]] = None,
    ) -> DefinitionOfDone:
        """
        Create DoD from manual list of items.

        Args:
            items: List of DoD item descriptions
            types: Optional list of criterion types (same length as items)

        Returns:
            DefinitionOfDone with manual source
        """
        dod_items = []
        for i, desc in enumerate(items):
            if types and i < len(types):
                ctype = self._parse_criterion_type(types[i], desc)
            else:
                ctype = self._infer_criterion_type(desc)

            dod_items.append(DoDItem(
                description=desc,
                criterion_type=ctype,
            ))

        return DefinitionOfDone(
            items=dod_items,
            source=DoDSource.MANUAL,
            format=DoDFormat.CHECKLIST,
            confirmed=True,  # Manual input is pre-confirmed
        )
