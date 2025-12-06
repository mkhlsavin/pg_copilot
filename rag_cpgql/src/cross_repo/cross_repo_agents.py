"""
Cross-Repository Analysis Agents - Scenario 10

Three specialized agents for multi-repository analysis:
1. RepositoryIndexer: Index and catalog repositories
2. CrossRepoAnalyzer: Detect code duplication across repos
3. DependencyMapper: Map inter-repository dependencies

Author: Cross-Repository Analysis Team
Date: 2025-11-23
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import logging

from .repo_patterns import (
    RepositoryInfo,
    CodeInstance,
    CodeDuplication,
    DependencyCall,
    CrossRepoDependency,
    ConsolidationOpportunity,
    ConsolidationReport,
    DuplicationSeverity,
    DependencyType,
    RiskLevel,
    DUPLICATION_PATTERNS,
    DEPENDENCY_PATTERNS,
    calculate_similarity,
    classify_duplication_severity,
    calculate_coupling_score,
    classify_risk_level,
)

logger = logging.getLogger(__name__)


# ============================================================================
# AGENT 1: REPOSITORY INDEXER
# ============================================================================

class RepositoryIndexer:
    """
    Index and catalog multiple repositories.

    Capabilities:
    - Discover repositories in workspace
    - Extract repository metadata
    - Build unified index
    - Track repository relationships
    """

    def __init__(self, cpg_service=None):
        """Initialize repository indexer"""
        self.cpg = cpg_service
        self.indexed_repos: Dict[str, RepositoryInfo] = {}

    def discover_repositories(self, workspace_path: str) -> List[RepositoryInfo]:
        """
        Discover repositories in workspace directory.

        Args:
            workspace_path: Root directory to search

        Returns:
            List of discovered repository information
        """
        logger.info(f"Discovering repositories in {workspace_path}")

        repos = []
        workspace = Path(workspace_path)

        if not workspace.exists():
            logger.warning(f"Workspace path does not exist: {workspace_path}")
            return repos

        # Look for git repositories
        for item in workspace.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it's a git repo
                git_dir = item / '.git'
                if git_dir.exists():
                    repo_info = self._extract_repo_metadata(item)
                    repos.append(repo_info)
                    self.indexed_repos[repo_info.repo_id] = repo_info

        logger.info(f"Discovered {len(repos)} repositories")
        return repos

    def _extract_repo_metadata(self, repo_path: Path) -> RepositoryInfo:
        """Extract metadata from repository"""
        repo_name = repo_path.name
        repo_id = f"repo-{repo_name.lower().replace(' ', '-')}"

        # Count files by extension
        file_count = 0
        language_counts = defaultdict(int)
        subsystems = set()

        for file in repo_path.rglob('*'):
            if file.is_file() and not self._should_ignore(file):
                file_count += 1
                ext = file.suffix.lower()
                language_counts[ext] += 1

                # Extract subsystems (top-level dirs)
                relative = file.relative_to(repo_path)
                if len(relative.parts) > 1:
                    subsystems.add(relative.parts[0])

        # Determine primary language
        primary_language = self._determine_language(language_counts)

        return RepositoryInfo(
            repo_id=repo_id,
            name=repo_name,
            path=str(repo_path),
            language=primary_language,
            file_count=file_count,
            primary_subsystems=list(subsystems)[:10],  # Top 10
            metadata={
                'language_distribution': dict(language_counts),
            }
        )

    def index_repository_cpg(self, repo_info: RepositoryInfo) -> RepositoryInfo:
        """
        Index repository into CPG database.

        Args:
            repo_info: Repository to index

        Returns:
            Updated repository info with CPG statistics
        """
        if not self.cpg:
            logger.warning("No CPG service available")
            return repo_info

        try:
            # Query method count from CPG
            # In real implementation, this would filter by repository
            query = """
                SELECT COUNT(*) as method_count
                FROM nodes_method
                WHERE filename LIKE ?
            """
            result = self.cpg.execute_custom_sql(
                query,
                (f"{repo_info.name}%",)
            )

            if result:
                repo_info.method_count = result[0].get('method_count', 0)

            # Query total lines (estimated from methods)
            line_query = """
                SELECT SUM(
                    CAST(line_number_end AS INTEGER) -
                    CAST(line_number AS INTEGER)
                ) as total_lines
                FROM nodes_method
                WHERE filename LIKE ?
            """
            line_result = self.cpg.execute_custom_sql(
                line_query,
                (f"{repo_info.name}%",)
            )

            if line_result:
                repo_info.line_count = line_result[0].get('total_lines', 0) or 0

            repo_info.cpg_indexed = True
            logger.info(f"Indexed {repo_info.name}: {repo_info.method_count} methods")

        except Exception as e:
            logger.error(f"Error indexing repository {repo_info.name}: {e}")

        return repo_info

    def _should_ignore(self, file: Path) -> bool:
        """Check if file should be ignored"""
        ignore_patterns = [
            '.git', '__pycache__', 'node_modules', '.venv',
            'venv', 'build', 'dist', '.pytest_cache'
        ]
        return any(pattern in str(file) for pattern in ignore_patterns)

    def _determine_language(self, language_counts: Dict[str, int]) -> str:
        """Determine primary programming language"""
        ext_to_lang = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
        }

        if not language_counts:
            return 'Unknown'

        # Find most common extension
        most_common_ext = max(language_counts, key=language_counts.get)
        return ext_to_lang.get(most_common_ext, 'Unknown')

    def get_repository_summary(self) -> Dict[str, Any]:
        """Get summary of all indexed repositories"""
        return {
            'total_repos': len(self.indexed_repos),
            'total_files': sum(r.file_count for r in self.indexed_repos.values()),
            'total_methods': sum(r.method_count for r in self.indexed_repos.values()),
            'languages': list(set(r.language for r in self.indexed_repos.values())),
            'repositories': [
                {
                    'id': r.repo_id,
                    'name': r.name,
                    'language': r.language,
                    'methods': r.method_count,
                    'files': r.file_count,
                }
                for r in self.indexed_repos.values()
            ]
        }


# ============================================================================
# AGENT 2: CROSS-REPO ANALYZER
# ============================================================================

class CrossRepoAnalyzer:
    """
    Detect code duplication across repositories.

    Capabilities:
    - Find duplicate code across repos
    - Calculate similarity scores
    - Identify consolidation opportunities
    - Suggest shared libraries
    """

    def __init__(self, cpg_service=None):
        """Initialize cross-repo analyzer"""
        self.cpg = cpg_service

    def find_code_duplications(
        self,
        repositories: List[RepositoryInfo],
        min_similarity: float = 70.0,
        min_lines: int = 10
    ) -> List[CodeDuplication]:
        """
        Find code duplications across repositories.

        Args:
            repositories: List of repositories to analyze
            min_similarity: Minimum similarity threshold (0-100)
            min_lines: Minimum number of lines to consider

        Returns:
            List of detected code duplications
        """
        logger.info(f"Analyzing {len(repositories)} repositories for duplications")

        duplications = []

        # Get all methods from all repositories
        all_methods = []
        for repo in repositories:
            methods = self._get_repo_methods(repo)
            all_methods.extend([(repo, method) for method in methods])

        # Compare methods pairwise (from different repos)
        for i, (repo1, method1) in enumerate(all_methods):
            for repo2, method2 in all_methods[i+1:]:
                # Only compare across different repos
                if repo1.repo_id == repo2.repo_id:
                    continue

                # Calculate similarity
                similarity = calculate_similarity(
                    method1.get('code', ''),
                    method2.get('code', '')
                )

                if similarity >= min_similarity:
                    line_count = method1.get('line_count', 0)

                    if line_count >= min_lines:
                        duplication = self._create_duplication_finding(
                            repo1, method1,
                            repo2, method2,
                            similarity
                        )
                        duplications.append(duplication)

        logger.info(f"Found {len(duplications)} code duplications")
        return duplications

    def find_similar_utilities(
        self,
        repositories: List[RepositoryInfo]
    ) -> List[CodeDuplication]:
        """
        Find similar utility functions across repositories.

        Args:
            repositories: List of repositories

        Returns:
            List of similar utility functions
        """
        # Focus on common utility names
        utility_patterns = [
            'format', 'parse', 'validate', 'sanitize',
            'convert', 'transform', 'hash', 'encode',
            'decode', 'escape', 'unescape'
        ]

        duplications = []

        for pattern in utility_patterns:
            methods_by_repo = {}

            for repo in repositories:
                methods = self._find_methods_by_name_pattern(repo, pattern)
                if methods:
                    methods_by_repo[repo.repo_id] = (repo, methods)

            # If found in multiple repos, compare them
            if len(methods_by_repo) >= 2:
                repos = list(methods_by_repo.values())
                for i, (repo1, methods1) in enumerate(repos):
                    for repo2, methods2 in repos[i+1:]:
                        for m1 in methods1:
                            for m2 in methods2:
                                similarity = calculate_similarity(
                                    m1.get('code', ''),
                                    m2.get('code', '')
                                )

                                if similarity >= 70.0:
                                    dup = self._create_duplication_finding(
                                        repo1, m1, repo2, m2, similarity
                                    )
                                    duplications.append(dup)

        return duplications

    def identify_consolidation_opportunities(
        self,
        duplications: List[CodeDuplication]
    ) -> List[ConsolidationOpportunity]:
        """
        Identify opportunities to consolidate code.

        Args:
            duplications: List of detected duplications

        Returns:
            List of consolidation opportunities
        """
        opportunities = []

        # Group duplications by pattern name
        grouped = defaultdict(list)
        for dup in duplications:
            grouped[dup.pattern_name].append(dup)

        # Create opportunities for each group
        for pattern_name, dups in grouped.items():
            if len(dups) < 2:
                continue

            # Collect affected repos
            affected_repos = set()
            total_savings = 0
            total_instances = 0

            for dup in dups:
                affected_repos.update(inst.repo_id for inst in dup.instances)
                total_savings += dup.potential_savings
                total_instances += len(dup.instances)

            # Estimate effort (base + per repo)
            effort = 4.0 + (len(affected_repos) * 2.0)

            # Calculate priority (1-5, 1=highest)
            if total_savings > 500:
                priority = 1
            elif total_savings > 200:
                priority = 2
            elif total_savings > 100:
                priority = 3
            elif total_savings > 50:
                priority = 4
            else:
                priority = 5

            opportunity = ConsolidationOpportunity(
                opportunity_id=f"consolidate-{pattern_name.lower().replace(' ', '-')}",
                title=f"Consolidate {pattern_name} across {len(affected_repos)} repositories",
                affected_repos=list(affected_repos),
                duplication_count=total_instances,
                estimated_effort=effort,
                estimated_savings=total_savings,
                priority=priority,
                action_plan=f"1. Create shared library for {pattern_name}\n"
                            f"2. Extract common implementation\n"
                            f"3. Update {len(affected_repos)} repositories to use shared library\n"
                            f"4. Remove duplicate code"
            )
            opportunities.append(opportunity)

        # Sort by priority
        opportunities.sort(key=lambda o: (o.priority, -o.estimated_savings))

        return opportunities

    def _get_repo_methods(self, repo: RepositoryInfo) -> List[Dict]:
        """Get all methods from a repository"""
        if not self.cpg:
            return []

        try:
            query = """
                SELECT
                    id,
                    name,
                    filename,
                    line_number,
                    line_number_end,
                    code,
                    signature
                FROM nodes_method
                WHERE filename LIKE ?
                LIMIT 100
            """
            results = self.cpg.execute_custom_sql(query, (f"%{repo.name}%",))

            methods = []
            for row in results:
                methods.append({
                    'id': row.get('id'),
                    'name': row.get('name'),
                    'filename': row.get('filename'),
                    'line_number': row.get('line_number'),
                    'line_number_end': row.get('line_number_end'),
                    'line_count': (row.get('line_number_end', 0) or 0) - (row.get('line_number', 0) or 0),
                    'code': row.get('code', ''),
                    'signature': row.get('signature', ''),
                })

            return methods

        except Exception as e:
            logger.error(f"Error getting methods for {repo.name}: {e}")
            return []

    def _find_methods_by_name_pattern(
        self,
        repo: RepositoryInfo,
        pattern: str
    ) -> List[Dict]:
        """Find methods matching name pattern"""
        if not self.cpg:
            return []

        try:
            query = """
                SELECT
                    id, name, filename, line_number, code, signature
                FROM nodes_method
                WHERE filename LIKE ?
                AND name ILIKE ?
                LIMIT 20
            """
            results = self.cpg.execute_custom_sql(
                query,
                (f"%{repo.name}%", f"%{pattern}%")
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error finding methods: {e}")
            return []

    def _create_duplication_finding(
        self,
        repo1: RepositoryInfo,
        method1: Dict,
        repo2: RepositoryInfo,
        method2: Dict,
        similarity: float
    ) -> CodeDuplication:
        """Create a code duplication finding"""
        instance1 = CodeInstance(
            repo_id=repo1.repo_id,
            file_path=method1.get('filename', ''),
            method_name=method1.get('name', ''),
            start_line=method1.get('line_number', 0),
            end_line=method1.get('line_number_end', 0),
            code_snippet=method1.get('code', '')[:200],
            signature=method1.get('signature', '')
        )

        instance2 = CodeInstance(
            repo_id=repo2.repo_id,
            file_path=method2.get('filename', ''),
            method_name=method2.get('name', ''),
            start_line=method2.get('line_number', 0),
            end_line=method2.get('line_number_end', 0),
            code_snippet=method2.get('code', '')[:200],
            signature=method2.get('signature', '')
        )

        line_count = method1.get('line_count', 0)
        severity = classify_duplication_severity(similarity, line_count)

        return CodeDuplication(
            pattern_id=f"dup-{repo1.repo_id}-{repo2.repo_id}-{method1.get('id')}",
            pattern_name=f"Duplicate {method1.get('name', 'method')}",
            similarity_score=similarity,
            severity=severity,
            instances=[instance1, instance2],
            recommendation=f"Extract to shared library and import in both {repo1.name} and {repo2.name}",
            estimated_consolidation_effort=3.0,
            potential_savings=line_count
        )


# ============================================================================
# AGENT 3: DEPENDENCY MAPPER
# ============================================================================

class DependencyMapper:
    """
    Map inter-repository dependencies.

    Capabilities:
    - Detect API calls between services
    - Map import dependencies
    - Calculate coupling scores
    - Identify coupling hotspots
    - Generate dependency graphs
    """

    def __init__(self, cpg_service=None):
        """Initialize dependency mapper"""
        self.cpg = cpg_service

    def map_dependencies(
        self,
        repositories: List[RepositoryInfo]
    ) -> List[CrossRepoDependency]:
        """
        Map dependencies between repositories.

        Args:
            repositories: List of repositories to analyze

        Returns:
            List of cross-repository dependencies
        """
        logger.info(f"Mapping dependencies across {len(repositories)} repositories")

        dependencies = []

        # For each pair of repos, look for dependencies
        for i, source_repo in enumerate(repositories):
            for target_repo in repositories[i+1:]:
                # Check for API calls
                api_deps = self._find_api_dependencies(source_repo, target_repo)
                dependencies.extend(api_deps)

                # Check for imports
                import_deps = self._find_import_dependencies(source_repo, target_repo)
                dependencies.extend(import_deps)

        logger.info(f"Found {len(dependencies)} cross-repo dependencies")
        return dependencies

    def calculate_coupling_matrix(
        self,
        repositories: List[RepositoryInfo],
        dependencies: List[CrossRepoDependency]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate coupling matrix between all repositories.

        Args:
            repositories: List of repositories
            dependencies: List of dependencies

        Returns:
            Matrix of coupling scores (repo_id -> repo_id -> score)
        """
        matrix = defaultdict(lambda: defaultdict(float))

        for dep in dependencies:
            matrix[dep.source_repo][dep.target_repo] = dep.coupling_score
            # Also add reverse (undirected coupling)
            matrix[dep.target_repo][dep.source_repo] = dep.coupling_score

        return dict(matrix)

    def generate_dependency_graph(
        self,
        dependencies: List[CrossRepoDependency]
    ) -> Dict[str, List[str]]:
        """
        Generate dependency graph.

        Args:
            dependencies: List of dependencies

        Returns:
            Adjacency list (repo_id -> [dependent_repo_ids])
        """
        graph = defaultdict(list)

        for dep in dependencies:
            graph[dep.source_repo].append(dep.target_repo)

        return dict(graph)

    def detect_circular_dependencies(
        self,
        dependency_graph: Dict[str, List[str]]
    ) -> List[List[str]]:
        """
        Detect circular dependencies in the graph.

        Args:
            dependency_graph: Dependency graph

        Returns:
            List of circular dependency cycles
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)

        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _find_api_dependencies(
        self,
        source_repo: RepositoryInfo,
        target_repo: RepositoryInfo
    ) -> List[CrossRepoDependency]:
        """Find API call dependencies between repos"""
        if not self.cpg:
            return []

        dependencies = []

        try:
            # Look for HTTP/API calls that might target the other repo
            # In real implementation, this would parse URLs/endpoints
            query = """
                SELECT
                    m.id,
                    m.name as method_name,
                    m.filename,
                    c.name as call_name,
                    c.code
                FROM nodes_method m
                JOIN nodes_call c ON c.method_inst_id = m.id
                WHERE m.filename LIKE ?
                AND (
                    c.code ILIKE '%requests.get%' OR
                    c.code ILIKE '%requests.post%' OR
                    c.code ILIKE '%http%' OR
                    c.code ILIKE '%api%'
                )
                AND c.code ILIKE ?
                LIMIT 10
            """

            results = self.cpg.execute_custom_sql(
                query,
                (f"%{source_repo.name}%", f"%{target_repo.name}%")
            )

            if results:
                calls = []
                for row in results:
                    call = DependencyCall(
                        source_method=row.get('method_name', ''),
                        source_file=row.get('filename', ''),
                        target_endpoint=f"{target_repo.name} API",
                        call_code=row.get('code', '')[:100]
                    )
                    calls.append(call)

                # Calculate coupling
                total_methods = source_repo.method_count + target_repo.method_count
                coupling = calculate_coupling_score(len(calls), total_methods)
                risk = classify_risk_level(coupling, DependencyType.API_CALL)

                dependency = CrossRepoDependency(
                    dependency_id=f"dep-{source_repo.repo_id}-{target_repo.repo_id}-api",
                    source_repo=source_repo.repo_id,
                    target_repo=target_repo.repo_id,
                    dependency_type=DependencyType.API_CALL,
                    coupling_score=coupling,
                    risk_level=risk,
                    calls=calls,
                    mitigation="Consider using message queue for loose coupling"
                )
                dependencies.append(dependency)

        except Exception as e:
            logger.error(f"Error finding API dependencies: {e}")

        return dependencies

    def _find_import_dependencies(
        self,
        source_repo: RepositoryInfo,
        target_repo: RepositoryInfo
    ) -> List[CrossRepoDependency]:
        """Find import dependencies between repos"""
        if not self.cpg:
            return []

        # For import dependencies, we would look for:
        # - Python: import statements referencing other repo
        # - Java: import statements
        # - JS: require/import statements

        # Simplified implementation for demo
        return []

    def generate_dependency_report(
        self,
        repositories: List[RepositoryInfo],
        dependencies: List[CrossRepoDependency],
        duplications: List[CodeDuplication],
        opportunities: List[ConsolidationOpportunity]
    ) -> ConsolidationReport:
        """Generate complete consolidation report"""
        # Calculate total savings
        total_savings = sum(dup.potential_savings for dup in duplications)

        # Generate dependency graph
        dep_graph = self.generate_dependency_graph(dependencies)

        # Risk summary
        risk_summary = {
            'critical': sum(1 for d in dependencies if d.risk_level == RiskLevel.CRITICAL),
            'high': sum(1 for d in dependencies if d.risk_level == RiskLevel.HIGH),
            'medium': sum(1 for d in dependencies if d.risk_level == RiskLevel.MEDIUM),
            'low': sum(1 for d in dependencies if d.risk_level == RiskLevel.LOW),
        }

        return ConsolidationReport(
            total_repos=len(repositories),
            total_methods=sum(r.method_count for r in repositories),
            duplications=duplications,
            dependencies=dependencies,
            opportunities=opportunities,
            dependency_graph=dep_graph,
            estimated_total_savings=total_savings,
            risk_summary=risk_summary
        )
