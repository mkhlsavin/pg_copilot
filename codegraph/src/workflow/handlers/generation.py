"""Generation Handler for LLM response generation.

Handles:
- Query generation from natural language
- Response synthesis and formatting
- Prompt building and template rendering
- Multi-turn conversation context
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseHandler, HandlerResult

logger = logging.getLogger(__name__)


class GenerationHandler(BaseHandler):
    """
    Handler for LLM response generation.

    Manages prompt building, query generation, and
    response synthesis using configured LLM providers.
    """

    def __init__(
        self,
        llm_provider=None,
        generator_agent=None,
        prompt_registry=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize generation handler.

        Args:
            llm_provider: LLM provider instance
            generator_agent: GeneratorAgent for query generation
            prompt_registry: PromptRegistry for templates
            config: Additional configuration
        """
        super().__init__(config)
        self._llm = llm_provider
        self._generator = generator_agent
        self._prompts = prompt_registry
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history = config.get('max_history', 10) if config else 10

    def set_llm(self, llm_provider):
        """Set or update LLM provider."""
        self._llm = llm_provider
        self.log_info("LLM provider updated")

    def set_generator(self, generator_agent):
        """Set or update generator agent."""
        self._generator = generator_agent
        self.log_info("Generator agent updated")

    def handle(
        self,
        operation: str,
        **kwargs
    ) -> HandlerResult:
        """
        Execute generation operation.

        Args:
            operation: Type of generation operation
            **kwargs: Operation-specific arguments

        Returns:
            HandlerResult with generated content
        """
        start_time = time.time()

        try:
            if operation == "query":
                result = self._generate_query(**kwargs)
            elif operation == "response":
                result = self._generate_response(**kwargs)
            elif operation == "summary":
                result = self._generate_summary(**kwargs)
            elif operation == "explanation":
                result = self._generate_explanation(**kwargs)
            elif operation == "prompt":
                result = self._build_prompt(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, True)

            return HandlerResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                metadata={"operation": operation}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, False)
            self.log_error(f"Generation failed ({operation}): {e}")

            return HandlerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                metadata={"operation": operation}
            )

    def generate_query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Generate SQL query from natural language question.

        Args:
            question: Natural language question
            context: Optional retrieval context

        Returns:
            HandlerResult with generated query
        """
        return self.handle("query", question=question, context=context)

    def generate_response(
        self,
        question: str,
        query_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Generate natural language response from query results.

        Args:
            question: Original question
            query_results: Results from CPG query
            context: Optional additional context

        Returns:
            HandlerResult with formatted response
        """
        return self.handle(
            "response",
            question=question,
            query_results=query_results,
            context=context
        )

    def generate_summary(
        self,
        content: str,
        max_length: int = 500
    ) -> HandlerResult:
        """
        Generate summary of content.

        Args:
            content: Content to summarize
            max_length: Maximum summary length

        Returns:
            HandlerResult with summary
        """
        return self.handle(
            "summary",
            content=content,
            max_length=max_length
        )

    def generate_explanation(
        self,
        code: str,
        context: Optional[str] = None
    ) -> HandlerResult:
        """
        Generate explanation of code.

        Args:
            code: Code to explain
            context: Optional context about the code

        Returns:
            HandlerResult with explanation
        """
        return self.handle(
            "explanation",
            code=code,
            context=context
        )

    def add_to_history(self, role: str, content: str):
        """
        Add message to conversation history.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self._conversation_history.append({
            "role": role,
            "content": content
        })

        # Trim history if needed
        if len(self._conversation_history) > self._max_history:
            self._conversation_history = self._conversation_history[-self._max_history:]

    def clear_history(self):
        """Clear conversation history."""
        self._conversation_history.clear()
        self.log_info("Conversation history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._conversation_history.copy()

    # === Private Generation Methods ===

    def _generate_query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SQL query from question."""
        if self._generator:
            # Use generator agent if available
            query, is_valid, error = self._generator.generate(
                question=question,
                context=context or {}
            )
            return {
                "query": query,
                "valid": is_valid,
                "error": error,
                "method": "generator_agent"
            }

        # Fallback: use LLM directly
        if not self._llm:
            raise RuntimeError("No generator agent or LLM provider available")

        prompt = self._build_query_prompt(question, context)
        response = self._llm.generate_simple(
            prompt=prompt,
            max_tokens=300,
            temperature=0.3
        )

        # Extract query from response
        query = self._extract_query(response)

        return {
            "query": query,
            "valid": True,  # Assume valid, will be checked by executor
            "error": None,
            "method": "llm_direct",
            "raw_response": response
        }

    def _generate_response(
        self,
        question: str,
        query_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate natural language response."""
        if not self._llm:
            # Return structured response without LLM
            return self._format_results_as_response(question, query_results)

        # Build prompt with results
        prompt = self._build_response_prompt(question, query_results, context)

        response = self._llm.generate_simple(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7
        )

        # Add to history
        self.add_to_history("user", question)
        self.add_to_history("assistant", response)

        return {
            "response": response,
            "result_count": len(query_results),
            "question": question
        }

    def _generate_summary(
        self,
        content: str,
        max_length: int = 500
    ) -> Dict[str, Any]:
        """Generate summary of content."""
        if not self._llm:
            # Simple truncation fallback
            summary = content[:max_length]
            if len(content) > max_length:
                summary += "..."
            return {"summary": summary, "method": "truncation"}

        prompt = f"""Summarize the following content in {max_length} characters or less.
Focus on the key points and main findings.

Content:
{content}

Summary:"""

        response = self._llm.generate_simple(
            prompt=prompt,
            max_tokens=max_length // 3,  # Rough token estimate
            temperature=0.5
        )

        return {
            "summary": response,
            "original_length": len(content),
            "method": "llm"
        }

    def _generate_explanation(
        self,
        code: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate code explanation."""
        if not self._llm:
            return {
                "explanation": "LLM not available for explanation",
                "code_lines": len(code.split('\n'))
            }

        context_text = f"\nContext: {context}" if context else ""

        prompt = f"""Explain the following code in clear, concise terms.
Describe what it does, its purpose, and any important implementation details.
{context_text}

Code:
```
{code}
```

Explanation:"""

        response = self._llm.generate_simple(
            prompt=prompt,
            max_tokens=500,
            temperature=0.5
        )

        return {
            "explanation": response,
            "code_lines": len(code.split('\n'))
        }

    def _build_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build prompt from template."""
        if self._prompts:
            try:
                prompt = self._prompts.get_prompt(template_name, **variables)
                return {"prompt": prompt, "template": template_name}
            except Exception as e:
                self.log_warning(f"Template not found: {template_name}, error: {e}")

        # Fallback: simple variable substitution
        template = variables.get('_template', '')
        for key, value in variables.items():
            if key != '_template':
                template = template.replace(f'{{{key}}}', str(value))

        return {"prompt": template, "template": "fallback"}

    def _build_query_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for query generation."""
        prompt_parts = [
            "You are a SQL query generator for Code Property Graph analysis.",
            "Generate a SQL query to answer the following question.",
            "",
            "Available tables:",
            "- nodes_method: id, name, full_name, filename, line_number, signature",
            "- nodes_call: id, name, code, filename, line_number, containing_method_id",
            "- nodes_comment: id, code, filename, containing_method_id",
            "- edges_call: src, dst (nodes_call.id -> nodes_method.id)",
            ""
        ]

        if context and context.get('enrichment_hints'):
            hints = context['enrichment_hints']
            if hints.get('tags'):
                prompt_parts.append("Relevant keywords:")
                for tag in hints['tags'][:5]:
                    value = tag.get('tag_value') or tag.get('value', '')
                    if value:
                        prompt_parts.append(f"  - {value}")
                prompt_parts.append("")

        prompt_parts.extend([
            f"Question: {question}",
            "",
            "SQL Query:"
        ])

        return '\n'.join(prompt_parts)

    def _build_response_prompt(
        self,
        question: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for response generation."""
        # Format results for prompt
        results_text = self._format_results_for_prompt(results)

        prompt = f"""Based on the code analysis results, provide a clear and helpful answer.

Question: {question}

Analysis Results:
{results_text}

Provide a clear, structured answer that:
1. Directly addresses the question
2. References specific findings from the results
3. Provides context when helpful

Answer:"""

        return prompt

    def _format_results_for_prompt(
        self,
        results: List[Dict[str, Any]],
        max_results: int = 20
    ) -> str:
        """Format query results for inclusion in prompt."""
        if not results:
            return "No results found."

        lines = []
        for i, row in enumerate(results[:max_results], 1):
            # Format each result based on available fields
            if 'name' in row and 'filename' in row:
                line_num = row.get('line_number', '')
                lines.append(f"{i}. {row['name']} ({row['filename']}:{line_num})")
            elif 'name' in row:
                lines.append(f"{i}. {row['name']}")
            else:
                # Generic formatting
                items = [f"{k}: {v}" for k, v in list(row.items())[:3]]
                lines.append(f"{i}. {', '.join(items)}")

        if len(results) > max_results:
            lines.append(f"... and {len(results) - max_results} more results")

        return '\n'.join(lines)

    def _format_results_as_response(
        self,
        question: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format results as structured response without LLM."""
        if not results:
            response = f"No results found for: {question}"
        else:
            lines = [f"Found {len(results)} results:"]
            for i, row in enumerate(results[:10], 1):
                if 'name' in row:
                    filename = row.get('filename', 'unknown')
                    line_num = row.get('line_number', '')
                    lines.append(f"  {i}. {row['name']} ({filename}:{line_num})")
                else:
                    lines.append(f"  {i}. {row}")

            if len(results) > 10:
                lines.append(f"  ... and {len(results) - 10} more")

            response = '\n'.join(lines)

        return {
            "response": response,
            "result_count": len(results),
            "question": question,
            "method": "structured"
        }

    def _extract_query(self, response: str) -> str:
        """Extract SQL query from LLM response."""
        import re

        # Try to find SELECT ... FROM pattern
        sql_match = re.search(
            r'(SELECT\s+[\s\S]*?FROM\s+[\s\S]*?)(?:;|$)',
            response,
            re.IGNORECASE | re.MULTILINE
        )

        if sql_match:
            return sql_match.group(1).strip().rstrip(';')

        # Fallback: return as-is if it looks like SQL
        if 'SELECT' in response.upper() and 'FROM' in response.upper():
            return response.strip()

        # Default fallback
        return "SELECT name, filename FROM nodes_method LIMIT 10"
