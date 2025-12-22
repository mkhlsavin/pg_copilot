"""Data loading utilities for Q&A pairs and CPGQL examples."""
import json
import jsonlines
import random
from typing import List, Dict, Tuple

def load_qa_pairs(file_path: str) -> List[Dict]:
    """Load Q&A pairs from JSONL file."""
    qa_pairs = []
    with jsonlines.open(file_path) as reader:
        for obj in reader:
            qa_pairs.append(obj)
    return qa_pairs

def load_cpgql_examples(file_path: str) -> List[Dict]:
    """Load CPGQL training examples from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_jsonl(data: List[Dict], file_path: str):
    """Save data to JSONL file."""
    with jsonlines.open(file_path, 'w') as writer:
        for item in data:
            writer.write(item)

def save_json(data: Dict, file_path: str):
    """Save data to JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def split_dataset(
    qa_pairs: List[Dict],
    train_ratio: float = 0.85,
    random_seed: int = 42
) -> Tuple[List[Dict], List[Dict]]:
    """
    Split Q&A pairs into train and test sets.

    Args:
        qa_pairs: List of Q&A dictionaries
        train_ratio: Ratio of training data (default 0.85)
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of (train_data, test_data)
    """
    random.seed(random_seed)
    shuffled = qa_pairs.copy()
    random.shuffle(shuffled)

    split_idx = int(train_ratio * len(shuffled))
    train_data = shuffled[:split_idx]
    test_data = shuffled[split_idx:]

    return train_data, test_data
