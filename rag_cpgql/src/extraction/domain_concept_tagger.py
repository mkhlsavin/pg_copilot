"""Domain concept tagger for DDG patterns.

Maps low-level code patterns to high-level PostgreSQL domain concepts
to bridge the semantic gap between user questions and DDG patterns.
"""

import re
from typing import List, Set


def infer_domain_concepts(
    method_name: str,
    parameter_name: str,
    target_code: str,
    file_path: str
) -> List[str]:
    """Infer domain concepts from code context.

    Args:
        method_name: Name of the method containing the pattern
        parameter_name: Name of the parameter/variable in the pattern
        target_code: Code snippet where data flows
        file_path: Source file path

    Returns:
        List of domain concept tags (e.g., ["mvcc", "visibility", "transaction"])
    """
    concepts: Set[str] = set()

    # Combine all text for keyword matching
    all_text = f"{method_name} {parameter_name} {target_code} {file_path}".lower()

    # MVCC & Transaction Isolation concepts
    if any(kw in all_text for kw in [
        "snapshot", "mvcc", "visibility", "xmin", "xmax", "xid",
        "tuplesatisfies", "heaptuplesatisfies", "cid", "cmin", "cmax"
    ]):
        concepts.add("mvcc")
        concepts.add("visibility")
        concepts.add("transaction-isolation")

    # Transaction Control concepts
    if any(kw in all_text for kw in [
        "transaction", "xact", "commit", "abort", "rollback", "savepoint",
        "twophase", "2pc", "prepare", "transam"
    ]):
        concepts.add("transaction-control")
        concepts.add("transam")

    # WAL & Durability concepts
    if any(kw in all_text for kw in [
        "wal", "xlog", "lsn", "checkpoint", "recovery", "replay",
        "xlrec", "xloginsert", "xlogflush"
    ]):
        concepts.add("wal")
        concepts.add("durability")
        concepts.add("recovery")

    # Index & Access Method concepts
    if any(kw in all_text for kw in ["brin", "gin", "gist", "btree", "hash", "bloom"]):
        concepts.add("indexing")
        concepts.add("access-method")

    # Specific index types
    if "brin" in all_text:
        concepts.add("brin-index")
    if "gin" in all_text or "ginutil" in all_text:
        concepts.add("gin-index")
    if "gist" in all_text:
        concepts.add("gist-index")
    if "btree" in all_text or "nbtree" in all_text:
        concepts.add("btree-index")

    # Buffer Management concepts
    if any(kw in all_text for kw in [
        "buffer", "cache", "eviction", "pin", "bufmgr", "freelist",
        "bufhdr", "bufpool", "lru"
    ]):
        concepts.add("buffer-management")
        concepts.add("caching")
        concepts.add("memory-management")

    # Query Execution concepts
    if any(kw in all_text for kw in [
        "executor", "execproc", "execmain", "execscan", "execnodes",
        "seqscan", "indexscan", "tidscan", "bitmapscan"
    ]):
        concepts.add("query-execution")
        concepts.add("executor")

    # Query Planning concepts
    if any(kw in all_text for kw in [
        "planner", "optimizer", "pathkeys", "costsize", "indxpath",
        "joinpath", "mergejoin", "hashjoin", "nestloop"
    ]):
        concepts.add("query-planning")
        concepts.add("optimizer")

    # Locking & Concurrency concepts
    if any(kw in all_text for kw in [
        "lock", "lwlock", "spinlock", "latch", "sema", "barrier",
        "lockmanager", "deadlock", "predicate"
    ]):
        concepts.add("concurrency-control")
        concepts.add("locking")

    # Storage & Heap concepts
    if any(kw in all_text for kw in [
        "heap", "tuple", "page", "relation", "relcache", "storage",
        "smgr", "md", "fsm", "vm"
    ]):
        concepts.add("storage-access")
        concepts.add("heap-tuple")

    # Vacuum & Cleanup concepts
    if any(kw in all_text for kw in [
        "vacuum", "autovacuum", "lazy", "cleanup", "freespace", "deadtuple"
    ]):
        concepts.add("vacuum")
        concepts.add("cleanup")
        concepts.add("maintenance")

    # Replication concepts
    if any(kw in all_text for kw in [
        "replication", "walsender", "walreceiver", "logical", "physical",
        "slot", "decode", "pgoutput"
    ]):
        concepts.add("replication")
        concepts.add("wal-streaming")

    # Partitioning concepts
    if any(kw in all_text for kw in [
        "partition", "partdesc", "partprune", "partbounds", "inheritanc"
    ]):
        concepts.add("partitioning")
        concepts.add("declarative-partition")

    # Parallel Query concepts
    if any(kw in all_text for kw in [
        "parallel", "worker", "sharedmem", "dsm", "dsa", "gather",
        "bgworker", "dynamic"
    ]):
        concepts.add("parallelism")
        concepts.add("parallel-query")

    # JIT compilation concepts
    if any(kw in all_text for kw in [
        "jit", "llvm", "compile", "codegen", "expression"
    ]):
        concepts.add("jit")
        concepts.add("compilation")

    # Extension & Plugin concepts
    if any(kw in all_text for kw in [
        "extension", "contrib", "plugin", "hook", "fdw", "foreigndata"
    ]):
        concepts.add("extension")
        concepts.add("extensibility")

    # Security & Access Control concepts
    if any(kw in all_text for kw in [
        "auth", "acl", "privilege", "grant", "role", "policy",
        "security", "rls", "rowsecurity"
    ]):
        concepts.add("security")
        concepts.add("access-control")

    # Type System concepts
    if any(kw in all_text for kw in [
        "typcache", "array", "record", "composite", "domain",
        "cast", "coerce"
    ]):
        concepts.add("type-system")
        concepts.add("data-types")

    # Catalog concepts
    if any(kw in all_text for kw in [
        "catalog", "syscache", "pgclass", "pgproc", "pgindex",
        "catcache", "inval"
    ]):
        concepts.add("catalog-access")
        concepts.add("system-catalog")

    # Memory Context concepts
    if any(kw in all_text for kw in [
        "memcontext", "palloc", "pfree", "aset", "allocset",
        "memory", "mcxt"
    ]):
        concepts.add("memory-management")
        concepts.add("memory-context")

    # Error Handling concepts
    if any(kw in all_text for kw in [
        "elog", "ereport", "error", "warning", "panic", "fatal",
        "errcode", "errmsg"
    ]):
        concepts.add("error-handling")
        concepts.add("logging")

    # Statistics concepts
    if any(kw in all_text for kw in [
        "stats", "analyze", "histogram", "correlation", "mcv",
        "statistic", "estimation"
    ]):
        concepts.add("statistics")
        concepts.add("query-optimization")

    # TOAST concepts
    if any(kw in all_text for kw in [
        "toast", "toastrel", "detoast", "varatt", "varlena"
    ]):
        concepts.add("toast")
        concepts.add("large-objects")

    # Add file-path-based concepts
    if "/access/" in file_path:
        concepts.add("access-method")
    if "/executor/" in file_path:
        concepts.add("query-execution")
    if "/optimizer/" in file_path or "/planner/" in file_path:
        concepts.add("query-planning")
    if "/storage/" in file_path:
        concepts.add("storage-layer")
    if "/replication/" in file_path:
        concepts.add("replication")
    if "/utils/" in file_path:
        concepts.add("utilities")

    return sorted(list(concepts))  # Sort for consistency


