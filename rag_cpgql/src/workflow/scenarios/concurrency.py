"""
Scenario 09: Concurrency Analysis Workflow

Analyzes concurrency patterns, synchronization primitives, and detects
potential race conditions and lock-related issues.

**Capabilities:**
- Lock usage analysis (LWLock, SpinLock, regular locks)
- Race condition detection (TOCTOU, unprotected access)
- Shared memory access analysis
- Lock ordering analysis (deadlock detection)
- Atomic operation tracking
- Condition variable and latch usage

Uses ConcurrencyAnalyzer from src/analysis/concurrency_analyzer.py
"""

import logging
from typing import Dict, List, Any, Optional

from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.analysis.concurrency_analyzer import ConcurrencyAnalyzer
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)


def concurrency_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 09: Concurrency Analysis Workflow

    Analyzes concurrency patterns and synchronization issues:
    1. Lock usage analysis (LWLock, SpinLock, regular locks)
    2. Race condition detection (TOCTOU, unprotected shared access)
    3. Shared memory access patterns
    4. Lock ordering analysis (deadlock risks)
    5. Atomic operations and memory barriers

    Returns comprehensive concurrency analysis with risk assessment.
    """
    logger.info("Executing concurrency analysis workflow")

    try:
        with CPGQueryService() as cpg:
            analyzer = ConcurrencyAnalyzer(cpg)

            # Determine query focus from user question
            query_lower = state['query'].lower()

            # Initialize results
            lock_usages = []
            race_conditions = []
            shared_accesses = []
            lock_ordering = []
            atomic_ops = []
            concurrency_stats = {}

            # 1. Lock Usage Analysis
            if any(kw in query_lower for kw in ['lock', 'lwlock', 'spinlock', 'synchronization', 'mutex']):
                logger.info("Analyzing lock usage patterns...")

                # Determine specific lock type if mentioned
                lock_type = None
                if 'lwlock' in query_lower:
                    lock_type = 'lwlock'
                elif 'spinlock' in query_lower:
                    lock_type = 'spinlock'
                elif 'condvar' in query_lower or 'condition' in query_lower:
                    lock_type = 'condvar'
                elif 'latch' in query_lower:
                    lock_type = 'latch'

                lock_usages = analyzer.find_lock_usage(lock_type=lock_type, limit=50)
                logger.info(f"Found {len(lock_usages)} lock usages")

            # 2. Race Condition Detection
            if any(kw in query_lower for kw in ['race', 'toctou', 'concurrent', 'unsafe', 'condition']):
                logger.info("Detecting race conditions...")

                # Determine specific pattern if mentioned
                pattern_types = None
                if 'toctou' in query_lower:
                    pattern_types = ['toctou']
                elif 'signal' in query_lower:
                    pattern_types = ['signal_handler']
                elif 'unprotected' in query_lower or 'shared' in query_lower:
                    pattern_types = ['unprotected_access']

                race_conditions = analyzer.detect_race_conditions(
                    pattern_types=pattern_types,
                    limit=30
                )
                logger.info(f"Detected {len(race_conditions)} potential race conditions")

            # 3. Shared Memory Access
            if any(kw in query_lower for kw in ['shared', 'memory', 'shmem', 'access']):
                logger.info("Analyzing shared memory access...")
                shared_accesses = analyzer.analyze_shared_access(limit=50)
                logger.info(f"Found {len(shared_accesses)} shared access patterns")

            # 4. Lock Ordering Analysis
            if any(kw in query_lower for kw in ['ordering', 'deadlock', 'order']):
                logger.info("Analyzing lock ordering...")
                lock_ordering = analyzer.detect_lock_ordering_issues(limit=20)
                logger.info(f"Found {len(lock_ordering)} potential lock ordering issues")

            # 5. Atomic Operations
            if any(kw in query_lower for kw in ['atomic', 'barrier', 'fence', 'volatile']):
                logger.info("Finding atomic operations...")
                atomic_ops = analyzer.find_atomic_operations(limit=50)
                logger.info(f"Found {len(atomic_ops)} atomic operations")

            # 6. Get overall statistics
            concurrency_stats = analyzer.get_concurrency_statistics()

            # If no specific focus, run comprehensive analysis
            if not any([lock_usages, race_conditions, shared_accesses, lock_ordering, atomic_ops]):
                logger.info("Running comprehensive concurrency analysis...")
                lock_usages = analyzer.find_lock_usage(limit=30)
                race_conditions = analyzer.detect_race_conditions(limit=20)
                shared_accesses = analyzer.analyze_shared_access(limit=30)
                atomic_ops = analyzer.find_atomic_operations(limit=30)

            # Build evidence list
            evidence = []
            if lock_usages:
                evidence.append(f"Lock usages found: {len(lock_usages)}")
                lock_types = set(lu.lock_type for lu in lock_usages)
                evidence.append(f"Lock types: {', '.join(lock_types)}")
            if race_conditions:
                evidence.append(f"Potential race conditions: {len(race_conditions)}")
                high_sev = len([r for r in race_conditions if r.severity == 'high'])
                if high_sev > 0:
                    evidence.append(f"High severity races: {high_sev}")
            if shared_accesses:
                evidence.append(f"Shared access patterns: {len(shared_accesses)}")
                unprotected = len([s for s in shared_accesses if not s.is_protected])
                if unprotected > 0:
                    evidence.append(f"Unprotected accesses: {unprotected}")
            if lock_ordering:
                evidence.append(f"Lock ordering issues: {len(lock_ordering)}")
            if atomic_ops:
                evidence.append(f"Atomic operations: {len(atomic_ops)}")
            if concurrency_stats:
                evidence.append(f"Functions using locks: {concurrency_stats.get('functions_using_locks', 0)}")

            # Prepare CPG results for state
            cpg_results = []

            # Add lock usages to results
            for lu in lock_usages:
                cpg_results.append({
                    'name': lu.function_name,
                    'type': 'lock_usage',
                    'lock_type': lu.lock_type,
                    'operation': lu.operation,
                    'filename': lu.file_name,
                    'line_number': lu.line_number
                })

            # Add race conditions to results
            for rc in race_conditions:
                cpg_results.append({
                    'name': ', '.join(rc.affected_functions),
                    'type': 'race_condition',
                    'pattern_type': rc.pattern_type,
                    'severity': rc.severity,
                    'description': rc.description
                })

            # Add atomic ops to results
            for ao in atomic_ops:
                cpg_results.append({
                    'name': ao.get('function_name', ''),
                    'type': 'atomic_operation',
                    'operation_type': ao.get('operation_type', ''),
                    'atomic_func': ao.get('atomic_func', ''),
                    'filename': ao.get('file_name', '')
                })

            # Build LLM prompt
            llm = LLMInterface()
            registry = get_global_registry()

            # Prepare summary sections
            lock_summary = ""
            if lock_usages:
                lock_summary = "\n**Lock Usage Patterns:**\n"
                by_type = {}
                for lu in lock_usages:
                    by_type.setdefault(lu.lock_type, []).append(lu)
                for ltype, usages in by_type.items():
                    lock_summary += f"- {ltype}: {len(usages)} usages\n"
                    for u in usages[:3]:
                        lock_summary += f"  - {u.function_name} ({u.operation}) in {u.file_name}:{u.line_number}\n"

            race_summary = ""
            if race_conditions:
                race_summary = "\n**Potential Race Conditions:**\n"
                for rc in race_conditions[:5]:
                    race_summary += f"- [{rc.severity.upper()}] {rc.pattern_type}: {rc.description[:100]}\n"

            shared_summary = ""
            if shared_accesses:
                shared_summary = "\n**Shared Memory Access:**\n"
                for sa in shared_accesses[:5]:
                    status = "protected" if sa.is_protected else "UNPROTECTED"
                    shared_summary += f"- {sa.variable_name} ({status}): accessed by {len(sa.accessor_functions)} functions\n"

            atomic_summary = ""
            if atomic_ops:
                atomic_summary = "\n**Atomic Operations:**\n"
                by_op = {}
                for ao in atomic_ops:
                    op = ao.get('operation_type', 'unknown')
                    by_op.setdefault(op, []).append(ao)
                for op, ops in by_op.items():
                    atomic_summary += f"- {op}: {len(ops)} operations\n"

            stats_summary = ""
            if concurrency_stats:
                stats_summary = "\n**Concurrency Statistics:**\n"
                stats_summary += f"- LWLock calls: {concurrency_stats.get('lwlock_calls', 0)}\n"
                stats_summary += f"- SpinLock calls: {concurrency_stats.get('spinlock_calls', 0)}\n"
                stats_summary += f"- Regular lock calls: {concurrency_stats.get('lock_acquire_calls', 0)}\n"
                stats_summary += f"- Atomic operations: {concurrency_stats.get('atomic_calls', 0)}\n"
                stats_summary += f"- Shared memory calls: {concurrency_stats.get('shmem_calls', 0)}\n"
                stats_summary += f"- Functions using locks: {concurrency_stats.get('functions_using_locks', 0)}\n"

            # Build prompt
            prompt_vars = {
                'domain': 'PostgreSQL',
                'query': state['query'],
                'lock_analysis': lock_summary if lock_summary else 'No lock patterns analyzed',
                'race_conditions': race_summary if race_summary else 'No race conditions detected',
                'shared_access': shared_summary if shared_summary else 'No shared access patterns analyzed',
                'atomic_ops': atomic_summary if atomic_summary else 'No atomic operations analyzed',
                'statistics': stats_summary if stats_summary else 'No statistics available'
            }

            # Use debugging_expert prompt as fallback (similar domain)
            try:
                prompts = registry.get_agent_prompt('debugging_expert', **prompt_vars)
            except Exception:
                prompts = {
                    'system': "You are a concurrency and synchronization expert for C codebases.",
                    'user': f"Analyze the concurrency patterns in the codebase."
                }

            concurrency_prompt = f"""{prompts['system']}

