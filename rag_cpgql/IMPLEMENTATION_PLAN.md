# Implementation Plan

This plan aligns the implemented LangGraph workflow with the target design described in `LANGGRAPH_ARCHITECTURE.md` and the action items from `LANGGRAPH_IMPLEMENTATION.md`. It summarizes completed work, identifies remaining gaps, and maps the roadmap to the near/medium/long-term enhancements defined in those documents.

## Architectural Alignment

The target architecture defines a multi-agent LangGraph StateGraph with explicit state fields and the following agents: Analyzer → Retriever → Enrichment → Generator → Validator ↔ Refiner → Executor → Interpreter → Evaluator (RAGAS). The current codebase implements this graph end-to-end; the table below captures each node’s status with respect to the design document.

| Component | Target Responsibilities (`LANGGRAPH_ARCHITECTURE.md`) | Implementation Status | Notes |
| --- | --- | --- | --- |
| AnalyzerAgent | Intent/domain classification, keyword extraction | ✅ Implemented (`AnalyzerAgent.analyze`) | Uses rule-based heuristics; optional LLM mode still pending. |
| RetrieverAgent | ChromaDB retrieval of Q&A (top-3) and CPGQL examples (top-5) | ✅ Implemented (`RetrieverAgent.retrieve`) | Supports reranking; integrates with shared `VectorStoreReal`. |
| EnrichmentAgent | Map domain/keywords to enrichment tags and prompt context | ✅ Implemented (`EnrichmentAgent.get_enrichment_hints`) | Coverage scoring and tag examples exported; Joern bootstrap instructions documented. |
| GeneratorAgent + CPGQLGenerator | Build enriched prompt, generate/validate CPGQL | ✅ Implemented (`GeneratorAgent.generate`) | Uses Qwen3-Coder (grammar disabled per README); validates syntax and execution directives. |
| Validator | Syntax/safety checks, feed errors to refiner | ✅ `validate_node` | Performs structural checks (prefix, terminators, parentheses, quotes, dangerous ops). |
| Refiner | Retry on validation failure (≤2 attempts) | ✅ `refine_node` | Basic heuristics; advanced LLM-powered refinement is scheduled (medium-term). |
| Executor (Joern) | Execute valid queries on Joern server | ✅ `execute_node` | `scripts/bootstrap_joern.ps1` automates server launch/imports. |
| Interpreter | Convert results/errors into natural language | ✅ `interpret_node` | Adds confidence scores; triggers fallback messaging on failure. |
| Evaluator | Compute RAGAS metrics (faithfulness, relevance, context) | ✅ `evaluate_node` + `test_with_ragas.py` | Inline RAGAS evaluation with heuristic fallback when dependencies are unavailable. |
| State Schema | Rich state with question, retrieval context, generation metadata, execution result, evaluation metrics, message log | ✅ `RAGCPGQLState` in `langgraph_workflow.py` | Mirrors architecture document; messages persisted for observability. |

## Completed Milestones

- **Data and enrichment foundation:** Consolidated 27k QA pairs, 1,072 exemplar queries, and 12-layer enriched `pg17_full.cpg` (quality 100/100).
- **LangGraph workflow:** Implemented 9-node StateGraph with retry loop, execution integration, and message logging (`src/workflow/langgraph_workflow.py`).
- **Joern automation:** Added `scripts/bootstrap_joern.ps1` and wired auto-bootstrap into `experiments/test_langgraph_workflow.py` to align with Joern startup sequence in the architecture plan.
- **Evaluation assets:** Delivered 30-question, 30-question enrichment, and 200-question suites; latest 200Q run achieved 98.0 % validity, 3.72 s average generation time, 0.446 enrichment coverage.
- **RAGAS integration:** `evaluate_node` now computes RAGAS metrics inline (faithfulness, answer relevance, context precision/recall) with heuristic fallback when dependencies are unavailable; `experiments/test_with_ragas.py` remains available for aggregated analysis (e.g., Q&A similarity 0.791, 100 % validity for 30Q set).
- **Retrieval caching:** `RetrieverAgent` maintains an LRU cache (default 128 entries) to avoid redundant ChromaDB queries during batch evaluations, with cache hit/miss logging for observability.
- **Documentation:** README/experiments docs updated with Joern bootstrap flow and environment requirements; implementation plan realigned with architecture/future-enhancement docs.

