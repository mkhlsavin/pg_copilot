"""
Documentation File Discovery

Scans documentation folders and identifies Markdown files with their metadata.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

from .config import DOCS_ROOT, SOURCE_FOLDERS, BILINGUAL_FOLDERS

logger = logging.getLogger(__name__)


@dataclass
class DocFile:
    """Represents a documentation file with metadata."""

    source_path: Path
    relative_path: str
    folder: str
    filename: str
    language: str  # 'en' or 'ru'
    content: str = ""
    title: Optional[str] = None
    has_translation: bool = False
    headings: List[str] = field(default_factory=list)
    mtime: float = 0.0  # File modification time (timestamp)

    def __post_init__(self):
        if self.content and not self.title:
            self.title = extract_title(self.content)
        if self.content and not self.headings:
            self.headings = extract_headings(self.content)


@dataclass
class TranslationStatus:
    """Status of a document's translation."""

    en_exists: bool
    ru_exists: bool
    en_mtime: float
    ru_mtime: float
    use_existing_ru: bool  # True if ru is newer than en (use ru directly)


def detect_language(content: str) -> str:
    """
    Detect if content is primarily English or Russian.

    Based on ratio of Cyrillic to Latin characters.
    """
    cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', content))
    latin_count = len(re.findall(r'[a-zA-Z]', content))

    if latin_count == 0 and cyrillic_count == 0:
        return 'en'  # Default to English for empty/code-only content

    # If more than 10% Cyrillic, consider it Russian
    total = cyrillic_count + latin_count
    if total > 0 and cyrillic_count / total > 0.1:
        return 'ru'

    return 'en'


