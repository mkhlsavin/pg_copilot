"""Real ChromaDB vector store implementation for CodeGraph."""
import chromadb
from chromadb.config import Settings
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStoreReal:
    """Real ChromaDB-based vector store for Q&A pairs and SQL examples."""

    def __init__(self, persist_directory: str = None):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        if persist_directory is None:
            persist_directory = str(Path(__file__).parent.parent.parent / "chroma_db")

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize embedding model
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Collections
        self.qa_collection = None
        self.sql_collection = None

        logger.info(f"ChromaDB initialized at: {persist_directory}")

    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.client.get_collection(name=name)
        except Exception:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )

    def initialize_collections(self):
        """Initialize Q&A and SQL examples collections."""
        self.qa_collection = self._get_or_create_collection("qa_pairs")
        self.sql_collection = self._get_or_create_collection("sql_examples")
        logger.info("Collections initialized")

    def index_qa_pairs(self, qa_file: Path, max_items: int = None):
        """
        Index Q&A pairs into ChromaDB.

        Args:
            qa_file: Path to JSONL file with Q&A pairs
            max_items: Maximum number of items to index (for testing)
        """
        logger.info(f"Indexing Q&A pairs from: {qa_file}")

        if self.qa_collection is None:
            self.initialize_collections()

        # Check if already indexed
        existing_count = self.qa_collection.count()
        if existing_count > 0:
            logger.info(f"Collection already has {existing_count} items")
            return existing_count

        # Read Q&A pairs
        qa_pairs = []
        with open(qa_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if max_items and i >= max_items:
                    break
                try:
                    data = json.loads(line)
                    qa_pairs.append(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping line {i}: {e}")
                    continue

        if not qa_pairs:
            logger.error("No Q&A pairs loaded!")
            return 0

        logger.info(f"Loaded {len(qa_pairs)} Q&A pairs")

        # Prepare data for indexing
        documents = []
        metadatas = []
        ids = []

        for i, item in enumerate(qa_pairs):
            question = item.get('question', '')
            answer = item.get('answer', '')

            # Combined text for embedding
            combined_text = f"Question: {question}\nAnswer: {answer}"
            documents.append(combined_text)

            # Metadata
            metadata = {
                'question': question[:500],  # Truncate for metadata
                'answer': answer[:500],
                'difficulty': item.get('difficulty', 'unknown'),
                'source': item.get('source', 'unknown')
            }

            # Add topics if available
            if 'topics' in item and isinstance(item['topics'], list):
                metadata['topics'] = ','.join(item['topics'][:5])  # First 5 topics

            metadatas.append(metadata)
            ids.append(f"qa_{i}")

        # Generate embeddings
        logger.info("Generating embeddings for Q&A pairs...")
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Index in batches
        batch_size = 100
        total_indexed = 0

        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))

            self.qa_collection.add(
                embeddings=embeddings[i:batch_end].tolist(),
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end]
            )

            total_indexed += (batch_end - i)
            logger.info(f"Indexed {total_indexed}/{len(documents)} Q&A pairs")

        logger.info(f"Successfully indexed {total_indexed} Q&A pairs")
        return total_indexed

    def index_sql_examples(self, sql_file: Path, max_items: int = None):
        """
        Index SQL examples into ChromaDB.

        Args:
            sql_file: Path to JSON file with SQL examples
            max_items: Maximum number of items to index (for testing)
        """
        logger.info(f"Indexing SQL examples from: {sql_file}")

        if self.sql_collection is None:
            self.initialize_collections()

        # Check if already indexed
        existing_count = self.sql_collection.count()
        if existing_count > 0:
            logger.info(f"Collection already has {existing_count} items")
            return existing_count

        # Read SQL examples
        with open(sql_file, 'r', encoding='utf-8') as f:
            examples_data = json.load(f)

        # Handle both list and dict formats
        if isinstance(examples_data, list):
            examples = examples_data
        else:
            examples = examples_data.get('examples', [])

        if max_items:
            examples = examples[:max_items]

        if not examples:
            logger.error("No SQL examples loaded!")
            return 0

        logger.info(f"Loaded {len(examples)} SQL examples")

        # Prepare data for indexing
        documents = []
        metadatas = []
        ids = []

        for i, item in enumerate(examples):
            question = item.get('question', '')
            sql = item.get('sql', '')
            query_type = item.get('query_type', 'unknown')

            if not question or not sql:
                logger.warning(f"Skipping item {i}: missing question or sql")
                continue

            # Combined text for embedding
            combined_text = f"{question} {sql}"
            documents.append(combined_text)

            # Metadata
            metadata = {
                'question': question[:500],
                'sql': sql[:1000],  # SQL queries can be longer
                'query_type': query_type,
                'category': item.get('category', 'sql'),
                'complexity': item.get('complexity', 'unknown')
            }

            metadatas.append(metadata)
            ids.append(f"sql_{i}")

        # Generate embeddings
        logger.info("Generating embeddings for SQL examples...")
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Index in batches
        batch_size = 100
        total_indexed = 0

        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))

            self.sql_collection.add(
                embeddings=embeddings[i:batch_end].tolist(),
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end]
            )

            total_indexed += (batch_end - i)
            logger.info(f"Indexed {total_indexed}/{len(documents)} SQL examples")

        logger.info(f"Successfully indexed {total_indexed} SQL examples")
        return total_indexed

    def retrieve_qa(
        self,
        query: str,
        top_k: int = 3,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve similar Q&A pairs.

        Args:
            query: Query text
            top_k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of Q&A pairs with metadata
        """
        if self.qa_collection is None:
            self.initialize_collections()

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0]

        # Retrieve from ChromaDB
        results = self.qa_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=filter_dict
        )

        # Format results
        qa_pairs = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                qa_pairs.append({
                    'question': metadata.get('question', ''),
                    'answer': metadata.get('answer', ''),
                    'difficulty': metadata.get('difficulty', 'unknown'),
                    'source': metadata.get('source', 'unknown'),
                    'similarity': 1 - distance  # Convert distance to similarity
                })

        return qa_pairs

    def retrieve_sql(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        query_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant SQL examples.

        Args:
            query: Query text
            keywords: Optional keywords to boost relevance
            query_type: Optional filter by query type (find_callees, find_callers, etc.)
            top_k: Number of results to return

        Returns:
            List of SQL examples
        """
        if self.sql_collection is None:
            self.initialize_collections()

        # Combine query with keywords for better retrieval
        if keywords:
            enhanced_query = f"{query} {' '.join(keywords)}"
        else:
            enhanced_query = query

        # Generate query embedding
        query_embedding = self.embedding_model.encode([enhanced_query])[0]

        # Build filter if query_type specified
        where_filter = {"query_type": query_type} if query_type else None

        # Retrieve from ChromaDB
        results = self.sql_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where_filter
        )

        # Format results
        examples = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                examples.append({
                    'question': metadata.get('question', ''),
                    'sql': metadata.get('sql', ''),
                    'query_type': metadata.get('query_type', 'unknown'),
                    'category': metadata.get('category', 'unknown'),
                    'complexity': metadata.get('complexity', 'unknown'),
                    'similarity': 1 - distance
                })

        return examples

    def get_stats(self) -> Dict:
        """Get statistics about indexed data."""
        if self.qa_collection is None or self.sql_collection is None:
            self.initialize_collections()

        return {
            'qa_pairs_count': self.qa_collection.count(),
            'sql_examples_count': self.sql_collection.count()
        }

    def reset(self):
        """Reset (clear) all collections - USE WITH CAUTION!"""
        logger.warning("Resetting all collections!")
        if self.qa_collection:
            self.client.delete_collection("qa_pairs")
        if self.sql_collection:
            self.client.delete_collection("sql_examples")
        self.qa_collection = None
        self.sql_collection = None
        logger.info("All collections reset")
