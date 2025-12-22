"""Scala Output Parser for Joern CPGQL Results.

Parses Joern's Scala-formatted query output into Python objects.
Handles List, Map, tuples, and primitive values.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


def parse_scala_output(output: str) -> List[Any]:
    """
    Parse Joern Scala output into Python list of objects.

    Handles formats like:
    - List(item1, item2, ...)
    - List((a, b), (c, d), ...)
    - List(Map("key" -> "value", ...), ...)
    - Vector(...)
    - Seq(...)

    Args:
        output: Raw Scala output string from Joern

    Returns:
        List of parsed Python objects (dicts, tuples, primitives)
    """
    if not output or not isinstance(output, str):
        return []

    output = output.strip()

    # Handle empty collections
    if output in ('List()', 'Vector()', 'Seq()', 'Array()', '()'):
        return []

    # Handle val = result pattern
    if output.startswith('val ') or output.startswith('res'):
        # Extract the value part after '='
        eq_pos = output.find('=')
        if eq_pos != -1:
            output = output[eq_pos + 1:].strip()

    # Try to parse as collection
    try:
        result = _parse_value(output)
        if isinstance(result, list):
            return result
        elif result is not None:
            return [result]
        return []
    except Exception as e:
        logger.debug(f"Failed to parse Scala output: {e}")
        # Fallback: try line-by-line parsing
        return _parse_line_by_line(output)


def _parse_value(text: str) -> Any:
    """
    Parse a single Scala value.

    Args:
        text: Scala value string

    Returns:
        Parsed Python value
    """
    text = text.strip()

    if not text:
        return None

    # Handle None/null
    if text in ('None', 'null', 'Nothing'):
        return None

    # Handle boolean
    if text == 'true':
        return True
    if text == 'false':
        return False

    # Handle numbers
    if re.match(r'^-?\d+L?$', text):
        return int(text.rstrip('L'))
    if re.match(r'^-?\d+\.\d+[fFdD]?$', text):
        return float(text.rstrip('fFdD'))

    # Handle Some(x)
    if text.startswith('Some(') and text.endswith(')'):
        inner = text[5:-1]
        return _parse_value(inner)

    # Handle strings
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        return text[1:-1]

    # Handle List/Vector/Seq/Array
    for prefix in ('List(', 'Vector(', 'Seq(', 'Array(', 'ArrayBuffer('):
        if text.startswith(prefix) and text.endswith(')'):
            inner = text[len(prefix):-1]
            return _parse_collection(inner)

    # Handle Map
    if text.startswith('Map(') and text.endswith(')'):
        inner = text[4:-1]
        return _parse_map(inner)

    # Handle tuple
    if text.startswith('(') and text.endswith(')'):
        inner = text[1:-1]
        return _parse_tuple(inner)

    # Return as string if nothing else matches
    return text


def _parse_collection(inner: str) -> List[Any]:
    """Parse collection contents."""
    if not inner.strip():
        return []

    items = _split_top_level(inner, ',')
    return [_parse_value(item) for item in items if item.strip()]


def _parse_tuple(inner: str) -> tuple:
    """Parse tuple contents."""
    if not inner.strip():
        return ()

    items = _split_top_level(inner, ',')
    return tuple(_parse_value(item) for item in items if item.strip())


def _parse_map(inner: str) -> Dict[str, Any]:
    """Parse Map contents."""
    if not inner.strip():
        return {}

    result = {}
    pairs = _split_top_level(inner, ',')

    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue

        # Handle "key" -> value
        if ' -> ' in pair:
            key, value = pair.split(' -> ', 1)
            key = _parse_value(key.strip())
            value = _parse_value(value.strip())
            if isinstance(key, str):
                result[key] = value
        # Handle key -> value (without quotes)
        elif '->' in pair:
            key, value = pair.split('->', 1)
            key = _parse_value(key.strip())
            value = _parse_value(value.strip())
            if isinstance(key, str):
                result[key] = value

    return result


def _split_top_level(text: str, delimiter: str) -> List[str]:
    """
    Split text by delimiter, respecting parentheses and quotes.

    Args:
        text: String to split
        delimiter: Delimiter character

    Returns:
        List of split parts
    """
    parts = []
    current = []
    depth = 0
    in_string = False
    string_char = None
    i = 0

    while i < len(text):
        char = text[i]

        # Handle string quotes
        if char in ('"', "'") and (i == 0 or text[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None

        if not in_string:
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
            elif char == delimiter and depth == 0:
                parts.append(''.join(current).strip())
                current = []
                i += 1
                continue

        current.append(char)
        i += 1

    if current:
        parts.append(''.join(current).strip())

    return parts


def _parse_line_by_line(output: str) -> List[Any]:
    """
    Fallback parser: split by lines and parse each.

    Args:
        output: Multi-line output

    Returns:
        List of parsed values
    """
    result = []
    lines = output.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('#'):
            continue

        # Skip Scala REPL artifacts
        if line.startswith('scala>') or line.startswith('res'):
            continue

        parsed = _parse_value(line)
        if parsed is not None:
            if isinstance(parsed, list):
                result.extend(parsed)
            else:
                result.append(parsed)

    return result


def parse_json_like(output: str) -> List[Dict[str, Any]]:
    """
    Parse JSON-like output from Joern.

    Handles output like:
    {"id": 1, "name": "foo"}
    {"id": 2, "name": "bar"}

    Args:
        output: JSON-like output string

    Returns:
        List of dictionaries
    """
    import json

    result = []
    lines = output.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                result.append(obj)
            elif isinstance(obj, list):
                result.extend(obj)
        except json.JSONDecodeError:
            # Not JSON, try Scala parser
            parsed = _parse_value(line)
            if isinstance(parsed, dict):
                result.append(parsed)

    return result
