"""
Email Thread Parser

Reconstructs threaded conversations from raw email data.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from tqdm import tqdm

import config
from utils import (
    load_json,
    save_json,
    normalize_subject,
    clean_email_body,
    extract_email_address,
    get_timestamp
)


logger = logging.getLogger(__name__)


class ThreadParser:
    """Parser for reconstructing email thread structure."""

    def __init__(self, raw_emails: List[Dict]):
        """
        Initialize parser.

        Args:
            raw_emails: List of email dictionaries from scraper
        """
        self.emails = raw_emails
        self.message_map = {}  # message_id -> email
        self.threads = {}  # root_id -> thread tree

    def build_message_map(self):
        """Build index mapping message IDs to emails."""
        logger.info("Building message ID index...")

        for email in self.emails:
            msg_id = email.get('message_id')
            if msg_id:
                self.message_map[msg_id] = email

        logger.info(f"Indexed {len(self.message_map)} messages by ID")

    def find_thread_root(self, email: Dict, depth: int = 0) -> str:
        """
        Find root message of thread.

        Args:
            email: Email dictionary
            depth: Current recursion depth

        Returns:
            Message ID of thread root
        """
        # Prevent infinite recursion
        if depth > config.MAX_THREAD_DEPTH:
            return email.get('message_id', '')

        # If no in_reply_to, this is the root
        in_reply_to = email.get('in_reply_to') or ''
        in_reply_to = in_reply_to.strip() if in_reply_to else ''
        if not in_reply_to:
            return email.get('message_id', '')

        # Try to find parent
        parent = self.message_map.get(in_reply_to)
        if parent:
            return self.find_thread_root(parent, depth + 1)

        # If parent not found, check references
        references = email.get('references', [])
        if references:
            # First reference is typically the root
            first_ref = references[0].strip()
            if first_ref in self.message_map:
                return first_ref

        # Fallback: this email is the root
        return email.get('message_id', '')

    def build_thread_tree(self, root_id: str) -> Dict:
        """
        Build hierarchical thread structure.

        Args:
            root_id: Root message ID

        Returns:
            Thread tree dictionary
        """
        root_email = self.message_map.get(root_id)
        if not root_email:
            return None

        # Find all messages in this thread
        thread_messages = []
        messages_to_process = [root_id]
        processed = set()

        while messages_to_process:
            current_id = messages_to_process.pop(0)

            if current_id in processed:
                continue

            processed.add(current_id)

            email = self.message_map.get(current_id)
            if not email:
                continue

            # Add to thread
            thread_messages.append(email)

            # Find children (messages replying to this one)
            for msg_id, msg in self.message_map.items():
                if msg_id in processed:
                    continue

                parent_id = msg.get('in_reply_to') or ''
                parent_id = parent_id.strip() if parent_id else ''
                if parent_id == current_id:
                    messages_to_process.append(msg_id)

        # Build thread structure
        thread = {
            'thread_id': root_id,
            'root_message_id': root_id,
            'subject': normalize_subject(root_email.get('subject', '')),
            'start_date': root_email.get('date', ''),
            'end_date': root_email.get('date', ''),
            'message_count': len(thread_messages),
            'participants': [],
            'messages': []
        }

        # Process messages
        participants = set()

        for email in thread_messages:
            # Update date range
            email_date = email.get('date', '')
            if email_date:
                if not thread['start_date'] or email_date < thread['start_date']:
                    thread['start_date'] = email_date
                if not thread['end_date'] or email_date > thread['end_date']:
                    thread['end_date'] = email_date

            # Track participants
            from_email = extract_email_address(email.get('from', ''))
            if from_email:
                participants.add(from_email)

            # Clean body
            cleaned_body = clean_email_body(email.get('body', ''))

            # Add message to thread
            parent_id = email.get('in_reply_to') or ''
            parent_id = parent_id.strip() if parent_id else ''

            message = {
                'message_id': email.get('message_id', ''),
                'parent_id': parent_id,
                'from': email.get('from', ''),
                'date': email.get('date', ''),
                'subject': email.get('subject', ''),
                'body': email.get('body', ''),
                'cleaned_body': cleaned_body,
                'url': email.get('url', '')
            }

            thread['messages'].append(message)

        # Sort messages by date
        thread['messages'].sort(key=lambda m: m.get('date', ''))

        # Set participants
        thread['participants'] = sorted(participants)

        # Build aggregated content
        thread['aggregated_content'] = self.aggregate_thread_content(thread)

        return thread

    def aggregate_thread_content(self, thread: Dict) -> str:
        """
        Combine all messages in thread into single text.

        Args:
            thread: Thread dictionary

        Returns:
            Aggregated content string
        """
        parts = []

        for i, message in enumerate(thread['messages'], 1):
            parts.append(f"[Message {i}]")
            parts.append(f"From: {message['from']}")
            parts.append(f"Date: {message['date']}")
            parts.append("")
            parts.append(message['cleaned_body'])
            parts.append("")
            parts.append("---")
            parts.append("")

        return '\n'.join(parts)

    def parse_threads(self) -> Dict:
        """
        Parse all threads.

        Returns:
            Dictionary of threads
        """
        logger.info(f"Parsing threads from {len(self.emails)} emails...")

        # Build message index
        self.build_message_map()

        # Find all thread roots
        root_ids = set()

        for email in tqdm(self.emails, desc="Finding thread roots"):
            root_id = self.find_thread_root(email)
            if root_id:
                root_ids.add(root_id)

        logger.info(f"Found {len(root_ids)} thread roots")

        # Build thread trees
        threads = {}

        for root_id in tqdm(root_ids, desc="Building thread trees"):
            thread = self.build_thread_tree(root_id)

            if thread and thread['message_count'] >= config.MIN_THREAD_SIZE:
                # Use normalized subject + date as thread ID
                thread_id = f"{thread['start_date'][:10]}-{thread['subject'][:50]}"
                thread_id = thread_id.lower().replace(' ', '-').replace('/', '-')

                threads[thread_id] = thread

        logger.info(f"Built {len(threads)} threads (min size: {config.MIN_THREAD_SIZE})")

        self.threads = threads
        return threads

    def get_statistics(self) -> Dict:
        """
        Get thread statistics.

        Returns:
            Statistics dictionary
        """
        if not self.threads:
            return {}

        message_counts = [t['message_count'] for t in self.threads.values()]

        stats = {
            'total_threads': len(self.threads),
            'total_messages': sum(message_counts),
            'avg_messages_per_thread': sum(message_counts) / len(message_counts) if message_counts else 0,
            'min_messages': min(message_counts) if message_counts else 0,
            'max_messages': max(message_counts) if message_counts else 0,
            'total_participants': len(set(
                p for t in self.threads.values() for p in t['participants']
            ))
        }

        return stats

    def save_to_json(self, output_path: str = config.PROCESSED_THREADS_FILE):
        """Save processed threads to JSON."""
        output = {
            'threads': list(self.threads.values()),
            'metadata': {
                'total_threads': len(self.threads),
                'total_emails': len(self.emails),
                'parsed_at': get_timestamp(),
                **self.get_statistics()
            }
        }

        save_json(output, output_path)
        logger.info(f"Saved {len(self.threads)} threads to {output_path}")


def main():
    """Main function for standalone execution."""
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting thread parser")

    # Load raw emails
    raw_emails = load_json(config.RAW_THREADS_FILE)
    logger.info(f"Loaded {len(raw_emails)} raw emails")

    # Parse threads
    parser = ThreadParser(raw_emails)
    threads = parser.parse_threads()

    # Show statistics
    stats = parser.get_statistics()
    logger.info("Thread Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # Save results
    parser.save_to_json()

    logger.info("Thread parsing complete")


if __name__ == '__main__':
    main()
