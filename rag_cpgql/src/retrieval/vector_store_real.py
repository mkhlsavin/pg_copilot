"""Real ChromaDB vector store implementation for RAG-CPGQL."""
import chromadb
from chromadb.config import Settings
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStoreReal:
    """Real ChromaDB-based vector store for Q&A pairs and CPGQL examples."""

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
        self.cpgql_collection = None

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
        """Initialize Q&A and CPGQL collections."""
        self.qa_collection = self._get_or_create_collection("qa_pairs")
        self.cpgql_collection = self._get_or_create_collection("cpgql_examples")
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

    def index_cpgql_examples(self, cpgql_file: Path, max_items: int = None):
        """
        Index CPGQL examples into ChromaDB.

        Args:
            cpgql_file: Path to JSON file with CPGQL examples
            max_items: Maximum number of items to index (for testing)
        """
        logger.info(f"Indexing CPGQL examples from: {cpgql_file}")

        if self.cpgql_collection is None:
            self.initialize_collections()

        # Check if already indexed
        existing_count = self.cpgql_collection.count()
        if existing_count > 0:
            logger.info(f"Collection already has {existing_count} items")
            return existing_count

        # Read CPGQL examples
        with open(cpgql_file, 'r', encoding='utf-8') as f:
            examples_data = json.load(f)

        # Handle both list and dict formats
        if isinstance(examples_data, list):
            examples = examples_data
        else:
            examples = examples_data.get('examples', [])

        if max_items:
            examples = examples[:max_items]

        if not examples:
            logger.error("No CPGQL examples loaded!")
            return 0

        logger.info(f"Loaded {len(examples)} CPGQL examples")

        # Prepare data for indexing
        documents = []
        metadatas = []
        ids = []

        for i, item in enumerate(examples):
            # Handle different formats
            if 'question' in item and 'query' in item:
                # Format 1: Direct question-query pairs
                question = item.get('question', '')
                query = item.get('query', '')
            elif 'instruction' in item and 'output' in item:
                # Format 2: instruction-output pairs (extract CPGQL from output)
                question = item.get('instruction', '')[:200]  # Truncate
                output = item.get('output', '')

                # Extract query from output (contains JSON with queries array)
                try:
                    # Try to extract query from JSON-like output
                    if 'queries' in output:
                        query = output  # Store full output
                    else:
                        query = output[:500]
                except:
                    query = output[:500]
            else:
                # Skip invalid items
                logger.warning(f"Skipping item {i}: unknown format")
                continue

            if not question or not query:
                continue

            # Combined text for embedding (focus on question/instruction)
            combined_text = f"{question} {query}"
            documents.append(combined_text)

            # Metadata
            metadata = {
                'question': question[:500],
                'query': query[:500],
                'category': item.get('category', 'cpgql'),
                'complexity': item.get('complexity', 'unknown')
            }

            metadatas.append(metadata)
            ids.append(f"cpgql_{i}")

        # Generate embeddings
        logger.info("Generating embeddings for CPGQL examples...")
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

            self.cpgql_collection.add(
                embeddings=embeddings[i:batch_end].tolist(),
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end]
            )

            total_indexed += (batch_end - i)
            logger.info(f"Indexed {total_indexed}/{len(documents)} CPGQL examples")

        logger.info(f"Successfully indexed {total_indexed} CPGQL examples")
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

    def retrieve_cpgql(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant CPGQL examples.

        Args:
            query: Query text
            keywords: Optional keywords to boost relevance
            top_k: Number of results to return

        Returns:
            List of CPGQL examples
        """
        if self.cpgql_collection is None:
            self.initialize_collections()

        # Combine query with keywords for better retrieval
        if keywords:
            enhanced_query = f"{query} {' '.join(keywords)}"
        else:
            enhanced_query = query

        # Generate query embedding
        query_embedding = self.embedding_model.encode([enhanced_query])[0]

        # Retrieve from ChromaDB
        results = self.cpgql_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )

        # Format results
        examples = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                examples.append({
                    'question': metadata.get('question', ''),
                    'query': metadata.get('query', ''),
                    'category': metadata.get('category', 'unknown'),
                    'complexity': metadata.get('complexity', 'unknown'),
                    'similarity': 1 - distance
                })

        return examples

    def get_stats(self) -> Dict:
        """Get statistics about indexed data."""
        if self.qa_collection is None or self.cpgql_collection is None:
            self.initialize_collections()

        return {
            'qa_pairs_count': self.qa_collection.count(),
            'cpgql_examples_count': self.cpgql_collection.count()
        }

    def reset(self):
        """Reset (clear) all collections - USE WITH CAUTION!"""
        logger.warning("Resetting all collections!")
        if self.qa_collection:
            self.client.delete_collection("qa_pairs")
        if self.cpgql_collection:
            self.client.delete_collection("cpgql_examples")
        self.qa_collection = None
        self.cpgql_collection = None
        logger.info("All collections reset")
