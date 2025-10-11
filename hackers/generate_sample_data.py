"""
Sample Data Generator

Generates sample email data for testing the pipeline without scraping.
"""
import json
import random
from datetime import datetime, timedelta

import config
from utils import ensure_dir, get_timestamp


def generate_sample_emails(count: int = 50) -> list:
    """Generate sample email data."""

    topics = [
        ("Query Planner Optimization", ["planner", "optimizer", "partition pruning"]),
        ("MVCC and Vacuum", ["mvcc", "vacuum", "visibility"]),
        ("WAL and Replication", ["wal", "replication", "logical decoding"]),
        ("Index Performance", ["btree", "index", "performance"]),
        ("Buffer Manager", ["buffer", "shared buffers", "cache"])
    ]

    emails = []
    base_date = datetime(2023, 1, 1)

    # Generate threads
    for thread_num in range(count // 5):
        topic_name, keywords = random.choice(topics)

        # Root message
        root_date = base_date + timedelta(days=thread_num * 7)
        root_id = f"<{root_date.strftime('%Y%m%d%H%M%S')}.root{thread_num}@postgresql.org>"

        root_email = {
            'message_id': root_id,
            'subject': f"[HACKERS] {topic_name} - discussion",
            'from': f'developer{random.randint(1, 10)}@postgresql.org',
            'date': root_date.isoformat(),
            'in_reply_to': '',
            'references': [],
            'body': f"""I've been investigating {topic_name.lower()} and found some interesting issues.

The current implementation in src/backend/{keywords[0]}.c has performance problems when dealing with large datasets.

Key concerns:
1. {keywords[0]} efficiency
2. {keywords[1]} overhead
3. {keywords[2]} improvements

What do others think? Has anyone benchmarked this?

Best regards""",
            'url': f'https://postgrespro.com/message/{thread_num}',
            'scraped_at': get_timestamp()
        }

        emails.append(root_email)

        # Generate 3-5 replies per thread
        num_replies = random.randint(3, 5)
        prev_id = root_id

        for reply_num in range(num_replies):
            reply_date = root_date + timedelta(hours=reply_num * 6)
            reply_id = f"<{reply_date.strftime('%Y%m%d%H%M%S')}.reply{thread_num}_{reply_num}@postgresql.org>"

            reply_email = {
                'message_id': reply_id,
                'subject': f"Re: [HACKERS] {topic_name} - discussion",
                'from': f'expert{random.randint(1, 5)}@postgresql.org',
                'date': reply_date.isoformat(),
                'in_reply_to': prev_id,
                'references': [root_id],
                'body': f"""Good point about {keywords[reply_num % len(keywords)]}.

I think we should focus on optimizing the {keywords[0]} code path. Looking at the source in src/backend/{keywords[1]}, there are several opportunities for improvement.

Have you considered using {keywords[2]}? That might help with the performance issues.

We should also update the documentation to reflect these changes.""",
                'url': f'https://postgrespro.com/message/{thread_num}-{reply_num}',
                'scraped_at': get_timestamp()
            }

            emails.append(reply_email)
            prev_id = reply_id

    return emails


def main():
    """Generate sample data."""
    print("Generating sample email data...")

    # Generate emails
    emails = generate_sample_emails(count=50)

    print(f"Generated {len(emails)} sample emails in {len(emails) // 5} threads")

    # Save to raw_threads.json
    ensure_dir(config.DATA_DIR)

    with open(config.RAW_THREADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2)

    print(f"Saved to {config.RAW_THREADS_FILE}")

    # Show sample
    print("\nSample email:")
    print(f"Subject: {emails[0]['subject']}")
    print(f"From: {emails[0]['from']}")
    print(f"Body preview: {emails[0]['body'][:100]}...")

    print("\nYou can now run:")
    print("  python main.py --parse")
    print("  python main.py --cluster")
    print("  etc.")


if __name__ == '__main__':
    main()
