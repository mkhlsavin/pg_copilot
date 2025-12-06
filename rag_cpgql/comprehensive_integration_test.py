#!/usr/bin/env python3
"""
Comprehensive integration test - tests all fixed algorithms
"""

import time
import sys
from src.services.cpg_query_service import CPGQueryService
from src.analysis.call_graph_analyzer import CallGraphAnalyzer

def main():
    print("="*80)
    print("COMPREHENSIVE INTEGRATION TEST")
    print("Testing all fixed CallGraphAnalyzer algorithms on real CPG (52K methods)")
    print("="*80)
    print()

    # Initialize
    print("Initializing...")
    cpg_service = CPGQueryService('cpg.duckdb')
    analyzer = CallGraphAnalyzer(cpg_service)
    print("[OK] Initialized")
    print()

    results = {}

    # Test 1: PageRank
    print("TEST 1: PageRank")
    print("-" * 60)
    try:
        start = time.time()
        pr_results = analyzer.compute_pagerank(max_iterations=10, top_n=20)
        elapsed = time.time() - start
        print(f"[OK] Completed in {elapsed:.2f}s")
        print(f"     Results: {len(pr_results)} methods")
        if pr_results:
            top = pr_results[0]
            print(f"     Top: {top['method_name']} (score: {top['pagerank_score']:.6f})")
        results['PageRank'] = {'status': 'PASS', 'time': elapsed, 'count': len(pr_results)}
    except Exception as e:
        print(f"[FAIL] {e}")
        results['PageRank'] = {'status': 'FAIL', 'error': str(e)}
    print()

    # Test 2: SCC (Tarjan's Algorithm)
    print("TEST 2: Strongly Connected Components (SCC)")
    print("-" * 60)
    try:
        start = time.time()
        sccs = analyzer.compute_strongly_connected_components()
        elapsed = time.time() - start
        print(f"[OK] Completed in {elapsed:.2f}s")
        print(f"     Total SCCs: {len(sccs)}")
        cycles = [scc for scc in sccs if len(scc) > 1]
        print(f"     SCCs with cycles: {len(cycles)}")
        if cycles:
            largest = max(cycles, key=len)
            print(f"     Largest cycle: {len(largest)} methods")
        results['SCC'] = {'status': 'PASS', 'time': elapsed, 'sccs': len(sccs), 'cycles': len(cycles)}
    except Exception as e:
        print(f"[FAIL] {e}")
        results['SCC'] = {'status': 'FAIL', 'error': str(e)}
    print()

    # Test 3: WCC (Union-Find)
    print("TEST 3: Weakly Connected Components (WCC)")
    print("-" * 60)
    try:
        start = time.time()
        wccs = analyzer.compute_weakly_connected_components()
        elapsed = time.time() - start
        print(f"[OK] Completed in {elapsed:.2f}s")
        print(f"     Total WCCs: {len(wccs)}")
        isolated = [wcc for wcc in wccs if len(wcc) == 1]
        print(f"     Isolated methods: {len(isolated)}")
        if wccs:
            largest = max(wccs, key=len)
            print(f"     Largest component: {len(largest)} methods")
        results['WCC'] = {'status': 'PASS', 'time': elapsed, 'wccs': len(wccs), 'isolated': len(isolated)}
    except Exception as e:
        print(f"[FAIL] {e}")
        results['WCC'] = {'status': 'FAIL', 'error': str(e)}
    print()

    # Test 4: Betweenness Centrality
    print("TEST 4: Betweenness Centrality (with sampling)")
    print("-" * 60)
    try:
        start = time.time()
        bc_results = analyzer.compute_betweenness_centrality(top_n=20)
        elapsed = time.time() - start
        print(f"[OK] Completed in {elapsed:.2f}s")
        print(f"     Results: {len(bc_results)} methods")
        if bc_results:
            top = bc_results[0]
            print(f"     Top: {top['method_name']} (betweenness: {top['betweenness']:.6f})")
        results['Betweenness'] = {'status': 'PASS', 'time': elapsed, 'count': len(bc_results)}
    except Exception as e:
        print(f"[FAIL] {e}")
        results['Betweenness'] = {'status': 'FAIL', 'error': str(e)}
    print()

    # Test 5: Cycle Detection (uses SCC)
    print("TEST 5: Cycle Detection")
    print("-" * 60)
    try:
        start = time.time()
        cycles = analyzer.detect_cycles(max_cycle_length=100)
        elapsed = time.time() - start
        print(f"[OK] Completed in {elapsed:.2f}s")
        print(f"     Cycles found: {len(cycles)}")
        if cycles:
            sizes = [len(c.methods) for c in cycles[:5]]
            print(f"     Sample cycle sizes: {sizes}")
        results['Cycles'] = {'status': 'PASS', 'time': elapsed, 'count': len(cycles)}
    except Exception as e:
        print(f"[FAIL] {e}")
        results['Cycles'] = {'status': 'FAIL', 'error': str(e)}
    print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for r in results.values() if r.get('status') == 'PASS')
    total = len(results)

    print(f"Tests: {passed}/{total} passed")
    print()

    for test_name, result in results.items():
        if result.get('status') == 'PASS':
            print(f"[OK] {test_name:20s} - {result['time']:.2f}s")
        else:
            print(f"[FAIL] {test_name:20s} - {result.get('error', 'Unknown error')}")

    print()
    print("PERFORMANCE SUMMARY")
    print("-" * 80)
    total_time = sum(r.get('time', 0) for r in results.values())
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Average per test: {total_time/total:.2f}s")
    print()

    if passed == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"[WARNING] {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
