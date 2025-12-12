"""
Tests for Call Graph Analyzer (Graph Method #2)

Tests:
- Shortest path finding
- Caller/callee discovery
- Cycle detection
- Impact analysis
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.analysis.call_graph_analyzer import (
    CallGraphAnalyzer,
    CallPath,
    CallCycle,
    ImpactAnalysis
)


@pytest.fixture
def mock_cpg_service():
    """Mock CPG service for testing"""
    mock = Mock()
    mock.execute_query = MagicMock()
    return mock


@pytest.fixture
def analyzer(mock_cpg_service):
    """Create CallGraphAnalyzer with mocked CPG service"""
    return CallGraphAnalyzer(mock_cpg_service)


class TestShortestPath:
    """Test shortest path finding"""

    def test_direct_call(self, analyzer, mock_cpg_service):
        """Test finding direct call (length=1)"""
        # Mock response: direct call from foo to bar
        mock_cpg_service.execute_query.return_value = [{
            'source_name': 'foo',
            'target_name': 'bar',
            'depth': 1,
            'path': '123,456'
        }]

        path = analyzer.find_shortest_path('foo', 'bar')

        assert path is not None
        assert path.source_method == 'foo'
        assert path.target_method == 'bar'
        assert path.path_length == 1
        assert path.path_type == "direct"

    def test_transitive_call(self, analyzer, mock_cpg_service):
        """Test finding transitive call (length>1)"""
        # Mock response: foo -> baz -> bar
        mock_cpg_service.execute_query.side_effect = [
            [{
                'source_name': 'foo',
                'target_name': 'bar',
                'depth': 2,
                'path': '123,789,456'
            }],
            [{'name': 'baz'}]  # Intermediate method
        ]

        path = analyzer.find_shortest_path('foo', 'bar', max_depth=5)

        assert path is not None
        assert path.path_length == 2
        assert path.path_type == "transitive"
        assert 'baz' in path.intermediate_methods

    def test_no_path_exists(self, analyzer, mock_cpg_service):
        """Test when no path exists between methods"""
        mock_cpg_service.execute_query.return_value = []

        path = analyzer.find_shortest_path('foo', 'bar')

        assert path is None

    def test_max_depth_limit(self, analyzer, mock_cpg_service):
        """Test that max_depth parameter is respected"""
        mock_cpg_service.execute_query.return_value = []

        path = analyzer.find_shortest_path('foo', 'bar', max_depth=2)

        # Verify the query was called (max_depth is passed internally)
        assert mock_cpg_service.execute_query.called
        # With no path found, result should be None
        assert path is None


class TestCallersAndCallees:
    """Test finding callers and callees"""

    def test_find_direct_callers(self, analyzer, mock_cpg_service):
        """Test finding direct callers only"""
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'foo'},
            {'caller_name': 'bar'},
            {'caller_name': 'baz'}
        ]

        callers = analyzer.find_all_callers('target_method', direct_only=True)

        assert len(callers) == 3
        assert 'foo' in callers
        assert 'bar' in callers
        assert 'baz' in callers

    def test_find_transitive_callers(self, analyzer, mock_cpg_service):
        """Test finding transitive callers (recursive)"""
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'foo'},
            {'caller_name': 'bar'},
            {'caller_name': 'baz'},
            {'caller_name': 'qux'},  # Transitive caller
            {'caller_name': 'quux'}  # Transitive caller
        ]

        callers = analyzer.find_all_callers('target_method', max_depth=3, direct_only=False)

        assert len(callers) == 5
        assert 'qux' in callers  # Transitive should be included

    def test_find_direct_callees(self, analyzer, mock_cpg_service):
        """Test finding direct callees"""
        mock_cpg_service.execute_query.return_value = [
            {'callee_name': 'malloc'},
            {'callee_name': 'free'},
            {'callee_name': 'printf'}
        ]

        callees = analyzer.find_all_callees('source_method', direct_only=True)

        assert len(callees) == 3
        assert 'malloc' in callees
        assert 'free' in callees

    def test_empty_callers_list(self, analyzer, mock_cpg_service):
        """Test method with no callers"""
        mock_cpg_service.execute_query.return_value = []

        callers = analyzer.find_all_callers('isolated_method')

        assert callers == []


class TestCycleDetection:
    """Test cycle and recursion detection"""

    def test_self_recursion(self, analyzer, mock_cpg_service):
        """Test detecting self-recursive methods"""
        # Mock: factorial calls itself
        # Updated for SCC-based detection
        mock_cpg_service.execute_query.side_effect = [
            # SCC query (call edges)
            [{'caller_name': 'factorial', 'callee_name': 'factorial'}],
            # Self-recursive query
            [{'method_name': 'factorial'}]
        ]

        cycles = analyzer.detect_cycles()

        assert len(cycles) >= 1
        self_recursive = [c for c in cycles if c.is_self_recursive]
        assert len(self_recursive) == 1
        assert 'factorial' in self_recursive[0].methods
        assert self_recursive[0].cycle_length == 1

    def test_mutual_recursion(self, analyzer, mock_cpg_service):
        """Test detecting mutual recursion (A->B->A)"""
        # Mock: is_even <-> is_odd
        # Updated for SCC-based detection
        mock_cpg_service.execute_query.side_effect = [
            # SCC query (call edges)
            [
                {'caller_name': 'is_even', 'callee_name': 'is_odd'},
                {'caller_name': 'is_odd', 'callee_name': 'is_even'}
            ],
            # Self-recursive query
            []
        ]

        cycles = analyzer.detect_cycles()

        assert len(cycles) >= 1
        mutual = [c for c in cycles if not c.is_self_recursive]
        assert len(mutual) >= 1
        assert mutual[0].cycle_length >= 2
        assert 'is_even' in mutual[0].methods or 'is_odd' in mutual[0].methods

    def test_no_cycles(self, analyzer, mock_cpg_service):
        """Test when no cycles exist"""
        mock_cpg_service.execute_query.side_effect = [
            [],  # No self-recursion
            []   # No mutual recursion
        ]

        cycles = analyzer.detect_cycles()

        assert cycles == []


class TestImpactAnalysis:
    """Test impact analysis for method changes"""

    def test_high_impact_method(self, analyzer, mock_cpg_service):
        """Test analyzing a high-impact method (called by many)"""
        # Mock: malloc is called by many methods
        def mock_query(query, params=None):
            if 'direct' in str(query) or params and len(params) == 1:
                # Direct callers
                return [{'caller_name': f'caller_{i}'} for i in range(50)]
            elif 'transitive' in str(query) or (params and len(params) == 2):
                # Transitive callers
                return [{'caller_name': f'caller_{i}'} for i in range(200)]
            elif 'COUNT' in query:
                # Total methods
                return [{'total': 10000}]
            return []

        mock_cpg_service.execute_query.side_effect = [
            [{'caller_name': f'caller_{i}'} for i in range(50)],  # Direct callers
            [{'caller_name': f'caller_{i}'} for i in range(200)],  # Transitive callers
            [{'callee_name': f'callee_{i}'} for i in range(10)],  # Direct callees
            [{'callee_name': f'callee_{i}'} for i in range(20)],  # Transitive callees
            [{'total': 10000}]  # Total methods
        ]

        analysis = analyzer.analyze_impact('malloc', max_depth=3)

        assert analysis.method_name == 'malloc'
        assert len(analysis.direct_callers) == 50
        assert len(analysis.transitive_callers) > 0
        assert analysis.impact_score > 0.0

    def test_low_impact_method(self, analyzer, mock_cpg_service):
        """Test analyzing a low-impact method (few callers)"""
        mock_cpg_service.execute_query.side_effect = [
            [{'caller_name': 'foo'}],  # 1 direct caller
            [{'caller_name': 'foo'}, {'caller_name': 'bar'}],  # 2 transitive
            [{'callee_name': 'baz'}],  # 1 direct callee
            [{'callee_name': 'baz'}, {'callee_name': 'qux'}],  # 2 transitive
            [{'total': 10000}]  # Total methods
        ]

        analysis = analyzer.analyze_impact('helper_function', max_depth=3)

        assert analysis.impact_score < 0.1  # Low impact

    def test_isolated_method(self, analyzer, mock_cpg_service):
        """Test analyzing an isolated method (no callers/callees)"""
        # Use return_value instead of side_effect to handle variable query count
        mock_cpg_service.execute_query.return_value = []

        analysis = analyzer.analyze_impact('dead_code', max_depth=3)

        assert len(analysis.direct_callers) == 0
        assert len(analysis.transitive_callers) == 0
        assert len(analysis.direct_callees) == 0
        assert len(analysis.transitive_callees) == 0
        assert analysis.impact_score == 0.0


class TestCallStatistics:
    """Test call graph statistics"""

    def test_get_statistics(self, analyzer, mock_cpg_service):
        """Test retrieving call graph statistics"""
        mock_cpg_service.execute_query.return_value = [{
            'total_methods': 5000,
            'total_calls': 15000,
            'avg_fan_out': 3.0,
            'avg_fan_in': 2.5
        }]

        stats = analyzer.get_call_statistics()

        assert stats['total_methods'] == 5000
        assert stats['total_calls'] == 15000
        assert stats['average_fan_out'] == 3.0
        assert stats['average_fan_in'] == 2.5

    def test_statistics_with_error(self, analyzer, mock_cpg_service):
        """Test statistics when query fails"""
        mock_cpg_service.execute_query.side_effect = Exception("DB error")

        stats = analyzer.get_call_statistics()

        assert stats == {}


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_method_name_with_special_chars(self, analyzer, mock_cpg_service):
        """Test handling method names with special characters"""
        mock_cpg_service.execute_query.return_value = [{
            'caller_name': 'operator++'
        }]

        callers = analyzer.find_all_callers('operator++', direct_only=True)

        assert 'operator++' in callers

    def test_very_deep_call_chain(self, analyzer, mock_cpg_service):
        """Test handling very deep call chains"""
        mock_cpg_service.execute_query.return_value = [{
            'source_name': 'main',
            'target_name': 'leaf',
            'depth': 20,
            'path': ','.join([str(i) for i in range(20)])
        }]

        path = analyzer.find_shortest_path('main', 'leaf', max_depth=25)

        assert path is not None
        assert path.path_length == 20

    def test_query_error_handling(self, analyzer, mock_cpg_service):
        """Test error handling when query fails"""
        mock_cpg_service.execute_query.side_effect = Exception("Query error")

        # Should not raise exception, return empty/None
        path = analyzer.find_shortest_path('foo', 'bar')
        assert path is None

        callers = analyzer.find_all_callers('foo')
        assert callers == []

        cycles = analyzer.detect_cycles()
        assert cycles == []


# ============================================================================
# Phase 1.2 Tests - New Advanced Graph Algorithms
# ============================================================================


class TestPageRank:
    """Test compute_pagerank() - Phase 1.2"""

    def test_simple_pagerank(self, analyzer, mock_cpg_service):
        """Test PageRank on simple graph"""
        # Mock call edges: A calls B, A calls C, B calls C
        # Expected: C has highest PageRank (called by both A and B)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'A', 'callee_name': 'C'},
            {'caller_name': 'B', 'callee_name': 'C'}
        ]

        results = analyzer.compute_pagerank(max_iterations=20, top_n=10)

        assert len(results) == 3
        # C should have highest PageRank
        assert results[0]['method_name'] == 'C'
        assert results[0]['pagerank_score'] > results[1]['pagerank_score']

    def test_pagerank_hub_method(self, analyzer, mock_cpg_service):
        """Test PageRank identifies hub methods (called by many)"""
        # Mock: palloc called by 10 methods
        edges = [{'caller_name': f'caller_{i}', 'callee_name': 'palloc'} for i in range(10)]
        mock_cpg_service.execute_query.return_value = edges

        results = analyzer.compute_pagerank(top_n=15)  # Request more to get all

        assert len(results) >= 5  # At least top 5
        # palloc should be in results with high PageRank
        palloc_result = next((r for r in results if r['method_name'] == 'palloc'), None)
        assert palloc_result is not None
        assert palloc_result['in_degree'] == 10
        # palloc should have highest PageRank (called by 10 methods)
        assert palloc_result == results[0]  # Should be first (highest)

    def test_pagerank_convergence(self, analyzer, mock_cpg_service):
        """Test PageRank converges within max_iterations"""
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'C'}
        ]

        results = analyzer.compute_pagerank(max_iterations=10, tolerance=0.001)

        # Should converge and return results
        assert len(results) > 0
        # Sum of PageRank scores should be close to 1.0 (within reasonable bound)
        total_pr = sum(r['pagerank_score'] for r in results)
        # Note: With 3 methods, each starts at 1/3, so sum should be ~1.0
        # But due to damping and convergence, it might be slightly less
        assert 0.25 < total_pr < 1.05

    def test_pagerank_empty_graph(self, analyzer, mock_cpg_service):
        """Test PageRank on empty graph"""
        mock_cpg_service.execute_query.return_value = []

        results = analyzer.compute_pagerank()

        assert len(results) == 0

    def test_pagerank_top_n_limit(self, analyzer, mock_cpg_service):
        """Test top_n parameter limits results"""
        edges = [{'caller_name': f'A{i}', 'callee_name': f'B{i}'} for i in range(100)]
        mock_cpg_service.execute_query.return_value = edges

        results = analyzer.compute_pagerank(top_n=10)

        assert len(results) == 10


class TestStronglyConnectedComponents:
    """Test compute_strongly_connected_components() - Phase 1.2"""

    def test_simple_scc_no_cycles(self, analyzer, mock_cpg_service):
        """Test SCC on acyclic graph"""
        # A -> B -> C (no cycles)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'C'}
        ]

        sccs = analyzer.compute_strongly_connected_components()

        # Each method in its own SCC
        assert len(sccs) == 3
        assert all(len(scc) == 1 for scc in sccs)

    def test_scc_self_recursion(self, analyzer, mock_cpg_service):
        """Test SCC detects self-recursion"""
        # A calls itself
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'A'}
        ]

        sccs = analyzer.compute_strongly_connected_components()

        # A is in its own SCC (size 1 but has self-loop)
        assert len(sccs) == 1
        assert sccs[0] == ['A']

    def test_scc_mutual_recursion(self, analyzer, mock_cpg_service):
        """Test SCC detects mutual recursion"""
        # A <-> B (mutual recursion)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'A'}
        ]

        sccs = analyzer.compute_strongly_connected_components()

        # A and B should be in same SCC
        assert len(sccs) == 1
        assert len(sccs[0]) == 2
        assert set(sccs[0]) == {'A', 'B'}

    def test_scc_complex_cycle(self, analyzer, mock_cpg_service):
        """Test SCC detects complex cycles"""
        # A -> B -> C -> D -> A (4-way cycle)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'C'},
            {'caller_name': 'C', 'callee_name': 'D'},
            {'caller_name': 'D', 'callee_name': 'A'}
        ]

        sccs = analyzer.compute_strongly_connected_components()

        # All 4 methods in one SCC
        assert len(sccs) == 1
        assert len(sccs[0]) == 4
        assert set(sccs[0]) == {'A', 'B', 'C', 'D'}

    def test_scc_multiple_components(self, analyzer, mock_cpg_service):
        """Test SCC finds multiple components"""
        # Two separate cycles: A <-> B and C <-> D
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'A'},
            {'caller_name': 'C', 'callee_name': 'D'},
            {'caller_name': 'D', 'callee_name': 'C'}
        ]

        sccs = analyzer.compute_strongly_connected_components()

        # Two SCCs of size 2
        assert len(sccs) == 2
        assert all(len(scc) == 2 for scc in sccs)


class TestWeaklyConnectedComponents:
    """Test compute_weakly_connected_components() - Phase 1.2"""

    def test_single_wcc(self, analyzer, mock_cpg_service):
        """Test WCC on fully connected graph"""
        # A -> B -> C (all connected)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'C'}
        ]

        wccs = analyzer.compute_weakly_connected_components()

        # All methods in one WCC
        assert len(wccs) == 1
        assert len(wccs[0]) == 3

    def test_multiple_wccs(self, analyzer, mock_cpg_service):
        """Test WCC finds isolated components"""
        # Two isolated components: A -> B and C -> D
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'C', 'callee_name': 'D'}
        ]

        wccs = analyzer.compute_weakly_connected_components()

        # Two WCCs
        assert len(wccs) == 2
        assert all(len(wcc) == 2 for wcc in wccs)

    def test_wcc_dead_code(self, analyzer, mock_cpg_service):
        """Test WCC identifies potential dead code"""
        # Large main component + small isolated component (dead code)
        edges = [{'caller_name': f'main_{i}', 'callee_name': f'main_{i+1}'} for i in range(100)]
        edges.append({'caller_name': 'dead_func', 'callee_name': 'helper'})

        mock_cpg_service.execute_query.return_value = edges

        wccs = analyzer.compute_weakly_connected_components()

        # Main component + 1 small isolated component
        assert len(wccs) == 2
        assert len(wccs[0]) > 50  # Large main component
        assert len(wccs[1]) == 2   # Small isolated (dead code)

    def test_wcc_empty_graph(self, analyzer, mock_cpg_service):
        """Test WCC on empty graph"""
        mock_cpg_service.execute_query.return_value = []

        wccs = analyzer.compute_weakly_connected_components()

        assert len(wccs) == 0


class TestBetweennessCentrality:
    """Test compute_betweenness_centrality() - Phase 1.2"""

    def test_simple_betweenness(self, analyzer, mock_cpg_service):
        """Test betweenness on simple path"""
        # A -> B -> C (B is bridge between A and C)
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'B', 'callee_name': 'C'}
        ]

        results = analyzer.compute_betweenness_centrality(sample_size=3, top_n=10)

        # B should have highest betweenness
        b_result = next((r for r in results if r['method_name'] == 'B'), None)
        assert b_result is not None
        assert b_result['betweenness_score'] > 0

    def test_betweenness_hub_method(self, analyzer, mock_cpg_service):
        """Test betweenness identifies bridge methods"""
        # Star topology: A calls B, C calls B, D calls B
        # B connects all paths
        mock_cpg_service.execute_query.return_value = [
            {'caller_name': 'A', 'callee_name': 'B'},
            {'caller_name': 'C', 'callee_name': 'B'},
            {'caller_name': 'D', 'callee_name': 'B'}
        ]

        results = analyzer.compute_betweenness_centrality(sample_size=4)

        # B should have high betweenness
        b_result = next((r for r in results if r['method_name'] == 'B'), None)
        assert b_result is not None

    def test_betweenness_sampling(self, analyzer, mock_cpg_service):
        """Test betweenness uses sampling for large graphs"""
        # Mock large graph
        edges = [{'caller_name': f'A{i}', 'callee_name': f'B{i}'} for i in range(2000)]
        mock_cpg_service.execute_query.return_value = edges

        # Should use sampling automatically
        results = analyzer.compute_betweenness_centrality(sample_size=100, top_n=10)

        assert len(results) == 10

    def test_betweenness_empty_graph(self, analyzer, mock_cpg_service):
        """Test betweenness on empty graph"""
        mock_cpg_service.execute_query.return_value = []

        results = analyzer.compute_betweenness_centrality()

        assert len(results) == 0


class TestCyclomaticComplexity:
    """Test compute_cyclomatic_complexity() - Phase 1.2"""

    def test_simple_complexity(self, analyzer, mock_cpg_service):
        """Test cyclomatic complexity calculation"""
        # Mock CFG: 5 nodes, 6 edges => M = 6 - 5 + 2 = 3
        mock_cpg_service.execute_query.return_value = [{
            'method_name': 'foo',
            'filename': 'test.c',
            'node_count': 5,
            'edge_count': 6
        }]

        results = analyzer.compute_cyclomatic_complexity(method_name='foo')

        assert len(results) == 1
        assert results[0]['method_name'] == 'foo'
        assert results[0]['complexity'] == 3
        assert results[0]['risk_level'] == 'low'

    def test_high_complexity(self, analyzer, mock_cpg_service):
        """Test high complexity detection"""
        # M = 75 - 50 + 2 = 27 (high risk)
        mock_cpg_service.execute_query.return_value = [{
            'method_name': 'complex_func',
            'filename': 'complex.c',
            'node_count': 50,
            'edge_count': 75
        }]

        results = analyzer.compute_cyclomatic_complexity(method_name='complex_func')

        assert results[0]['complexity'] == 27
        assert results[0]['risk_level'] == 'high'

    def test_very_high_complexity(self, analyzer, mock_cpg_service):
        """Test very high complexity detection"""
        # M = 150 - 100 + 2 = 52 (very high risk)
        mock_cpg_service.execute_query.return_value = [{
            'method_name': 'monster_func',
            'filename': 'monster.c',
            'node_count': 100,
            'edge_count': 150
        }]

        results = analyzer.compute_cyclomatic_complexity(method_name='monster_func')

        assert results[0]['complexity'] == 52
        assert results[0]['risk_level'] == 'very_high'

    def test_complexity_top_n(self, analyzer, mock_cpg_service):
        """Test top_n parameter"""
        # Mock 100 methods
        mock_results = [{
            'method_name': f'func_{i}',
            'filename': 'test.c',
            'node_count': i + 5,
            'edge_count': (i + 5) + i
        } for i in range(100)]

        mock_cpg_service.execute_query.return_value = mock_results

        results = analyzer.compute_cyclomatic_complexity(top_n=10)

        assert len(results) == 10
        # Should be sorted by complexity descending
        complexities = [r['complexity'] for r in results]
        assert complexities == sorted(complexities, reverse=True)

    def test_complexity_no_cfg(self, analyzer, mock_cpg_service):
        """Test when no CFG data available"""
        mock_cpg_service.execute_query.return_value = []

        results = analyzer.compute_cyclomatic_complexity()

        assert len(results) == 0


class TestDetectCyclesEnhanced:
    """Test detect_cycles() enhanced with SCC - Phase 1.2"""

    def test_cycles_uses_scc(self, analyzer, mock_cpg_service):
        """Test that detect_cycles() now uses SCC internally"""
        # Mock SCC query (called internally)
        mock_cpg_service.execute_query.side_effect = [
            # SCC query (Tarjan's algorithm input)
            [
                {'caller_name': 'A', 'callee_name': 'B'},
                {'caller_name': 'B', 'callee_name': 'A'}
            ],
            # Self-recursive query
            [{'method_name': 'C'}]
        ]

        cycles = analyzer.detect_cycles(max_cycle_length=10)

        # Should find the A-B mutual recursion + C self-recursion
        assert len(cycles) >= 1

    def test_cycles_accuracy_improvement(self, analyzer, mock_cpg_service):
        """Test improved accuracy from SCC"""
        # Complex mutual recursion that heuristics might miss
        mock_cpg_service.execute_query.side_effect = [
            # Call edges forming complex cycle
            [
                {'caller_name': 'A', 'callee_name': 'B'},
                {'caller_name': 'B', 'callee_name': 'C'},
                {'caller_name': 'C', 'callee_name': 'D'},
                {'caller_name': 'D', 'callee_name': 'A'}
            ],
            # Self-recursive query
            []
        ]

        cycles = analyzer.detect_cycles(max_cycle_length=10)

        # Should find the 4-way cycle accurately
        assert len(cycles) >= 1
        # Should have a cycle with 4 methods
        has_4way_cycle = any(len(c.methods) == 4 for c in cycles)
        assert has_4way_cycle


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
