"""
Semantic Mode Nodes - Core CodeGraph Workflow

Node functions for the semantic analysis path of the LangGraph workflow.
Handles find-method type questions using retrieval-augmented generation.

Nodes:
- analyze_node: Extract intent, domain, keywords
- retrieve_node: Retrieve relevant context
- enrich_node: Get CPG metadata enrichment
- generate_node: Generate CPGQL query
- validate_node: Validate query syntax
- refine_node: Refine invalid queries
- execute_node: Execute query on Joern
- interpret_node: Generate natural language answer
- adaptive_refine_node: Learn and apply refinements
"""

import re
import time
import logging
from typing import Dict, Any

from langchain_core.messages import AIMessage

from src.workflow._state import RAGCPGQLState
from src.workflow._components import (
    get_analyzer,
    get_retriever,
    get_enrichment_agent,
    get_generator_agent,
    get_interpreter_agent,
    get_joern_client,
    get_adaptive_refiner,
)
from src.workflow._helpers import (
    post_process_query,
    count_scala_results,
    is_empty_result,
)
from src.ranking.result_ranker import ResultRanker
from src.agents.executor_agent_with_fallback import ExecutorAgentWithFallback
from src.agents.adaptive_refiner import classify_question_type

logger = logging.getLogger(__name__)


def analyze_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Analyzer Agent: Extract intent, domain, and keywords from question."""
    logger.info("=== ANALYZER AGENT ===")

    try:
        question = state["question"]

        # Analyze question (shared analyzer ensures consistent heuristics)
        analysis = get_analyzer().analyze(question)

        # Update state
        state["intent"] = analysis.get("intent", "unknown")
        state["domain"] = analysis.get("domain", "general")
        state["keywords"] = analysis.get("keywords", [])
        state["complexity"] = analysis.get("complexity", "medium")

        # Phase 7: Capture query mode
        state["query_mode"] = analysis.get("query_mode", "find-method")
        state["query_mode_confidence"] = analysis.get("query_mode_confidence", 0.5)

        # Add message
        state["messages"].append(AIMessage(
            content=f"Analysis: domain={state['domain']}, intent={state['intent']}, "
                   f"complexity={state['complexity']}, query_mode={state['query_mode']} "
                   f"(conf: {state['query_mode_confidence']:.2f})"
        ))

        logger.info(f"Domain: {state['domain']}, Intent: {state['intent']}, "
                   f"QueryMode: {state['query_mode']} ({state['query_mode_confidence']:.2f})")

    except Exception as e:
        logger.error(f"Analyzer error: {e}", exc_info=True)
        state["error"] = f"Analyzer failed: {str(e)}"

    return state


def retrieve_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Retriever Agent: Retrieve relevant context from vector store."""
    logger.info("=== RETRIEVER AGENT ===")

    try:
        question = state["question"]

        # Get analysis context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", []),
            "intent": state.get("intent")
        }

        # Retrieve context using shared retriever
        retrieval_result = get_retriever().retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=3,
            top_k_cpgql=5
        )

        # Update state
        state["similar_qa"] = retrieval_result.get("similar_qa", [])
        state["cpgql_examples"] = retrieval_result.get("cpgql_examples", [])
        state["retrieval_metadata"] = retrieval_result.get("retrieval_stats", {})

        # Add message
        qa_count = len(state["similar_qa"])
        cpgql_count = len(state["cpgql_examples"])
        avg_sim = state["retrieval_metadata"].get("avg_qa_similarity")
        sim_text = f"{avg_sim:.3f}" if isinstance(avg_sim, (int, float)) else "n/a"

        state["messages"].append(AIMessage(
            content=f"Retrieved: {qa_count} Q&A pairs, {cpgql_count} CPGQL examples "
                   f"(avg similarity: {sim_text})"
        ))

        logger.info(f"Retrieved {qa_count} Q&A, {cpgql_count} CPGQL examples")

    except Exception as e:
        logger.error(f"Retriever error: {e}", exc_info=True)
        state["error"] = f"Retriever failed: {str(e)}"

    return state