def extract_title(content: str) -> Optional[str]:
    """Extract the first H1 title from Markdown content."""
    match = re.search(r'^#\s+(.+?)(?:\s*\{.*\})?$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_headings(content: str) -> List[str]:
    """Extract all headings from Markdown content."""
    headings = []
    for match in re.finditer(r'^(#{1,6})\s+(.+?)(?:\s*\{.*\})?$', content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        headings.append((level, text))
    return headings


def discover_docs(
    docs_root: Path = None,
    folders: List[str] = None
) -> Dict[str, List[DocFile]]:
    """
    Discover all Markdown documentation files.

    Args:
        docs_root: Root documentation directory
        folders: List of folders to scan

    Returns:
        Dictionary mapping folder names to lists of DocFile objects
    """
    docs_root = docs_root or DOCS_ROOT
    folders = folders or SOURCE_FOLDERS

    result: Dict[str, List[DocFile]] = {}

    for folder in folders:
        folder_path = docs_root / folder
        if not folder_path.exists():
            logger.warning(f"Folder not found: {folder_path}")
            continue

        files = _scan_folder(folder_path, folder, docs_root)
        if files:
            result[folder] = files
            logger.info(f"Found {len(files)} files in {folder}")

    return result


def _scan_folder(folder_path: Path, folder_name: str, docs_root: Path) -> List[DocFile]:
    """Scan a single folder for Markdown files."""
    files = []

    # Check if this is a bilingual folder with en/ru subdirectories
    if folder_name in BILINGUAL_FOLDERS:
        # Process en/ subdirectory
        en_path = folder_path / "en"
        if en_path.exists():
            for md_file in en_path.rglob("*.md"):
                doc = _create_doc_file(md_file, folder_name, docs_root, "en")
                if doc:
                    files.append(doc)

        # Process ru/ subdirectory
        ru_path = folder_path / "ru"
        if ru_path.exists():
            for md_file in ru_path.rglob("*.md"):
                doc = _create_doc_file(md_file, folder_name, docs_root, "ru")
                if doc:
                    files.append(doc)

        # Also check root README
        root_readme = folder_path / "README.md"
        if root_readme.exists():
            doc = _create_doc_file(root_readme, folder_name, docs_root, "en")
            if doc:
                files.append(doc)
    else:
        # Regular folder - scan all .md files
        for md_file in folder_path.rglob("*.md"):
            doc = _create_doc_file(md_file, folder_name, docs_root, None)
            if doc:
                files.append(doc)

    return files


def _create_doc_file(
    file_path: Path,
    folder_name: str,
    docs_root: Path,
    forced_language: Optional[str] = None
) -> Optional[DocFile]:
    """Create a DocFile from a file path."""
    try:
        content = file_path.read_text(encoding='utf-8')
        relative_path = str(file_path.relative_to(docs_root)).replace('\\', '/')

        # Determine language
        if forced_language:
            language = forced_language
        else:
            language = detect_language(content)

        # Get file modification time
        mtime = file_path.stat().st_mtime

        return DocFile(
            source_path=file_path,
            relative_path=relative_path,
            folder=folder_name,
            filename=file_path.name,
            language=language,
            content=content,
            mtime=mtime,
        )
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def group_by_language(docs: Dict[str, List[DocFile]]) -> Dict[str, Dict[str, List[DocFile]]]:
    """
    Group documentation files by language.

    Returns:
        {
            'en': {'folder': [DocFile, ...]},
            'ru': {'folder': [DocFile, ...]}
        }
    """
    result = {'en': {}, 'ru': {}}

    for folder, files in docs.items():
        for doc in files:
            lang = doc.language
            if folder not in result[lang]:
                result[lang][folder] = []
            result[lang][folder].append(doc)

    return result


def find_missing_translations(docs: Dict[str, List[DocFile]]) -> List[DocFile]:
    """
    Find English documents that don't have Russian translations.

    For bilingual folders, checks if matching ru/ file exists.
    For other folders, all English files need translation.
    """
    missing = []

    for folder, files in docs.items():
        if folder in BILINGUAL_FOLDERS:
            # Check which en/ files don't have ru/ counterparts
            en_files = {f.filename: f for f in files if f.language == 'en'}
            ru_files = {f.filename for f in files if f.language == 'ru'}

            for filename, doc in en_files.items():
                if filename not in ru_files:
                    missing.append(doc)
        else:
            # All English files need translation
            for doc in files:
                if doc.language == 'en':
                    missing.append(doc)

    return missing


def check_translation_status(
    docs_root: Path,
    folder: str,
    filename: str
) -> TranslationStatus:
    """
    Check the translation status of a document.

    Determines if a Russian translation exists and whether it's newer
    than the English version (meaning it should be used directly).

    Args:
        docs_root: Root documentation directory
        folder: Section folder name (e.g., 'guides')
        filename: Filename without path (e.g., 'CLI_GUIDE.md')

    Returns:
        TranslationStatus with comparison results
    """
    en_path = docs_root / folder / 'en' / filename
    ru_path = docs_root / folder / 'ru' / filename

    en_exists = en_path.exists()
    ru_exists = ru_path.exists()

    en_mtime = en_path.stat().st_mtime if en_exists else 0.0
    ru_mtime = ru_path.stat().st_mtime if ru_exists else 0.0

    # Use existing RU if it exists AND is newer than EN
    use_existing_ru = ru_exists and ru_mtime > en_mtime

    return TranslationStatus(
        en_exists=en_exists,
        ru_exists=ru_exists,
        en_mtime=en_mtime,
        ru_mtime=ru_mtime,
        use_existing_ru=use_existing_ru,
    )


def get_translation_summary(docs_root: Path = None) -> Dict[str, Dict[str, TranslationStatus]]:
    """
    Get translation status summary for all documents.

    Returns:
        {
            'folder': {
                'filename': TranslationStatus,
                ...
            },
            ...
        }
    """
    docs_root = docs_root or DOCS_ROOT
    summary: Dict[str, Dict[str, TranslationStatus]] = {}

    for folder in BILINGUAL_FOLDERS:
        folder_path = docs_root / folder
        if not folder_path.exists():
            continue

        en_path = folder_path / 'en'
        if not en_path.exists():
            continue

        summary[folder] = {}

        # Get all English files
        for md_file in en_path.rglob('*.md'):
            filename = md_file.name
            status = check_translation_status(docs_root, folder, filename)
            summary[folder][filename] = status

    return summary


def print_translation_summary(docs_root: Path = None):
    """Print a human-readable translation status summary."""
    summary = get_translation_summary(docs_root)

    print("\n" + "=" * 70)
    print("TRANSLATION STATUS SUMMARY")
    print("=" * 70)

    total_files = 0
    translated = 0
    outdated = 0
    missing = 0

    for folder, files in summary.items():
        print(f"\n{folder}/")
        for filename, status in sorted(files.items()):
            total_files += 1
            if status.use_existing_ru:
                mark = "[RU OK]"
                translated += 1
            elif status.ru_exists:
                mark = "[RU OLD]"
                outdated += 1
            else:
                mark = "[NO RU]"
                missing += 1
            print(f"  {mark} {filename}")

    print("\n" + "-" * 70)
    print(f"Total files:      {total_files}")
    print(f"Up-to-date RU:    {translated}")
    print(f"Outdated RU:      {outdated}")
    print(f"Missing RU:       {missing}")
    print("=" * 70)


if __name__ == "__main__":
    # Test discovery
    logging.basicConfig(level=logging.INFO)

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        # Show translation status summary
        print_translation_summary()
    else:
        # Normal discovery test
        docs = discover_docs()

        print("\n=== Documentation Structure ===")
        for folder, files in docs.items():
            print(f"\n{folder}/")
            for doc in files:
                print(f"  - {doc.filename} ({doc.language}) - {doc.title or 'No title'}")

        missing = find_missing_translations(docs)
        print(f"\n=== Files needing Russian translation: {len(missing)} ===")
        for doc in missing[:10]:
            print(f"  - {doc.relative_path}")

        print("\nRun with --status to see translation status summary")
