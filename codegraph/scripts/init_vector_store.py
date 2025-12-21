"""Initialize ChromaDB vector store and index training data."""
import sys
import logging
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retrieval.vector_store_real import VectorStoreReal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Initialize vector store and index all data."""

    print("\n" + "="*80)
    print("ChromaDB Vector Store Initialization")
    print("="*80 + "\n")

    # Paths
    data_dir = Path(__file__).parent.parent / "data"
    qa_file = data_dir / "train_split_merged.jsonl"  # Use merged dataset (23,156 pairs)
    sql_file = data_dir / "sql_examples.json"  # SQL/PGQ examples for DuckDB

    # Check files exist
    if not qa_file.exists():
        logger.error(f"Q&A file not found: {qa_file}")
        return 1

    if not sql_file.exists():
        logger.error(f"SQL examples file not found: {sql_file}")
        return 1

    print(f"Q&A file: {qa_file}")
    print(f"SQL examples file: {sql_file}\n")

    # Initialize vector store
    print("1. Initializing ChromaDB...")
    start_time = time.time()

    vector_store = VectorStoreReal()
    vector_store.initialize_collections()

    init_time = time.time() - start_time
    print(f"   Initialized in {init_time:.2f}s\n")

    # Check current stats
    stats = vector_store.get_stats()
    print(f"Current stats:")
    print(f"  Q&A pairs: {stats['qa_pairs_count']}")
    print(f"  SQL examples: {stats['sql_examples_count']}\n")

    # Index Q&A pairs
    if stats['qa_pairs_count'] == 0:
        print("2. Indexing Q&A pairs...")
        start_time = time.time()

        qa_count = vector_store.index_qa_pairs(qa_file)

        qa_time = time.time() - start_time
        print(f"   Indexed {qa_count} Q&A pairs in {qa_time:.2f}s")
        print(f"   Rate: {qa_count / qa_time:.2f} pairs/sec\n")
    else:
        print("2. Q&A pairs already indexed (skipping)\n")

    # Index SQL examples
    if stats['sql_examples_count'] == 0:
        print("3. Indexing SQL examples...")
        start_time = time.time()

        sql_count = vector_store.index_sql_examples(sql_file)

        sql_time = time.time() - start_time
        print(f"   Indexed {sql_count} SQL examples in {sql_time:.2f}s")
        print(f"   Rate: {sql_count / sql_time:.2f} examples/sec\n")
    else:
        print("3. SQL examples already indexed (skipping)\n")

    # Final stats
    stats = vector_store.get_stats()
    print("="*80)
    print("Final Statistics")
    print("="*80 + "\n")
    print(f"Q&A pairs indexed:     {stats['qa_pairs_count']:,}")
    print(f"SQL examples indexed:  {stats['sql_examples_count']:,}")
    print(f"Total items:           {stats['qa_pairs_count'] + stats['sql_examples_count']:,}")

    # Test retrieval
    print("\n" + "="*80)
    print("Testing Retrieval")
    print("="*80 + "\n")

    test_query = "How does PostgreSQL handle vacuum operations?"
    print(f"Query: {test_query}\n")

    print("Top-3 Q&A pairs:")
    qa_results = vector_store.retrieve_qa(test_query, top_k=3)
    for i, result in enumerate(qa_results, 1):
        print(f"{i}. (sim={result['similarity']:.3f}) {result['question'][:80]}...")

    print("\nTop-5 SQL examples:")
    sql_results = vector_store.retrieve_sql(test_query, top_k=5)
    for i, result in enumerate(sql_results, 1):
        print(f"{i}. (sim={result['similarity']:.3f}) {result['sql'][:60]}...")

    print("\n" + "="*80)
    print("Initialization Complete!")
    print("="*80 + "\n")

    print("Vector store ready at: codegraph/chroma_db/")
    print("You can now use VectorStoreReal in your RAG pipeline.\n")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
