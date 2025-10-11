# Thread Parser Module Documentation

## Overview

The `thread_parser.py` module reconstructs threaded email conversations from raw mailing list data, building parent-child relationships between messages and cleaning email content for downstream processing.

## Purpose

- Reconstruct conversation threads using email headers (Message-ID, In-Reply-To, References)
- Build hierarchical tree structures representing discussions
- Clean quoted text, signatures, and boilerplate
- Extract meaningful conversation content

## Architecture

```
┌──────────────────────────────────────────────────┐
│            Thread Parser Module                   │
├──────────────────────────────────────────────────┤
│                                                   │
│  Input:                                           │
│    - data/raw_threads.json                        │
│                                                   │
│  Process:                                         │
│    1. Parse email headers for thread info         │
│    2. Build message ID → message mapping          │
│    3. Construct parent-child relationships        │
│    4. Create thread trees                         │
│    5. Clean message content                       │
│    6. Aggregate thread conversations              │
│                                                   │
│  Output:                                          │
│    - data/processed_threads.json                  │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. ThreadParser Class

Main class for thread reconstruction.

```python
class ThreadParser:
    def __init__(self, raw_emails: List[Dict]):
        """
        Initialize parser with raw email data.

        Args:
            raw_emails: List of email dictionaries from scraper
        """
        self.emails = raw_emails
        self.message_map = {}  # message_id -> email
        self.threads = {}      # root_id -> thread tree

    def parse_threads(self) -> Dict[str, List[Dict]]:
        """
        Parse all threads.

        Returns:
            Dictionary mapping thread_id to list of messages
        """

    def save_to_json(self, output_path: str):
        """Save processed threads to JSON file."""
```

### 2. Core Functions

#### `build_message_map(emails: List[Dict]) -> Dict[str, Dict]`

Creates index mapping message IDs to email objects.

**Purpose:**
- Fast lookup of messages by ID
- Resolve In-Reply-To and References headers

**Example:**
```python
message_map = build_message_map(emails)
parent = message_map.get(email['in_reply_to'])
```

#### `extract_thread_root(email: Dict) -> str`

Identifies the root message of a thread.

**Logic:**
1. If email has no `in_reply_to` → it's a root
2. If `in_reply_to` exists → traverse up to find root
3. If `references` exists → first reference is root
4. Fallback: use subject line similarity

**Returns:** Message ID of thread root

**Example:**
```python
root_id = extract_thread_root(email)
# Returns: "<20230415103045.GA12345@server.com>"
```

#### `build_thread_tree(root_id: str, message_map: Dict) -> Dict`

Constructs hierarchical thread structure.

**Structure:**
```python
{
    "thread_id": "<root-message-id>",
    "root_message": {...},
    "subject": "Original subject line",
    "start_date": "2023-04-15T10:30:00Z",
    "end_date": "2023-04-22T16:45:00Z",
    "message_count": 18,
    "participants": ["john@pg.org", "jane@pg.org", ...],
    "messages": [
        {
            "message_id": "<...>",
            "depth": 0,  # Thread depth
            "parent_id": null,
            "children": ["<child-1-id>", "<child-2-id>"],
            "from": "...",
            "date": "...",
            "subject": "...",
            "body": "...",
            "cleaned_body": "..."  # After cleaning
        },
        {
            "message_id": "<child-1-id>",
            "depth": 1,
            "parent_id": "<root-id>",
            "children": [],
            ...
        }
    ]
}
```

**Algorithm:**
1. Start with root message
2. Find all messages with `in_reply_to` = root_id
3. Recursively process children
4. Build depth-first tree structure

#### `clean_email_body(body: str) -> str`

Removes noise from email content.

**Cleaning Steps:**

1. **Remove Quoted Text**
   ```python
   # Remove lines starting with '>'
   lines = [l for l in body.split('\n') if not l.strip().startswith('>')]
   ```

2. **Remove Attribution Lines**
   ```python
   # Remove "On ... wrote:" patterns
   body = re.sub(r'On .+ wrote:', '', body)
   ```

3. **Remove Email Signatures**
   ```python
   # Remove everything after '--'
   if '--' in body:
       body = body.split('--')[0]
   ```

4. **Remove URLs (optional)**
   ```python
   # Remove or preserve URLs based on config
   body = re.sub(r'https?://\S+', '', body)
   ```

5. **Normalize Whitespace**
   ```python
   # Remove extra blank lines
   body = re.sub(r'\n\s*\n', '\n\n', body)
   body = body.strip()
   ```

**Example:**
```python
raw = """
On 2023-04-15 John wrote:
> I think we should optimize the planner.

Good point! I agree we should focus on partition pruning.

--
Jane Expert
PostgreSQL Developer
"""

