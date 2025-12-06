"""
Consolidate 17 benchmark scenarios into 14 scenarios aligned with intent_taxonomy.py

Mapping:
- scenario_01_onboarding: 01_definition_search + 02_call_graph + 03_data_flow + 13_subsystem + 14_debugging + 16_business_logic
- scenario_02_security_audit: 04_vulnerability + 08_entry_points + 15_new_vulnerabilities
- scenario_03_documentation: 12_documentation (rename)
- scenario_04_feature_dev: NEW (placeholder)
- scenario_05_refactoring: 05_dead_code + 07_duplicates
- scenario_06_performance: 06_complexity + 09_concurrency + 10_memory
- scenario_07_test_coverage: 17_test_generation (rename)
- scenario_08_compliance: NEW (placeholder)
- scenario_09_code_review: NEW (placeholder)
- scenario_10_cross_repo: NEW (placeholder)
- scenario_11_architecture: 11_dependencies (rename)
- scenario_12_tech_debt: NEW (placeholder)
- scenario_13_mass_refactoring: NEW (placeholder)
- scenario_14_security_incident: NEW (placeholder)
"""

import os
import shutil
import yaml
from pathlib import Path
from datetime import datetime

GROUND_TRUTH_PATH = Path("tests/benchmark/ground_truth")
BACKUP_PATH = Path("tests/benchmark/ground_truth_backup")

# Mapping from new scenario to old scenarios
SCENARIO_MAPPING = {
    "scenario_01_onboarding": {
        "sources": ["scenario_01_definition_search", "scenario_02_call_graph", "scenario_03_data_flow",
                    "scenario_13_subsystem", "scenario_14_debugging", "scenario_16_business_logic"],
        "name": "Codebase Onboarding",
        "workflow": "onboarding_workflow",
        "graph_methods": ["find_definition", "find_all_references", "trace_callers", "trace_callees",
                         "trace_data_flow", "explain_subsystem", "find_breakpoints"]
    },
    "scenario_02_security_audit": {
        "sources": ["scenario_04_vulnerability", "scenario_08_entry_points", "scenario_15_new_vulnerabilities"],
        "name": "Security Audit",
        "workflow": "security_workflow",
        "graph_methods": ["find_vulnerabilities", "find_entry_points", "trace_taint_flow"]
    },
    "scenario_03_documentation": {
        "sources": ["scenario_12_documentation"],
        "name": "Documentation Generation",
        "workflow": "documentation_workflow",
        "graph_methods": ["generate_docs", "extract_comments"]
    },
    "scenario_04_feature_dev": {
        "sources": [],  # NEW - placeholder
        "name": "Feature Development",
        "workflow": "feature_dev_workflow",
        "graph_methods": ["find_extension_points", "find_hooks"]
    },
    "scenario_05_refactoring": {
        "sources": ["scenario_05_dead_code", "scenario_07_duplicates"],
        "name": "Refactoring Assistance",
        "workflow": "refactoring_workflow",
        "graph_methods": ["find_dead_code", "find_duplicates", "analyze_complexity"]
    },
    "scenario_06_performance": {
        "sources": ["scenario_06_complexity", "scenario_09_concurrency", "scenario_10_memory"],
        "name": "Performance Optimization",
        "workflow": "performance_workflow",
        "graph_methods": ["find_hotspots", "analyze_complexity", "find_locks", "find_memory_patterns"]
    },
    "scenario_07_test_coverage": {
        "sources": ["scenario_17_test_generation"],
        "name": "Test Coverage Analysis",
        "workflow": "test_coverage_workflow",
        "graph_methods": ["generate_tests", "find_untested_paths"]
    },
    "scenario_08_compliance": {
        "sources": [],  # NEW - placeholder
        "name": "Compliance Checking",
        "workflow": "compliance_workflow",
        "graph_methods": ["check_coding_style", "verify_naming"]
    },
    "scenario_09_code_review": {
        "sources": [],  # NEW - placeholder
        "name": "Code Review Assistance",
        "workflow": "code_review_workflow",
        "graph_methods": ["analyze_diff", "find_breaking_changes"]
    },
    "scenario_10_cross_repo": {
        "sources": [],  # NEW - placeholder
        "name": "Cross-Repository Impact",
        "workflow": "cross_repo_workflow",
        "graph_methods": ["find_external_callers", "analyze_api_changes"]
    },
    "scenario_11_architecture": {
        "sources": ["scenario_11_dependencies"],
        "name": "Architecture Violation Detection",
        "workflow": "architecture_workflow",
        "graph_methods": ["analyze_dependencies", "find_circular_deps"]
    },
    "scenario_12_tech_debt": {
        "sources": [],  # NEW - placeholder
        "name": "Technical Debt Quantification",
        "workflow": "tech_debt_workflow",
        "graph_methods": ["find_todos", "quantify_debt"]
    },
    "scenario_13_mass_refactoring": {
        "sources": [],  # NEW - placeholder
        "name": "Mass Refactoring Automation",
        "workflow": "mass_refactoring_workflow",
        "graph_methods": ["rename_symbol", "change_signature"]
    },
    "scenario_14_security_incident": {
        "sources": [],  # NEW - placeholder
        "name": "Security Incident Response",
        "workflow": "security_incident_workflow",
        "graph_methods": ["trace_vulnerability_impact", "find_affected_code"]
    }
}


