"""
Project Manager for RAG-CPGQL Copilot

Manages multiple CPG projects, allowing switching between different codebases
(e.g., PostgreSQL, FSIN Module, etc.)
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

from src.config import get_joern_cpg_path, get_joern_source_path

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """Represents a CPG project configuration."""
    name: str
    db_path: str
    cpg_path: str
    language: str
    description: str
    source_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def exists(self) -> bool:
        """Check if the project's DuckDB file exists."""
        return Path(self.db_path).exists()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "db_path": self.db_path,
            "cpg_path": self.cpg_path,
            "language": self.language,
            "description": self.description,
            "source_path": self.source_path,
            **self.metadata
        }


class ProjectManager:
    """
    Manages CPG projects for the RAG-CPGQL copilot.

    Provides functionality to:
    - List available projects
    - Switch between projects
    - Add new projects
    - Get the currently active project
    """

    def __init__(self, config_path: str = "projects.yaml"):
        """
        Initialize ProjectManager.

        Args:
            config_path: Path to the projects.yaml configuration file
        """
        self.config_path = Path(config_path)
        self._projects: Dict[str, Project] = {}
        self._active_project: Optional[str] = None
        self._callbacks: List[callable] = []

        self._load_config()

    def _load_config(self) -> None:
        """Load projects configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Projects config not found at {self.config_path}, creating default")
            self._create_default_config()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning("Empty projects config, creating default")
                self._create_default_config()
                return

            # Load projects
            projects_config = config.get('projects', {})
            for name, proj_config in projects_config.items():
                self._projects[name] = Project(
                    name=name,
                    db_path=proj_config.get('db_path', ''),
                    cpg_path=proj_config.get('cpg_path', ''),
                    language=proj_config.get('language', 'unknown'),
                    description=proj_config.get('description', ''),
                    source_path=proj_config.get('source_path'),
                    metadata={k: v for k, v in proj_config.items()
                             if k not in ('db_path', 'cpg_path', 'language', 'description', 'source_path')}
                )

            # Load active project
            self._active_project = config.get('active_project')
            if self._active_project and self._active_project not in self._projects:
                logger.warning(f"Active project '{self._active_project}' not found, using first available")
                self._active_project = next(iter(self._projects.keys()), None)

            logger.info(f"Loaded {len(self._projects)} projects, active: {self._active_project}")

        except Exception as e:
            logger.error(f"Failed to load projects config: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default configuration with PostgreSQL project.

        Uses JOERN_CPG_PATH and JOERN_SOURCE_PATH env vars or config.yaml.
        """
        cpg_path = get_joern_cpg_path()
        source_path = get_joern_source_path()

        self._projects = {
            "postgresql": Project(
                name="postgresql",
                db_path="cpg.duckdb",
                cpg_path=str(cpg_path) if cpg_path else "workspace/pg17_full.cpg",
                language="c",
                description="PostgreSQL 17 Source Code",
                source_path=str(source_path) if source_path else None
            )
        }
        self._active_project = "postgresql"
        self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to YAML file."""
        config = {
            "projects": {name: proj.to_dict() for name, proj in self._projects.items()},
            "active_project": self._active_project
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Saved projects config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save projects config: {e}")

    def list_projects(self) -> List[Project]:
        """
        Get list of all available projects.

        Returns:
            List of Project objects
        """
        return list(self._projects.values())

    def get_project(self, name: str) -> Optional[Project]:
        """
        Get a specific project by name.

        Args:
            name: Project name

        Returns:
            Project object or None if not found
        """
        return self._projects.get(name)

    def get_active_project(self) -> Optional[Project]:
        """
        Get the currently active project.

        Returns:
            Active Project object or None
        """
        if self._active_project:
            return self._projects.get(self._active_project)
        return None

    def get_active_db_path(self) -> str:
        """
        Get the database path of the active project.

        Returns:
            Path to DuckDB file, defaults to 'cpg.duckdb'
        """
        project = self.get_active_project()
        if project:
            return project.db_path
        return "cpg.duckdb"

    def switch_project(self, name: str) -> bool:
        """
        Switch to a different project.

        Args:
            name: Name of the project to switch to

        Returns:
            True if switch was successful, False otherwise
        """
        if name not in self._projects:
            logger.error(f"Project '{name}' not found")
            return False

        project = self._projects[name]
        if not project.exists():
            logger.warning(f"Project '{name}' DuckDB file does not exist at {project.db_path}")
            # Still allow switching, but warn user

        old_project = self._active_project
        self._active_project = name
        self._save_config()

        logger.info(f"Switched project: {old_project} -> {name}")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(old_project, name, project)
            except Exception as e:
                logger.error(f"Callback error during project switch: {e}")

        return True

    def add_project(
        self,
        name: str,
        db_path: str,
        language: str,
        description: str,
        cpg_path: str = "",
        source_path: Optional[str] = None,
        switch_to: bool = False
    ) -> bool:
        """
        Add a new project to the configuration.

        Args:
            name: Unique project name
            db_path: Path to the DuckDB file
            language: Programming language (c, python, java, etc.)
            description: Human-readable description
            cpg_path: Path to the CPG file (optional)
            source_path: Path to source code (optional)
            switch_to: Whether to switch to this project after adding

        Returns:
            True if project was added successfully
        """
        if name in self._projects:
            logger.error(f"Project '{name}' already exists")
            return False

        self._projects[name] = Project(
            name=name,
            db_path=db_path,
            cpg_path=cpg_path,
            language=language,
            description=description,
            source_path=source_path
        )
        self._save_config()

        logger.info(f"Added project: {name} ({language}) - {description}")

        if switch_to:
            return self.switch_project(name)
        return True

    def remove_project(self, name: str) -> bool:
        """
        Remove a project from the configuration.

        Args:
            name: Name of the project to remove

        Returns:
            True if project was removed successfully
        """
        if name not in self._projects:
            logger.error(f"Project '{name}' not found")
            return False

        if self._active_project == name:
            logger.error(f"Cannot remove active project '{name}'")
            return False

        del self._projects[name]
        self._save_config()

        logger.info(f"Removed project: {name}")
        return True

    def on_project_switch(self, callback: callable) -> None:
        """
        Register a callback to be called when project is switched.

        Callback signature: callback(old_project: str, new_project: str, project: Project)

        Args:
            callback: Function to call on project switch
        """
        self._callbacks.append(callback)

    def format_project_list(self) -> str:
        """
        Format projects list for display.

        Returns:
            Formatted string listing all projects
        """
        lines = ["Available projects:"]

        for name, project in self._projects.items():
            marker = "*" if name == self._active_project else " "
            status = "[OK]" if project.exists() else "[MISSING]"
            lines.append(f"  {marker} {name:<20} {status:<10} {project.db_path:<40} {project.description}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ProjectManager(projects={len(self._projects)}, active={self._active_project})"


# Global singleton instance
_project_manager: Optional[ProjectManager] = None


def get_project_manager(config_path: str = "projects.yaml") -> ProjectManager:
    """
    Get the global ProjectManager singleton.

    Args:
        config_path: Path to projects.yaml (only used on first call)

    Returns:
        ProjectManager instance
    """
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(config_path)
    return _project_manager


def reset_project_manager() -> None:
    """Reset the global ProjectManager singleton (for testing)."""
    global _project_manager
    _project_manager = None
