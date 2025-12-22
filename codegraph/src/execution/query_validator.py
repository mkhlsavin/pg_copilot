"""CPGQL query validator for safety and syntax checks."""
import json
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validate CPGQL queries before execution."""

    REQUIRED_START = 'cpg'
    ALLOWED_NODE_TYPES = [
        'method', 'call', 'identifier', 'parameter', 'literal',
        'local', 'file', 'namespace', 'typeDecl', 'member',
        'metaData', 'comment', 'block', 'controlStructure'
    ]
    ALLOWED_TRAVERSALS = [
        'caller', 'callee', 'ast', 'dataFlow', 'reachableBy',
        'controlledBy', 'dominates', 'postDominates', 'cfgNext',
        'argument', 'receiver', 'inCall', 'isExternal', 'isPublic',
        'isPrivate', 'isStatic', 'isVirtual', 'filter', 'where',
        'name', 'code', 'lineNumber', 'columnNumber', 'order',
        'fullName', 'signature', 'filename', 'l', 'p', 'head',
        'take', 'drop', 'map', 'flatMap', 'foreach', 'collect'
    ]

    # Dangerous patterns that could harm the system
    DANGEROUS_PATTERNS = [
        'system', 'exec', 'runtime', 'import', 'os.', 'subprocess',
        'file.write', 'file.delete', 'process.', '__import__',
        'eval', 'compile'
    ]

    def is_valid(self, query: str) -> Tuple[bool, str]:
        """
        Check if query is safe to execute.

        Args:
            query: CPGQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "Query must be non-empty string"

        query_lower = query.lower().strip()

        # Must start with 'cpg'
        if not query_lower.startswith(self.REQUIRED_START):
            return False, f"Query must start with '{self.REQUIRED_START}'"

        # Check for dangerous operations
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in query_lower:
                return False, f"Dangerous pattern detected: {pattern}"

        # Should end with .l or .p or other terminator
        if not any(query_lower.endswith(term) for term in ['.l', '.p', '.tolist', '.toset']):
            logger.warning(f"Query does not end with standard terminator (.l, .p, etc.)")

        return True, "Valid"

    def parse_json_query(self, text: str) -> Tuple[str, str]:
        """
        Extract CPGQL query from JSON response.

        Args:
            text: LLM response text (may contain JSON)

        Returns:
            Tuple of (query_string, error_message)
        """
        try:
            # Try to parse as JSON
            if '{' in text and '}' in text:
                # Extract JSON object
                start = text.find('{')
                end = text.rfind('}') + 1
                json_str = text[start:end]

                data = json.loads(json_str)

                # Look for query field
                if 'query' in data:
                    return data['query'], None
                elif 'queries' in data and isinstance(data['queries'], list):
                    # Return first query if multiple
                    return data['queries'][0], None
                else:
                    return None, "No 'query' field found in JSON"
            else:
                return None, "No JSON object found in response"

        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {e}"
        except Exception as e:
            return None, f"Error parsing query: {e}"

    def validate_and_parse(self, llm_response: str) -> Tuple[str, bool, str]:
        """
        Parse and validate LLM response containing CPGQL query.

        Args:
            llm_response: Raw LLM response text

        Returns:
            Tuple of (query_string, is_valid, message)
        """
        # Parse JSON
        query, parse_error = self.parse_json_query(llm_response)

        if parse_error:
            return None, False, f"Parse error: {parse_error}"

        # Validate
        is_valid, validation_msg = self.is_valid(query)

        return query, is_valid, validation_msg
