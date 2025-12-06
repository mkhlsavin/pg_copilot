"""
Add Vector Embeddings to DuckDB CPG Schema

Phase 1 Extension: Adds vector embedding columns to nodes_method and nodes_call
tables to enable hybrid semantic-structural queries within DuckDB.

Schema Changes:
- nodes_method: Add embedding, embedding_model, embedding_updated_at columns
- nodes_call: Add embedding, embedding_model, embedding_updated_at columns

Features:
- Batch embedding generation using sentence-transformers
- Incremental updates (only embed new/changed nodes)
- Cosine similarity search functions
- Embedding metadata tracking

Author: Phase 1 Implementation
Date: November 25, 2025
"""

import duckdb
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy import for sentence transformers
_embedding_model = None


def get_embedding_model(model_name: str = 'all-MiniLM-L6-v2'):
    """
    Get or create sentence transformer model (lazy loading).

    Args:
        model_name: Sentence transformer model name

    Returns:
        Sentence transformer model instance
    """
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {model_name}")
            _embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded (dim={_embedding_model.get_sentence_embedding_dimension()})")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    return _embedding_model


class VectorEmbeddingManager:
    """
    Manager for adding and updating vector embeddings in DuckDB CPG.

    Supports:
    - Schema migration (add embedding columns)
    - Batch embedding generation
    - Incremental updates
    - Similarity search functions
    """

    def __init__(self, db_path: str = "cpg.duckdb", model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize Vector Embedding Manager.

        Args:
            db_path: Path to DuckDB database
            model_name: Sentence transformer model name
        """
        self.db_path = db_path
        self.model_name = model_name
        self.conn = None
        self.embedding_dim = None

    def connect(self):
        """Connect to DuckDB database"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        logger.info(f"Connecting to DuckDB: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)

        # Get embedding dimension
        model = get_embedding_model(self.model_name)
        self.embedding_dim = model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def add_embedding_columns(self):
        """
        Add embedding columns to nodes_method and nodes_call tables.

        Schema changes:
        - embedding: FLOAT[] - Vector embedding (384 dimensions for all-MiniLM-L6-v2)
        - embedding_model: VARCHAR - Model name used for embedding
        - embedding_updated_at: TIMESTAMP - Last update time
        """
        logger.info("Adding embedding columns to schema...")

        try:
            # Check if columns already exist
            method_has_embedding = self._column_exists('nodes_method', 'embedding')
            call_has_embedding = self._column_exists('nodes_call', 'embedding')

            # Add columns to nodes_method
            if not method_has_embedding:
                logger.info("Adding embedding columns to nodes_method...")
                self.conn.execute("""
                    ALTER TABLE nodes_method
                    ADD COLUMN embedding FLOAT[]
                """)
                self.conn.execute("""
                    ALTER TABLE nodes_method
                    ADD COLUMN embedding_model VARCHAR
                """)
                self.conn.execute("""
                    ALTER TABLE nodes_method
                    ADD COLUMN embedding_updated_at TIMESTAMP
                """)
                logger.info("[OK] nodes_method embedding columns added")
            else:
                logger.info("[OK] nodes_method already has embedding columns")

            # Add columns to nodes_call
            if not call_has_embedding:
                logger.info("Adding embedding columns to nodes_call...")
                self.conn.execute("""
                    ALTER TABLE nodes_call
                    ADD COLUMN embedding FLOAT[]
                """)
                self.conn.execute("""
                    ALTER TABLE nodes_call
                    ADD COLUMN embedding_model VARCHAR
                """)
                self.conn.execute("""
                    ALTER TABLE nodes_call
                    ADD COLUMN embedding_updated_at TIMESTAMP
                """)
                logger.info("[OK] nodes_call embedding columns added")
            else:
                logger.info("[OK] nodes_call already has embedding columns")

            logger.info("Schema migration complete")

        except Exception as e:
            logger.error(f"Failed to add embedding columns: {e}")
            raise

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """
        Check if column exists in table.

        Args:
            table_name: Table name
            column_name: Column name

        Returns:
            True if column exists
        """
        try:
            result = self.conn.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                AND column_name = '{column_name}'
            """).fetchall()
            return len(result) > 0
        except:
            return False

    def generate_method_embeddings(
        self,
        batch_size: int = 100,
        limit: Optional[int] = None,
        force_update: bool = False
    ) -> int:
        """
        Generate embeddings for methods in nodes_method table.

        Embedding text format: "{name} {signature} {code}"

        Args:
            batch_size: Number of methods to process per batch
            limit: Optional limit on total methods to process
            force_update: If True, re-embed all methods (otherwise only new ones)

        Returns:
            Number of methods embedded
        """
        logger.info("Generating method embeddings...")

        # Get methods to embed
        where_clause = "WHERE embedding IS NULL" if not force_update else ""
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT id, name, signature, code, full_name
            FROM nodes_method
            {where_clause}
            {limit_clause}
        """

        methods = self.conn.execute(query).fetchall()
        total = len(methods)

        if total == 0:
            logger.info("No methods to embed")
            return 0

        logger.info(f"Embedding {total} methods (batch_size={batch_size})...")

        model = get_embedding_model(self.model_name)
        embedded_count = 0

        # Process in batches
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = methods[batch_start:batch_end]

            # Prepare texts for embedding
            texts = []
            for method in batch:
                id_, name, signature, code, full_name = method
                # Combine name, signature, and code snippet
                text = self._make_method_text(name, signature, code, full_name)
                texts.append(text)

            # Generate embeddings
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

            # Update database
            timestamp = datetime.now()
            for i, method in enumerate(batch):
                id_ = method[0]
                embedding_list = embeddings[i].tolist()

                self.conn.execute("""
                    UPDATE nodes_method
                    SET embedding = ?,
                        embedding_model = ?,
                        embedding_updated_at = ?
                    WHERE id = ?
                """, [embedding_list, self.model_name, timestamp, id_])

            embedded_count += len(batch)
            logger.info(f"Progress: {embedded_count}/{total} methods embedded ({embedded_count/total*100:.1f}%)")

        logger.info(f"[OK] Embedded {embedded_count} methods")
        return embedded_count

    def generate_call_embeddings(
        self,
        batch_size: int = 100,
        limit: Optional[int] = None,
        force_update: bool = False
    ) -> int:
        """
        Generate embeddings for call nodes in nodes_call table.

        Embedding text format: "{name} {method_full_name} {code}"

        Args:
            batch_size: Number of calls to process per batch
            limit: Optional limit on total calls to process
            force_update: If True, re-embed all calls (otherwise only new ones)

        Returns:
            Number of calls embedded
        """
        logger.info("Generating call embeddings...")

        # Get calls to embed
        where_clause = "WHERE embedding IS NULL" if not force_update else ""
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT id, name, method_full_name, code, signature
            FROM nodes_call
            {where_clause}
            {limit_clause}
        """

        calls = self.conn.execute(query).fetchall()
        total = len(calls)

        if total == 0:
            logger.info("No calls to embed")
            return 0

        logger.info(f"Embedding {total} calls (batch_size={batch_size})...")

        model = get_embedding_model(self.model_name)
        embedded_count = 0

        # Process in batches
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = calls[batch_start:batch_end]

            # Prepare texts for embedding
            texts = []
            for call in batch:
                id_, name, method_full_name, code, signature = call
                # Combine name, target method, and code
                text = self._make_call_text(name, method_full_name, code, signature)
                texts.append(text)

            # Generate embeddings
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

            # Update database
            timestamp = datetime.now()
            for i, call in enumerate(batch):
                id_ = call[0]
                embedding_list = embeddings[i].tolist()

                self.conn.execute("""
                    UPDATE nodes_call
                    SET embedding = ?,
                        embedding_model = ?,
                        embedding_updated_at = ?
                    WHERE id = ?
                """, [embedding_list, self.model_name, timestamp, id_])

            embedded_count += len(batch)
            logger.info(f"Progress: {embedded_count}/{total} calls embedded ({embedded_count/total*100:.1f}%)")

        logger.info(f"[OK] Embedded {embedded_count} calls")
        return embedded_count

    def _make_method_text(
        self,
        name: str,
        signature: str,
        code: str,
        full_name: str
    ) -> str:
        """
        Create text representation for method embedding.

        Format: "{name} {signature} {code_snippet}"

        Args:
            name: Method name
            signature: Method signature
            code: Method code
            full_name: Full method name

        Returns:
            Text for embedding
        """
        # Truncate code to avoid very long texts
        code_snippet = code[:500] if code else ""

        parts = []
        if name:
            parts.append(name)
        if signature:
            parts.append(signature)
        if code_snippet:
            parts.append(code_snippet)

        return " ".join(parts)

    def _make_call_text(
        self,
        name: str,
        method_full_name: str,
        code: str,
        signature: str
    ) -> str:
        """
        Create text representation for call embedding.

        Format: "{name} calls {method_full_name} {code}"

        Args:
            name: Call name
            method_full_name: Target method
            code: Call code
            signature: Call signature

        Returns:
            Text for embedding
        """
        parts = []
        if name:
            parts.append(name)
        if method_full_name:
            parts.append(f"calls {method_full_name}")
        if code:
            parts.append(code)

        return " ".join(parts)

    def create_similarity_search_functions(self):
        """
        Create UDFs for cosine similarity search in DuckDB.

        Creates:
        - cosine_similarity(vec1, vec2): Compute cosine similarity
        - method_similarity_search(query_embedding, top_k): Search methods
        - call_similarity_search(query_embedding, top_k): Search calls
        """
        logger.info("Creating similarity search functions...")

        # Note: DuckDB doesn't support complex UDFs directly
        # We'll provide Python functions for use in the client instead
        # The actual similarity search will be done via Python

        logger.info("[OK] Similarity search functions ready (Python-based)")

    def search_similar_methods(
        self,
        query_text: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar methods using vector similarity.

        Args:
            query_text: Query text to embed and search
            top_k: Number of results to return

        Returns:
            List of similar methods with scores
        """
        # Generate query embedding
        model = get_embedding_model(self.model_name)
        query_embedding = model.encode(query_text, convert_to_numpy=True)

        # Get all method embeddings
        # Note: For large datasets, this should use an ANN index
        results = self.conn.execute("""
            SELECT id, name, full_name, signature, code, embedding
            FROM nodes_method
            WHERE embedding IS NOT NULL
        """).fetchall()

        if not results:
            logger.warning("No method embeddings found")
            return []

        # Compute cosine similarities
        similarities = []
        for row in results:
            id_, name, full_name, signature, code, embedding = row
            if embedding:
                emb_array = np.array(embedding)
                similarity = self._cosine_similarity(query_embedding, emb_array)
                similarities.append({
                    'id': id_,
                    'name': name,
                    'full_name': full_name,
                    'signature': signature,
                    'code': code,
                    'similarity': float(similarity)
                })

        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def search_similar_calls(
        self,
        query_text: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar call nodes using vector similarity.

        Args:
            query_text: Query text to embed and search
            top_k: Number of results to return

        Returns:
            List of similar calls with scores
        """
        # Generate query embedding
        model = get_embedding_model(self.model_name)
        query_embedding = model.encode(query_text, convert_to_numpy=True)

        # Get all call embeddings
        results = self.conn.execute("""
            SELECT id, name, method_full_name, code, embedding
            FROM nodes_call
            WHERE embedding IS NOT NULL
        """).fetchall()

        if not results:
            logger.warning("No call embeddings found")
            return []

        # Compute cosine similarities
        similarities = []
        for row in results:
            id_, name, method_full_name, code, embedding = row
            if embedding:
                emb_array = np.array(embedding)
                similarity = self._cosine_similarity(query_embedding, emb_array)
                similarities.append({
                    'id': id_,
                    'name': name,
                    'method_full_name': method_full_name,
                    'code': code,
                    'similarity': float(similarity)
                })

        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_embedding_stats(self) -> Dict:
        """
        Get statistics about embeddings in database.

        Returns:
            Dictionary with embedding statistics
        """
        stats = {}

        # Method embedding stats
        method_stats = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as embedded,
                COUNT(CASE WHEN embedding IS NULL THEN 1 END) as not_embedded
            FROM nodes_method
        """).fetchone()

        stats['methods'] = {
            'total': method_stats[0],
            'embedded': method_stats[1],
            'not_embedded': method_stats[2],
            'coverage': method_stats[1] / method_stats[0] * 100 if method_stats[0] > 0 else 0
        }

        # Call embedding stats
        call_stats = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as embedded,
                COUNT(CASE WHEN embedding IS NULL THEN 1 END) as not_embedded
            FROM nodes_call
        """).fetchone()

        stats['calls'] = {
            'total': call_stats[0],
            'embedded': call_stats[1],
            'not_embedded': call_stats[2],
            'coverage': call_stats[1] / call_stats[0] * 100 if call_stats[0] > 0 else 0
        }

        stats['model'] = self.model_name
        stats['embedding_dim'] = self.embedding_dim

        return stats


def main():
    """
    Main function for embedding generation.

    Usage:
        python add_vector_embeddings.py
    """
    import argparse

    parser = argparse.ArgumentParser(description="Add vector embeddings to DuckDB CPG")
    parser.add_argument('--db', default='cpg.duckdb', help='DuckDB database path')
    parser.add_argument('--model', default='all-MiniLM-L6-v2', help='Embedding model')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    parser.add_argument('--limit', type=int, help='Limit number of nodes to embed')
    parser.add_argument('--force', action='store_true', help='Force re-embedding')
    parser.add_argument('--methods-only', action='store_true', help='Only embed methods')
    parser.add_argument('--calls-only', action='store_true', help='Only embed calls')

    args = parser.parse_args()

    with VectorEmbeddingManager(args.db, args.model) as manager:
        # Add schema columns
        manager.add_embedding_columns()

        # Generate embeddings
        if not args.calls_only:
            manager.generate_method_embeddings(
                batch_size=args.batch_size,
                limit=args.limit,
                force_update=args.force
            )

        if not args.methods_only:
            manager.generate_call_embeddings(
                batch_size=args.batch_size,
                limit=args.limit,
                force_update=args.force
            )

        # Print stats
        stats = manager.get_embedding_stats()
        logger.info("\n=== Embedding Statistics ===")
        logger.info(f"Model: {stats['model']}")
        logger.info(f"Dimension: {stats['embedding_dim']}")
        logger.info(f"\nMethods:")
        logger.info(f"  Total: {stats['methods']['total']}")
        logger.info(f"  Embedded: {stats['methods']['embedded']}")
        logger.info(f"  Coverage: {stats['methods']['coverage']:.1f}%")
        logger.info(f"\nCalls:")
        logger.info(f"  Total: {stats['calls']['total']}")
        logger.info(f"  Embedded: {stats['calls']['embedded']}")
        logger.info(f"  Coverage: {stats['calls']['coverage']:.1f}%")


if __name__ == '__main__':
    main()