def backup_ground_truth():
    """Backup current ground_truth directory"""
    if BACKUP_PATH.exists():
        print(f"   Backup already exists at: {BACKUP_PATH}")
        return  # Don't overwrite existing backup

    shutil.copytree(str(GROUND_TRUTH_PATH), str(BACKUP_PATH))
    print(f"Backed up to: {BACKUP_PATH}")


def load_yaml(path: Path) -> dict:
    """Load YAML file"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    """Save YAML file"""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)


def merge_questions(source_dirs: list, new_scenario_id: str, scenario_config: dict, language: str = "en") -> dict:
    """Merge questions from multiple source directories"""
    all_questions = []

    for source_dir in source_dirs:
        # Read from backup since original was removed
        source_path = BACKUP_PATH / source_dir / f"questions_{language}.yaml"
        if source_path.exists():
            data = load_yaml(source_path)
            if data and 'questions' in data:
                # Update question IDs to include source scenario
                for q in data['questions']:
                    old_id = q.get('id', '')
                    # Preserve original category info in ID
                    all_questions.append(q)

    # Count difficulties
    difficulty_dist = {"easy": 0, "medium": 0, "hard": 0}
    for q in all_questions:
        diff = q.get('difficulty', 'medium')
        if diff in difficulty_dist:
            difficulty_dist[diff] += 1

    return {
        "scenario": {
            "id": new_scenario_id,
            "name": scenario_config['name'],
            "mapped_workflow": scenario_config['workflow'],
            "graph_methods": scenario_config['graph_methods']
        },
        "metadata": {
            "version": "2.0",
            "language": language,
            "question_count": len(all_questions),
            "difficulty_distribution": difficulty_dist,
            "consolidated_from": source_dirs
        },
        "questions": all_questions
    }


def create_placeholder(scenario_id: str, scenario_config: dict, language: str = "en") -> dict:
    """Create placeholder for new scenario"""
    return {
        "scenario": {
            "id": scenario_id,
            "name": scenario_config['name'],
            "mapped_workflow": scenario_config['workflow'],
            "graph_methods": scenario_config['graph_methods']
        },
        "metadata": {
            "version": "2.0",
            "language": language,
            "question_count": 0,
            "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
            "note": "Placeholder - questions to be added"
        },
        "questions": []
    }


def consolidate_scenarios():
    """Main consolidation function"""
    print("=" * 60)
    print("Consolidating 17 scenarios into 14")
    print("=" * 60)

    # Step 1: Backup
    print("\n1. Backing up current ground_truth...")
    backup_ground_truth()

    # Step 2: Remove old directories
    print("\n2. Removing old directories...")
    for item in GROUND_TRUTH_PATH.iterdir():
        if item.is_dir() and item.name.startswith("scenario_"):
            shutil.rmtree(str(item))
            print(f"   Removed: {item.name}")

    # Step 3: Create new structure
    print("\n3. Creating new 14-scenario structure...")
    for scenario_id, config in SCENARIO_MAPPING.items():
        scenario_path = GROUND_TRUTH_PATH / scenario_id
        scenario_path.mkdir(exist_ok=True)

        for language in ["en", "ru"]:
            if config['sources']:
                # Merge from existing scenarios
                merged = merge_questions(config['sources'], scenario_id, config, language)
                if merged['questions']:  # Only if we have questions
                    save_yaml(scenario_path / f"questions_{language}.yaml", merged)
                    print(f"   Created: {scenario_id}/questions_{language}.yaml ({merged['metadata']['question_count']} questions)")
            else:
                # Create placeholder
                placeholder = create_placeholder(scenario_id, config, language)
                save_yaml(scenario_path / f"questions_{language}.yaml", placeholder)
                print(f"   Created: {scenario_id}/questions_{language}.yaml (placeholder)")

    print("\n" + "=" * 60)
    print("Consolidation complete!")
    print("=" * 60)


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)  # Go to project root
    consolidate_scenarios()
