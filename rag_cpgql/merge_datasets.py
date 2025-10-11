"""Merge hackers and pg_books datasets into a single comprehensive dataset."""
import json
import random
from pathlib import Path

def load_jsonl(filepath):
    """Load JSONL file."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def save_jsonl(data, filepath):
    """Save data to JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def normalize_qa(qa_item, source):
    """Normalize QA item to common format."""
    normalized = {
        'question': qa_item['question'],
        'answer': qa_item['answer'],
        'difficulty': qa_item.get('difficulty', 'intermediate'),
        'topics': qa_item.get('topics', []),
        'cluster_id': qa_item.get('cluster_id', 0),
        'cluster_label': qa_item.get('cluster_label', ''),
        'source_files': qa_item.get('source_files', []),
        'thread_ids': qa_item.get('thread_ids', []),
        'source_dataset': source,  # Add source identifier
        'qa_id': qa_item.get('qa_id', f"{source}_{qa_item.get('cluster_id', 0)}")
    }
    return normalized

def main():
    print("=" * 80)
    print("MERGING DATASETS: Hackers + PG Books")
    print("=" * 80)

    # Paths
    hackers_path = Path("C:/Users/user/pg_copilot/hackers/output/pg_copilot_qa_dataset.jsonl")
    pg_books_path = Path("C:/Users/user/pg_copilot/pg_books/output/qa_pairs.jsonl")
    output_dir = Path("C:/Users/user/pg_copilot/rag_cpgql/data")

    # Load datasets
    print("\nLoading datasets...")
    hackers_data = load_jsonl(hackers_path)
    print(f"[OK] Loaded {len(hackers_data)} QA pairs from Hackers dataset")

    pg_books_data = load_jsonl(pg_books_path)
    print(f"[OK] Loaded {len(pg_books_data)} QA pairs from PG Books dataset")

    # Normalize and merge
    print("\nNormalizing and merging...")
    merged_data = []

    for qa in hackers_data:
        merged_data.append(normalize_qa(qa, 'hackers'))

    for qa in pg_books_data:
        merged_data.append(normalize_qa(qa, 'pg_books'))

    print(f"[OK] Merged total: {len(merged_data)} QA pairs")

    # Shuffle with fixed seed for reproducibility
    random.seed(42)
    random.shuffle(merged_data)
    print("[OK] Shuffled dataset with seed=42")

    # Split into train/test (85%/15%)
    split_point = int(len(merged_data) * 0.85)
    train_data = merged_data[:split_point]
    test_data = merged_data[split_point:]

    print(f"\nSplit statistics:")
    print(f"  Train: {len(train_data)} pairs ({len(train_data)/len(merged_data)*100:.1f}%)")
    print(f"  Test:  {len(test_data)} pairs ({len(test_data)/len(merged_data)*100:.1f}%)")

    # Analyze source distribution
    train_hackers = sum(1 for qa in train_data if qa['source_dataset'] == 'hackers')
    train_pg_books = sum(1 for qa in train_data if qa['source_dataset'] == 'pg_books')
    test_hackers = sum(1 for qa in test_data if qa['source_dataset'] == 'hackers')
    test_pg_books = sum(1 for qa in test_data if qa['source_dataset'] == 'pg_books')

    print(f"\nSource distribution:")
    print(f"  Train: Hackers={train_hackers}, PG_Books={train_pg_books}")
    print(f"  Test:  Hackers={test_hackers}, PG_Books={test_pg_books}")

    # Analyze difficulty distribution
    train_difficulties = {}
    test_difficulties = {}
    for qa in train_data:
        diff = qa['difficulty']
        train_difficulties[diff] = train_difficulties.get(diff, 0) + 1
    for qa in test_data:
        diff = qa['difficulty']
        test_difficulties[diff] = test_difficulties.get(diff, 0) + 1

    print(f"\nDifficulty distribution (Train):")
    for diff, count in sorted(train_difficulties.items()):
        print(f"  {diff}: {count} ({count/len(train_data)*100:.1f}%)")

    print(f"\nDifficulty distribution (Test):")
    for diff, count in sorted(test_difficulties.items()):
        print(f"  {diff}: {count} ({count/len(test_data)*100:.1f}%)")

    # Save splits
    print("\nSaving merged datasets...")
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train_split_merged.jsonl"
    test_path = output_dir / "test_split_merged.jsonl"
    all_path = output_dir / "all_qa_merged.jsonl"

    save_jsonl(train_data, train_path)
    print(f"[OK] Saved train split to: {train_path}")

    save_jsonl(test_data, test_path)
    print(f"[OK] Saved test split to: {test_path}")

    save_jsonl(merged_data, all_path)
    print(f"[OK] Saved complete dataset to: {all_path}")

    # Generate summary report
    report = {
        'total_pairs': len(merged_data),
        'train_pairs': len(train_data),
        'test_pairs': len(test_data),
        'split_ratio': {'train': 0.85, 'test': 0.15},
        'source_datasets': {
            'hackers': len(hackers_data),
            'pg_books': len(pg_books_data)
        },
        'source_distribution': {
            'train': {'hackers': train_hackers, 'pg_books': train_pg_books},
            'test': {'hackers': test_hackers, 'pg_books': test_pg_books}
        },
        'difficulty_distribution': {
            'train': train_difficulties,
            'test': test_difficulties
        },
        'random_seed': 42
    }

    report_path = output_dir / "dataset_merge_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved merge report to: {report_path}")

    print("\n" + "=" * 80)
    print("DATASET MERGE COMPLETE")
    print("=" * 80)
    print(f"\nTotal: {len(merged_data)} QA pairs")
    print(f"Train: {len(train_data)} pairs")
    print(f"Test:  {len(test_data)} pairs")
    print("\nFiles created:")
    print(f"  - {train_path}")
    print(f"  - {test_path}")
    print(f"  - {all_path}")
    print(f"  - {report_path}")

if __name__ == "__main__":
    main()
