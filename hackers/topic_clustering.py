"""
Topic Clustering Module

Clusters email threads by topic using semantic embeddings.
"""
import logging
import os
from collections import Counter, defaultdict
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    logging.warning("HDBSCAN not available, using KMeans only")

import config
from utils import load_json, save_json, get_timestamp


logger = logging.getLogger(__name__)


class TopicClusterer:
    """Clusters threads by topic using embeddings."""

    def __init__(self, threads: List[Dict], embedding_model: str = config.EMBEDDING_MODEL):
        """
        Initialize clusterer.

        Args:
            threads: List of processed threads
            embedding_model: HuggingFace model name for embeddings
        """
        self.threads = threads
        self.embedding_model_name = embedding_model
        self.model = None
        self.embeddings = None
        self.labels = None
        self.clusters = {}

    def load_model(self):
        """Load sentence transformer model."""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.model = SentenceTransformer(self.embedding_model_name)
        logger.info("Model loaded successfully")

    def prepare_thread_texts(self) -> List[str]:
        """
        Extract representative text from threads.

        Returns:
            List of text strings
        """
        texts = []

        for thread in self.threads:
            # Weight subject more heavily
            subject = thread.get('subject', '')
            content = thread.get('aggregated_content', '')[:2000]  # Limit length

            # Repeat subject for higher weight
            text = f"{subject} {subject} {subject} {content}"
            texts.append(text)

        return texts

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings

        Returns:
            Embeddings array (n_texts, embedding_dim)
        """
        logger.info(f"Generating embeddings for {len(texts)} threads...")

        # Check for cached embeddings
        if os.path.exists(config.EMBEDDINGS_CACHE_FILE):
            try:
                embeddings = np.load(config.EMBEDDINGS_CACHE_FILE)
                if len(embeddings) == len(texts):
                    logger.info("Loaded cached embeddings")
                    return embeddings
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}")

        # Generate new embeddings
        embeddings = self.model.encode(
            texts,
            show_progress_bar=config.SHOW_PROGRESS,
            batch_size=32,
            convert_to_numpy=True
        )

        # Cache embeddings
        np.save(config.EMBEDDINGS_CACHE_FILE, embeddings)
        logger.info(f"Generated and cached embeddings: {embeddings.shape}")

        return embeddings

    def cluster_hdbscan(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Cluster using HDBSCAN.

        Args:
            embeddings: Thread embeddings

        Returns:
            Cluster labels
        """
        if not HDBSCAN_AVAILABLE:
            logger.warning("HDBSCAN not available, falling back to KMeans")
            return self.cluster_kmeans(embeddings)

        logger.info(f"Clustering with HDBSCAN (min_cluster_size={config.MIN_CLUSTER_SIZE})")

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=config.MIN_CLUSTER_SIZE,
            min_samples=2,
            metric='euclidean',
            cluster_selection_epsilon=0.5,
            core_dist_n_jobs=-1
        )

        labels = clusterer.fit_predict(embeddings)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        logger.info(f"HDBSCAN found {n_clusters} clusters, {n_noise} noise points")

        return labels

    def cluster_kmeans(self, embeddings: np.ndarray, n_clusters: int = None) -> np.ndarray:
        """
        Cluster using K-Means.

        Args:
            embeddings: Thread embeddings
            n_clusters: Number of clusters (auto-determine if None)

        Returns:
            Cluster labels
        """
        if n_clusters is None:
            # Auto-determine: ~10-15% of threads, but not more than available samples
            n_clusters = max(2, min(50, len(embeddings) // 10))
            n_clusters = min(n_clusters, len(embeddings))

        logger.info(f"Clustering with KMeans (n_clusters={n_clusters})")

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=config.RANDOM_SEED,
            n_init=10,
            max_iter=300
        )

        labels = kmeans.fit_predict(embeddings)

        logger.info(f"KMeans created {n_clusters} clusters")

        return labels

    def extract_tfidf_keywords(self, thread_texts: List[str], n_keywords: int = config.N_KEYWORDS) -> List[str]:
        """
        Extract keywords using TF-IDF.

        Args:
            thread_texts: List of thread texts
            n_keywords: Number of keywords to extract

        Returns:
            List of keywords
        """
        if not thread_texts:
            return []

        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(thread_texts)
            feature_names = vectorizer.get_feature_names_out()

            # Sum TF-IDF scores
            scores = tfidf_matrix.sum(axis=0).A1
            top_indices = scores.argsort()[-n_keywords:][::-1]

            keywords = [feature_names[i] for i in top_indices]
            return keywords

        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}")
            return []

    def build_clusters(self, texts: List[str], labels: np.ndarray) -> Dict:
        """
        Build cluster structures with metadata.

        Args:
            texts: Thread texts
            labels: Cluster labels

        Returns:
            Clusters dictionary
        """
        logger.info("Building cluster structures...")

        # Group threads by cluster
        cluster_threads = defaultdict(list)

        for i, label in enumerate(labels):
            if label == -1:  # Skip noise
                continue

            thread = self.threads[i]
            cluster_threads[int(label)].append({
                'thread_id': thread.get('thread_id', ''),
                'subject': thread.get('subject', ''),
                'message_count': thread.get('message_count', 0),
                'start_date': thread.get('start_date', ''),
                'end_date': thread.get('end_date', ''),
                'thread_index': i
            })

        # Build cluster metadata
        clusters = []

        for cluster_id, threads in tqdm(cluster_threads.items(), desc="Processing clusters"):
            if len(threads) < config.MIN_CLUSTER_SIZE:
                continue

            # Get texts for this cluster
            cluster_texts = [texts[t['thread_index']] for t in threads]

            # Extract keywords
            keywords = self.extract_tfidf_keywords(cluster_texts)

            # Create label
            label_parts = keywords[:3] if len(keywords) >= 3 else keywords
            label = '_'.join(label_parts).lower().replace(' ', '_')

            cluster = {
                'cluster_id': cluster_id,
                'label': label,
                'keywords': keywords,
                'thread_count': len(threads),
                'threads': threads
            }

            clusters.append(cluster)

        logger.info(f"Built {len(clusters)} valid clusters")

        return {'clusters': clusters}

    def cluster_threads(
        self,
        method: str = config.CLUSTERING_METHOD,
        n_clusters: int = config.N_CLUSTERS
    ) -> Dict:
        """
        Cluster threads by topic.

        Args:
            method: 'hdbscan' or 'kmeans'
            n_clusters: Number of clusters (for KMeans)

        Returns:
            Clustered topics dictionary
        """
        # Handle empty threads
        if not self.threads:
            logger.warning("No threads to cluster")
            return {'clusters': []}

        # Load model
        if self.model is None:
            self.load_model()

        # Prepare texts
        texts = self.prepare_thread_texts()

        if not texts:
            logger.warning("No texts generated from threads")
            return {'clusters': []}

        # Generate embeddings
        self.embeddings = self.generate_embeddings(texts)

        if len(self.embeddings) == 0:
            logger.warning("No embeddings generated")
            return {'clusters': []}

        # Cluster
        if method == 'hdbscan':
            self.labels = self.cluster_hdbscan(self.embeddings)
        elif method == 'kmeans':
            self.labels = self.cluster_kmeans(self.embeddings, n_clusters)
        else:
            raise ValueError(f"Unknown clustering method: {method}")

        # Build clusters
        self.clusters = self.build_clusters(texts, self.labels)

        return self.clusters

    def save_to_json(self, output_path: str = config.CLUSTERED_TOPICS_FILE):
        """Save clustered topics to JSON."""
        output = {
            **self.clusters,
            'metadata': {
                'total_clusters': len(self.clusters.get('clusters', [])),
                'total_threads': len(self.threads),
                'embedding_model': self.embedding_model_name,
                'clustering_method': config.CLUSTERING_METHOD,
                'min_cluster_size': config.MIN_CLUSTER_SIZE,
                'clustered_at': get_timestamp()
            }
        }

        save_json(output, output_path)
        logger.info(f"Saved {len(self.clusters.get('clusters', []))} clusters to {output_path}")


def main():
    """Main function for standalone execution."""
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Starting topic clustering")

    # Load processed threads
    data = load_json(config.PROCESSED_THREADS_FILE)
    threads = data.get('threads', [])
    logger.info(f"Loaded {len(threads)} threads")

    # Cluster threads
    clusterer = TopicClusterer(threads)
    clusters = clusterer.cluster_threads()

    logger.info(f"Created {len(clusters.get('clusters', []))} topic clusters")

    # Save results
    clusterer.save_to_json()

    logger.info("Topic clustering complete")


if __name__ == '__main__':
    main()