def enrich_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Enrichment Agent: Get relevant enrichment hints from CPG metadata."""
    logger.info("=== ENRICHMENT AGENT ===")

    try:
        question = state["question"]

        # Get analysis context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", [])
        }

        # Get enrichment hints
        hints = get_enrichment_agent().get_enrichment_hints(
            question=question,
            analysis=analysis
        )

        # Calculate coverage from agent output
        coverage = hints.get("coverage_score", 0.0)
        tag_count = len(hints.get("tags", []))

        # Update state
        state["enrichment_hints"] = hints
        state["enrichment_coverage"] = coverage

        # Add message
        state["messages"].append(AIMessage(
            content=f"Enrichment: {tag_count} tag hints ({coverage:.0%} coverage)"
        ))

        logger.info(f"Enrichment: {tag_count} tag hints, {coverage:.0%} coverage")

    except Exception as e:
        logger.error(f"Enrichment error: {e}", exc_info=True)
        state["error"] = f"Enrichment failed: {str(e)}"

    return state


def generate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Generator Agent: Generate CPGQL query with full context."""
    logger.info("=== GENERATOR AGENT ===")

    try:
        start_time = time.time()

        question = state["question"]
        use_multi_query = state.get("use_multi_query", False)

        # Get context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", []),
            "intent": state.get("intent"),
            "complexity": state.get("complexity")
        }

        context = {
            "analysis": analysis,
            "similar_qa": state.get("similar_qa", []),
            "cpgql_examples": state.get("cpgql_examples", []),
            "enrichment_hints": state.get("enrichment_hints", {}),
            "retrieval_metadata": state.get("retrieval_metadata", {})
        }

        generator = get_generator_agent()

        if use_multi_query:
            # Multi-query approach: generate 3 variants
            logger.info("Using multi-query approach (Query Funnel)")
            variants = generator.generate_query_variants(
                question=question,
                context=context,
                num_variants=3
            )

            state["query_variants"] = variants

            # Set the first (PRECISE) variant as the primary query for validation
            if variants:
                raw_query = variants[0].get("query", "")
                # Apply post-processing to convert exact matching to pattern matching
                processed_query, was_modified = post_process_query(raw_query)
                state["cpgql_query"] = processed_query
                state["query_valid"] = True  # Will be validated later
                state["validation_error"] = None
            else:
                state["cpgql_query"] = ""
                state["query_valid"] = False
                state["validation_error"] = "No query variants generated"

            generation_time = time.time() - start_time
            state["generation_time"] = generation_time

            # Add message
            variant_count = len(variants)
            state["messages"].append(AIMessage(
                content=f"Generated {variant_count} query variants ({generation_time:.2f}s) - Query Funnel approach"
            ))

            logger.info(f"Generated {variant_count} query variants in {generation_time:.2f}s")

        else:
            # Original single-query approach
            query, is_valid, error = generator.generate(
                question=question,
                context=context
            )

            # Apply post-processing to convert exact matching to pattern matching
            processed_query, was_modified = post_process_query(query)

            generation_time = time.time() - start_time

            # Update state
            state["cpgql_query"] = processed_query
            state["generation_time"] = generation_time
            state["query_valid"] = is_valid
            state["validation_error"] = error if error else None

            # Add message
            preview = (query or "")[:100]
            state["messages"].append(AIMessage(
                content=f"Generated query ({generation_time:.2f}s | valid={'yes' if is_valid else 'no'}): {preview}"
            ))

            logger.info(f"Generated query (valid={is_valid}) in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Generator error: {e}", exc_info=True)
        state["error"] = f"Generator failed: {str(e)}"
        state["query_valid"] = False
        state["validation_error"] = str(e)

    return state


