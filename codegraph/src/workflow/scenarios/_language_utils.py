"""
Language utilities for scenario workflows.

Provides helper functions to add language instructions to LLM prompts
based on the language setting in the workflow state context.
"""

from typing import Dict, Any, Optional


def get_language_instruction(state: Dict[str, Any]) -> str:
    """
    Get language instruction based on state context.

    Args:
        state: Workflow state containing context with language setting

    Returns:
        Language instruction string to append to system prompt
    """
    language = 'en'
    if state.get('context') and isinstance(state.get('context'), dict):
        language = state['context'].get('language', 'en')

    if language == 'ru':
        return "\n\n**ВАЖНО: Отвечай ТОЛЬКО на русском языке. Весь ответ должен быть полностью на русском.**"
    elif language != 'en':
        return f"\n\n**IMPORTANT: Respond ONLY in {language} language.**"

    return ""


def add_language_instruction(system_prompt: str, state: Dict[str, Any]) -> str:
    """
    Add language instruction to system prompt based on state context.

    Args:
        system_prompt: Original system prompt
        state: Workflow state containing context with language setting

    Returns:
        System prompt with language instruction appended
    """
    instruction = get_language_instruction(state)
    return system_prompt + instruction if instruction else system_prompt
