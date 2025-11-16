"""Parser for Scala CPGQL output to Python dict/list objects."""
import re
import json
import logging
from typing import Union, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_scala_output(output: str) -> Union[Dict, List, None]:
    """
    Parse Joern Scala output to Python dict/list.

    Handles formats:
    - Map("key" -> "value", ...)
    - List(Map(...), Map(...), ...)
    - Option[Map] = Some(Map(...))
    - Option[Map] = None

    Args:
        output: Raw Scala output string from Joern

    Returns:
        Parsed Python dict, list, or None
    """
    if not output or not isinstance(output, str):
        return None

    # Remove ANSI color codes
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)

    # Check for None/empty result
    if 'None' in output or 'List()' in output or not output.strip():
        logger.debug("Scala output is None or empty")
        return None

    try:
        # Case 1: Option[Map] = Some(Map(...))
        if 'Option' in output and 'Some' in output:
            # Extract the Map from Some(...)
            some_match = re.search(r'Some\s*\((.*)\)', output, re.DOTALL)
            if some_match:
                map_content = some_match.group(1)
                return _parse_map(map_content)

        # Case 2: Direct Map(...)
        if output.strip().startswith('Map('):
            return _parse_map(output)

        # Case 3: List[Map]
        if 'List(' in output and 'Map(' in output:
            return _parse_list_of_maps(output)

        # Case 4: Try to find any Map(...) structure
        map_matches = re.finditer(r'Map\s*\(([^)]+(?:\([^)]*\)[^)]*)*)\)', output, re.DOTALL)
        results = []
        for match in map_matches:
            parsed = _parse_map(match.group(0))
            if parsed:
                results.append(parsed)

        if results:
            return results if len(results) > 1 else results[0]

        logger.warning(f"Could not parse Scala output: {output[:200]}")
        return None

    except Exception as e:
        logger.error(f"Error parsing Scala output: {e}", exc_info=True)
        return None


def _parse_map(map_str: str) -> Optional[Dict]:
    """
    Parse a Scala Map(...) string to Python dict.

    Example:
        Map("method" -> "foo", "file" -> "bar.c", "line" -> 123)
    """
    # Extract content between Map( and )
    content_match = re.search(r'Map\s*\((.*)\)', map_str, re.DOTALL)
    if not content_match:
        return None

    content = content_match.group(1)

    # Parse key-value pairs
    result = {}

    # Split by comma, but be careful of nested structures
    pairs = _split_by_comma(content)

    for pair in pairs:
        # Parse "key" -> value
        kv_match = re.match(r'\s*"([^"]+)"\s*->\s*(.+)', pair.strip(), re.DOTALL)
        if kv_match:
            key = kv_match.group(1)
            value_str = kv_match.group(2).strip()

            # Parse value
            value = _parse_value(value_str)
            result[key] = value

    return result if result else None


def _parse_list_of_maps(list_str: str) -> List[Dict]:
    """Parse a Scala List(Map(...), Map(...), ...) to Python list of dicts."""
    maps = []

    i = 0
    while i < len(list_str):
        # Look for Map( at current position
        if list_str[i:i+4] == 'Map(':
            # Found start of a Map, now find the matching closing )
            start = i
            i += 4  # Skip past "Map("
            depth = 1

            # Find the matching closing parenthesis
            while i < len(list_str) and depth > 0:
                if list_str[i] == '(':
                    depth += 1
                elif list_str[i] == ')':
                    depth -= 1
                i += 1

            # Extract the Map string (including "Map(" and ")")
            map_str = list_str[start:i]
            parsed = _parse_map(map_str)
            if parsed:
                maps.append(parsed)
        else:
            i += 1

    return maps


def _split_by_comma(text: str) -> List[str]:
    """Split by comma, respecting nested parentheses and quotes."""
    parts = []
    current = []
    depth = 0
    in_quotes = False

    for char in text:
        if char == '"' and (not current or current[-1] != '\\'):
            in_quotes = not in_quotes

        if not in_quotes:
            if char in '([':
                depth += 1
            elif char in ')]':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(''.join(current).strip())
                current = []
                continue

        current.append(char)

    if current:
        parts.append(''.join(current).strip())

    return parts


def _parse_value(value_str: str) -> Union[str, int, float, List, None]:
    """Parse a Scala value to Python type."""
    value_str = value_str.strip()

    # Check for None
    if value_str in ('None', 'null'):
        return None

    # Check for List
    if value_str.startswith('List('):
        return _parse_list(value_str)

    # Check for string
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]

    # Check for number
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # Return as string
    return value_str


def _parse_list(list_str: str) -> List:
    """Parse a Scala List(...) to Python list."""
    # Extract content between List( and )
    content_match = re.search(r'List\s*\((.*)\)', list_str, re.DOTALL)
    if not content_match:
        return []

    content = content_match.group(1)

    # Split by comma
    items = _split_by_comma(content)

    # Parse each item
    result = []
    for item in items:
        value = _parse_value(item)
        if value is not None:
            result.append(value)

    return result