def validate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Validator Agent: Validate query syntax and safety."""
    logger.info("=== VALIDATOR AGENT ===")

    try:
        query = state.get("cpgql_query", "")

        if not query:
            state["query_valid"] = False
            state["validation_error"] = "Empty query"
            return state

        # Basic validation checks
        errors = []

        # 1. Check for required CPGQL components
        if "cpg." not in query.lower():
            errors.append("Query must start with 'cpg.'")

        # 2. Check for .l terminator (list results)
        if not (query.endswith(".l") or query.endswith(".toList") or
                query.endswith(".size") or query.endswith(".head")):
            errors.append("Query should end with .l, .toList, .size, or .head")

        # 3. Check for dangerous operations
        dangerous_ops = ["delete", "drop", "remove", "clear"]
        query_lower = query.lower()
        for op in dangerous_ops:
            if op in query_lower:
                errors.append(f"Dangerous operation detected: {op}")

        # 4. Check balanced parentheses
        if query.count("(") != query.count(")"):
            errors.append("Unbalanced parentheses")

        # 5. Check balanced quotes
        if query.count('"') % 2 != 0:
            errors.append("Unbalanced quotes")

        # Set validation result
        if errors:
            state["query_valid"] = False
            state["validation_error"] = "; ".join(errors)
            logger.warning(f"Validation failed: {state['validation_error']}")
        else:
            state["query_valid"] = True
            state["validation_error"] = None
            logger.info("Query validation passed")

        # Add message
        status = "VALID" if state["query_valid"] else "INVALID"
        state["messages"].append(AIMessage(
            content=f"Validation: {status}" +
                   (f" - {state['validation_error']}" if not state["query_valid"] else "")
        ))

    except Exception as e:
        logger.error(f"Validator error: {e}", exc_info=True)
        state["query_valid"] = False
        state["validation_error"] = f"Validation error: {str(e)}"

    return state


def refine_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Refiner Agent: Refine query based on validation error."""
    logger.info("=== REFINER AGENT ===")

    try:
        retry_count = state.get("retry_count", 0)

        # Check retry limit
        if retry_count >= 2:
            logger.warning("Max retries reached, using fallback query")
            state["cpgql_query"] = "cpg.method.name.l.take(10)"
            state["query_valid"] = True
            state["validation_error"] = None
            state["messages"].append(AIMessage(
                content="Max retries reached, using fallback query"
            ))
            return state

        # Get previous query and error
        previous_query = state.get("cpgql_query") or ""
        error = state.get("validation_error", "") or ""

        logger.info(f"Refining query (attempt {retry_count + 1}/2)")
        logger.info(f"Error: {error}")

        # Simple refinement logic
        refined_query = previous_query.strip()

        if not refined_query:
            # If we have nothing to refine, fall back to a safe default
            refined_query = "cpg.method.name.l"

        # Fix common issues
        if "Query must start with 'cpg.'" in error:
            if not refined_query.startswith("cpg."):
                refined_query = "cpg." + refined_query

        if "Query should end with" in error:
            if not any(refined_query.endswith(t) for t in [".l", ".toList", ".size", ".head"]):
                refined_query = refined_query.rstrip(".") + ".l"

        if "Unbalanced parentheses" in error:
            open_count = refined_query.count("(")
            close_count = refined_query.count(")")
            if open_count > close_count:
                refined_query += ")" * (open_count - close_count)

        # Update state
        state["cpgql_query"] = refined_query
        state["retry_count"] = retry_count + 1

        # Add message
        preview = refined_query[:100] if refined_query else "[empty]"
        state["messages"].append(AIMessage(
            content=f"Refined query (attempt {retry_count + 1}): {preview}"
        ))

        logger.info(f"Refined query: {refined_query}")

    except Exception as e:
        logger.error(f"Refiner error: {e}", exc_info=True)
        state["error"] = f"Refiner failed: {str(e)}"

    return state


