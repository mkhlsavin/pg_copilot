# Topic Clustering Module Documentation

## Overview

The `topic_clustering.py` module groups related email threads by topic using semantic embeddings and clustering algorithms, enabling efficient aggregation of discussions about similar PostgreSQL internals topics.

## Purpose

- Embed thread content using transformer models
- Cluster similar discussions together
- Extract topic keywords and themes
- Identify major discussion categories (e.g., query planner, WAL, MVCC, storage)

## Architecture

```
┌──────────────────────────────────────────────────┐
│         Topic Clustering Module                   │
├──────────────────────────────────────────────────┤
│                                                   │
│  Input:                                           │
│    - data/processed_threads.json                  │
│                                                   │
│  Process:                                         │
│    1. Extract thread text (subject + content)     │
│    2. Generate embeddings (sentence-transformers) │
│    3. Dimensionality reduction (optional)         │
│    4. Clustering (HDBSCAN/KMeans)                 │
│    5. Extract topic keywords (TF-IDF/KeyBERT)     │
│    6. Label clusters with topics                  │
│                                                   │
│  Output:                                          │
│    - data/clustered_topics.json                   │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. TopicClusterer Class

Main class for clustering threads by topic.

```python
class TopicClusterer:
    def __init__(self, threads: Dict, embedding_model: str = 'all-MiniLM-L6-v2'):
        """
        Initialize clusterer.

        Args:
            threads: Processed threads from thread_parser
            embedding_model: HuggingFace model name for embeddings
        """
        self.threads = threads
        self.model = SentenceTransformer(embedding_model)
        self.embeddings = None
        self.clusters = None

    def cluster_threads(self, n_clusters: int = None, method: str = 'hdbscan') -> Dict:
        """
        Cluster threads by topic.

        Args:
            n_clusters: Number of clusters (for KMeans)
            method: 'hdbscan' or 'kmeans'

        Returns:
            Clustered topics dictionary
        """

    def save_to_json(self, output_path: str):
        """Save clustered topics to JSON file."""
```

### 2. Core Functions

#### `prepare_thread_text(thread: Dict) -> str`

Extracts representative text from thread for embedding.

**Strategy:**
```python
def prepare_thread_text(thread: Dict) -> str:
    """
    Combine subject + aggregated content.
    Optionally weight subject higher (repeat N times).
    """
    subject = thread['subject']
    content = thread['aggregated_content'][:2000]  # Limit length

    # Weight subject more heavily
    text = f"{subject} {subject} {subject} {content}"

    return text
```

**Example Output:**
```
"Query planner optimization for partitioned tables Query planner optimization for partitioned tables Query planner optimization for partitioned tables I've been investigating partition pruning and found that the planner doesn't consider runtime pruning when..."
```

#### `generate_embeddings(texts: List[str], model: SentenceTransformer) -> np.ndarray`

Creates dense vector representations of threads.

**Process:**
```python
from sentence_transformers import SentenceTransformer

def generate_embeddings(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    """
    Generate embeddings with progress tracking.

    Returns:
        Array of shape (n_threads, embedding_dim)
        embedding_dim = 384 for all-MiniLM-L6-v2
    """
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True
    )
    return embeddings
```

**Embedding Models:**

| Model | Dimension | Speed | Quality |
|-------|-----------|-------|---------|
| all-MiniLM-L6-v2 | 384 | Fast | Good |
| all-mpnet-base-v2 | 768 | Medium | Better |
| all-distilroberta-v1 | 768 | Medium | Better |

#### `cluster_hdbscan(embeddings: np.ndarray, min_cluster_size: int = 5) -> np.ndarray`

Density-based clustering (automatically determines number of clusters).

**Advantages:**
- No need to specify cluster count
- Handles noise (assigns -1 label)
- Finds arbitrarily shaped clusters

**Implementation:**
```python
import hdbscan

def cluster_hdbscan(embeddings: np.ndarray, min_cluster_size: int = 5) -> np.ndarray:
    """
    HDBSCAN clustering.

    Args:
        embeddings: Thread embeddings
        min_cluster_size: Minimum threads per cluster

    Returns:
        Cluster labels (-1 for noise)
    """
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric='euclidean',
        cluster_selection_epsilon=0.5,
        core_dist_n_jobs=-1  # Use all CPU cores
    )

    labels = clusterer.fit_predict(embeddings)

    return labels
```

#### `cluster_kmeans(embeddings: np.ndarray, n_clusters: int) -> np.ndarray`

K-Means clustering (requires specifying cluster count).

**Advantages:**
- Deterministic with fixed seed
- Fast and simple
- All threads assigned to cluster

**Implementation:**
```python
from sklearn.cluster import KMeans

