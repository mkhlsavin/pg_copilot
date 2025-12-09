"""
Chat Service Module.

Provides business logic for chat operations.
Integrates with MultiScenarioCopilot for processing queries.
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger("api.services.chat")


class Evidence(BaseModel):
    """Evidence from code analysis."""

    type: str
    content: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 1.0


class ChatResponse(BaseModel):
    """Response from chat service."""

    answer: str
    scenario_id: str
    confidence: float
    evidence: List[Evidence] = []
    session_id: Optional[str] = None
    request_id: str
    processing_time_ms: float
    metadata: Dict[str, Any] = {}


class ChatService:
    """
    Chat service for processing queries.

    Integrates with MultiScenarioCopilot for code analysis.
    """

    def __init__(self):
        """Initialize the chat service."""
        self._copilot = None
        self._intent_classifier = None

    async def initialize(self) -> None:
        """
        Initialize the chat service and load required components.

        This is called lazily on first use.
        """
        if self._copilot is not None:
            return

        try:
            from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

            self._copilot = MultiScenarioCopilot()
            logger.info("Chat service initialized with MultiScenarioCopilot")
        except Exception as e:
            logger.error(f"Failed to initialize MultiScenarioCopilot: {e}")
            raise

        try:
            from src.intent.intent_classifier import IntentClassifier

            self._intent_classifier = IntentClassifier()
            logger.info("Intent classifier initialized")
        except Exception as e:
            logger.warning(f"Intent classifier not available: {e}")

    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        user_id: str = "",
        language: str = "en",
        context: Optional[List[Dict[str, str]]] = None,
    ) -> ChatResponse:
        """
        Process a chat query.

        Args:
            query: User query
            session_id: Session ID for context
            scenario_id: Specific scenario to use (optional)
            user_id: User ID
            language: Language code
            context: Previous dialogue turns for context

        Returns:
            Chat response
        """
        await self.initialize()

        start_time = time.time()
        request_id = f"{user_id}_{int(start_time * 1000)}"

        try:
            # Classify intent if no scenario specified
            if not scenario_id and self._intent_classifier:
                classification = self._intent_classifier.classify(query)
                scenario_id = classification.scenario_id
                confidence = classification.confidence
            else:
                confidence = 1.0

            scenario_id = scenario_id or "general_qa"

            # Process query through copilot
            if self._copilot:
                result = await self._process_with_copilot(
                    query=query,
                    scenario_id=scenario_id,
                    context=context,
                    language=language,
                )
            else:
                result = self._generate_fallback_response(query)

            processing_time_ms = (time.time() - start_time) * 1000

            return ChatResponse(
                answer=result.get("answer", ""),
                scenario_id=scenario_id,
                confidence=confidence,
                evidence=[
                    Evidence(**e) for e in result.get("evidence", [])
                ],
                session_id=session_id,
                request_id=request_id,
                processing_time_ms=processing_time_ms,
                metadata=result.get("metadata", {}),
            )

        except Exception as e:
            logger.exception(f"Error processing query: {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return ChatResponse(
                answer=f"Error processing query: {str(e)}",
                scenario_id=scenario_id or "error",
                confidence=0.0,
                evidence=[],
                session_id=session_id,
                request_id=request_id,
                processing_time_ms=processing_time_ms,
            )

    async def process_query_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        user_id: str = "",
        language: str = "en",
        context: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Process a chat query with streaming response.

        Args:
            query: User query
            session_id: Session ID
            scenario_id: Specific scenario
            user_id: User ID
            language: Language code
            context: Previous dialogue turns

        Yields:
            Response chunks
        """
        await self.initialize()

        try:
            # Classify intent if no scenario specified
            if not scenario_id and self._intent_classifier:
                classification = self._intent_classifier.classify(query)
                scenario_id = classification.scenario_id

            scenario_id = scenario_id or "general_qa"

            # Yield scenario info first
            yield f"data: {{\"type\": \"scenario\", \"scenario_id\": \"{scenario_id}\"}}\n\n"

            # Process query and stream response
            if self._copilot:
                async for chunk in self._stream_copilot_response(
                    query=query,
                    scenario_id=scenario_id,
                    context=context,
                    language=language,
                ):
                    yield f"data: {{\"type\": \"chunk\", \"content\": {repr(chunk)}}}\n\n"
            else:
                # Fallback response
                fallback = self._generate_fallback_response(query)
                yield f"data: {{\"type\": \"chunk\", \"content\": {repr(fallback['answer'])}}}\n\n"

            # End of stream
            yield "data: {\"type\": \"done\"}\n\n"

        except Exception as e:
            logger.exception(f"Error in streaming query: {e}")
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    async def _process_with_copilot(
        self,
        query: str,
        scenario_id: str,
        context: Optional[List[Dict[str, str]]],
        language: str,
    ) -> Dict[str, Any]:
        """Process query using MultiScenarioCopilot."""
        import asyncio

        try:
            # Build context dict for copilot
            context_dict = {
                "scenario_id": scenario_id,
                "language": language,
            }
            if context:
                context_dict["history"] = [
                    f"{turn.get('role', 'user')}: {turn.get('content', '')}"
                    for turn in context[-5:]  # Last 5 turns
                ]

            # Run sync copilot.run() in thread pool (non-blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # default executor
                lambda: self._copilot.run(query, context_dict)
            )

            # Check for errors in result
            if result.get("error"):
                logger.warning(f"Copilot returned error: {result.get('error')}")

            return {
                "answer": result.get("answer", ""),
                "evidence": self._convert_evidence(result),
                "metadata": {
                    "scenario": result.get("scenario_id", scenario_id),
                    "confidence": result.get("confidence", 0.0),
                    "classification_method": result.get("classification_method"),
                },
            }
        except Exception as e:
            logger.error(f"Copilot processing error: {e}")
            return self._generate_fallback_response(query)

    def _convert_evidence(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert copilot evidence to API format."""
        evidence = []

        # Extract from CPG results
        cpg_results = result.get("cpg_results") or []
        for item in cpg_results[:10]:  # Limit to 10
            if isinstance(item, dict):
                evidence.append({
                    "type": "code",
                    "content": item.get("code", str(item)),
                    "file_path": item.get("filename"),
                    "line_number": item.get("line"),
                    "confidence": 1.0,
                })

        # Extract from methods
        methods = result.get("methods") or []
        for method in methods[:5]:
            if isinstance(method, dict):
                evidence.append({
                    "type": "method",
                    "content": method.get("name", str(method)),
                    "file_path": method.get("filename"),
                    "line_number": method.get("line"),
                    "confidence": 0.9,
                })

        return evidence

    async def _stream_copilot_response(
        self,
        query: str,
        scenario_id: str,
        context: Optional[List[Dict[str, str]]],
        language: str,
    ) -> AsyncGenerator[str, None]:
        """Stream response from copilot."""
        # Note: Actual streaming depends on copilot implementation
        # This is a simulation for non-streaming copilot
        result = await self._process_with_copilot(
            query=query,
            scenario_id=scenario_id,
            context=context,
            language=language,
        )

        answer = result.get("answer", "")

        # Simulate streaming by yielding chunks
        chunk_size = 50
        for i in range(0, len(answer), chunk_size):
            yield answer[i : i + chunk_size]

    def _generate_fallback_response(self, query: str) -> Dict[str, Any]:
        """Generate fallback response when copilot is unavailable."""
        return {
            "answer": (
                "I apologize, but the code analysis system is currently unavailable. "
                "Please try again later or contact support if the issue persists."
            ),
            "evidence": [],
            "metadata": {"fallback": True},
        }

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """
        Get list of available scenarios.

        Returns:
            List of scenario information
        """
        try:
            from src.intent.intent_taxonomy import SCENARIOS

            return [
                {
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "keywords": scenario.keywords,
                    "examples": scenario.example_queries[:3] if scenario.example_queries else [],
                }
                for scenario in SCENARIOS
            ]
        except Exception as e:
            logger.error(f"Failed to get scenarios: {e}")
            return []

    def get_scenario_info(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific scenario.

        Args:
            scenario_id: Scenario ID

        Returns:
            Scenario information or None
        """
        try:
            from src.intent.intent_taxonomy import SCENARIOS

            for scenario in SCENARIOS:
                if scenario.id == scenario_id:
                    return {
                        "id": scenario.id,
                        "name": scenario.name,
                        "description": scenario.description,
                        "keywords": scenario.keywords,
                        "examples": scenario.example_queries,
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get scenario info: {e}")
            return None


# Global chat service instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get the global chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