You are analyzing concurrency and synchronization patterns in a PostgreSQL-like codebase.

User Question: {state['query']}

**CONCURRENCY ANALYSIS RESULTS:**
{lock_summary}
{race_summary}
{shared_summary}
{atomic_summary}
{stats_summary}

Based on this analysis, provide:
1. Summary of concurrency patterns found
2. Identified synchronization issues or risks
3. Recommendations for thread safety improvements
4. Specific answers to the user's question about {state['query'][:50]}...

Focus on practical, actionable insights about locking, race conditions, and thread safety.
"""

            answer = llm.generate(add_language_instruction(prompts['system'], state), concurrency_prompt)

            # Update state
            state['cpg_results'] = cpg_results
            state['methods'] = [r for r in cpg_results if r.get('name')]
            state['answer'] = answer
            state['evidence'] = evidence
            state['metadata'] = {
                'lock_usages': len(lock_usages),
                'race_conditions': len(race_conditions),
                'shared_accesses': len(shared_accesses),
                'lock_ordering_issues': len(lock_ordering),
                'atomic_operations': len(atomic_ops),
                'concurrency_stats': concurrency_stats,
                'high_severity_races': len([r for r in race_conditions if r.severity == 'high']),
                'unprotected_accesses': len([s for s in shared_accesses if not s.is_protected]),
                'enhanced_mode': True,
                'scenario': 'concurrency_analysis'
            }

    except Exception as e:
        logger.error(f"Concurrency workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during concurrency analysis: {e}"

    return state


__all__ = ['concurrency_workflow']