def cluster_kmeans(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
    """
    K-Means clustering.

    Args:
        embeddings: Thread embeddings
        n_clusters: Number of clusters to create

    Returns:
        Cluster labels (0 to n_clusters-1)
    """
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10,
        max_iter=300
    )

    labels = kmeans.fit_predict(embeddings)

    return labels
```

#### `extract_topic_keywords(thread_texts: List[str], n_keywords: int = 5) -> List[str]`

Extracts representative keywords for a cluster.

**Method 1: TF-IDF**
```python
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_tfidf_keywords(thread_texts: List[str], n_keywords: int = 5) -> List[str]:
    """
    Extract keywords using TF-IDF.
    """
    vectorizer = TfidfVectorizer(
        max_features=100,
        stop_words='english',
        ngram_range=(1, 2)  # Unigrams and bigrams
    )

    tfidf_matrix = vectorizer.fit_transform(thread_texts)
    feature_names = vectorizer.get_feature_names_out()

    # Sum TF-IDF scores across all threads
    scores = tfidf_matrix.sum(axis=0).A1
    top_indices = scores.argsort()[-n_keywords:][::-1]

    keywords = [feature_names[i] for i in top_indices]

    return keywords
```

**Method 2: KeyBERT**
```python
from keybert import KeyBERT

def extract_keybert_keywords(thread_texts: List[str], n_keywords: int = 5) -> List[str]:
    """
    Extract keywords using KeyBERT (semantic approach).
    """
    kw_model = KeyBERT()

    # Combine all thread texts
    combined_text = ' '.join(thread_texts)

    # Extract keywords
    keywords = kw_model.extract_keywords(
        combined_text,
        keyphrase_ngram_range=(1, 2),
        stop_words='english',
        top_n=n_keywords,
        use_maxsum=True
    )

    return [kw[0] for kw in keywords]
```

**Example Keywords:**
```python
# Cluster about query planner
keywords = ['query planner', 'partition pruning', 'optimizer', 'plan node', 'cost estimation']
```

#### `label_cluster(keywords: List[str], thread_count: int) -> str`

Generates human-readable cluster label.

```python
def label_cluster(keywords: List[str], thread_count: int) -> str:
    """
    Create descriptive cluster label.

    Args:
        keywords: Top keywords for cluster
        thread_count: Number of threads in cluster

    Returns:
        Cluster label
    """
    # Take top 3 keywords
    label = '_'.join(keywords[:3])

    # Clean and format
    label = label.lower().replace(' ', '_')

    return f"{label}_{thread_count}threads"
```

**Example:**
```python
label = label_cluster(['query planner', 'partition pruning', 'optimizer'], 23)
# Returns: "query_planner_partition_pruning_optimizer_23threads"
```

## Data Flow

```
Threads → Text Extraction → Embeddings → Clustering → Keyword Extraction → Labels
   ↓             ↓               ↓            ↓              ↓               ↓
(parsed)     (subject+        (384-dim    (HDBSCAN)     (TF-IDF)     clustered_topics.json
             content)         vectors)
