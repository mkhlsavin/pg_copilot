"""Prepare data for RAG-CPGQL experiments."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.config import load_config
from utils.data_loader import load_qa_pairs, save_jsonl, split_dataset

def main():
    """Prepare training and test data."""
    # Load config
    config = load_config()

    print("=" * 60)
    print("RAG-CPGQL Data Preparation")
    print("=" * 60)

    # Load Q&A pairs
    print(f"\nLoading Q&A pairs from: {config.qa_pairs_source}")
    qa_pairs = load_qa_pairs(config.qa_pairs_source)
    print(f"Loaded {len(qa_pairs)} Q&A pairs")

    # Split dataset
    print(f"\nSplitting dataset (train: {config.get('split', 'train_ratio', default=0.85)}, test: {config.get('split', 'test_ratio', default=0.15)})")
    train_data, test_data = split_dataset(
        qa_pairs,
        train_ratio=config.get('split', 'train_ratio', default=0.85),
        random_seed=config.get('split', 'random_seed', default=42)
    )

    print(f"Train set: {len(train_data)} pairs")
    print(f"Test set: {len(test_data)} pairs")

    # Save splits
    print(f"\nSaving train split to: {config.train_split}")
    save_jsonl(train_data, config.train_split)

    print(f"Saving test split to: {config.test_split}")
    save_jsonl(test_data, config.test_split)

    # Show sample from test set
    print("\n" + "=" * 60)
    print("Sample from test set:")
    print("=" * 60)
    if test_data:
        sample = test_data[0]
        print(f"\nQuestion: {sample['question']}")
        print(f"\nAnswer: {sample['answer'][:200]}...")
        print(f"\nDifficulty: {sample.get('difficulty', 'N/A')}")
        print(f"Topics: {sample.get('topics', [])}")

    print("\n" + "=" * 60)
    print("Data preparation complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
