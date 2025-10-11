"""Full RAG-CPGQL Pipeline with LLM

This script runs the complete RAG pipeline:
1. Retrieves similar QA pairs using vector search
2. Uses LLM to generate CPGQL queries based on question and examples
3. Executes queries on Joern CPG
4. Interprets results with LLM
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import logging
from typing import List, Dict
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_rag_pipeline(questions: List[str], num_samples: int = 3):
    """Run full RAG pipeline on sample questions.

    Args:
        questions: List of questions to answer
        num_samples: Number of similar examples to retrieve per question
    """
    from utils.config import load_config
    from utils.data_loader import load_qa_pairs
    from retrieval.vector_store import VectorStore
    from execution.joern_client import JoernClient
    from generation.llm_interface import LLMInterface
    from generation.prompts import CPGQL_SYSTEM_PROMPT

    logger.info("=" * 80)
    logger.info(f"FULL RAG-CPGQL PIPELINE - {len(questions)} questions")
    logger.info("=" * 80)

    # Load config
    config = load_config()

    # Step 1: Initialize Vector Store
    logger.info("\n[1/5] Loading training data and building vector index...")
    train_data = load_qa_pairs(config.train_split)
    logger.info(f"  Loaded {len(train_data)} training examples")

    vector_store = VectorStore(model_name=config.embedding_model)
    start_time = time.time()
    vector_store.create_qa_index(train_data)
    logger.info(f"  Indexed in {time.time() - start_time:.1f}s")

    # Step 2: Connect to Joern
    logger.info("\n[2/5] Connecting to Joern CPG server...")
    joern = JoernClient(cpg_project_name="pg17_full.cpg", port=config.joern_port)
    if not joern.connect():
        logger.error("Failed to connect to Joern")
        return
    logger.info(f"  Connected to enriched CPG")

    # Step 3: Load LLM
    logger.info("\n[3/5] Loading fine-tuned LLM...")
    logger.info(f"  Model: {config.finetuned_model_path}")
    llm = LLMInterface(
        model_path=config.finetuned_model_path,
        n_ctx=8192,
        n_gpu_layers=-1,  # Use all GPU layers
        n_batch=512,
        n_threads=8
    )
    logger.info("  Model loaded successfully")

    # Step 4: Process each question through RAG pipeline
    logger.info(f"\n[4/5] Processing {len(questions)} questions...")

    results = []
    for i, question in enumerate(questions, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Question {i}/{len(questions)}")
        logger.info(f"{'='*60}")
        logger.info(f"Q: {question}")

        try:
            # 4.1: Retrieve similar examples
            logger.info("\n  [Retrieval] Searching for similar QA pairs...")
            similar_qa = vector_store.search_similar_qa(question, k=num_samples)
            logger.info(f"  Found {len(similar_qa)} similar examples:")
            for j, sim in enumerate(similar_qa[:3], 1):
                logger.info(f"    {j}. Similarity: {sim['similarity']:.3f}")
                logger.info(f"       Q: {sim['question'][:80]}...")

            # 4.2: Build few-shot prompt
            logger.info("\n  [Generation] Building prompt with examples...")
            examples_text = "\n\n".join([
                f"Example {j}:\nQuestion: {ex['question']}\nAnswer: {ex['answer'][:500]}..."
                for j, ex in enumerate(similar_qa, 1)
            ])

            user_prompt = f"""Given the following examples of PostgreSQL questions and CPGQL queries:

{examples_text}

Now, for this new question about PostgreSQL 17.6 source code:
"{question}"

Generate a CPGQL query to answer this question. The query should:
1. Use the enriched CPG with tags (cyclomatic-complexity, security-risk, etc.)
2. Return relevant code elements (methods, calls, parameters)
3. Be executable on Joern server

