"""Cache Management CLI Tool

This script provides utilities for managing the retrieval cache including:
- Viewing cache metrics
- Warming cache with common questions
- Invalidating cache entries
- Exporting metrics to JSON

Usage:
    # View current cache metrics
    conda run --name llama.cpp python scripts/manage_cache.py metrics

    # Warm cache with common questions
    conda run --name llama.cpp python scripts/manage_cache.py warm --file data/common_questions.txt

    # Invalidate cache by pattern
    conda run --name llama.cpp python scripts/manage_cache.py invalidate --pattern "vacuum"

    # Clear all cache
    conda run --name llama.cpp python scripts/manage_cache.py clear

    # Export metrics to JSON
    conda run --name llama.cpp python scripts/manage_cache.py export --output cache_metrics.json
"""

import sys
import argparse
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.retrieval.vector_store_real import VectorStoreReal


def get_retriever() -> RetrieverAgent:
    """Initialize and return a RetrieverAgent instance."""
    print("Initializing retriever agent...")

    # Initialize components
    analyzer = AnalyzerAgent()
    vector_store = VectorStoreReal()

    try:
        vector_store.initialize_collections()
    except Exception as e:
        print(f"Warning: Vector store initialization failed: {e}")

    retriever = RetrieverAgent(
        vector_store=vector_store,
        analyzer_agent=analyzer,
        cache_size=256,  # Larger cache for management operations
        cache_ttl_seconds=3600,  # 1 hour TTL
        enable_cache_metrics=True
    )

    print("✓ Retriever initialized")
    return retriever


def cmd_metrics(args):
    """Show current cache metrics."""
    retriever = get_retriever()
    metrics = retriever.get_cache_metrics()

    print("\n" + "="*80)
    print("CACHE METRICS")
    print("="*80)

    print(f"\n📊 Hit/Miss Statistics:")
    print(f"  Hits:      {metrics['hits']:,}")
    print(f"  Misses:    {metrics['misses']:,}")
    print(f"  Hit Rate:  {metrics['hit_rate']:.2%}")
    print(f"  Miss Rate: {metrics['miss_rate']:.2%}")

    print(f"\n💾 Size Statistics:")
    print(f"  Current:   {metrics['current_size']:,} / {metrics['max_size']:,} entries")
    print(f"  Utilization: {metrics['utilization']:.1%}")
    print(f"  Memory:    {metrics['memory_bytes'] / 1024:.1f} KB")

    print(f"\n⏱️  Timing Statistics:")
    print(f"  Avg Get:   {metrics['avg_get_time_ms']:.2f} ms")
    print(f"  Avg Set:   {metrics['avg_set_time_ms']:.2f} ms")

    print(f"\n🗑️  Eviction Statistics:")
    print(f"  By Size:   {metrics['evictions_by_size']:,}")
    print(f"  By TTL:    {metrics['evictions_by_ttl']:,}")
    print(f"  By Invalidation: {metrics['evictions_by_invalidation']:,}")

    if metrics['current_size'] > 0:
        print(f"\n📅 Age Statistics:")
        print(f"  Oldest:    {metrics['oldest_entry_age_seconds']:.1f} seconds")
        print(f"  Newest:    {metrics['newest_entry_age_seconds']:.1f} seconds")
        print(f"  Average:   {metrics['avg_entry_age_seconds']:.1f} seconds")

    print("\n" + "="*80 + "\n")


def cmd_warm(args):
    """Warm cache with questions from file."""
    if not args.file:
        print("Error: --file required for warm command")
        return

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return

    # Load questions
    print(f"Loading questions from {file_path}...")
    questions = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                questions.append(line)

    print(f"Loaded {len(questions)} questions")

    # Initialize retriever and warm cache
    retriever = get_retriever()

    print("\nWarming cache...")
    count = retriever.warm_cache(
        questions=questions,
        top_k_qa=args.top_k_qa,
        top_k_cpgql=args.top_k_cpgql
    )

    print(f"\n✓ Cache warmed: {count}/{len(questions)} questions cached")

    # Show updated metrics
    metrics = retriever.get_cache_metrics()
    print(f"\nCache status: {metrics['current_size']} entries, {metrics['utilization']:.1%} full")


def cmd_invalidate(args):
    """Invalidate cache entries by pattern."""
    if not args.pattern:
        print("Error: --pattern required for invalidate command")
        return

    retriever = get_retriever()

    print(f"Invalidating cache entries matching pattern: '{args.pattern}'...")
    count = retriever.invalidate_cache(pattern=args.pattern)

    print(f"✓ Invalidated {count} cache entries")

    # Show updated metrics
    metrics = retriever.get_cache_metrics()
    print(f"\nCache status: {metrics['current_size']} entries, {metrics['utilization']:.1%} full")


def cmd_clear(args):
    """Clear all cache entries."""
    if not args.force:
        response = input("Are you sure you want to clear all cache entries? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            return

    retriever = get_retriever()

    print("Clearing all cache entries...")
    count = retriever.invalidate_cache(pattern=None)

    print(f"✓ Cleared {count} cache entries")


def cmd_export(args):
    """Export cache metrics to JSON."""
    retriever = get_retriever()
    metrics = retriever.get_cache_metrics()

    output_path = Path(args.output) if args.output else Path("cache_metrics.json")

    print(f"Exporting metrics to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ Metrics exported to {output_path}")
    print(f"\nSummary:")
    print(f"  Hit Rate:   {metrics['hit_rate']:.2%}")
    print(f"  Size:       {metrics['current_size']} / {metrics['max_size']}")
    print(f"  Memory:     {metrics['memory_bytes'] / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Cache Management CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Metrics command
    parser_metrics = subparsers.add_parser('metrics', help='Show current cache metrics')

    # Warm command
    parser_warm = subparsers.add_parser('warm', help='Warm cache with questions from file')
    parser_warm.add_argument('--file', required=True, help='File with questions (one per line)')
    parser_warm.add_argument('--top-k-qa', type=int, default=3, help='Number of Q&A pairs per question')
    parser_warm.add_argument('--top-k-cpgql', type=int, default=5, help='Number of CPGQL examples per question')

    # Invalidate command
    parser_invalidate = subparsers.add_parser('invalidate', help='Invalidate cache by pattern')
    parser_invalidate.add_argument('--pattern', required=True, help='Pattern to match')

    # Clear command
    parser_clear = subparsers.add_parser('clear', help='Clear all cache entries')
    parser_clear.add_argument('--force', action='store_true', help='Skip confirmation')

    # Export command
    parser_export = subparsers.add_parser('export', help='Export metrics to JSON')
    parser_export.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    commands = {
        'metrics': cmd_metrics,
        'warm': cmd_warm,
        'invalidate': cmd_invalidate,
        'clear': cmd_clear,
        'export': cmd_export
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
