"""Logic Explanation Synthesizer (Phase 7D)

Synthesizes natural language explanations from call chain analysis.
"""
import logging
from typing import Dict, Optional
from src.generation.prompts_logic_explanation import (
    LOGIC_EXPLANATION_SYSTEM_PROMPT,
    LOGIC_EXPLANATION_USER_PROMPT,
    format_call_chain_for_prompt
)

logger = logging.getLogger(__name__)


class LogicSynthesizer:
    """
    Synthesizes natural language explanations of code mechanisms from call chain analysis.

    Takes structured call chain data and generates human-readable explanations
    covering:
    - Mechanism overview
    - Control flow (step-by-step)
    - Key function purposes
    - Consistency guarantees
    - Error handling
    """

    def __init__(self, llm=None):
        """
        Initialize Logic Synthesizer.

        Args:
            llm: LLM instance for generating explanations
        """
        self.llm = llm

    def synthesize(
        self,
        question: str,
        call_chain_analysis: Dict,
        max_tokens: int = 1000
    ) -> Dict:
        """
        Synthesize logic explanation from call chain analysis.

        Args:
            question: Original question
            call_chain_analysis: Result from CallChainAnalyzer.analyze()
            max_tokens: Maximum tokens for LLM response

        Returns:
            Dictionary with:
            - explanation: Natural language explanation
            - metadata: Generation metadata
        """
        logger.info("Synthesizing logic explanation from call chain")

        # Check if we have sufficient analysis data
        if not self._validate_analysis(call_chain_analysis):
            logger.warning("Insufficient call chain data for synthesis")
            return self._empty_result("Insufficient call chain data")

        # Format call chain for prompt
        formatted = format_call_chain_for_prompt(call_chain_analysis)

        # Build prompt
        system_prompt = LOGIC_EXPLANATION_SYSTEM_PROMPT
        user_prompt = LOGIC_EXPLANATION_USER_PROMPT.format(
            question=question,
            entry_point=formatted['entry_point'],
            call_graph=formatted['call_graph'],
            call_chains=formatted['call_chains'],
            key_functions=formatted['key_functions']
        )

        # Generate explanation
        if self.llm is None:
            # Fallback: template-based explanation
            logger.info("No LLM available, using template-based explanation")
            explanation = self._generate_template_explanation(
                question,
                call_chain_analysis,
                formatted
            )
        else:
            # LLM-based explanation
            logger.info("Generating explanation with LLM")
            explanation = self._generate_llm_explanation(
                system_prompt,
                user_prompt,
                max_tokens
            )

        result = {
            'explanation': explanation,
            'metadata': {
                'entry_point': call_chain_analysis.get('entry_point'),
                'key_function_count': len(call_chain_analysis.get('key_functions', [])),
                'call_chain_count': len(call_chain_analysis.get('call_chains', [])),
                'generation_method': 'llm' if self.llm else 'template',
                'explanation_length': len(explanation)
            }
        }

        logger.info(f"Logic explanation generated: {len(explanation)} chars, "
                   f"method={'llm' if self.llm else 'template'}")

        return result

    def _validate_analysis(self, analysis: Dict) -> bool:
        """
        Validate that call chain analysis has sufficient data.

        Args:
            analysis: Call chain analysis result

        Returns:
            True if analysis is sufficient for explanation
        """
        # Must have entry point
        if not analysis.get('entry_point'):
            return False

        # Must have at least some call graph edges
        call_graph = analysis.get('call_graph', {})
        total_edges = sum(len(callees) for callees in call_graph.values())
        if total_edges == 0:
            return False

        # Must have at least one key function
        if len(analysis.get('key_functions', [])) == 0:
            return False

        return True

    def _generate_template_explanation(
        self,
        question: str,
        analysis: Dict,
        formatted: Dict
    ) -> str:
        """
        Generate template-based explanation without LLM.

        Args:
            question: Original question
            analysis: Raw call chain analysis
            formatted: Formatted analysis for prompt

        Returns:
            Template-based explanation string
        """
        lines = []

        # Extract data
        entry_point = analysis.get('entry_point', 'Unknown')
        key_functions = analysis.get('key_functions', [])
        call_chains = analysis.get('call_chains', [])
        call_graph = analysis.get('call_graph', {})

        # Mechanism Overview
        lines.append("## Mechanism Overview")
        lines.append("")

        mechanism_keywords = self._extract_mechanism_keywords(question)
        if mechanism_keywords:
            lines.append(
                f"The {' '.join(mechanism_keywords)} mechanism is implemented through "
                f"a call chain starting from {entry_point}, coordinating {len(key_functions)} "
                f"key functions across the codebase."
            )
        else:
            lines.append(
                f"The mechanism is implemented through a call chain starting from "
                f"{entry_point}, coordinating {len(key_functions)} key functions."
            )
        lines.append("")

        # Control Flow
        lines.append("## Control Flow")
        lines.append("")

        # Use the longest call chain as the main flow
        if call_chains:
            main_chain = max(call_chains, key=lambda c: c['length'])
            path = main_chain['path']

            for i, method in enumerate(path, 1):
                callees = call_graph.get(method, [])

                lines.append(f"{i}. **{method}**")

                # Infer purpose from method name
                purpose = self._infer_method_purpose(method)
                if purpose:
                    lines.append(f"   - {purpose}")

                if callees:
                    callees_str = ', '.join(callees[:3])
                    if len(callees) > 3:
                        callees_str += f", and {len(callees) - 3} more"
                    lines.append(f"   - Calls: {callees_str}")

                lines.append("")
        else:
            lines.append(f"1. **{entry_point}**: Entry point method")
            lines.append("")

        # Key Functions
        lines.append("## Key Functions")
        lines.append("")

        for i, kf in enumerate(key_functions[:5], 1):
            method_name = kf['method']
            file_loc = f"{kf.get('file', 'unknown')}:{kf.get('line', 0)}"

            lines.append(f"### {method_name}")

            # Infer purpose
            purpose = self._infer_method_purpose(method_name)
            if purpose:
                lines.append(f"- **Purpose**: {purpose}")

            # Role in mechanism
            role = self._infer_method_role(method_name, key_functions[0]['method'])
            lines.append(f"- **Role**: {role}")

            lines.append(f"- **Location**: {file_loc}")
            lines.append("")

        # Consistency Guarantees (if applicable)
        if any(keyword in question.lower() for keyword in ['consistency', 'ensure', 'guarantee', 'atomicity']):
            lines.append("## Consistency Guarantees")
            lines.append("")

            # Look for transaction/locking related functions
            transaction_funcs = [
                kf['method'] for kf in key_functions
                if any(term in kf['method'].lower() for term in ['transaction', 'commit', 'abort', 'lock'])
            ]

            if transaction_funcs:
                lines.append("The mechanism ensures consistency through:")
                lines.append(f"1. Transaction management via {', '.join(transaction_funcs[:3])}")
                lines.append("2. Proper sequencing of operations in the call chain")
                lines.append("3. Cleanup and rollback on errors")
            else:
                lines.append("Consistency is maintained through the ordered execution of the call chain.")
            lines.append("")

        return '\n'.join(lines)

    def _generate_llm_explanation(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ) -> str:
        """
        Generate explanation using LLM.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt with call chain data
            max_tokens: Maximum tokens

        Returns:
            LLM-generated explanation
        """
        try:
            response = self.llm.invoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3  # Lower temperature for technical explanations
            )

            # Extract text from response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict):
                return response.get('content', str(response))
            else:
                return str(response)

        except Exception as e:
            logger.error(f"LLM explanation generation failed: {e}")
            # Fall back to template
            logger.info("Falling back to template-based explanation")
            return self._generate_template_explanation(
                user_prompt.split("Question: ")[1].split("\n")[0],
                {},
                {}
            )

    def _extract_mechanism_keywords(self, question: str) -> list:
        """Extract mechanism-related keywords from question."""
        mechanism_terms = ['shutdown', 'startup', 'checkpoint', 'replication',
                          'vacuum', 'recovery', 'transaction', 'locking']

        question_lower = question.lower()
        found = [term for term in mechanism_terms if term in question_lower]
        return found[:2]  # Return top 2

    def _infer_method_purpose(self, method_name: str) -> str:
        """Infer method purpose from name using common PostgreSQL patterns."""
        name_lower = method_name.lower()

        # Common patterns
        if 'shutdown' in name_lower or 'cleanup' in name_lower:
            return "Coordinates cleanup and shutdown operations"
        elif 'abort' in name_lower:
            return "Aborts current operation or transaction"
        elif 'commit' in name_lower:
            return "Commits transaction changes"
        elif 'interrupt' in name_lower or 'signal' in name_lower:
            return "Handles interrupts and signals"
        elif 'process' in name_lower:
            return "Processes events or requests"
        elif 'init' in name_lower or 'start' in name_lower:
            return "Initializes resources or starts operation"
        elif 'disconnect' in name_lower or 'release' in name_lower:
            return "Releases resources or connections"
        elif 'mark' in name_lower or 'checkpoint' in name_lower:
            return "Records progress or checkpoint state"
        elif 'worker' in name_lower or 'main' in name_lower:
            return "Main entry point for worker process"
        elif 'apply' in name_lower:
            return "Applies changes or operations"
        else:
            return "Performs specific mechanism operations"

    def _infer_method_role(self, method_name: str, top_key_function: str) -> str:
        """Infer method's role in the mechanism."""
        if method_name == top_key_function:
            return "Central coordinator of the mechanism"

        name_lower = method_name.lower()

        if 'shutdown' in name_lower or 'cleanup' in name_lower:
            return "Ensures proper cleanup and resource release"
        elif 'abort' in name_lower:
            return "Prevents partial or inconsistent state"
        elif 'checkpoint' in name_lower or 'mark' in name_lower:
            return "Maintains progress tracking for recovery"
        elif 'disconnect' in name_lower or 'release' in name_lower:
            return "Resource cleanup and release"
        else:
            return "Contributes to mechanism execution"

    def _empty_result(self, reason: str) -> Dict:
        """Return empty result with reason."""
        return {
            'explanation': f"Unable to generate explanation: {reason}",
            'metadata': {
                'entry_point': None,
                'key_function_count': 0,
                'call_chain_count': 0,
                'generation_method': 'none',
                'explanation_length': 0,
                'error': reason
            }
        }