cleaned = clean_email_body(raw)
# Returns: "Good point! I agree we should focus on partition pruning."
```

#### `aggregate_thread_content(thread: Dict) -> str`

Combines all messages in a thread into single text.

**Format:**
```
[Root Message]
From: John Developer
Date: 2023-04-15

Original message content...

---

[Reply 1]
From: Jane Expert
Date: 2023-04-15

Reply content...

---

[Reply 2]
...
```

**Purpose:**
- Create single document representing entire discussion
- Useful for embedding and clustering
- Preserves chronological order

## Data Flow

```
Raw Emails → Message Map → Thread Trees → Cleaned Content → Aggregated Threads
     ↓            ↓             ↓               ↓                 ↓
(scraped)   (ID lookup)   (hierarchy)      (denoised)    processed_threads.json
```

## Output Format

### processed_threads.json

```json
{
  "threads": [
    {
      "thread_id": "20230415-planner-optimization",
      "root_message_id": "<20230415103045.GA12345@server.com>",
      "subject": "Query planner optimization for partitioned tables",
      "start_date": "2023-04-15T10:30:45Z",
      "end_date": "2023-04-22T16:30:00Z",
      "message_count": 18,
      "participants": [
        "john@postgresql.org",
        "jane@postgresql.org",
        "bob@enterprise.com"
      ],
      "messages": [
        {
          "message_id": "<20230415103045.GA12345@server.com>",
          "depth": 0,
          "parent_id": null,
          "children": [
            "<20230415143022.GB67890@server.com>",
            "<20230416091234.GC11111@server.com>"
          ],
          "from": "John Developer <john@postgresql.org>",
          "date": "2023-04-15T10:30:45Z",
          "subject": "Query planner optimization for partitioned tables",
          "body": "Original body with quoted text and signature...",
          "cleaned_body": "I've been investigating partition pruning..."
        },
        {
          "message_id": "<20230415143022.GB67890@server.com>",
          "depth": 1,
          "parent_id": "<20230415103045.GA12345@server.com>",
          "children": ["<20230416100000.GD22222@server.com>"],
          "from": "Jane Expert <jane@postgresql.org>",
          "date": "2023-04-15T14:30:22Z",
          "subject": "Re: Query planner optimization for partitioned tables",
          "body": "...",
          "cleaned_body": "Good point. We should also consider runtime pruning..."
        }
      ],
      "aggregated_content": "Full chronological conversation text...",
      "topics": [],  # To be filled by topic_clustering.py
      "source_files": []  # To be filled by pg_source_context.py
    }
  ],
  "metadata": {
    "total_threads": 234,
    "total_messages": 1523,
    "date_range": "2022-01-01 to 2025-10-02",
    "average_messages_per_thread": 6.5
  }
}
```

## Configuration

Key settings in `config.py`:

```python
# Thread parsing configuration
MIN_THREAD_SIZE = 2  # Minimum messages to form a thread
MAX_THREAD_DEPTH = 20  # Prevent infinite recursion
CLEAN_QUOTED_TEXT = True
REMOVE_SIGNATURES = True
PRESERVE_URLS = False
NORMALIZE_SUBJECTS = True  # "Re: Re: Subject" → "Subject"
```

## Advanced Features

### 1. Orphan Message Handling

Handle messages with missing parent references.

```python
def handle_orphans(message_map: Dict, threads: Dict) -> List[Dict]:
    """
    Find messages with in_reply_to that doesn't exist.
    Group orphans by subject similarity.
    """
    orphans = []
    for msg_id, msg in message_map.items():
        if msg['in_reply_to'] and msg['in_reply_to'] not in message_map:
            orphans.append(msg)

    # Group by normalized subject
    orphan_threads = defaultdict(list)
    for orphan in orphans:
        normalized = normalize_subject(orphan['subject'])
        orphan_threads[normalized].append(orphan)

    return orphan_threads
```

### 2. Subject Normalization

Standardize subject lines for better matching.

```python
def normalize_subject(subject: str) -> str:
    """
    Remove Re:, Fwd:, [HACKERS], etc.

    Examples:
        "Re: [HACKERS] Planner bug" → "Planner bug"
        "Fwd: Re: Query issue" → "Query issue"
    """
    subject = re.sub(r'^(Re:|Fwd:|RE:|FW:)\s*', '', subject, flags=re.IGNORECASE)
    subject = re.sub(r'\[HACKERS\]\s*', '', subject, flags=re.IGNORECASE)
    subject = re.sub(r'\s+', ' ', subject).strip()
    return subject
