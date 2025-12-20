"""
Source Content Step.

Imports full source code content into nodes_file.content from source_path.
This step runs after CPG export to populate file contents for code navigation.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)

# Maximum file size to import (500 KB - increased to include large core files)
MAX_FILE_SIZE = 500 * 1024

# Language detection by file extension
LANGUAGE_EXTENSIONS = {
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
    '.py': 'python', '.pyw': 'python',
    '.java': 'java',
    '.js': 'javascript', '.jsx': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.cs': 'csharp',
    '.kt': 'kotlin', '.kts': 'kotlin',
    '.swift': 'swift',
    '.scala': 'scala',
    '.yaml': 'yaml', '.yml': 'yaml',
    '.json': 'json',
    '.xml': 'xml',
    '.html': 'html', '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss', '.sass': 'sass',
    '.sql': 'sql',
    '.sh': 'shell', '.bash': 'shell',
    '.ps1': 'powershell',
    '.md': 'markdown',
    '.txt': 'text',
    '.ini': 'ini',
    '.toml': 'toml',
    '.conf': 'config',
    '.cfg': 'config',
}


class SourceContentStep:
    """Step for importing source code content into nodes_file.

    This step reads source files from source_path and populates
    the nodes_file.content field with full file contents.
    Files larger than MAX_FILE_SIZE are skipped.
    """

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize source content step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute source content import.

        Args:
            context: Pipeline context with source_path and duckdb_path.

        Returns:
            Dictionary with import statistics.
        """
        source_path = Path(context.get("source_path", ""))
        duckdb_path = context.get("duckdb_path", "")

        if not source_path or not source_path.exists():
            logger.warning(f"Source path not found: {source_path}")
            return {"source_files_imported": 0, "source_import_skipped": True}

        self._report_progress(10, "Connecting to DuckDB...")
        conn = duckdb.connect(duckdb_path)

        try:
            # Ensure nodes_file table exists with new columns
            self._ensure_schema(conn)

            # Get files that need content
            self._report_progress(20, "Getting file list from nodes_file...")
            files = self._get_files_needing_content(conn)

            if not files:
                # If nodes_file is empty, scan source_path directly
                self._report_progress(25, "Scanning source directory...")
                files = self._scan_and_insert_files(conn, source_path)

            total_files = len(files)
            imported = 0
            skipped_size = 0
            skipped_not_found = 0
            skipped_error = 0

            self._report_progress(30, f"Importing {total_files} files...")

            for i, (file_id, file_name) in enumerate(files):
                if i % 100 == 0:
                    progress = 30 + int((i / max(total_files, 1)) * 60)
                    self._report_progress(progress, f"Processing file {i}/{total_files}...")

                # Find file in source_path
                file_path = self._find_file(source_path, file_name)
                if not file_path:
                    skipped_not_found += 1
                    continue

                # Check file size
                try:
                    file_size = file_path.stat().st_size
                    if file_size > MAX_FILE_SIZE:
                        skipped_size += 1
                        continue
                except Exception:
                    skipped_error += 1
                    continue

                # Read and import content
                try:
                    content = file_path.read_text(encoding='utf-8', errors='replace')
                    language = self._detect_language(file_path.suffix)

                    conn.execute("""
                        UPDATE nodes_file
                        SET content = ?, size_bytes = ?, language = ?
                        WHERE id = ?
                    """, [content, len(content), language, file_id])
                    imported += 1

                except Exception as e:
                    logger.debug(f"Error reading {file_path}: {e}")
                    skipped_error += 1

            conn.commit()

            # Normalize paths for JOIN compatibility with nodes_method
            self._report_progress(92, "Normalizing file paths...")
            self._normalize_paths(conn)

        finally:
            conn.close()

        self._report_progress(95, "Generating statistics...")

        stats = {
            "source_files_imported": imported,
            "source_files_skipped_size": skipped_size,
            "source_files_skipped_not_found": skipped_not_found,
            "source_files_skipped_error": skipped_error,
            "source_files_total": total_files,
        }

        logger.info(
            f"Source content import: {imported} imported, "
            f"{skipped_size} skipped (size), "
            f"{skipped_not_found} not found, "
            f"{skipped_error} errors"
        )

        self._report_progress(100, f"Imported {imported} source files")

        return stats

    def _ensure_schema(self, conn) -> None:
        """Ensure nodes_file table has required columns."""
        try:
            # Check if columns exist
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'nodes_file' AND column_name = 'size_bytes'"
            ).fetchall()

            if not result:
                # Add new columns if they don't exist
                try:
                    conn.execute("ALTER TABLE nodes_file ADD COLUMN size_bytes INTEGER")
                except Exception:
                    pass  # Column may already exist

                try:
                    conn.execute("ALTER TABLE nodes_file ADD COLUMN language VARCHAR")
                except Exception:
                    pass  # Column may already exist

                # Rename code to content if needed
                try:
                    conn.execute("ALTER TABLE nodes_file RENAME COLUMN code TO content")
                except Exception:
                    pass  # Column may already be named content

        except Exception as e:
            logger.debug(f"Schema check: {e}")

    def _get_files_needing_content(self, conn) -> List[tuple]:
        """Get files from nodes_file that need content."""
        try:
            # Try with content column
            result = conn.execute("""
                SELECT id, name FROM nodes_file
                WHERE content IS NULL OR content = ''
            """).fetchall()
            return result
        except Exception:
            try:
                # Fallback to code column (old schema)
                result = conn.execute("""
                    SELECT id, name FROM nodes_file
                    WHERE code IS NULL OR code = ''
                """).fetchall()
                return result
            except Exception:
                return []

    def _scan_and_insert_files(self, conn, source_path: Path) -> List[tuple]:
        """Scan source directory and insert files into nodes_file."""
        files = []
        file_id = 1

        # Get max existing id
        try:
            result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM nodes_file").fetchone()
            file_id = (result[0] or 0) + 1
        except Exception:
            pass

        for ext in LANGUAGE_EXTENSIONS.keys():
            for file_path in source_path.rglob(f"*{ext}"):
                try:
                    if file_path.stat().st_size <= MAX_FILE_SIZE:
                        rel_path = str(file_path.relative_to(source_path))
                        conn.execute("""
                            INSERT OR IGNORE INTO nodes_file (id, name, hash, content)
                            VALUES (?, ?, '', '')
                        """, [file_id, rel_path])
                        files.append((file_id, rel_path))
                        file_id += 1
                except Exception:
                    continue

        logger.info(f"Scanned {len(files)} files from source directory")
        return files

    def _find_file(self, source_path: Path, file_name: str) -> Optional[Path]:
        """Find file in source_path by name."""
        if not file_name:
            return None

        # Strip leading slashes
        file_name = file_name.lstrip('/\\')

        # Try direct path first
        direct_path = source_path / file_name
        if direct_path.exists():
            return direct_path

        # Try searching by filename only
        base_name = Path(file_name).name
        for match in source_path.rglob(base_name):
            if match.is_file():
                return match

        return None

    def _detect_language(self, suffix: str) -> str:
        """Detect programming language from file extension."""
        return LANGUAGE_EXTENSIONS.get(suffix.lower(), 'unknown')

    def _normalize_paths(self, conn) -> None:
        """Normalize file paths for JOIN compatibility with nodes_method.

        Joern exports method filenames without common prefixes like 'src/'.
        This method strips such prefixes from nodes_file.name to enable
        direct JOINs between nodes_method.filename and nodes_file.name.
        """
        # Common prefixes that Joern strips from method filenames
        prefixes_to_strip = ['src/', 'src\\\\', 'source/', 'source\\\\']

        for prefix in prefixes_to_strip:
            try:
                # Count files with this prefix
                like_pattern = prefix.replace('\\\\', '\\') + '%'
                result = conn.execute(
                    "SELECT COUNT(*) FROM nodes_file WHERE name LIKE ?",
                    [like_pattern]
                ).fetchone()

                if result and result[0] > 0:
                    prefix_len = len(prefix.replace('\\\\', '\\'))
                    conn.execute(
                        f"UPDATE nodes_file SET name = SUBSTRING(name, {prefix_len + 1}) "
                        f"WHERE name LIKE ?",
                        [like_pattern]
                    )
                    logger.info(f"Normalized {result[0]} paths by stripping '{prefix}' prefix")

            except Exception as e:
                logger.debug(f"Path normalization for prefix '{prefix}': {e}")

        conn.commit()

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.debug(f"Source content step: {progress}% - {message}")
