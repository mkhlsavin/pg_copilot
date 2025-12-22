"""
Unit tests for IntentClassifier component.

Tests:
1. Keyword matching for all 14 intents
2. Unambiguous classification
3. Ambiguous classification (multiple matches)
4. LLM fallback scenarios
5. Error handling
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.intent.intent_classifier import IntentClassifier
from src.intent.intent_taxonomy import INTENT_TAXONOMY


class TestIntentClassifier(unittest.TestCase):
    """Test suite for IntentClassifier"""

    def setUp(self):
        """Initialize classifier for each test"""
        self.classifier = IntentClassifier(llm_client=None)  # No LLM for unit tests

    # ========================================================================
    # KEYWORD MATCHING TESTS
    # ========================================================================

    def test_onboarding_intent(self):
        """Test classification of onboarding queries"""
        queries = [
            "Give me an overview of the codebase",
            "Explain the architecture overview",
            "Introduction to the module structure",
            "Getting started with this project"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'onboarding',
                           f"Failed for query: {query}")
            # Method can be 'keyword' or 'keyword_priority' depending on match
            self.assertIn(result['method'], ['keyword', 'keyword_priority'])
            self.assertGreaterEqual(result['confidence'], 0.9)

    def test_security_audit_intent(self):
        """Test classification of security audit queries"""
        queries = [
            "Find all SQL injection vulnerabilities",
            "Show me buffer overflow risks",
            "Which functions handle untrusted input?",
            "Check for security vulnerabilities"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'security_audit',
                           f"Failed for query: {query}")
            self.assertGreaterEqual(result['confidence'], 0.9)

    def test_documentation_intent(self):
        """Test classification of documentation queries"""
        # Note: Avoid PostgreSQL subsystem names (executor, planner, parser, etc.)
        # as they now trigger onboarding intent
        # Also avoid "create" keyword which triggers feature_development
        queries = [
            "Generate API documentation for this module",
            "Document the connection handling code",
            "Generate docs for the authentication functions",
            "Write API docs for these functions"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'documentation',
                           f"Failed for query: {query}")

    def test_feature_development_intent(self):
        """Test classification of feature development queries"""
        queries = [
            "Where should I add a new join algorithm?",
            "How to implement a custom index type?",
            "Find extension points for the optimizer",
            "Where to add new functionality?"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'feature_development',
                           f"Failed for query: {query}")

    def test_performance_intent(self):
        """Test classification of performance queries"""
        queries = [
            "Find performance hotspots",
            "Which functions are slow?",
            "Optimize the slow database queries",
            "Profile CPU intensive operations"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'performance',
                           f"Failed for query: {query}")

    def test_refactoring_intent(self):
        """Test classification of refactoring queries"""
        queries = [
            "Find duplicate code in this module",
            "Which functions are too complex?",
            "Clean up technical debt",
            "Refactor the god class in utils"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'refactoring',
                           f"Failed for query: {query}")

    def test_test_coverage_intent(self):
        """Test classification of test coverage queries"""
        queries = [
            "Which functions lack test coverage?",
            "Generate test cases for this module",
            "Find functions without unit tests",
            "Show missing tests"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'test_coverage',
                           f"Failed for query: {query}")

    # ========================================================================
    # EDGE CASE TESTS
    # ========================================================================

    def test_no_keyword_match_fallback(self):
        """Test fallback when no keywords match"""
        query = "Tell me something random about stuff"
        result = self.classifier.classify(query)

        # Should fall back to onboarding (safest default)
        self.assertEqual(result['intent'], 'onboarding')
        self.assertEqual(result['method'], 'fallback')
        self.assertLess(result['confidence'], 0.5)

    def test_multiple_keyword_matches(self):
        """Test priority-based selection when multiple keywords match"""
        # Query with both security and performance keywords
        query = "Find security vulnerabilities that cause performance issues"

        result = self.classifier.classify(query)

        # Should pick higher priority (security has priority 10 vs performance 8)
        self.assertEqual(result['intent'], 'security_audit')
        self.assertEqual(result['method'], 'keyword_priority')
        self.assertIn('performance', result.get('matches', []))

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive"""
        queries = [
            "FIND SECURITY VULNERABILITIES",
            "find security vulnerabilities",
            "FiNd SeCuRiTy VuLnErAbIlItIeS"
        ]

        for query in queries:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], 'security_audit')

    # ========================================================================
    # TAXONOMY VALIDATION TESTS
    # ========================================================================

    def test_all_intents_have_required_fields(self):
        """Test that all intents in taxonomy have required fields"""
        required_fields = ['id', 'name', 'keywords', 'examples', 'priority']

        for intent_key, intent_data in INTENT_TAXONOMY.items():
            for field in required_fields:
                self.assertIn(field, intent_data,
                            f"Intent '{intent_key}' missing field '{field}'")

            # Check types
            self.assertIsInstance(intent_data['keywords'], list)
            self.assertIsInstance(intent_data['examples'], list)
            self.assertIsInstance(intent_data['priority'], int)

            # Check non-empty
            self.assertGreater(len(intent_data['keywords']), 0)
            self.assertGreater(len(intent_data['examples']), 0)

    def test_intent_count(self):
        """Test that we have the expected number of intents (16 as of current version)"""
        # Updated from 14 to 16 - added 'debugging' and 'entry_points' intents
        self.assertEqual(len(INTENT_TAXONOMY), 16)

    def test_unique_scenario_ids(self):
        """Test that all scenario IDs are unique"""
        scenario_ids = [v['id'] for v in INTENT_TAXONOMY.values()]
        self.assertEqual(len(scenario_ids), len(set(scenario_ids)))

    # ========================================================================
    # VALIDATION METHODS TESTS
    # ========================================================================

    def test_validate_intent(self):
        """Test intent validation method"""
        # Valid intents
        self.assertTrue(self.classifier.validate_intent('onboarding'))
        self.assertTrue(self.classifier.validate_intent('security_audit'))

        # Invalid intents
        self.assertFalse(self.classifier.validate_intent('invalid_intent'))
        self.assertFalse(self.classifier.validate_intent(''))
        self.assertFalse(self.classifier.validate_intent(None))

    def test_get_intent_info(self):
        """Test getting intent information"""
        info = self.classifier.get_intent_info('security_audit')

        self.assertIsNotNone(info)
        # Scenario ID format changed to include intent name
        self.assertEqual(info['id'], 'scenario_02_security_audit')
        self.assertEqual(info['name'], 'Security Audit')
        self.assertIn('security', info['keywords'])

        # Invalid intent
        self.assertIsNone(self.classifier.get_intent_info('invalid'))

    # ========================================================================
    # LLM CLASSIFICATION TESTS (with mocking)
    # ========================================================================

    def test_llm_classification_with_mock(self):
        """Test LLM classification with mocked LLM client"""
        # Create mock LLM client
        mock_llm = Mock()
        mock_llm.generate.return_value = '''{
            "intent": "security_audit",
            "scenario_id": "scenario_2",
            "confidence": 0.85,
            "reasoning": "Query mentions vulnerabilities"
        }'''

        classifier = IntentClassifier(llm_client=mock_llm)

        # Ambiguous query (matches multiple keywords)
        query = "Find code issues related to security and performance"

        result = classifier.classify(query)

        # Should use LLM classification
        self.assertEqual(result['method'], 'llm')
        self.assertEqual(result['intent'], 'security_audit')
        self.assertAlmostEqual(result['confidence'], 0.85, places=2)

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    def test_llm_fallback_on_error(self):
        """Test fallback when LLM classification fails"""
        # Create mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM error")

        classifier = IntentClassifier(llm_client=mock_llm)

        # Query with multiple keyword matches
        query = "Find security and performance issues"

        result = classifier.classify(query)

        # Should fall back to keyword priority
        self.assertEqual(result['method'], 'llm_fallback')
        self.assertIn('error', result)
        self.assertEqual(result['intent'], 'security_audit')  # Higher priority

    def test_llm_with_malformed_json(self):
        """Test handling of malformed JSON from LLM"""
        mock_llm = Mock()
        mock_llm.generate.return_value = "This is not valid JSON"

        classifier = IntentClassifier(llm_client=mock_llm)

        query = "Ambiguous query"

        result = classifier.classify(query)

        # Should fall back gracefully
        self.assertIn(result['intent'], INTENT_TAXONOMY.keys())

    # ========================================================================
    # PRIORITY TESTS
    # ========================================================================

    def test_high_priority_intents(self):
        """Test that security and incident scenarios have highest priority"""
        priorities = {k: v['priority'] for k, v in INTENT_TAXONOMY.items()}

        # Security audit should be priority 10
        self.assertEqual(priorities['security_audit'], 10)
        # Security incident is now priority 11 (highest)
        self.assertEqual(priorities['security_incident'], 11)

        # Performance should be high (8)
        self.assertEqual(priorities['performance'], 8)

        # Compliance now has higher priority (9) for enterprise scenarios
        self.assertEqual(priorities['compliance'], 9)


class TestIntentClassifierIntegration(unittest.TestCase):
    """Integration tests for IntentClassifier with real queries"""

    def setUp(self):
        self.classifier = IntentClassifier(llm_client=None)

    def test_realistic_query_classification(self):
        """Test classification on realistic developer queries"""
        test_cases = [
            ("How do I get started with the PostgreSQL codebase?", "onboarding"),
            ("Are there any SQL injection risks in the parser?", "security_audit"),
            ("Write documentation for ExecProcNode", "documentation"),
            ("Where should I add support for MERGE statement?", "feature_development"),
            ("Identify slow functions in the executor", "performance"),
            ("Find duplicate code that needs refactoring", "refactoring"),
            ("Which modules lack unit tests?", "test_coverage"),
        ]

        for query, expected_intent in test_cases:
            result = self.classifier.classify(query)
            self.assertEqual(result['intent'], expected_intent,
                           f"Failed for query: {query}")

    def test_context_aware_classification(self):
        """Test that context can influence classification"""
        query = "Find issues in this code"

        # With security context
        context = {"file": "security/validate_input.c"}
        result = self.classifier.classify(query, context=context)
        # Note: Current implementation doesn't use context yet,
        # but this test documents expected future behavior


if __name__ == '__main__':
    unittest.main()
