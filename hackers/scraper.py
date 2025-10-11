"""
PostgreSQL Hackers Mailing List Scraper

Scrapes email threads from https://www.postgresql.org/list/pgsql-hackers
"""
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

import config
from utils import save_json, load_json, get_timestamp


logger = logging.getLogger(__name__)


class MailingListScraper:
    """Scraper for PostgreSQL mailing list archives."""

    def __init__(
        self,
        base_url: str = config.MAILING_LIST_URL,
        start_year: int = config.START_YEAR,
        end_year: int = config.END_YEAR
    ):
        """
        Initialize scraper.

        Args:
            base_url: Base URL of mailing list
            start_year: Starting year
            end_year: Ending year
        """
        self.base_url = base_url
        self.start_year = start_year
        self.end_year = end_year
        self.session = requests.Session()
        self.emails = []

    def get_archive_urls(self) -> List[str]:
        """
        Generate list of archive URLs to scrape.

        Returns:
            List of archive page URLs
        """
        urls = []

        for year in range(self.start_year, self.end_year + 1):
            for month in range(1, 13):
                # Format: https://www.postgresql.org/list/pgsql-hackers/2023-01
                url = f"{self.base_url}/{year}-{month:02d}"
                urls.append(url)

        logger.info(f"Generated {len(urls)} archive URLs ({self.start_year}-{self.end_year})")
        return urls

    def fetch_page(self, url: str, retries: int = config.MAX_RETRIES) -> Optional[str]:
        """
        Fetch HTML page with retry logic.

        Args:
            url: URL to fetch
            retries: Maximum retry attempts

        Returns:
            HTML content or None on failure
        """
        headers = {
            'User-Agent': random.choice(config.USER_AGENTS)
        }

        for attempt in range(retries):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=config.REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    logger.debug(f"Page not found: {url}")
                    return None
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")

            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")

                if attempt < retries - 1:
                    time.sleep(config.RATE_LIMIT_DELAY * (2 ** attempt))

        return None

    def parse_day_links(self, html: str) -> List[str]:
        """
        Extract day pagination links from archive page.

        Args:
            html: Archive page HTML

        Returns:
            List of day URLs (e.g., /list/pgsql-hackers/since/202201010000/)
        """
        soup = BeautifulSoup(html, 'html.parser')
        day_urls = []

        # Find the day links section
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Day links follow pattern: /list/pgsql-hackers/since/YYYYMMDDHHMMSS/
            if '/since/' in href and 'pgsql-hackers' in href:
                full_url = urljoin('https://www.postgresql.org', href)
                day_urls.append(full_url)

        return list(set(day_urls))  # Deduplicate

    def parse_message_list(self, html: str, archive_url: str) -> List[str]:
        """
        Extract message URLs from archive page.

        Args:
            html: Archive page HTML
            archive_url: Archive page URL

        Returns:
            List of message URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        message_urls = []

        # Find all links to individual messages
        # PostgreSQL archives use /message-id/{encoded_id} format
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Check if it's a message link
            if href.startswith('/message-id/'):
                full_url = urljoin('https://www.postgresql.org', href)
                message_urls.append(full_url)

        return list(set(message_urls))  # Deduplicate

    def parse_email_content(self, html: str, url: str) -> Optional[Dict]:
        """
        Extract email metadata and content from message page.

        Args:
            html: Message page HTML
            url: Message URL

        Returns:
            Email dictionary or None
        """
        soup = BeautifulSoup(html, 'html.parser')

        try:
            email = {
                'message_id': None,
                'subject': None,
                'from': None,
                'date': None,
                'in_reply_to': None,
                'references': [],
                'body': None,
                'url': url,
                'scraped_at': get_timestamp()
            }

            # Extract from header table (first table on page)
            tables = soup.find_all('table')
            if tables:
                header_table = tables[0]

                for row in header_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')

                    if th and td:
                        header_name = th.get_text().strip().rstrip(':').lower()
                        header_value = td.get_text().strip()

                        if header_name == 'from':
                            email['from'] = header_value
                        elif header_name == 'subject':
                            email['subject'] = header_value
                        elif header_name == 'date':
                            email['date'] = header_value
                        elif header_name == 'message-id':
                            email['message_id'] = header_value

            # Extract In-Reply-To and References from meta tags or header table
            # PostgreSQL.org doesn't always show these in the header table
            # Try to get from HTML comments or reconstruct from thread info

            # Extract body from div with class 'message-content'
            body_elem = soup.find('div', class_='message-content')
            if body_elem:
                email['body'] = body_elem.get_text().strip()

            # Validate we got essential fields
            if email['subject'] and email['body'] and email['from']:
                return email
            else:
                logger.warning(f"Incomplete email data from {url}")
                return None

        except Exception as e:
            logger.error(f"Error parsing email from {url}: {e}")
            return None

    def scrape_archive(self, archive_url: str) -> List[Dict]:
        """
        Scrape all messages from a single archive page and its day pages.

        Args:
            archive_url: Archive page URL

        Returns:
            List of email dictionaries
        """
        logger.info(f"Scraping archive: {archive_url}")

        # Fetch archive page
        html = self.fetch_page(archive_url)
        if not html:
            return []

        # Get all day links for pagination
        day_urls = self.parse_day_links(html)
        logger.info(f"Found {len(day_urls)} day pages in {archive_url}")

        # Collect all message URLs from main page and all day pages
        all_message_urls = set()

        # Get messages from main page
        message_urls = self.parse_message_list(html, archive_url)
        all_message_urls.update(message_urls)

        # Get messages from each day page
        for day_url in day_urls:
            time.sleep(config.RATE_LIMIT_DELAY)  # Respect rate limit
            day_html = self.fetch_page(day_url)
            if day_html:
                day_message_urls = self.parse_message_list(day_html, day_url)
                all_message_urls.update(day_message_urls)

        logger.info(f"Found {len(all_message_urls)} total messages in {archive_url}")

        emails = []
        message_list = list(all_message_urls)

        # Scrape individual messages concurrently
        def fetch_and_parse(msg_url):
            """Fetch and parse a single message."""
            time.sleep(config.RATE_LIMIT_DELAY)  # Respect rate limit
            msg_html = self.fetch_page(msg_url)
            if msg_html:
                return self.parse_email_content(msg_html, msg_url)
            return None

        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=config.CONCURRENT_REQUESTS) as executor:
            # Submit all tasks
            futures = {executor.submit(fetch_and_parse, url): url for url in message_list}

            # Collect results with progress bar
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc=f"Messages from {archive_url.split('/')[-1]}", leave=False):
                email = future.result()
                if email:
                    emails.append(email)

        logger.info(f"Scraped {len(emails)} emails from {archive_url}")
        return emails

    def scrape_all(self, max_archives: int = None) -> List[Dict]:
        """
        Scrape all archives.

        Args:
            max_archives: Limit number of archives (for testing)

        Returns:
            List of all email dictionaries
        """
        archive_urls = self.get_archive_urls()

        if max_archives:
            archive_urls = archive_urls[:max_archives]
            logger.info(f"Limiting to {max_archives} archives for testing")

        # Start with existing emails from checkpoint (if loaded)
        all_emails = self.emails if self.emails else []

        # Track which archives we've already scraped by URL in email metadata
        scraped_archives = set()
        if all_emails:
            # Extract unique archive months from existing emails
            for email in all_emails:
                if 'date' in email and email['date']:
                    # Extract YYYY-MM from date like "2022-01-15 12:34:56"
                    date_parts = email['date'].split()[0].split('-')
                    if len(date_parts) >= 2:
                        archive_month = f"{date_parts[0]}-{date_parts[1]}"
                        archive_url = f"{self.base_url}/{archive_month}"
                        scraped_archives.add(archive_url)

            logger.info(f"Resuming from checkpoint: {len(all_emails)} emails from {len(scraped_archives)} archives")

        for archive_url in tqdm(archive_urls, desc="Scraping archives"):
            # Skip if already scraped
            if archive_url in scraped_archives:
                logger.info(f"Skipping already scraped archive: {archive_url}")
                continue

            emails = self.scrape_archive(archive_url)
            all_emails.extend(emails)

            # Save checkpoint after each archive
            self.save_checkpoint(all_emails)

        self.emails = all_emails
        logger.info(f"Total emails scraped: {len(all_emails)}")

        return all_emails

    def save_checkpoint(self, emails: List[Dict]):
        """Save progress checkpoint."""
        save_json(emails, config.SCRAPER_CHECKPOINT_FILE)
        logger.info(f"Saved checkpoint: {len(emails)} emails")

    def load_checkpoint(self) -> List[Dict]:
        """Load previous checkpoint."""
        try:
            emails = load_json(config.SCRAPER_CHECKPOINT_FILE)
            logger.info(f"Loaded checkpoint: {len(emails)} emails")
            return emails
        except FileNotFoundError:
            logger.info("No checkpoint found")
            return []

    def save_to_json(self, output_path: str = config.RAW_THREADS_FILE):
        """Save scraped emails to JSON."""
        save_json(self.emails, output_path)
        logger.info(f"Saved {len(self.emails)} emails to {output_path}")


def main():
    """Main function for standalone execution."""
    import sys
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting mailing list scraper")

    # Initialize scraper
    scraper = MailingListScraper()

    # Check for existing checkpoint
    checkpoint_emails = scraper.load_checkpoint()
    if checkpoint_emails:
        response = input(f"Found checkpoint with {len(checkpoint_emails)} emails. Resume? (y/n): ")
        if response.lower() == 'y':
            scraper.emails = checkpoint_emails

    # Scrape
    try:
        # For testing, limit archives
        max_archives = int(sys.argv[1]) if len(sys.argv) > 1 else None

        new_emails = scraper.scrape_all(max_archives=max_archives)

        # Save results
        scraper.save_to_json()

        logger.info(f"Scraping complete: {len(scraper.emails)} total emails")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        scraper.save_checkpoint(scraper.emails)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        scraper.save_checkpoint(scraper.emails)
        sys.exit(1)


if __name__ == '__main__':
    main()
