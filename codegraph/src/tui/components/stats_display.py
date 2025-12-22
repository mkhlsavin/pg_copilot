"""Statistics display component for CPG and ChromaDB data."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DUCKDB_PATH = Path("cpg.duckdb")
DEFAULT_CHROMADB_PATH = Path("chromadb_storage")


@dataclass
class CPGStats:
    """CPG statistics from DuckDB."""

    # Node counts
    method_count: int = 0
    call_node_count: int = 0
    identifier_count: int = 0
    literal_count: int = 0
    local_count: int = 0
    param_count: int = 0
    return_count: int = 0
    block_count: int = 0
    control_structure_count: int = 0
    type_decl_count: int = 0

    # Edge counts
    ast_edge_count: int = 0
    cfg_edge_count: int = 0
    call_edge_count: int = 0
    ref_edge_count: int = 0
    reaching_def_edge_count: int = 0
    argument_edge_count: int = 0
    receiver_edge_count: int = 0
    condition_edge_count: int = 0


@dataclass
class ChromaDBStats:
    """ChromaDB collection statistics."""

    code_documentation_count: int = 0
    qa_pairs_count: int = 0
    cpgql_examples_count: int = 0


@dataclass
class SystemStats:
    """Combined system statistics."""

    cpg_stats: Optional[CPGStats] = None
    chromadb_stats: Optional[ChromaDBStats] = None
    db_path: str = ""
    db_size_mb: float = 0.0
    chromadb_path: str = ""
    cpg_available: bool = False
    chromadb_available: bool = False
    error_messages: Dict[str, str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = {}


class StatsDisplay:
    """
    Component to collect and display system statistics.

    Shows CPG database statistics (node/edge counts)
    and ChromaDB collection statistics.
    """

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        duckdb_path: Optional[Path] = None,
        chromadb_path: Optional[Path] = None,
    ):
        """
        Initialize stats display.

        Args:
            theme: Color theme
            duckdb_path: Path to DuckDB database
            chromadb_path: Path to ChromaDB storage
        """
        self.theme = theme
        self.duckdb_path = duckdb_path or DEFAULT_DUCKDB_PATH
        self.chromadb_path = chromadb_path or DEFAULT_CHROMADB_PATH

    def collect_stats(self) -> SystemStats:
        """
        Collect statistics from all data sources.

        Returns:
            SystemStats with all collected statistics
        """
        stats = SystemStats(
            db_path=str(self.duckdb_path),
            chromadb_path=str(self.chromadb_path),
        )

        # Get DuckDB stats
        self._collect_cpg_stats(stats)

        # Get ChromaDB stats
        self._collect_chromadb_stats(stats)

        return stats

    def _collect_cpg_stats(self, stats: SystemStats):
        """Collect CPG statistics from DuckDB."""
        try:
            # Check if file exists
            if not self.duckdb_path.exists():
                stats.error_messages["cpg"] = f"Database not found: {self.duckdb_path}"
                return

            # Get file size
            stats.db_size_mb = self.duckdb_path.stat().st_size / (1024 * 1024)

            # Import and use DuckDB client
            try:
                from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

                with DuckDBCPGClient(str(self.duckdb_path)) as client:
                    cpg_statistics = client.get_statistics()

                    stats.cpg_stats = CPGStats(
                        method_count=cpg_statistics.method_count,
                        call_node_count=cpg_statistics.call_node_count,
                        identifier_count=cpg_statistics.identifier_count,
                        literal_count=cpg_statistics.literal_count,
                        local_count=cpg_statistics.local_count,
                        param_count=cpg_statistics.param_count,
                        return_count=cpg_statistics.return_count,
                        block_count=cpg_statistics.block_count,
                        control_structure_count=cpg_statistics.control_structure_count,
                        type_decl_count=cpg_statistics.type_decl_count,
                        ast_edge_count=cpg_statistics.ast_edge_count,
                        cfg_edge_count=cpg_statistics.cfg_edge_count,
                        call_edge_count=cpg_statistics.call_edge_count,
                        ref_edge_count=cpg_statistics.ref_edge_count,
                        reaching_def_edge_count=cpg_statistics.reaching_def_edge_count,
                        argument_edge_count=cpg_statistics.argument_edge_count,
                        receiver_edge_count=cpg_statistics.receiver_edge_count,
                        condition_edge_count=cpg_statistics.condition_edge_count,
                    )
                    stats.cpg_available = True

            except ImportError as e:
                stats.error_messages["cpg"] = f"DuckDB client not available: {e}"

        except Exception as e:
            logger.error(f"Failed to collect CPG stats: {e}")
            stats.error_messages["cpg"] = str(e)

    def _collect_chromadb_stats(self, stats: SystemStats):
        """Collect ChromaDB collection statistics."""
        try:
            # Check if directory exists
            if not self.chromadb_path.exists():
                stats.error_messages["chromadb"] = f"Storage not found: {self.chromadb_path}"
                return

            chroma_stats = ChromaDBStats()

            # Try to get documentation store stats
            try:
                from src.retrieval.doc_vector_store import DocumentationVectorStore

                doc_store = DocumentationVectorStore(
                    persist_directory=str(self.chromadb_path)
                )
                doc_stats = doc_store.get_stats()
                chroma_stats.code_documentation_count = doc_stats.get("total_documents", 0)

            except ImportError:
                logger.debug("DocumentationVectorStore not available")
            except Exception as e:
                logger.debug(f"Could not get doc store stats: {e}")

            # Try to get QA/CPGQL store stats
            try:
                from src.retrieval.vector_store_real import VectorStoreReal

                vector_store = VectorStoreReal()
                vector_stats = vector_store.get_stats()
                chroma_stats.qa_pairs_count = vector_stats.get("qa_pairs_count", 0)
                chroma_stats.cpgql_examples_count = vector_stats.get("cpgql_examples_count", 0)

            except ImportError:
                logger.debug("VectorStoreReal not available")
            except Exception as e:
                logger.debug(f"Could not get vector store stats: {e}")

            stats.chromadb_stats = chroma_stats
            stats.chromadb_available = True

        except Exception as e:
            logger.error(f"Failed to collect ChromaDB stats: {e}")
            stats.error_messages["chromadb"] = str(e)

    def render(self, stats: SystemStats) -> Panel:
        """
        Render statistics as Rich panel.

        Args:
            stats: SystemStats to render

        Returns:
            Rich Panel with statistics tables
        """
        panels = []

        # CPG Statistics panel
        panels.append(self._render_cpg_panel(stats))

        # ChromaDB Statistics panel
        panels.append(self._render_chromadb_panel(stats))

        return Panel(
            Group(*panels),
            title="[bold]System Statistics[/bold]",
            border_style=self.theme.border,
        )

    def _render_cpg_panel(self, stats: SystemStats) -> Panel:
        """Render CPG statistics panel."""
        if not stats.cpg_available:
            error_msg = stats.error_messages.get("cpg", "CPG data not available")
            return Panel(
                f"[red]{error_msg}[/red]",
                title="[bold cyan]CPG Database[/bold cyan]",
                border_style="red",
            )

        cpg = stats.cpg_stats

        # Create two-column layout: Nodes and Edges
        nodes_table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            box=None,
        )
        nodes_table.add_column("Node Type", style="cyan")
        nodes_table.add_column("Count", justify="right")

        nodes_table.add_row("Methods", f"{cpg.method_count:,}")
        nodes_table.add_row("Calls", f"{cpg.call_node_count:,}")
        nodes_table.add_row("Identifiers", f"{cpg.identifier_count:,}")
        nodes_table.add_row("Literals", f"{cpg.literal_count:,}")
        nodes_table.add_row("Locals", f"{cpg.local_count:,}")
        nodes_table.add_row("Parameters", f"{cpg.param_count:,}")
        nodes_table.add_row("Returns", f"{cpg.return_count:,}")
        nodes_table.add_row("Blocks", f"{cpg.block_count:,}")
        nodes_table.add_row("ControlStruct", f"{cpg.control_structure_count:,}")
        nodes_table.add_row("TypeDecls", f"{cpg.type_decl_count:,}")

        edges_table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            box=None,
        )
        edges_table.add_column("Edge Type", style="yellow")
        edges_table.add_column("Count", justify="right")

        edges_table.add_row("AST", f"{cpg.ast_edge_count:,}")
        edges_table.add_row("CFG", f"{cpg.cfg_edge_count:,}")
        edges_table.add_row("CALL", f"{cpg.call_edge_count:,}")
        edges_table.add_row("REF", f"{cpg.ref_edge_count:,}")
        edges_table.add_row("REACHING_DEF", f"{cpg.reaching_def_edge_count:,}")
        edges_table.add_row("ARGUMENT", f"{cpg.argument_edge_count:,}")
        edges_table.add_row("RECEIVER", f"{cpg.receiver_edge_count:,}")
        edges_table.add_row("CONDITION", f"{cpg.condition_edge_count:,}")

        # Combine in columns
        columns = Columns([
            Panel(nodes_table, title="[bold]NODES[/bold]", border_style="dim"),
            Panel(edges_table, title="[bold]EDGES[/bold]", border_style="dim"),
        ])

        # Header with file info
        header = Text()
        header.append(f"Database: {stats.db_path}", style="dim")
        header.append(f" ({stats.db_size_mb:.1f} MB)\n", style="dim")

        return Panel(
            Group(header, columns),
            title="[bold cyan]CPG Database[/bold cyan]",
            border_style=self.theme.border,
        )

    def _render_chromadb_panel(self, stats: SystemStats) -> Panel:
        """Render ChromaDB statistics panel."""
        if not stats.chromadb_available:
            error_msg = stats.error_messages.get("chromadb", "ChromaDB not available")
            return Panel(
                f"[yellow]{error_msg}[/yellow]",
                title="[bold green]ChromaDB[/bold green]",
                border_style="yellow",
            )

        chroma = stats.chromadb_stats

        table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            box=None,
        )
        table.add_column("Collection", style="green")
        table.add_column("Documents", justify="right")

        table.add_row("code_documentation", f"{chroma.code_documentation_count:,}")
        table.add_row("qa_pairs", f"{chroma.qa_pairs_count:,}")
        table.add_row("cpgql_examples", f"{chroma.cpgql_examples_count:,}")

        # Header
        header = Text()
        header.append(f"Storage: {stats.chromadb_path}\n", style="dim")

        return Panel(
            Group(header, table),
            title="[bold green]ChromaDB[/bold green]",
            border_style=self.theme.border,
        )
