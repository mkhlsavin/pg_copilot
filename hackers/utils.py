"""
Utility functions shared across modules
"""
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Any


def setup_logging(log_file: str = None, log_level: str = "INFO"):
    """
    Setup logging configuration.

    Args:
        log_file: Path to log file (optional)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


def ensure_dir(directory: str):
    """
    Create directory if it doesn't exist.

    Args:
        directory: Directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")


def load_json(file_path: str) -> Any:
    """
    Load JSON from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON object
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, file_path: str, indent: int = 2):
    """
    Save data to JSON file.

    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation (default: 2)
    """
    ensure_dir(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    logging.info(f"Saved JSON to: {file_path}")


def load_jsonl(file_path: str) -> List[Dict]:
    """
    Load JSONL (JSON Lines) file.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of JSON objects
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                obj = json.loads(line.strip())
                data.append(obj)
            except json.JSONDecodeError as e:
                logging.warning(f"Error parsing line {line_num} in {file_path}: {e}")
                continue

    return data


def save_jsonl(data: List[Dict], file_path: str):
    """
    Save data to JSONL (JSON Lines) file.

    Args:
        data: List of dictionaries
        file_path: Output file path
    """
    ensure_dir(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        for obj in data:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')

    logging.info(f"Saved {len(data)} entries to JSONL: {file_path}")


def append_jsonl(obj: Dict, file_path: str):
    """
    Append single object to JSONL file.

    Args:
        obj: Dictionary to append
        file_path: JSONL file path
    """
    ensure_dir(os.path.dirname(file_path))

    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def normalize_subject(subject: str) -> str:
    """
    Normalize email subject line.

    Removes Re:, Fwd:, [HACKERS], etc.

    Args:
        subject: Subject line

    Returns:
        Normalized subject
    """
    # Remove Re:, Fwd:, etc.
    subject = re.sub(r'^(Re:|Fwd:|RE:|FW:)\s*', '', subject, flags=re.IGNORECASE)

    # Remove [HACKERS], [pgsql-hackers], etc.
    subject = re.sub(r'\[(?:HACKERS|pgsql-hackers)\]\s*', '', subject, flags=re.IGNORECASE)

    # Normalize whitespace
    subject = re.sub(r'\s+', ' ', subject).strip()

    return subject


def clean_email_body(body: str) -> str:
    """
    Clean email body text.

    Removes quoted text, signatures, and extra whitespace.

    Args:
        body: Raw email body

    Returns:
        Cleaned body text
    """
    if not body:
        return ""

    lines = body.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip quoted lines
        if stripped.startswith('>'):
            continue

        # Skip attribution lines
        if re.match(r'On .+ wrote:', line):
            continue

        # Stop at signature
        if stripped == '--':
            break

        cleaned_lines.append(line)

    # Join and normalize whitespace
    cleaned = '\n'.join(cleaned_lines)
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)  # Max 2 newlines
    cleaned = cleaned.strip()

    return cleaned


def extract_email_address(from_field: str) -> str:
    """
    Extract email address from From field.

    Args:
        from_field: Email From field (e.g., "John Doe <john@example.com>")

    Returns:
        Email address
    """
    match = re.search(r'<(.+?)>', from_field)
    if match:
        return match.group(1)

    # Fallback: assume entire field is email
    return from_field.strip()


def estimate_tokens(text: str) -> int:
    """
    Rough token estimate (1 token ≈ 4 characters for English).

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return len(text) // 4


def truncate_text(text: str, max_length: int, suffix: str = "... [truncated]") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Input text
        max_length: Maximum length
        suffix: Truncation suffix

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO timestamp string
    """
    return datetime.now().isoformat()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def extract_component_from_path(file_path: str) -> str:
    """
    Extract PostgreSQL component name from file path.

    Args:
        file_path: File path (e.g., "src/backend/optimizer/plan/planner.c")

    Returns:
        Component name (e.g., "optimizer")
    """
    parts = file_path.replace('\\', '/').split('/')

    # src/backend/<component>/...
    if 'backend' in parts:
        idx = parts.index('backend')
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # src/include/<component>/...
    if 'include' in parts:
        idx = parts.index('include')
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return 'unknown'


def extract_keywords_from_path(file_path: str) -> List[str]:
    """
    Extract keywords from file path.

    Args:
        file_path: File path

    Returns:
        List of keywords
    """
    keywords = []

    # Get path components
    parts = file_path.replace('\\', '/').split('/')
    for part in parts:
        # Skip common directories
        if part in ['src', 'backend', 'include', 'frontend']:
            continue

        # Add directory names
        keywords.append(part)

    # Add filename without extension
    filename = os.path.basename(file_path)
    name_without_ext = os.path.splitext(filename)[0]
    keywords.append(name_without_ext)

    return keywords


def validate_json_structure(obj: Dict, required_fields: List[str]) -> List[str]:
    """
    Validate JSON object has required fields.

    Args:
        obj: JSON object to validate
        required_fields: List of required field names

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for field in required_fields:
        if field not in obj:
            errors.append(f"Missing required field: {field}")
        elif obj[field] is None or obj[field] == "":
            errors.append(f"Empty required field: {field}")

    return errors


def safe_filename(filename: str) -> str:
    """
    Convert string to safe filename.

    Args:
        filename: Input filename

    Returns:
        Safe filename
    """
    # Remove or replace invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe = re.sub(r'_+', '_', safe)  # Collapse multiple underscores
    safe = safe.strip('_')

    return safe


class ProgressTracker:
    """Simple progress tracker for long-running operations."""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()

    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
        percentage = (self.current / self.total) * 100

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta = format_duration(remaining)
        else:
            eta = "unknown"

        logging.info(f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%) - ETA: {eta}")

    def finish(self):
        """Mark as complete."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logging.info(f"{self.description}: Complete in {format_duration(elapsed)}")


def retry_on_error(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
    """
    Retry function on error.

    Args:
        func: Function to call
        max_retries: Maximum retry attempts
        delay: Delay between retries (seconds)
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    import time

    last_error = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logging.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")

            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff

    raise last_error
