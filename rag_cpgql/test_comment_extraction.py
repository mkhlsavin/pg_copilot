"""
Test comment extraction from Joern CPG.

This script tests the comment extraction queries to verify:
1. Joern CPG has comment information
2. Query syntax is correct
3. We can extract meaningful documentation

Run with: python test_comment_extraction.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.execution.joern_client import JoernClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_joern_connection():
    """Test basic Joern connection."""
    logger.info("Testing Joern connection...")
    client = JoernClient(server_endpoint='localhost:8080')

    if not client.connect():
        logger.error("Failed to connect to Joern")
        return None

    result = client.execute_query("cpg.method.name.take(1).l")
    if result['success']:
        logger.info("✓ Joern connection successful")
        return client
    else:
        logger.error(f"✗ Joern connection failed: {result.get('error')}")
        return None


def test_comment_nodes_exist(client):
    """Test if CPG has comment nodes."""
    logger.info("\nTesting if CPG contains comment nodes...")

    query = "cpg.comment.size"
    result = client.execute_query(query)

    if result['success']:
        raw_result = result.get('result', '').strip()
        # Parse "val res288: Int = 12591916" format
        try:
            comment_count = int(raw_result.split('=')[-1].strip())
            logger.info(f"✓ CPG contains {comment_count:,} comment nodes")
            return comment_count
        except:
            logger.error(f"✗ Failed to parse comment count: {raw_result}")
            return 0
    else:
        logger.error(f"✗ Failed to query comments: {result.get('error')}")
        return 0


def test_method_comment_extraction(client, limit=5):
    """Test extracting comments from methods."""
    logger.info(f"\nTesting method comment extraction (limit={limit})...")

    query = f"""
    cpg.method
      .filter(m => m.comment.nonEmpty)
      .take({limit})
      .map {{ m =>
        val name = m.name
        val file = m.file.name.headOption.getOrElse("unknown")
        val comment = m.comment.l.mkString("\\n")
        s"$name | $file | $comment"
      }}
      .l
    """.strip()

    result = client.execute_query(query)

    if result['success']:
        lines = [l for l in result.get('result', '').split('\n') if l.strip() and not l.startswith('res')]
        logger.info(f"✓ Extracted {len(lines)} methods with comments")

        if lines:
            logger.info("\nSample method comments:")
            for i, line in enumerate(lines[:3], 1):
                parts = line.split(' | ', 2)
                if len(parts) >= 3:
                    name, file, comment = parts
                    logger.info(f"\n  {i}. Method: {name}")
                    logger.info(f"     File: {file}")
                    logger.info(f"     Comment: {comment[:150]}...")

        return len(lines)
    else:
        logger.error(f"✗ Method comment extraction failed: {result.get('error')}")
        return 0


def test_file_comment_extraction(client, limit=5):
    """Test extracting file-level comments."""
    logger.info(f"\nTesting file comment extraction (limit={limit})...")

    query = f"""
    cpg.file
      .filter(f => f.comment.nonEmpty)
      .take({limit})
      .map {{ f =>
        val path = f.name
        val comment = f.comment.l.mkString("\\n")
        s"$path | $comment"
      }}
      .l
    """.strip()

    result = client.execute_query(query)

    if result['success']:
        lines = [l for l in result.get('result', '').split('\n') if l.strip() and not l.startswith('res')]
        logger.info(f"✓ Extracted {len(lines)} files with comments")

        if lines:
            logger.info("\nSample file comments:")
            for i, line in enumerate(lines[:2], 1):
                parts = line.split(' | ', 1)
                if len(parts) >= 2:
                    path, comment = parts
                    logger.info(f"\n  {i}. File: {path}")
                    logger.info(f"     Comment: {comment[:150]}...")

        return len(lines)
    else:
        logger.error(f"✗ File comment extraction failed: {result.get('error')}")
        return 0


def test_alternative_method_docs(client, limit=5):
    """Test alternative approach: link methods to nearby comment nodes."""
    logger.info(f"\nTesting alternative: Linking methods to comment nodes (limit={limit})...")

    # Find comment nodes that are children of method AST nodes
    query = f"""
    cpg.method
      .take({limit})
      .map {{ m =>
        val name = m.name
        val file = m.file.name.headOption.getOrElse("unknown")
        val lineNum = m.lineNumber.getOrElse(0)
        val comments = cpg.comment
          .where(_.file.name(file))
          .filter(c => {{
            val cLine = c.lineNumber.getOrElse(0)
            cLine > 0 && cLine < lineNum && (lineNum - cLine) < 20
          }})
          .code
          .l
          .mkString(" | ")
        s"$name || $file || $lineNum || $comments"
      }}
      .l
    """.strip()

    result = client.execute_query(query)

    if result['success']:
        raw_lines = result.get('result', '').split('\n')
        lines = [l for l in raw_lines if l.strip() and ' || ' in l]
        methods_with_docs = [l for l in lines if len(l.split(' || ')[-1]) > 10]

        logger.info(f"✓ Found {len(methods_with_docs)} methods with nearby comments")

        if methods_with_docs:
            logger.info("\nSample methods with documentation:")
            for i, line in enumerate(methods_with_docs[:3], 1):
                parts = line.split(' || ', 3)
                if len(parts) >= 4:
                    name, file, line_num, comments = parts
                    logger.info(f"\n  {i}. Method: {name} (line {line_num})")
                    logger.info(f"     File: {file}")
                    logger.info(f"     Comments: {comments[:200]}...")

        return len(methods_with_docs)
    else:
        logger.error(f"✗ Comment linking failed: {result.get('error')}")
        return 0


def test_direct_comment_sample(client, limit=10):
    """Test extracting raw comment samples directly."""
    logger.info(f"\nTesting direct comment extraction (limit={limit})...")

    query = f"""
    cpg.comment
      .take({limit})
      .map {{ c =>
        val file = c.file.name.headOption.getOrElse("unknown")
        val lineNum = c.lineNumber.getOrElse(0)
        val code = c.code
        s"$file || $lineNum || $code"
      }}
      .l
    """.strip()

    result = client.execute_query(query)

    if result['success']:
        raw_lines = result.get('result', '').split('\n')
        lines = [l for l in raw_lines if l.strip() and ' || ' in l]

        logger.info(f"✓ Extracted {len(lines)} comment samples")

        if lines:
            logger.info("\nSample comments:")
            for i, line in enumerate(lines[:5], 1):
                parts = line.split(' || ', 2)
                if len(parts) >= 3:
                    file, line_num, comment = parts
                    logger.info(f"\n  {i}. {file}:{line_num}")
                    logger.info(f"     {comment[:150]}...")

        return len(lines)
    else:
        logger.error(f"✗ Direct comment extraction failed: {result.get('error')}")
        return 0


def main():
    """Run all tests."""
    print("="*70)
    print("Joern CPG Comment Extraction Test Suite")
    print("="*70)

    # Test connection
    client = test_joern_connection()
    if not client:
        print("\n✗ Cannot proceed without Joern connection")
        print("\nTo start Joern:")
        print("  cd C:/Users/user/joern")
        print("  joern -J-Xmx16G --server --server-host localhost --server-port 8080")
        print("\nThen bootstrap the CPG:")
        print("  python pg17_client.py --query 'import _root_.io.joern.joerncli.console.Joern'")
        print("  python pg17_client.py --query 'import _root_.io.shiftleft.semanticcpg.language._'")
        print("  python pg17_client.py --query 'Joern.open(\"pg17_full.cpg\")'")
        print("  python pg17_client.py --query 'val cpg = Joern.cpg'")
        return

    # Test comment availability
    comment_count = test_comment_nodes_exist(client)

    # Test raw comment extraction
    direct_count = test_direct_comment_sample(client, limit=20)

    # Test extraction methods
    method_count = test_method_comment_extraction(client, limit=10)
    file_count = test_file_comment_extraction(client, limit=10)
    alt_count = test_alternative_method_docs(client, limit=50)

    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total comment nodes in CPG: {comment_count:,}")
    print(f"Direct comment samples extracted: {direct_count}")
    print(f"Methods with comments (via .comment property): {method_count}")
    print(f"Files with comments: {file_count}")
    print(f"Methods linked to nearby comments: {alt_count}")
    print("="*70)

    if comment_count > 0 and (alt_count > 0 or direct_count > 0):
        print("\n✓ SUCCESS: CPG contains extractable documentation")
        print(f"\n  • {comment_count:,} total comment nodes available")
        print(f"  • {alt_count} methods successfully linked to comments")
        print(f"  • Comment extraction via proximity-based linking works")
        print("\nNext steps:")
        print("  1. Run full extraction: conda run -n llama.cpp python src/extraction/comment_extractor.py --method-limit 1000")
        print("  2. Build vector store: conda run -n llama.cpp python src/retrieval/doc_vector_store.py")
        print("  3. Test retrieval: Search for 'MVCC visibility' and check relevance")
    elif comment_count > 0:
        print("\n⚠ WARNING: CPG has comments but extraction queries need refinement")
        print("The CPG was likely created without comment preservation.")
        print("\nTo rebuild CPG with comments, use c2cpg with --comments flag")
    else:
        print("\n✗ ISSUE: CPG does not contain comment nodes")
        print("\nThe PostgreSQL CPG needs to be regenerated with comment preservation.")
        print("Check Joern documentation for c2cpg comment extraction options.")


if __name__ == '__main__':
    main()