## Gaps vs Target Design

Although the core architecture is in place, several items from the design and implementation notes remain outstanding:

1. **Prompt refinement:** Refiner relies on static heuristics; the design references LLM-guided refinement for harder failures.
2. **Streaming observability:** No real-time progress or LangSmith tracing yet, reducing transparency for long-running jobs.
3. **Retrieval cache coverage:** Prototype caching exists inside `RetrieverAgent`, but eviction/invalidations and broader reuse policies still need refinement.
4. **Human-in-the-loop hooks:** Workflow is fully automated; pausing for feedback requires additional guardrails.
5. **Downstream deployment:** Architecture roadmap mentions production API and LangGraph ecosystem integrations (LangSmith, LangServe) still pending.

## Roadmap (Aligned with `LANGGRAPH_IMPLEMENTATION.md`)

### Near-Term (1–2 Weeks)

| Item | Status | Plan |
| --- | --- | --- |
| ✅ Complete test suite | **Done** | 200-question run completed (98 % validity). |
| ✅ RAGAS integration in workflow | **Done** | `evaluate_node` now calls RAGAS metrics (with heuristic fallback when dependencies are unavailable). |
| ⬜ Streaming output | In progress | Add progress logging/TTY updates (e.g., via LangGraph callbacks or Rich console). |
| ✅ Retrieval caching | **Done** | Added LRU cache to `RetrieverAgent` (configurable size, cache hit logging). |

### Medium-Term (1–2 Months)

| Item | Status | Plan |
| --- | --- | --- |
| ⬜ Advanced refinement | Open | Use LLM (Qwen3-Coder or smaller) to repair invalid queries with guidance from validator/executor errors. |
| ⬜ Multi-step queries | Open | Introduce planner node to decompose complex questions into sequential queries. |
| ⬜ Answer synthesis | Open | Generate richer natural-language responses using LLM summarization over executor outputs. |
| ⬜ Human-in-the-loop | Open | Add decision points to pause after generation or execution for manual confirmation/edits. |

### Long-Term (3+ Months)

| Item | Status | Plan |
| --- | --- | --- |
| ⬜ LangSmith integration | Open | Instrument LangGraph with LangSmith tracing for Analytics/observability. |
| ⬜ A/B testing | Open | Run controlled experiments on alternative prompts/models + collect metrics. |
| ⬜ Active learning | Open | Incorporate feedback loop to update prompts/enrichment weights from user corrections. |
| ⬜ Production API | Open | Package workflow as FastAPI (or LangServe) service with authentication and resource controls. |

## Supporting Workstreams

- **Tooling & Automation:** Extend bootstrap script to support health checks/retries and integrate into CI or long-running runners (LangGraph tests, 200Q benchmark). Add teardown to free GPU resources when idle.
- **Prompt & Retrieval Quality:** Tune enrichment weighting and exemplar selection to increase enrichment coverage (>0.6) and raise CPGQL example similarity (>0.3) as highlighted by RAGAS results.
- **Monitoring & Observability:** Add structured logging or streaming to surface retry counts, executor latency, and metric trends per run.
- **Documentation & Knowledge Sharing:** Keep README/experiments guides aligned with architectural evolution; document new scripts and ops procedures alongside workflow changes.

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Joern service drift or manual steps reappearing | Continue automating through `bootstrap_joern.ps1`; add health checks before long benchmarks. |
| LLM resource pressure | Maintain quantized Qwen3-Coder baseline; explore batching or model swapping for development workflows. |
| Metric credibility | Integrate official RAGAS metrics early; validate with manual spot-checks before publishing results. |
| Feature-tag drift | Schedule periodic enrichment validation when upstream PostgreSQL snapshot changes. |

## Next Immediate Actions

1. Instrument LangGraph runs with streaming progress output (per future-enhancement guidance).
2. Refine retrieval caching (invalidations, metrics) and observe gains on large evaluations.
3. Tune prompts/enrichment weighting to lift enrichment usage and coverage.
4. Document bootstrap + workflow execution steps in CI/readme to keep operations consistent.

This plan will be updated as each enhancement is delivered, keeping the implementation aligned with the design documents.*** End Patch