Provide ONLY the CPGQL query, no explanation."""

            # 4.3: Generate CPGQL query with LLM
            logger.info("  Generating CPGQL query...")
            raw_response = llm.generate(
                system_prompt=CPGQL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=512,
                temperature=0.1  # Low temperature for precise queries
            )

            logger.info(f"\n  Raw LLM Response:")
            logger.info(f"  {raw_response[:200]}...")

            # Parse LLM response - handle JSON or plain text
            generated_query = raw_response.strip()

            # Try to extract from JSON if LLM returned {"query": "..."}
            if generated_query.startswith('{'):
                try:
                    parsed = json.loads(generated_query)
                    if 'query' in parsed:
                        generated_query = parsed['query']
                        logger.info("  Extracted query from JSON wrapper")
                except:
                    pass

            # Remove markdown code blocks if present
            if generated_query.startswith('```'):
                lines = generated_query.split('\n')
                # Remove first and last lines (code fence)
                generated_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else generated_query
                logger.info("  Extracted query from markdown code block")

            generated_query = generated_query.strip()

            # POST-PROCESSING: Fix common LLM mistakes with tag values
            logger.info("\n  [Validation] Checking and fixing query...")
            original_query = generated_query

            # Fix 1: Replace invented "wal-ctl" with correct "wal-logging"
            if '"wal-ctl"' in generated_query or '"wal-control"' in generated_query or '"wal-recovery"' in generated_query:
                logger.warning("  ⚠️  Fixing invented WAL tag value...")
                generated_query = generated_query.replace('"wal-ctl"', '"wal-logging"')
                generated_query = generated_query.replace('"wal-control"', '"wal-logging"')
                generated_query = generated_query.replace('"wal-recovery"', '"wal-logging"')

            # Fix 2: Replace invented "security-check" with correct "security-risk"
            if '"security-check"' in generated_query or '"security-validation"' in generated_query:
                logger.warning("  ⚠️  Fixing invented security tag value...")
                generated_query = generated_query.replace('"security-check"', '"security-risk"')
                generated_query = generated_query.replace('"security-validation"', '"security-risk"')

            # Fix 3: Replace method security tags with call security tags
            if 'method.where(_.tag.nameExact("security-risk")' in generated_query:
                logger.warning("  ⚠️  Fixing security-risk on wrong node type (method -> call)...")
                generated_query = generated_query.replace('method.where(_.tag.nameExact("security-risk")', 'call.where(_.tag.nameExact("security-risk")')

            # Fix 4: Fix Call node properties (c.filename -> c.file.name)
            if 'cpg.call' in generated_query and '.filename' in generated_query:
                logger.warning("  ⚠️  Fixing Call node filename access...")
                # Fix within map: c.filename -> c.file.name
                generated_query = generated_query.replace('c.filename', 'c.file.name')
                # Also fix .lineNumber -> .lineNumber.getOrElse(0)
                if '.lineNumber)' in generated_query:
                    generated_query = generated_query.replace('.lineNumber)', '.lineNumber.getOrElse(0))')

            if generated_query != original_query:
                logger.info(f"  ✅ Query corrected")
                logger.info(f"  Original: {original_query[:150]}...")
                logger.info(f"  Corrected: {generated_query[:150]}...")
            else:
                logger.info(f"  ✅ Query looks valid")

            logger.info(f"\n  Final CPGQL Query:")
            logger.info(f"  {generated_query[:200]}...")

            # 4.4: Execute query on Joern
            logger.info("\n  [Execution] Running query on Joern CPG...")
            execution_result = joern.execute_query(generated_query)

            if execution_result.get('success'):
                stdout = execution_result['results'].get('stdout', '')

                # Check for actual Scala compilation errors (not ANSI color codes)
                # Real errors have format: "[E006]", "[E008]", etc. followed by "Error:"
                is_error = False
                if '[E' in stdout and 'Error:' in stdout:
                    # Check if it's a real error, not just ANSI codes like "\u001b[31m"
                    error_patterns = ['Not Found Error:', 'Type Mismatch:', 'Syntax Error:']
                    is_error = any(pattern in stdout for pattern in error_patterns)

                if is_error:
                    logger.warning("  Query executed but returned compilation error")
                    logger.warning(f"  Error: {stdout[:300]}")
                    execution_success = False
                    final_answer = f"Query execution failed: {stdout[:300]}"
                else:
                    logger.info("  Query executed successfully")
                    execution_success = True

                    # Show result preview
                    result_preview = stdout[:500].replace('\r\n', ' ').replace('\n', ' ')
                    logger.info(f"  Result preview: {result_preview}...")

                    # 4.5: Interpret results with LLM
                    logger.info("\n  [Interpretation] Generating natural language answer...")
                    interpretation_prompt = f"""Based on this CPGQL query result from PostgreSQL 17.6 source code:

Query: {generated_query}

Result: {stdout[:2000]}

Provide a concise answer to the original question:
"{question}"

Focus on the key findings from the CPG analysis."""

                    final_answer = llm.generate(
                        system_prompt="You are a PostgreSQL expert. Interpret CPG query results clearly and concisely.",
                        user_prompt=interpretation_prompt,
                        max_tokens=512,
                        temperature=0.3
                    )

                    logger.info("\n  Final Answer:")
                    logger.info(f"  {final_answer[:300]}...")

            else:
                logger.error(f"  Query execution failed: {execution_result.get('error')}")
                execution_success = False
                final_answer = f"Execution error: {execution_result.get('error')}"

            results.append({
                'question': question,
                'similar_examples_count': len(similar_qa),
                'generated_query': generated_query,
                'execution_success': execution_success,
                'raw_result': execution_result['results'].get('stdout', '') if execution_success else None,
                'final_answer': final_answer
            })

        except Exception as e:
            logger.error(f"  ERROR processing question: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'question': question,
                'error': str(e),
                'execution_success': False
            })

    # Step 5: Summary
    logger.info("\n" + "=" * 80)
    logger.info("[5/5] PIPELINE SUMMARY")
    logger.info("=" * 80)

    successful = sum(1 for r in results if r.get('execution_success'))
    logger.info(f"\nSuccessful executions: {successful}/{len(results)} ({100*successful/len(results):.1f}%)")

    # Save results
    output_file = f"rag_pipeline_results_{len(questions)}q.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'pipeline': 'Full RAG-CPGQL',
            'num_questions': len(questions),
            'num_examples_per_question': num_samples,
            'success_rate': successful / len(results),
            'results': results
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\nResults saved to: {output_file}")

    # Cleanup
    logger.info("\nCleaning up...")
    joern.close()

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Example questions
    test_questions = [
        "How does PostgreSQL handle WAL (Write-Ahead Logging) for crash recovery?",
        "What functions in PostgreSQL implement B-tree index splitting?",
        "Which security checks are performed during table access in PostgreSQL?",
    ]

    run_rag_pipeline(test_questions, num_samples=3)
