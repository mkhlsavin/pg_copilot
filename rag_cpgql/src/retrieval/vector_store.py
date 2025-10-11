"""Vector store for RAG retrieval using ChromaDB."""
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector database for similarity search."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', persist_directory: str = None):
        """
        Initialize vector store.

        Args:
            model_name: Sentence transformer model name
            persist_directory: Directory to persist ChromaDB (optional)
        """
        self.encoder = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name}")

        # Initialize ChromaDB
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        self.qa_collection = None
        self.cpgql_collection = None

    def create_qa_index(self, qa_pairs: List[Dict], collection_name: str = "qa_pairs"):
        """
        Index Q&A pairs by question embeddings.

        Args:
            qa_pairs: List of Q&A dictionaries
            collection_name: Collection name in ChromaDB
        """
        logger.info(f"Creating Q&A index with {len(qa_pairs)} pairs...")

        # Create or get collection
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        self.qa_collection = self.client.create_collection(collection_name)

        # Extract questions
        questions = [qa['question'] for qa in qa_pairs]

        # Generate embeddings
        logger.info("Generating question embeddings...")
        embeddings = self.encoder.encode(questions, show_progress_bar=True)

        # Prepare metadatas (ChromaDB only supports str, int, float, bool)
        metadatas = []
        for qa in qa_pairs:
            meta = {}
            for key, value in qa.items():
                if isinstance(value, list):
                    # Convert lists to comma-separated strings
                    meta[key] = ','.join(str(v) for v in value) if value else ''
                elif isinstance(value, (str, int, float, bool)):
                    meta[key] = value
                else:
                    # Skip unsupported types
                    continue
            metadatas.append(meta)

        # Add to collection
        self.qa_collection.add(
            embeddings=embeddings.tolist(),
            documents=questions,
            metadatas=metadatas,
            ids=[f"qa_{i}" for i in range(len(qa_pairs))]
        )

        logger.info(f"Q&A index created with {len(qa_pairs)} pairs")

    def create_cpgql_index(self, cpgql_examples: List[Dict], collection_name: str = "cpgql_examples"):
        """
        Index CPGQL examples by instruction + input.

        Args:
            cpgql_examples: List of CPGQL example dictionaries
            collection_name: Collection name in ChromaDB
        """
        logger.info(f"Creating CPGQL index with {len(cpgql_examples)} examples...")

        # Create or get collection
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        self.cpgql_collection = self.client.create_collection(collection_name)

        # Combine instruction + input for better matching
        texts = []
        for ex in cpgql_examples:
            # Truncate long code snippets
            input_text = ex.get('input', '')[:500]
            text = f"{ex.get('instruction', '')}\n{input_text}"
            texts.append(text)

        # Generate embeddings
        logger.info("Generating CPGQL embeddings...")
        embeddings = self.encoder.encode(texts, show_progress_bar=True)

        # Prepare metadatas (ChromaDB only supports str, int, float, bool)
        metadatas = []
        for ex in cpgql_examples:
            meta = {}
            for key, value in ex.items():
                if isinstance(value, list):
                    # Convert lists to comma-separated strings
                    meta[key] = ','.join(str(v) for v in value) if value else ''
                elif isinstance(value, (str, int, float, bool)):
                    # Truncate very long strings
                    if isinstance(value, str) and len(value) > 1000:
                        meta[key] = value[:1000]
                    else:
                        meta[key] = value
                else:
                    # Skip unsupported types
                    continue
            metadatas.append(meta)

        # Add to collection
        self.cpgql_collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=[f"cpgql_{i}" for i in range(len(cpgql_examples))]
        )

        logger.info(f"CPGQL index created with {len(cpgql_examples)} examples")

    def search_similar_qa(self, question: str, k: int = 3) -> List[Dict]:
        """
        Retrieve top-k similar Q&A pairs.

        Args:
            question: Query question
            k: Number of results to return

        Returns:
            List of similar Q&A pairs
        """
        if not self.qa_collection:
            logger.warning("Q&A collection not initialized")
            return []

        # Generate query embedding
        embedding = self.encoder.encode([question])

        # Search
        results = self.qa_collection.query(
            query_embeddings=embedding.tolist(),
            n_results=k
        )

        # Combine metadata with similarity scores
        if not results['metadatas'] or not results['distances']:
            return []

        similar_qa = []
        for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
            qa = dict(metadata)
            qa['similarity'] = 1 - distance  # Convert distance to similarity
            qa['distance'] = distance
            similar_qa.append(qa)

        return similar_qa

    def search_similar_cpgql(self, question: str, k: int = 5) -> List[Dict]:
        """
        Retrieve top-k similar CPGQL examples.

        Args:
            question: Query question
            k: Number of results to return

        Returns:
            List of similar CPGQL examples
        """
        if not self.cpgql_collection:
            logger.warning("CPGQL collection not initialized")
            return []

        # Generate query embedding
        embedding = self.encoder.encode([question])

        # Search
        results = self.cpgql_collection.query(
            query_embeddings=embedding.tolist(),
            n_results=k
        )

        # Return metadata (CPGQL examples)
        return results['metadatas'][0] if results['metadatas'] else []

    def get_stats(self) -> Dict:
        """Get statistics about indexed data."""
        stats = {}

        if self.qa_collection:
            stats['qa_count'] = self.qa_collection.count()

        if self.cpgql_collection:
            stats['cpgql_count'] = self.cpgql_collection.count()

        return stats