def execute_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Executor Agent: Execute query on Joern CPG server."""
    logger.info("=== EXECUTOR AGENT ===")

    try:
        use_multi_query = state.get("use_multi_query", False)
        query_variants = state.get("query_variants", [])

        # Get persistent Joern client (reuses connection across queries)
        joern_client = get_joern_client()

        if not joern_client:
            logger.warning("Joern client not available, skipping execution")
            state["execution_success"] = False
            state["execution_error"] = "Joern server not available"
            state["messages"].append(AIMessage(
                content="Execution skipped: Joern server not available"
            ))
            return state

        if use_multi_query and query_variants:
            # Use ExecutorAgentWithFallback for multi-query approach
            logger.info("Using ExecutorAgentWithFallback for multi-query execution")

            executor = ExecutorAgentWithFallback(
                joern_client=joern_client,
                min_results_threshold=5
            )

            exec_result = executor.execute_with_fallback(
                query_variants=query_variants,
                question=state["question"]
            )

            # Update state with fallback execution results
            state["cpgql_query"] = exec_result.get("query_used", "")
            state["execution_result"] = {"result": exec_result.get("raw_result", ""), "success": exec_result.get("success", False)}
            state["execution_success"] = exec_result.get("success", False)
            state["execution_time"] = state.get("generation_time", 0.0)  # Approximate
            state["execution_error"] = None if exec_result.get("success") else "All query variants failed"
            state["fallback_count"] = exec_result.get("fallback_count", 0)
            state["specificity_used"] = exec_result.get("specificity", "unknown")

            # Add message with fallback info
            num_results = len(exec_result.get("results", []))
            specificity = exec_result.get("specificity", "unknown")
            fallback_count = exec_result.get("fallback_count", 0)

            state["messages"].append(AIMessage(
                content=f"Execution: {specificity.upper()} query succeeded (fallbacks: {fallback_count}, results: {num_results})"
            ))

            logger.info(f"Multi-query execution: {specificity.upper()} succeeded with {num_results} results after {fallback_count} fallbacks")

            # Phase 2: Rank results by relevance (if we have results)
            results = exec_result.get("results", [])
            if results and num_results > 0:
                logger.info(f"Ranking {num_results} results by relevance")

                ranker = ResultRanker()

                # Build context for ranking
                ranking_context = {
                    'enrichment_hints': state.get('enrichment_hints', {}),
                    'analysis': {
                        'domain': state.get('domain', 'unknown'),
                        'intent': state.get('intent', ''),
                        'keywords': state.get('keywords', [])
                    }
                }

                # Rank results
                ranked = ranker.rank_results(
                    results=results,
                    question=state["question"],
                    context=ranking_context,
                    top_k=10
                )

                # Store ranked results in state
                state["ranked_results"] = ranked
                state["ranking_metadata"] = {
                    "top_score": ranked[0]["score"] if ranked else 0.0,
                    "num_ranked": len(ranked),
                    "avg_score": sum(r["score"] for r in ranked) / len(ranked) if ranked else 0.0
                }

                logger.info(f"Ranked {len(ranked)} results - Top score: {ranked[0]['score']:.3f}, Avg: {state['ranking_metadata']['avg_score']:.3f}")
            else:
                logger.info("No results to rank")
                state["ranked_results"] = []
                state["ranking_metadata"] = {"top_score": 0.0, "num_ranked": 0, "avg_score": 0.0}

        else:
            # Original single-query execution
            query = state.get("cpgql_query", "")

            if not query or not state.get("query_valid", False):
                logger.warning("Skipping execution: invalid query")
                state["execution_success"] = False
                state["execution_error"] = "Query not valid, skipping execution"
                return state

            def _attempt_execution(current_query: str) -> tuple:
                start = time.time()
                result_payload = joern_client.execute_query(current_query)
                elapsed = time.time() - start
                return result_payload, elapsed

            exec_result, execution_time = _attempt_execution(query)

            if exec_result.get("success") and is_empty_result(exec_result.get("result")):
                # FALLBACK MECHANISM DISABLED FOR ACCURACY
                logger.warning(
                    "Primary query returned no rows. Fallback mechanism disabled to prevent "
                    "garbage results. Query was: %s", query
                )
                exec_result = {
                    "success": True,
                    "result": "No results found for the specified criteria",
                    "error": None
                }

            # Update state
            state["cpgql_query"] = query
            state["execution_result"] = exec_result
            state["execution_success"] = exec_result.get("success", False)
            state["execution_time"] = execution_time
            state["execution_error"] = exec_result.get("error") if not exec_result.get("success") else None

            # Add message
            if state["execution_success"]:
                result_length = len(str(exec_result.get("result", "")))
                state["messages"].append(AIMessage(
                    content=f"Execution successful ({execution_time:.2f}s): {result_length} chars"
                ))
                logger.info(f"Execution successful: {result_length} chars in {execution_time:.2f}s")
            else:
                state["messages"].append(AIMessage(
                    content=f"Execution failed: {state['execution_error']}"
                ))
                logger.warning(f"Execution failed: {state['execution_error']}")

        # NOTE: Don't close joern_client - we're using a persistent connection!

    except Exception as e:
        logger.error(f"Executor error: {e}", exc_info=True)
        state["execution_success"] = False
        state["execution_error"] = str(e)
        state["messages"].append(AIMessage(
            content=f"Execution error: {str(e)}"
        ))

    return state


def interpret_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Interpreter Agent: Convert query results to natural language answer."""
    logger.info("=== INTERPRETER AGENT ===")

    try:
        # Get interpreter agent
        interpreter = get_interpreter_agent()

        # Extract relevant state
        question = state["question"]
        query = state.get("cpgql_query", "")
        execution_success = state.get("execution_success", False)
        execution_result = state.get("execution_result", {})
        execution_error = state.get("execution_error")
        enrichment_hints = state.get("enrichment_hints", {})

        # Check if fallback was used (query changed during execution)
        used_fallback = False
        fallback_query = None
        # Look for fallback message in state messages
        for msg in state.get("messages", []):
            if hasattr(msg, "content") and "Fallback query executed:" in str(msg.content):
                used_fallback = True
                # Extract the fallback query from the message
                match = re.search(r"Fallback query executed: (.+)", str(msg.content))
                if match:
                    fallback_query = match.group(1).strip()
                break

        # Call the interpreter agent
        interpretation = interpreter.interpret(
            question=question,
            query=query,
            execution_success=execution_success,
            execution_result=execution_result,
            execution_error=execution_error,
            enrichment_hints=enrichment_hints,
            used_fallback=used_fallback,
            fallback_query=fallback_query
        )

        # Update state with interpretation results
        state["answer"] = interpretation["answer"]
        state["answer_confidence"] = interpretation["confidence"]

        # Add message
        summary_type = interpretation.get("summary_type", "unknown")
        state["messages"].append(AIMessage(
            content=f"Answer generated ({summary_type} synthesis, confidence: {state['answer_confidence']:.1%})"
        ))

        logger.info(
            f"Answer generated: {len(state['answer'])} chars, "
            f"confidence={state['answer_confidence']:.2f}, "
            f"type={summary_type}"
        )

    except Exception as e:
        logger.error(f"Interpreter error: {e}", exc_info=True)
        state["answer"] = f"I encountered an error while interpreting the results: {str(e)}"
        state["answer_confidence"] = 0.0
        state["messages"].append(AIMessage(
            content=f"Interpretation error: {str(e)}"
        ))

    return state


