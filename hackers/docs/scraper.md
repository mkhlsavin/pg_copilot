# Scraper Module Documentation

## Overview

The `scraper.py` module is responsible for downloading and extracting email threads from the PostgreSQL pgsql-hackers mailing list archive (https://www.postgresql.org/list/pgsql-hackers) for the period 2022-2025.

## Purpose

- Fetch mailing list archives from the web
- Preserve thread structure through email headers (In-Reply-To, References, Message-ID)
- Handle pagination and rate limiting
- Store raw email data for downstream processing

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Scraper Module                      │
├─────────────────────────────────────────────────┤
│                                                  │
│  Input:                                          │
│    - Base URL: https://www.postgresql.org/list/... │
│    - Date range: 2022-2025                       │
│                                                  │
│  Process:                                        │
│    1. Discover archive pages (monthly/yearly)   │
│    2. Parse email list pages                     │
│    3. Extract individual message URLs           │
│    4. Download full message content              │
│    5. Extract headers and body                   │
│                                                  │
│  Output:                                         │
│    - data/raw_threads.json                       │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Key Components

### 1. MailingListScraper Class

Main class that orchestrates the scraping process.

```python
class MailingListScraper:
    def __init__(self, base_url: str, start_year: int, end_year: int):
        """
        Initialize scraper.

        Args:
            base_url: Base URL of mailing list
            start_year: Starting year (2022)
            end_year: Ending year (2025)
        """

    def scrape_all(self) -> List[Dict]:
        """
        Scrape all emails in date range.

        Returns:
            List of email dictionaries
        """

    def save_to_json(self, output_path: str):
        """Save scraped data to JSON file."""
```

### 2. Core Functions

#### `get_archive_urls(start_year: int, end_year: int) -> List[str]`

Generates list of archive page URLs to scrape.

**Logic:**
- PostgresPro archives may be organized by year/month
- Generates URLs like: `/list/pgsql-hackers/2023-01`, `/list/pgsql-hackers/2023-02`, etc.
- Returns list of all monthly archive URLs in range

**Example:**
```python
urls = get_archive_urls(2022, 2025)
# Returns:
# ['https://www.postgresql.org/list/pgsql-hackers/2022-01',
#  'https://www.postgresql.org/list/pgsql-hackers/2022-02', ...]
```

#### `fetch_page(url: str, retries: int = 3) -> Optional[str]`

Fetches HTML content with retry logic.

**Features:**
- Exponential backoff on failures
- Rate limiting (configurable delay)
- User-agent rotation to avoid blocking
- Timeout handling

**Example:**
```python
html = fetch_page('https://www.postgresql.org/list/pgsql-hackers/2023-01')
```

#### `parse_message_list(html: str) -> List[str]`

Extracts individual message URLs from archive page.

**Parsing Strategy:**
- Find all `<a>` tags linking to messages
- Extract href attributes
- Filter for actual message links (not navigation)
- Return list of full message URLs

**Example HTML Pattern:**
```html
<a href="/message-id/some-message-123">Subject: Planner optimization</a>
```

#### `parse_email_content(html: str) -> Dict`

Extracts email metadata and content from individual message page.

**Extracted Fields:**
```python
{
    "message_id": "unique-message-id",
    "subject": "Email subject line",
    "from": "Author Name <email@domain.com>",
    "date": "2023-04-15 10:30:00",
    "in_reply_to": "parent-message-id",  # For threading
    "references": ["msg-1", "msg-2"],     # Thread ancestry
    "body": "Email body text...",
    "url": "https://www.postgresql.org/message-id/..."
}
```

**HTML Parsing:**
- Use BeautifulSoup to parse message page
- Extract headers from `<div class="header">` or similar
- Clean body text (remove HTML tags, preserve formatting)
- Handle quoted text markers (">", "On ... wrote:")

## Data Flow

```
Archive List Page → Message List Pages → Individual Messages → Raw JSON
       ↓                    ↓                    ↓                 ↓
  (2022-2025)        (Message URLs)        (Full Content)    raw_threads.json
```

## Output Format

### raw_threads.json

```json
[
  {
    "message_id": "<20230415103045.GA12345@server.com>",
    "subject": "[HACKERS] Query planner optimization for partitioned tables",
    "from": "John Developer <john@postgresql.org>",
    "date": "2023-04-15T10:30:45Z",
    "in_reply_to": null,
    "references": [],
    "body": "I've been investigating...",
    "url": "https://www.postgresql.org/message-id/...",
    "scraped_at": "2025-10-02T12:00:00Z"
  },
  {
    "message_id": "<20230415143022.GB67890@server.com>",
    "subject": "Re: [HACKERS] Query planner optimization for partitioned tables",
    "from": "Jane Expert <jane@postgresql.org>",
    "date": "2023-04-15T14:30:22Z",
    "in_reply_to": "<20230415103045.GA12345@server.com>",
    "references": ["<20230415103045.GA12345@server.com>"],
    "body": "Good point. We should also consider...",
    "url": "https://www.postgresql.org/message-id/...",
    "scraped_at": "2025-10-02T12:05:00Z"
  }
]
```

## Configuration

Key settings in `config.py`:

```python
# Scraper configuration
MAILING_LIST_URL = "https://www.postgresql.org/list/pgsql-hackers"
START_YEAR = 2022
END_YEAR = 2025
RATE_LIMIT_DELAY = 1.0  # Seconds between requests
MAX_RETRIES = 3
TIMEOUT = 30  # Request timeout in seconds
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (X11; Linux x86_64)..."
]
```

## Error Handling

### Common Issues

1. **Rate Limiting (429 Too Many Requests)**
   - Increase `RATE_LIMIT_DELAY`
   - Implement exponential backoff
   - Rotate user agents

2. **Network Timeouts**
   - Retry with exponential backoff
   - Save progress periodically
   - Resume from last checkpoint

3. **HTML Structure Changes**
   - Update CSS selectors
   - Add fallback parsing strategies
   - Log unparseable pages for manual review

### Checkpointing

```python
def save_checkpoint(scraped_emails: List[Dict], checkpoint_file: str):
    """Save progress to allow resumption."""
    with open(checkpoint_file, 'w') as f:
        json.dump(scraped_emails, f, indent=2)

def load_checkpoint(checkpoint_file: str) -> List[Dict]:
    """Load previous progress."""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return []
```

## Usage Examples

### Basic Usage

```python
from scraper import MailingListScraper

# Initialize scraper
scraper = MailingListScraper(
    base_url="https://www.postgresql.org/list/pgsql-hackers",
    start_year=2022,
    end_year=2025
)

# Scrape all emails
emails = scraper.scrape_all()

# Save to file
scraper.save_to_json("data/raw_threads.json")

print(f"Scraped {len(emails)} emails")
```

### Advanced Usage with Progress Tracking

```python
from scraper import MailingListScraper
from tqdm import tqdm

scraper = MailingListScraper(
    base_url="https://www.postgresql.org/list/pgsql-hackers",
    start_year=2022,
    end_year=2025
)

# Get archive URLs
archive_urls = scraper.get_archive_urls(2022, 2025)

all_emails = []
for archive_url in tqdm(archive_urls, desc="Scraping archives"):
    # Get message URLs from archive
    html = scraper.fetch_page(archive_url)
    message_urls = scraper.parse_message_list(html)

    # Scrape individual messages
    for msg_url in tqdm(message_urls, desc=f"Messages from {archive_url}", leave=False):
        email_data = scraper.scrape_message(msg_url)
        all_emails.append(email_data)

        # Save checkpoint every 100 emails
        if len(all_emails) % 100 == 0:
            scraper.save_checkpoint(all_emails, "data/checkpoint.json")

scraper.save_to_json("data/raw_threads.json")
```

### Resume from Checkpoint

```python
from scraper import MailingListScraper

scraper = MailingListScraper(...)

# Load previous progress
existing_emails = scraper.load_checkpoint("data/checkpoint.json")
existing_ids = {e['message_id'] for e in existing_emails}

# Continue scraping, skip already downloaded
new_emails = scraper.scrape_all(skip_ids=existing_ids)

# Combine and save
all_emails = existing_emails + new_emails
scraper.save_to_json("data/raw_threads.json")
```

## Performance Considerations

### Estimated Metrics

- **Total time:** 2-4 hours (depends on archive size)
- **Expected email count:** 1,000-5,000 emails (2022-2025)
- **Rate limit:** 1 request/second (configurable)
- **Storage:** ~50-200 MB (JSON)

### Optimization Strategies

1. **Parallel Scraping**
   - Use `concurrent.futures.ThreadPoolExecutor`
   - Scrape multiple archives simultaneously
   - Respect rate limits globally

2. **Caching**
   - Cache fetched pages locally
   - Avoid re-downloading on failures
   - Use ETag/Last-Modified headers

3. **Incremental Updates**
   - Only scrape new months after initial run
   - Maintain database of scraped message IDs
   - Delta updates for ongoing monitoring

## Dependencies

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
tqdm>=4.66.0
```

## Testing

### Unit Tests

```python
import unittest
from scraper import parse_email_content

class TestScraper(unittest.TestCase):
    def test_parse_email_content(self):
        html = """
        <div class="message">
            <div class="header">
                <span class="from">John Doe</span>
                <span class="subject">Test Subject</span>
            </div>
            <div class="body">Message body here</div>
        </div>
        """
        result = parse_email_content(html)
        self.assertEqual(result['subject'], 'Test Subject')
        self.assertEqual(result['from'], 'John Doe')
```

### Integration Tests

```python
# Test actual scraping (use small date range)
scraper = MailingListScraper(
    base_url="https://www.postgresql.org/list/pgsql-hackers",
    start_year=2025,
    end_year=2025
)
emails = scraper.scrape_all()
assert len(emails) > 0
```

## Next Steps

After scraping completes:
1. Verify `data/raw_threads.json` contains expected data
2. Check thread relationships (in_reply_to, references)
3. Proceed to `thread_parser.py` for thread reconstruction

## Troubleshooting

### No emails scraped
- Verify URL structure matches archive format
- Check if website requires authentication
- Inspect HTML structure and update selectors

### Incomplete threads
- Ensure `in_reply_to` and `references` are extracted
- Verify message_id uniqueness
- Check for malformed email headers

### Blocked by server
- Reduce request rate (`RATE_LIMIT_DELAY`)
- Add random delays between requests
- Use residential proxies if necessary