```

## Output Format

### clustered_topics.json

```json
{
  "clusters": [
    {
      "cluster_id": 0,
      "label": "query_planner_partition_pruning_optimizer",
      "keywords": [
        "query planner",
        "partition pruning",
        "optimizer",
        "plan node",
        "cost estimation"
      ],
      "thread_count": 23,
      "threads": [
        {
          "thread_id": "20230415-planner-optimization",
          "subject": "Query planner optimization for partitioned tables",
          "message_count": 18,
          "start_date": "2023-04-15T10:30:45Z",
          "end_date": "2023-04-22T16:30:00Z",
          "similarity_score": 0.87
        },
        {
          "thread_id": "20230501-runtime-pruning",
          "subject": "Runtime partition pruning improvements",
          "message_count": 12,
          "start_date": "2023-05-01T09:15:00Z",
          "end_date": "2023-05-08T14:20:00Z",
          "similarity_score": 0.82
        }
      ]
    },
    {
      "cluster_id": 1,
      "label": "wal_replication_logical_decoding",
      "keywords": [
        "wal",
        "replication",
        "logical decoding",
        "slot",
        "replication origin"
      ],
      "thread_count": 15,
      "threads": [...]
    },
    {
      "cluster_id": 2,
      "label": "mvcc_visibility_vacuum_bloat",
      "keywords": [
        "mvcc",
        "tuple visibility",
        "vacuum",
        "bloat",
        "xmin xmax"
      ],
      "thread_count": 19,
      "threads": [...]
    }
  ],
  "metadata": {
    "total_clusters": 42,
    "total_threads": 234,
    "unclustered_threads": 8,
    "embedding_model": "all-MiniLM-L6-v2",
    "clustering_method": "hdbscan",
    "min_cluster_size": 5,
    "largest_cluster": {
      "cluster_id": 0,
      "label": "query_planner_partition_pruning_optimizer",
      "thread_count": 23
    }
  }
}
```

## Configuration

Key settings in `config.py`:

```python
# Topic clustering configuration
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Sentence transformer model
CLUSTERING_METHOD = 'hdbscan'  # 'hdbscan' or 'kmeans'
MIN_CLUSTER_SIZE = 5  # Minimum threads per cluster
N_CLUSTERS = None  # For KMeans (None = auto-determine)
KEYWORD_EXTRACTION = 'tfidf'  # 'tfidf' or 'keybert'
N_KEYWORDS = 5  # Keywords per cluster
REDUCE_DIMENSIONS = False  # Use UMAP for dimensionality reduction
UMAP_N_COMPONENTS = 50  # If REDUCE_DIMENSIONS=True
```

## Advanced Features

### 1. Dimensionality Reduction (UMAP)

Reduce embedding dimensions before clustering (can improve results).

```python
from umap import UMAP

def reduce_dimensions(embeddings: np.ndarray, n_components: int = 50) -> np.ndarray:
    """
    Reduce embedding dimensions using UMAP.

    Args:
        embeddings: Original embeddings (n_threads, 384)
        n_components: Target dimensions

    Returns:
        Reduced embeddings (n_threads, n_components)
    """
    reducer = UMAP(
        n_components=n_components,
        n_neighbors=15,
        min_dist=0.1,
        metric='cosine',
        random_state=42
    )

    reduced = reducer.fit_transform(embeddings)

    return reduced
```

### 2. Optimal Cluster Count (Elbow Method)

Determine best K for KMeans.

```python
from sklearn.metrics import silhouette_score

def find_optimal_clusters(embeddings: np.ndarray, k_range: range = range(10, 100, 10)):
    """
    Find optimal number of clusters using silhouette score.

    Args:
        embeddings: Thread embeddings
        k_range: Range of K values to try

    Returns:
        Optimal K
    """
    scores = []

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels)
        scores.append((k, score))

    # Return K with highest score
    optimal_k = max(scores, key=lambda x: x[1])[0]

    return optimal_k
```

### 3. Hierarchical Topic Structure

Build topic hierarchy (e.g., "storage" → "heap", "index", "toast").

```python
def build_topic_hierarchy(clusters: Dict, embeddings: np.ndarray) -> Dict:
    """
    Cluster the clusters to create hierarchy.

    Process:
    1. Compute cluster centroids
    2. Cluster centroids to group related topics
    3. Create parent-child relationships
    """
    from scipy.cluster.hierarchy import linkage, fcluster

    # Compute cluster centroids
    centroids = []
    for cluster in clusters.values():
        cluster_embeddings = embeddings[cluster['thread_indices']]
        centroid = cluster_embeddings.mean(axis=0)
        centroids.append(centroid)

    centroids = np.array(centroids)

    # Hierarchical clustering of centroids
    linkage_matrix = linkage(centroids, method='ward')
    parent_labels = fcluster(linkage_matrix, t=10, criterion='maxclust')

    # Build hierarchy
    hierarchy = {}
    for i, parent_id in enumerate(parent_labels):
        if parent_id not in hierarchy:
            hierarchy[parent_id] = []
        hierarchy[parent_id].append(i)

    return hierarchy
```

## Usage Examples

### Basic Usage

```python
from topic_clustering import TopicClusterer
import json

# Load processed threads
with open('data/processed_threads.json', 'r') as f:
    data = json.load(f)
    threads = data['threads']

# Cluster threads
clusterer = TopicClusterer(threads, embedding_model='all-MiniLM-L6-v2')
clustered = clusterer.cluster_threads(method='hdbscan', min_cluster_size=5)

# Save results
clusterer.save_to_json('data/clustered_topics.json')

print(f"Created {len(clustered['clusters'])} topic clusters")
```

### Advanced Usage with Visualization

```python
from topic_clustering import TopicClusterer
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import json

# Load and cluster
with open('data/processed_threads.json', 'r') as f:
    threads = json.load(f)['threads']