def enrich_pattern_description(
    original_description: str,
    concepts: List[str],
    method_name: str
) -> str:
    """Enrich pattern description with domain concepts.

    Args:
        original_description: Original pattern description
        concepts: List of domain concepts
        method_name: Method name for context

    Returns:
        Enriched description with concepts embedded
    """
    if not concepts:
        return original_description

    # Create natural language concept list
    concept_phrase = ", ".join(concepts[:5])  # Limit to top 5 concepts

    # Append concepts naturally to description
    enriched = f"{original_description} | PostgreSQL concepts: {concept_phrase} | Context: {method_name}"

    return enriched


# Example usage and testing
if __name__ == "__main__":
    # Test case 1: MVCC-related
    concepts1 = infer_domain_concepts(
        method_name="heap_fetch",
        parameter_name="relation",
        target_code="HeapTupleSatisfiesMVCC(tuple, snapshot, buffer)",
        file_path="backend/access/heap/heapam.c"
    )
    print("Test 1 (MVCC):", concepts1)
    # Expected: ['mvcc', 'visibility', 'transaction-isolation', 'heap-tuple', 'storage-access', 'access-method']

    # Test case 2: Index-related
    concepts2 = infer_domain_concepts(
        method_name="brin_summarize_range",
        parameter_name="index_rel",
        target_code="brin_form_tuple(desc, values, nulls)",
        file_path="backend/access/brin/brin.c"
    )
    print("Test 2 (BRIN):", concepts2)
    # Expected: ['brin-index', 'indexing', 'access-method']

    # Test case 3: WAL-related
    concepts3 = infer_domain_concepts(
        method_name="XLogInsert",
        parameter_name="record",
        target_code="XLogRecordAssemble(rmid, info)",
        file_path="backend/access/transam/xlog.c"
    )
    print("Test 3 (WAL):", concepts3)
    # Expected: ['wal', 'durability', 'recovery', 'transaction-control', 'transam']

    # Test enrichment
    enriched = enrich_pattern_description(
        original_description="Parameter flow from relation to HeapTupleSatisfiesMVCC",
        concepts=concepts1,
        method_name="heap_fetch"
    )
    print("\nEnriched description:", enriched)
