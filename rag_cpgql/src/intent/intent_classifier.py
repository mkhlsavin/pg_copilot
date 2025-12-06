"""
Hybrid Intent Classifier for multi-scenario routing.

Uses a two-tier approach:
1. Keyword matching for unambiguous queries (fast, rule-based)
2. LLM classification for ambiguous queries (slower, contextual)
"""

import re
from typing import Dict, List, Optional, Any
from .intent_taxonomy import INTENT_TAXONOMY


class IntentClassifier:
    """
    Classifies user queries into one of 14 enterprise scenarios.

    Architecture:
    - Stage 1: Keyword matching (95% confidence if single match)
    - Stage 2: LLM classification (if ambiguous or no keyword match)

    Input:
        query: str - User's natural language question
        context: Dict - Optional context (file path, previous intent, etc.)

    Output:
        {
            "intent": str,           # Intent key (e.g., "security_audit")
            "scenario_id": str,      # Scenario ID (e.g., "scenario_2")
            "confidence": float,     # 0.0 - 1.0
            "method": str,           # "keyword" or "llm"
            "matches": List[str]     # All keyword matches found
        }
    """

    def __init__(self, llm_client=None):
        """
        Initialize classifier.

        Args:
            llm_client: Optional LLM client for ambiguous classification
                       If None, will use keyword matching only
        """
        self.taxonomy = INTENT_TAXONOMY
        self.llm_client = llm_client

    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify user query into an intent.

        Args:
            query: User's question
            context: Optional context (file, subsystem, previous intent)

        Returns:
            Classification result with intent, confidence, method
        """
        # Stage 1: Keyword matching
        keyword_matches = self._match_keywords(query)

        # Unambiguous keyword match - use it directly
        if len(keyword_matches) == 1:
            intent_key = keyword_matches[0]
            return {
                "intent": intent_key,
                "scenario_id": self.taxonomy[intent_key]["id"],
                "confidence": 0.95,
                "method": "keyword",
                "matches": [intent_key]
            }

        # Multiple matches or no matches - use LLM if available
        if self.llm_client:
            return self._llm_classify(query, context, keyword_matches)

        # No LLM - use heuristics
        if len(keyword_matches) > 1:
            # Pick highest priority match
            best_match = max(
                keyword_matches,
                key=lambda k: self.taxonomy[k]["priority"]
            )
            return {
                "intent": best_match,
                "scenario_id": self.taxonomy[best_match]["id"],
                "confidence": 0.7,
                "method": "keyword_priority",
                "matches": keyword_matches
            }

        # No matches - default to onboarding (safest fallback)
        return {
            "intent": "onboarding",
            "scenario_id": "scenario_1",
            "confidence": 0.3,
            "method": "fallback",
            "matches": []
        }

    def _match_keywords(self, query: str) -> List[str]:
        """
        Match query against keyword patterns for all intents.

        Returns:
            List of intent keys that matched keywords
        """
        query_lower = query.lower()
        matches = []

        for intent_key, intent_data in self.taxonomy.items():
            # Check if any keyword appears in query
            for keyword in intent_data["keywords"]:
                keyword_lower = keyword.lower()

                # For multi-word keywords, use substring match
                # For single-word keywords, use word boundaries
                if ' ' in keyword_lower:
                    # Multi-word phrase - simple substring match
                    if keyword_lower in query_lower:
                        matches.append(intent_key)
                        break
                else:
                    # Single word - use word boundaries to avoid false positives
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    if re.search(pattern, query_lower):
                        matches.append(intent_key)
                        break  # One match per intent is enough

        return matches

    def _llm_classify(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        keyword_matches: List[str]
    ) -> Dict[str, Any]:
        """
        Use LLM to classify ambiguous queries.

        Args:
            query: User question
            context: Optional context
            keyword_matches: Preliminary keyword matches (may be empty)

        Returns:
            Classification result from LLM
        """
        # Build prompt with intent taxonomy
        prompt = self._build_classification_prompt(query, keyword_matches)

        try:
            # Call LLM
            response = self.llm_client.generate(prompt)

            # Parse LLM response (expecting JSON with intent and confidence)
            result = self._parse_llm_response(response)
            result["method"] = "llm"
            result["matches"] = keyword_matches

            return result

        except Exception as e:
            # LLM failed - fall back to keyword priority or default
            if keyword_matches:
                best_match = max(
                    keyword_matches,
                    key=lambda k: self.taxonomy[k]["priority"]
                )
                return {
                    "intent": best_match,
                    "scenario_id": self.taxonomy[best_match]["id"],
                    "confidence": 0.6,
                    "method": "llm_fallback",
                    "matches": keyword_matches,
                    "error": str(e)
                }

            return {
                "intent": "onboarding",
                "scenario_id": "scenario_1",
                "confidence": 0.3,
                "method": "error_fallback",
                "matches": [],
                "error": str(e)
            }

    def _build_classification_prompt(self, query: str, hints: List[str]) -> str:
        """
        Build LLM prompt for intent classification.

        Args:
            query: User question
            hints: Keyword match hints

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an intent classifier for a code analysis assistant.

Given a user query, classify it into ONE of these 14 scenarios:

"""

        # Add all scenarios
        for intent_key, intent_data in self.taxonomy.items():
            prompt += f"{intent_data['id']}: {intent_data['name']}\n"
            prompt += f"   Keywords: {', '.join(intent_data['keywords'][:5])}\n"
            prompt += f"   Example: {intent_data['examples'][0]}\n\n"

        prompt += f"""
User Query: "{query}"

"""

        if hints:
            prompt += f"Keyword matches suggest: {', '.join(hints)}\n\n"

        prompt += """Respond in JSON format:
{
    "intent": "<intent_key>",
    "scenario_id": "<scenario_id>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}
"""

        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response.

        Args:
            response: LLM output (should be JSON)

        Returns:
            Parsed classification result
        """
        import json

        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)

            # Validate intent exists
            intent_key = data.get("intent")
            if intent_key not in self.taxonomy:
                raise ValueError(f"Invalid intent: {intent_key}")

            return {
                "intent": intent_key,
                "scenario_id": data.get("scenario_id", self.taxonomy[intent_key]["id"]),
                "confidence": float(data.get("confidence", 0.8)),
                "reasoning": data.get("reasoning", "")
            }

        except (json.JSONDecodeError, ValueError) as e:
            # Parse failed - return default
            return {
                "intent": "onboarding",
                "scenario_id": "scenario_1",
                "confidence": 0.3,
                "reasoning": f"Parse error: {e}"
            }

    def get_intent_info(self, intent_key: str) -> Optional[Dict[str, Any]]:
        """
        Get full information about an intent.

        Args:
            intent_key: Intent identifier

        Returns:
            Intent metadata or None if not found
        """
        return self.taxonomy.get(intent_key)

    def validate_intent(self, intent_key: str) -> bool:
        """
        Check if intent key is valid.

        Args:
            intent_key: Intent to validate

        Returns:
            True if valid, False otherwise
        """
        return intent_key in self.taxonomy