```

### 3. Thread Merging

Merge related threads that discuss same topic.

```python
def merge_related_threads(threads: Dict, similarity_threshold: float = 0.8) -> Dict:
    """
    Merge threads with highly similar subjects.

    Args:
        threads: Dictionary of thread trees
        similarity_threshold: Minimum similarity to merge (0-1)

    Returns:
        Merged threads
    """
    from difflib import SequenceMatcher

    thread_list = list(threads.values())
    merged = []

    while thread_list:
        current = thread_list.pop(0)
        to_merge = []

        for i, other in enumerate(thread_list):
            similarity = SequenceMatcher(
                None,
                normalize_subject(current['subject']),
                normalize_subject(other['subject'])
            ).ratio()

            if similarity >= similarity_threshold:
                to_merge.append(i)

        # Merge threads
        for idx in reversed(to_merge):
            other = thread_list.pop(idx)
            current['messages'].extend(other['messages'])
            current['message_count'] += other['message_count']

        merged.append(current)

    return {t['thread_id']: t for t in merged}
```

## Usage Examples

### Basic Usage

```python
from thread_parser import ThreadParser
import json

# Load raw emails
with open('data/raw_threads.json', 'r') as f:
    raw_emails = json.load(f)

# Parse threads
parser = ThreadParser(raw_emails)
threads = parser.parse_threads()

# Save processed threads
parser.save_to_json('data/processed_threads.json')

print(f"Processed {len(threads)} threads")
```

### Advanced Usage with Statistics

```python
from thread_parser import ThreadParser
import json

# Load and parse
with open('data/raw_threads.json', 'r') as f:
    raw_emails = json.load(f)

parser = ThreadParser(raw_emails)
threads = parser.parse_threads()

# Analyze thread statistics
stats = {
    'total_threads': len(threads),
    'total_messages': sum(t['message_count'] for t in threads.values()),
    'avg_messages_per_thread': sum(t['message_count'] for t in threads.values()) / len(threads),
    'max_depth': max(max(m['depth'] for m in t['messages']) for t in threads.values()),
    'unique_participants': len(set(p for t in threads.values() for p in t['participants']))
}

print(json.dumps(stats, indent=2))

# Find longest threads
longest = sorted(threads.values(), key=lambda t: t['message_count'], reverse=True)[:10]
for thread in longest:
    print(f"{thread['subject']}: {thread['message_count']} messages")
```

### Custom Cleaning

```python
from thread_parser import ThreadParser, clean_email_body

# Custom cleaning function
def custom_cleaner(body: str) -> str:
    # First apply default cleaning
    body = clean_email_body(body)

    # Additional custom steps
    # Remove patch diffs
    if '--- a/' in body or '+++ b/' in body:
        lines = body.split('\n')
        body = '\n'.join(l for l in lines if not l.startswith(('---', '+++', '@@', '-', '+')))

    # Remove SQL query dumps
    body = re.sub(r'EXPLAIN.*?;', '[QUERY]', body, flags=re.DOTALL)

    return body

# Use custom cleaner
parser = ThreadParser(raw_emails)
parser.cleaner = custom_cleaner
threads = parser.parse_threads()
```

## Performance Considerations

### Estimated Metrics

- **Input size:** 1,000-5,000 emails
- **Processing time:** 30 seconds - 2 minutes
- **Output size:** ~30-150 MB
- **Thread count:** 200-500 threads (assuming avg 5-10 messages per thread)

### Optimization Strategies

1. **Message Map Caching**
   - Build message map once
   - Use for all thread reconstructions

2. **Parallel Processing**
   - Process independent threads in parallel
   - Use multiprocessing for large datasets

3. **Incremental Updates**
   - Only re-parse new messages
   - Maintain thread state across runs

## Dependencies

```
python-dateutil>=2.8.0
regex>=2023.0.0
```

## Testing

### Unit Tests

```python
import unittest
from thread_parser import normalize_subject, clean_email_body

class TestThreadParser(unittest.TestCase):
    def test_normalize_subject(self):
        self.assertEqual(
            normalize_subject("Re: [HACKERS] Planner bug"),
            "Planner bug"
        )

    def test_clean_email_body(self):
        raw = "On 2023 wrote:\n> quoted\n\nActual content\n--\nSignature"
        cleaned = clean_email_body(raw)
        self.assertEqual(cleaned, "Actual content")

    def test_thread_tree_depth(self):
        # Test max depth enforcement
        pass
```

## Troubleshooting

### Broken Thread Chains

**Issue:** Some messages not linked properly

**Solutions:**
- Check `in_reply_to` and `references` headers
- Use subject-based fallback matching
- Manually inspect orphaned messages

### Excessive Quoted Text

**Issue:** Cleaned body still contains quotes

**Solutions:**
- Improve regex patterns
- Add more quote markers (">", "|", etc.)
- Use ML-based quote detection

### Memory Issues with Large Threads

**Issue:** Very large threads cause memory problems

**Solutions:**
- Process threads in batches
- Stream messages instead of loading all
- Limit thread depth

## Next Steps

After thread parsing completes:
1. Verify thread structure in `data/processed_threads.json`
2. Check aggregated content quality
3. Proceed to `topic_clustering.py` for discussion grouping
