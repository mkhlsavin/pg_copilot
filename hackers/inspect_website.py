"""
Website Inspector

Inspects the PostgresPro mailing list structure to determine correct selectors.
"""
import requests
from bs4 import BeautifulSoup

def inspect_archive_page():
    """Inspect an archive page to understand structure."""
    # Test with a recent month
    url = "https://www.postgresql.org/list/pgsql-hackers/2022-01/"

    print(f"Fetching: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print("Failed to fetch page")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Save HTML for inspection
        with open('archive_sample.html', 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"\nHTML saved to archive_sample.html")
        print(f"Total links found: {len(soup.find_all('a'))}")

        # Look for message links
        print("\nFirst 10 links:")
        for i, link in enumerate(soup.find_all('a')[:10]):
            href = link.get('href', '')
            text = link.get_text()[:50]
            print(f"{i+1}. href={href} | text={text}")

        # Look for common structures
        print("\nLooking for tables:")
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")

        print("\nLooking for divs with class:")
        divs = soup.find_all('div', class_=True)
        classes = set()
        for div in divs:
            classes.update(div.get('class', []))
        print(f"Common classes: {list(classes)[:10]}")

    except Exception as e:
        print(f"Error: {e}")


def inspect_message_page():
    """Inspect a single message page."""
    # You'll need to get an actual message URL from the archive page first
    # This is a placeholder
    print("\nTo inspect a message page:")
    print("1. Run this script once to get archive_sample.html")
    print("2. Open archive_sample.html in browser")
    print("3. Find a message link")
    print("4. Update this function with a real message URL")


if __name__ == '__main__':
    print("PostgresPro Mailing List Inspector")
    print("=" * 60)
    inspect_archive_page()
    inspect_message_page()