clusterer = TopicClusterer(threads)
clustered = clusterer.cluster_threads(method='hdbscan')

# Visualize with t-SNE
tsne = TSNE(n_components=2, random_state=42)
embeddings_2d = tsne.fit_transform(clusterer.embeddings)

# Plot
plt.figure(figsize=(12, 8))
for cluster in clustered['clusters']:
    cluster_indices = [i for i, t in enumerate(threads) if t['thread_id'] in [th['thread_id'] for th in cluster['threads']]]
    plt.scatter(
        embeddings_2d[cluster_indices, 0],
        embeddings_2d[cluster_indices, 1],
        label=cluster['label'][:30],
        alpha=0.6
    )

plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.title('Thread Topic Clusters')
plt.tight_layout()
plt.savefig('topic_clusters.png', dpi=300, bbox_inches='tight')
```

### Finding Threads by Topic

```python
def find_threads_by_topic(clustered_data: Dict, topic_keywords: List[str]) -> List[Dict]:
    """
    Find all threads related to specific topics.

    Args:
        clustered_data: Output from topic_clustering
        topic_keywords: Keywords to search for

    Returns:
        Matching threads
    """
    matching_threads = []

    for cluster in clustered_data['clusters']:
        # Check if any keyword matches cluster keywords
        if any(kw.lower() in ' '.join(cluster['keywords']).lower() for kw in topic_keywords):
            matching_threads.extend(cluster['threads'])

    return matching_threads

# Example: Find all WAL-related discussions
with open('data/clustered_topics.json', 'r') as f:
    clustered = json.load(f)

wal_threads = find_threads_by_topic(clustered, ['wal', 'write ahead log', 'replication'])
print(f"Found {len(wal_threads)} WAL-related threads")
```

## Performance Considerations

### Estimated Metrics

- **Input size:** 200-500 threads
- **Embedding time:** 1-5 minutes (GPU: 30 seconds)
- **Clustering time:** 10-30 seconds
- **Total time:** ~5 minutes (CPU), ~1 minute (GPU)
- **Memory:** ~2-4 GB

### Optimization Strategies

1. **GPU Acceleration**
   ```python
   # Use GPU for embeddings
   model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
   ```

2. **Caching Embeddings**
   ```python
   # Save embeddings to avoid recomputation
   np.save('data/thread_embeddings.npy', embeddings)

   # Load cached embeddings
   embeddings = np.load('data/thread_embeddings.npy')
   ```

3. **Batch Processing**
   ```python
   # Process large datasets in batches
   batch_size = 1000
   for i in range(0, len(threads), batch_size):
       batch = threads[i:i+batch_size]
       # Process batch...
   ```

## Dependencies

```
sentence-transformers>=2.2.0
scikit-learn>=1.3.0
hdbscan>=0.8.33
umap-learn>=0.5.0
keybert>=0.8.0
numpy>=1.24.0
```

## Testing

### Unit Tests

```python
import unittest
from topic_clustering import prepare_thread_text, extract_tfidf_keywords

class TestTopicClustering(unittest.TestCase):
    def test_prepare_thread_text(self):
        thread = {
            'subject': 'Test Subject',
            'aggregated_content': 'This is test content'
        }
        text = prepare_thread_text(thread)
        self.assertIn('Test Subject', text)
        self.assertIn('test content', text)

    def test_keyword_extraction(self):
        texts = [
            'query planner optimization for PostgreSQL',
            'planner cost estimation improvements'
        ]
        keywords = extract_tfidf_keywords(texts, n_keywords=3)
        self.assertIn('planner', ' '.join(keywords))
```

## Troubleshooting

### Too Many Small Clusters

**Issue:** HDBSCAN creates too many small clusters

**Solutions:**
- Increase `min_cluster_size`
- Adjust `cluster_selection_epsilon`
- Switch to KMeans with fixed K

### Poor Cluster Quality

**Issue:** Threads clustered incorrectly

**Solutions:**
- Try better embedding model (all-mpnet-base-v2)
- Use UMAP dimensionality reduction
- Increase text length for embeddings
- Clean thread content more aggressively

### GPU Out of Memory

**Issue:** Embedding generation fails with GPU OOM

**Solutions:**
- Reduce batch size: `model.encode(..., batch_size=16)`
- Use CPU: `model = SentenceTransformer(..., device='cpu')`
- Process in smaller batches

## Next Steps

After clustering completes:
1. Verify cluster quality in `data/clustered_topics.json`
2. Review topic keywords
3. Proceed to `pg_source_context.py` for source code mapping
