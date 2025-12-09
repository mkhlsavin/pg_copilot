"""
ChromaDB Import Step.

Imports documentation and comments into ChromaDB.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class ChromaDBImportStep:
    """Step for importing documentation into ChromaDB."""

    # README file patterns to look for
    README_PATTERNS = [
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "Readme.md",
    ]

    # Documentation directories to scan
    DOC_DIRS = ["docs", "doc", "documentation", "wiki", "manual"]

    # Documentation file extensions
    DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".asciidoc"}

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize ChromaDB import step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute documentation import to ChromaDB.

        Args:
            context: Pipeline context with source_path and duckdb_path.

        Returns:
            Dictionary with chromadb_stats and chromadb_collection.
        """
        request = context["request"]
        source_path = Path(context["source_path"])
        duckdb_path = context.get("duckdb_path")

        stats = {
            "readme_indexed": 0,
            "docs_indexed": 0,
            "comments_indexed": 0,
        }

        # Create collection name based on project
        project_name = source_path.name.replace("-", "_").replace(".", "_").lower()
        collection_name = f"{project_name}_documentation"

        self._report_progress(5, "Initializing ChromaDB...")

        # Try to import ChromaDB store
        try:
            from src.retrieval.doc_vector_store import DocumentationVectorStore

            store = DocumentationVectorStore(
                persist_directory="chromadb_storage",
                collection_name=collection_name,
            )
        except ImportError:
            logger.warning("DocumentationVectorStore not available, using basic store")
            store = self._create_basic_store(collection_name)

        # Import README files
        if request.import_readme:
            self._report_progress(15, "Indexing README files...")
            stats["readme_indexed"] = await self._index_readme_files(
                store, source_path
            )

        # Import documentation files
        if request.import_docs:
            self._report_progress(40, "Indexing documentation...")
            stats["docs_indexed"] = await self._index_doc_files(store, source_path)

        # Import comments from CPG
        if request.import_comments and duckdb_path:
            self._report_progress(70, "Indexing code comments...")
            stats["comments_indexed"] = await self._index_comments_from_cpg(
                store, duckdb_path
            )

        self._report_progress(100, "Documentation import completed")

        logger.info(f"ChromaDB import stats: {stats}")

        return {
            "chromadb_stats": stats,
            "chromadb_collection": collection_name,
        }

    async def _index_readme_files(self, store, source_path: Path) -> int:
        """Index README files from the repository."""
        indexed = 0

        for pattern in self.README_PATTERNS:
            for readme_path in source_path.rglob(pattern):
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="ignore")

                    if len(content.strip()) < 10:
                        continue  # Skip empty files

                    # Create document
                    doc = {
                        "id": f"readme_{readme_path.relative_to(source_path)}",
                        "text": content[:10000],  # Limit size
                        "metadata": {
                            "doc_type": "readme",
                            "file_path": str(readme_path.relative_to(source_path)),
                            "title": readme_path.name,
                            "source": "readme",
                        },
                    }

                    self._add_document(store, doc)
                    indexed += 1
                    logger.debug(f"Indexed README: {readme_path}")

                except Exception as e:
                    logger.warning(f"Failed to index {readme_path}: {e}")

        return indexed

    async def _index_doc_files(self, store, source_path: Path) -> int:
        """Index documentation files from docs directories."""
        indexed = 0

        for doc_dir in self.DOC_DIRS:
            doc_path = source_path / doc_dir
            if not doc_path.exists():
                continue

            for file_path in doc_path.rglob("*"):
                if file_path.suffix.lower() not in self.DOC_EXTENSIONS:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    if len(content.strip()) < 10:
                        continue

                    # Extract title from content or filename
                    title = self._extract_title(content, file_path.stem)

                    doc = {
                        "id": f"doc_{file_path.relative_to(source_path)}",
                        "text": content[:10000],
                        "metadata": {
                            "doc_type": "documentation",
                            "file_path": str(file_path.relative_to(source_path)),
                            "title": title,
                            "source": "docs",
                        },
                    }

                    self._add_document(store, doc)
                    indexed += 1
                    logger.debug(f"Indexed doc: {file_path}")

                except Exception as e:
                    logger.warning(f"Failed to index {file_path}: {e}")

        return indexed

    async def _index_comments_from_cpg(self, store, duckdb_path: str) -> int:
        """Index code comments from the CPG (DuckDB)."""
        indexed = 0

        try:
            conn = duckdb.connect(duckdb_path, read_only=True)

            # Check if comments table exists
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            if "nodes_comment" not in table_names:
                logger.info("No comments table found in CPG")
                conn.close()
                return 0

            # Get comments
            comments = conn.execute("""
                SELECT id, code, filename, line_number
                FROM nodes_comment
                WHERE code IS NOT NULL AND LENGTH(code) > 20
                ORDER BY LENGTH(code) DESC
                LIMIT 5000
            """).fetchall()

            conn.close()

            for comment_id, code, filename, line_number in comments:
                try:
                    # Clean up comment
                    clean_code = self._clean_comment(code)
                    if len(clean_code) < 20:
                        continue

                    doc = {
                        "id": f"comment_{comment_id}",
                        "text": clean_code[:2000],
                        "metadata": {
                            "doc_type": "comment",
                            "file_path": filename or "unknown",
                            "line_number": line_number or 0,
                            "source": "cpg_comment",
                        },
                    }

                    self._add_document(store, doc)
                    indexed += 1

                except Exception as e:
                    logger.debug(f"Failed to index comment {comment_id}: {e}")

        except Exception as e:
            logger.warning(f"Failed to index comments from CPG: {e}")

        return indexed

    def _add_document(self, store, doc: Dict[str, Any]) -> None:
        """Add document to store (handles different store interfaces)."""
        try:
            if hasattr(store, "_add_documents"):
                store._add_documents([doc])
            elif hasattr(store, "add_documents"):
                store.add_documents([doc])
            elif hasattr(store, "add"):
                store.add(
                    ids=[doc["id"]],
                    documents=[doc["text"]],
                    metadatas=[doc.get("metadata", {})],
                )
        except Exception as e:
            logger.debug(f"Failed to add document: {e}")

    def _create_basic_store(self, collection_name: str):
        """Create a basic ChromaDB store if DocumentationVectorStore is not available."""
        try:
            import chromadb

            client = chromadb.PersistentClient(path="chromadb_storage")
            collection = client.get_or_create_collection(name=collection_name)
            return collection
        except ImportError:
            logger.error("ChromaDB not installed")
            return None

    def _extract_title(self, content: str, default: str) -> str:
        """Extract title from markdown/rst content."""
        lines = content.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            # Markdown heading
            if line.startswith("#"):
                return line.lstrip("#").strip()
            # RST heading (followed by === or ---)
            if len(line) > 0 and not line.startswith(("=", "-", "~")):
                return line

        return default

    def _clean_comment(self, code: str) -> str:
        """Clean up comment text."""
        # Remove common comment markers
        code = code.strip()

        # Remove C-style comment markers
        if code.startswith("/*"):
            code = code[2:]
        if code.endswith("*/"):
            code = code[:-2]
        if code.startswith("//"):
            code = code[2:]

        # Remove leading asterisks from multi-line comments
        lines = code.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"ChromaDB import step: {progress}% - {message}")
