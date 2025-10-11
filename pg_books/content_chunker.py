"""
Content Chunker

Splits extracted content (PDFs and web) into semantic chunks for RAG.
Uses intelligent chunking strategies to preserve context and meaning.
"""
import logging
import re
from typing import Dict, List, Optional
import tiktoken

import config
from utils import save_json, get_timestamp


logger = logging.getLogger(__name__)


class ContentChunker:
    """Chunks extracted content into semantic units."""

    def __init__(self, content_items: List[Dict]):
        """
        Initialize chunker.

        Args:
            content_items: List of extracted content items (from PDFs or web)
        """
        self.content_items = content_items
        self.chunks = []
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_content(self) -> List[Dict]:
        """
        Chunk all content items.

        Returns:
            List of chunked content items
        """
        logger.info(f"Chunking {len(self.content_items)} content items")

        for item in self.content_items:
            # Determine chunking strategy based on source type
            source_type = item.get('source_type', 'pdf')

            if source_type == 'web':
                chunks = self._chunk_web_item(item)
            elif source_type in ('README', 'C_COMMENT'):
                chunks = self._chunk_source_code_item(item)
            else:
                chunks = self._chunk_pdf_item(item)

            self.chunks.extend(chunks)

        logger.info(f"Created {len(self.chunks)} chunks from {len(self.content_items)} items")
        return self.chunks

    def _chunk_pdf_item(self, item: Dict) -> List[Dict]:
        """
        Chunk a PDF content item.

        Args:
            item: PDF content item

        Returns:
            List of chunks
        """
        text = item['text']
        tokens = self.count_tokens(text)

        # If text is small enough, keep as single chunk
        if tokens <= config.CHUNK_SIZE:
            return [self._create_chunk(item, text, 0)]

        # Otherwise, split using semantic chunking
        if config.CHUNK_METHOD == 'semantic':
            return self._semantic_chunk(item, text)
        else:
            return self._sliding_window_chunk(item, text)

    def _chunk_web_item(self, item: Dict) -> List[Dict]:
        """
        Chunk a web content item.

        Web items are already fairly granular (paragraphs, code blocks),
        so we only chunk if they exceed the size limit.

        Args:
            item: Web content item

        Returns:
            List of chunks
        """
        text = item['text']
        tokens = self.count_tokens(text)

        # Web items are already paragraph-level, so usually don't need chunking
        if tokens <= config.CHUNK_SIZE:
            return [self._create_chunk(item, text, 0)]

        # For large items (e.g., big code blocks), use semantic chunking
        if config.CHUNK_METHOD == 'semantic':
            return self._semantic_chunk(item, text)
        else:
            return self._sliding_window_chunk(item, text)

    def _chunk_source_code_item(self, item: Dict) -> List[Dict]:
        """
        Chunk a source code documentation item (README or C_COMMENT).

        Source code items use 'content' field instead of 'text'.

        Args:
            item: Source code content item

        Returns:
            List of chunks
        """
        # Source code items use 'content' field
        text = item.get('content', item.get('text', ''))
        tokens = self.count_tokens(text)

        # If text is small enough, keep as single chunk
        if tokens <= config.CHUNK_SIZE:
            return [self._create_chunk(item, text, 0)]

        # Use semantic chunking for larger items
        if config.CHUNK_METHOD == 'semantic':
            return self._semantic_chunk(item, text)
        else:
            return self._sliding_window_chunk(item, text)

    def _semantic_chunk(self, item: Dict, text: str) -> List[Dict]:
        """
        Split text using semantic boundaries (paragraphs, sections).

        Args:
            item: Content item
            text: Text to chunk

        Returns:
            List of chunks
        """
        chunks = []

        # Split by double newlines (paragraphs) or section breaks
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self.count_tokens(para)

            # If single paragraph exceeds chunk size, split it
            if para_tokens > config.CHUNK_SIZE:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(self._create_chunk(item, current_chunk, len(chunks)))
                    current_chunk = ""
                    current_tokens = 0

                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                for sent in sentences:
                    sent_tokens = self.count_tokens(sent)

                    if current_tokens + sent_tokens <= config.CHUNK_SIZE:
                        current_chunk += sent + " "
                        current_tokens += sent_tokens
                    else:
                        if current_chunk:
                            chunks.append(self._create_chunk(item, current_chunk.strip(), len(chunks)))
                        current_chunk = sent + " "
                        current_tokens = sent_tokens

            # If adding paragraph would exceed chunk size, save current chunk
            elif current_tokens + para_tokens > config.CHUNK_SIZE:
                if current_chunk:
                    chunks.append(self._create_chunk(item, current_chunk.strip(), len(chunks)))
                current_chunk = para + "\n\n"
                current_tokens = para_tokens

            # Otherwise add paragraph to current chunk
            else:
                current_chunk += para + "\n\n"
                current_tokens += para_tokens

        # Save final chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(item, current_chunk.strip(), len(chunks)))

        return chunks if chunks else [self._create_chunk(item, text, 0)]

    def _sliding_window_chunk(self, item: Dict, text: str) -> List[Dict]:
        """
        Split text using sliding window with overlap.

        Args:
            item: Content item
            text: Text to chunk

        Returns:
            List of chunks
        """
        chunks = []
        tokens = self.tokenizer.encode(text)

        start = 0
        chunk_idx = 0

        while start < len(tokens):
            end = min(start + config.CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            chunks.append(self._create_chunk(item, chunk_text, chunk_idx))

            # Move window with overlap
            start += config.CHUNK_SIZE - config.CHUNK_OVERLAP
            chunk_idx += 1

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitter (handles common cases)
        # Matches period, exclamation, or question mark followed by space/newline
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunk(self, original_item: Dict, chunk_text: str, chunk_idx: int) -> Dict:
        """
        Create a chunk with metadata.

        Args:
            original_item: Original content item
            chunk_text: Chunk text
            chunk_idx: Chunk index within item

        Returns:
            Chunk dict
        """
        source_type = original_item.get('source_type', 'pdf')

        # Build chunk with common fields
        chunk = {
            'source_type': source_type,
            'text': chunk_text,
            'chapter': original_item.get('chapter'),
            'section': original_item.get('section'),
            'chunk_index': chunk_idx,
            'token_count': self.count_tokens(chunk_text),
            'extracted_at': get_timestamp()
        }

        # Add source-specific metadata
        if source_type == 'web':
            chunk.update({
                'source_url': original_item.get('source_url'),
                'book_name': original_item.get('book_name'),
                'page_number': original_item.get('page_number'),
            })
        elif source_type in ('README', 'C_COMMENT'):
            metadata = original_item.get('metadata', {})
            chunk.update({
                'file_path': metadata.get('file_path'),
                'relative_path': metadata.get('relative_path'),
                'directory': metadata.get('directory'),
                'line_start': metadata.get('line_start')
            })
        else:  # PDF
            chunk.update({
                'pdf_file': original_item.get('pdf_file'),
                'page_number': original_item.get('page_number'),
            })

        # Include tables if present
        if original_item.get('tables'):
            chunk['tables'] = original_item['tables']

        return chunk

    def get_statistics(self) -> Dict:
        """Get chunking statistics."""
        if not self.chunks:
            return {}

        # Token statistics
        token_counts = [c['token_count'] for c in self.chunks]

        # Count by source type
        pdf_chunks = sum(1 for c in self.chunks if c['source_type'] == 'pdf')
        web_chunks = sum(1 for c in self.chunks if c['source_type'] == 'web')

        # Count chunks per chapter
        chapters = {}
        for chunk in self.chunks:
            chapter = chunk.get('chapter', 'Unknown')
            chapters[chapter] = chapters.get(chapter, 0) + 1

        return {
            'total_chunks': len(self.chunks),
            'pdf_chunks': pdf_chunks,
            'web_chunks': web_chunks,
            'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
            'min_tokens': min(token_counts) if token_counts else 0,
            'max_tokens': max(token_counts) if token_counts else 0,
            'unique_chapters': len(chapters),
            'chunks_per_chapter': chapters
        }

    def save_to_json(self, output_path: str = config.CHUNKED_CONTENT_FILE):
        """Save chunks to JSON."""
        save_json(self.chunks, output_path)
        logger.info(f"Saved {len(self.chunks)} chunks to {output_path}")


def main():
    """Main function for standalone execution."""
    import sys
    from utils import setup_logging, load_json

    setup_logging("INFO")

    # Load extracted content (PDF or web)
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Try web content first, fall back to PDF
        import os
        web_file = "data/web_the_internals_of_postgresql.json"
        pdf_file = config.EXTRACTED_CONTENT_FILE

        if os.path.exists(web_file):
            input_file = web_file
        elif os.path.exists(pdf_file):
            input_file = pdf_file
        else:
            logger.error("No extracted content found")
            sys.exit(1)

    logger.info(f"Loading content from: {input_file}")
    content = load_json(input_file)

    # Chunk
    chunker = ContentChunker(content)
    chunks = chunker.chunk_content()

    # Statistics
    stats = chunker.get_statistics()
    print("\n" + "=" * 60)
    print("Chunking Statistics:")
    print("=" * 60)
    for key, value in stats.items():
        if key == 'chunks_per_chapter':
            print(f"\n{key}:")
            for chapter, count in sorted(value.items())[:10]:
                print(f"  {chapter}: {count} chunks")
        else:
            print(f"{key}: {value}")

    # Save
    chunker.save_to_json()

    print("\n" + "=" * 60)
    print(f"Chunking complete!")
    print(f"Output: {config.CHUNKED_CONTENT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