def adaptive_refine_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Adaptive Refinement Agent: Learn from results and apply refinements if needed."""
    logger.info("=== ADAPTIVE REFINEMENT AGENT ===")

    try:
        refiner = get_adaptive_refiner()

        # Classify question type
        analysis = {
            "intent": state.get("intent"),
            "domain": state.get("domain"),
            "keywords": state.get("keywords", [])
        }
        question_type = classify_question_type(state["question"], analysis)
        state["question_type"] = question_type

        # Count results using proper Scala List parsing
        execution_result = state.get("execution_result", {})
        result_count = 0

        if execution_result and execution_result.get("success"):
            result_str = str(execution_result.get("result", ""))
            result_count = count_scala_results(result_str)
            logger.debug(f"Counted {result_count} results from {len(result_str)} chars of output")

        state["result_count"] = result_count

        # Record outcome for learning
        query = state.get("cpgql_query", "")
        success = result_count >= 5  # Consider success if >= 5 results

        refiner.record_query_outcome(
            question=state["question"],
            question_type=question_type,
            query=query,
            success=success,
            result_count=result_count,
            execution_time=state.get("execution_time", 0.0)
        )

        logger.info(f"Recorded query outcome: {result_count} results, success={success}, type={question_type}")

        # Apply refinements if results are insufficient
        if result_count < 5 and query:
            logger.info(f"Insufficient results ({result_count} < 5), generating refinement suggestions")

            suggestions = refiner.suggest_refinements(
                question=state["question"],
                question_type=question_type,
                failed_query=query,
                max_suggestions=3
            )

            state["refinement_suggestions"] = suggestions

            if suggestions:
                logger.info(f"Generated {len(suggestions)} refinement suggestions")

                # Try the best suggestion
                best_suggestion = suggestions[0]
                refined_query = best_suggestion["query"]
                strategy = best_suggestion["strategy"]

                logger.info(f"Applying refinement: {strategy}")
                logger.info(f"Refined query: {refined_query[:100]}...")

                # Try executing refined query
                joern_client = get_joern_client()
                if joern_client:
                    try:
                        start = time.time()
                        refined_result = joern_client.execute_query(refined_query)
                        elapsed = time.time() - start

                        if refined_result.get("success"):
                            refined_result_str = str(refined_result.get("result", ""))
                            refined_count = count_scala_results(refined_result_str)
                            logger.debug(f"Refinement counted {refined_count} results from {len(refined_result_str)} chars")

                            if refined_count > result_count:
                                logger.info(f"Refinement successful: {refined_count} results (improvement: +{refined_count - result_count})")

                                # Update state with refined results
                                state["cpgql_query"] = refined_query
                                state["execution_result"] = refined_result
                                state["execution_success"] = True
                                state["execution_time"] = elapsed
                                state["result_count"] = refined_count
                                state["refinement_applied"] = True
                                state["refinement_strategy"] = strategy

                                # Re-interpret with refined results
                                interpreter = get_interpreter_agent()
                                interpretation = interpreter.interpret(
                                    question=state["question"],
                                    query=refined_query,
                                    execution_success=True,
                                    execution_result=refined_result,
                                    execution_error=None,
                                    enrichment_hints=state.get("enrichment_hints", {}),
                                    used_fallback=False,
                                    fallback_query=None
                                )

                                state["answer"] = interpretation["answer"]
                                state["answer_confidence"] = interpretation["confidence"]

                                state["messages"].append(AIMessage(
                                    content=f"Refinement applied: {strategy} -> {refined_count} results (+{refined_count - result_count} improvement)"
                                ))
                            else:
                                logger.info(f"Refinement did not improve results: {refined_count} <= {result_count}")
                                state["refinement_applied"] = False
                        else:
                            logger.warning(f"Refined query failed: {refined_result.get('error')}")
                            state["refinement_applied"] = False
                    except Exception as e:
                        logger.error(f"Refinement execution error: {e}")
                        state["refinement_applied"] = False
                else:
                    logger.warning("Joern client not available for refinement")
                    state["refinement_applied"] = False
            else:
                logger.info("No refinement suggestions generated")
                state["refinement_applied"] = False
        else:
            logger.info(f"Results adequate ({result_count} >= 5), no refinement needed")
            state["refinement_applied"] = False

        # Save patterns periodically
        refiner.save_patterns()

    except Exception as e:
        logger.error(f"Adaptive refinement error: {e}", exc_info=True)
        state["refinement_applied"] = False

    return state
