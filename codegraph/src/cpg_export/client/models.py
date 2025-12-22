"""CPG Data Models.

Dataclasses for CPG statistics and query results.
"""
from dataclasses import dataclass


@dataclass
class CPGStatistics:
    """Statistics about the CPG.

    Contains counts for all CPG node and edge types according to CPG Spec v1.1.
    """
    # Node counts
    method_count: int = 0
    call_node_count: int = 0
    identifier_count: int = 0
    literal_count: int = 0
    local_count: int = 0
    param_count: int = 0
    return_count: int = 0
    block_count: int = 0
    control_structure_count: int = 0
    type_decl_count: int = 0

    # Edge counts
    ast_edge_count: int = 0
    cfg_edge_count: int = 0
    call_edge_count: int = 0
    ref_edge_count: int = 0
    reaching_def_edge_count: int = 0
    argument_edge_count: int = 0
    receiver_edge_count: int = 0
    condition_edge_count: int = 0

    def total_nodes(self) -> int:
        """Get total node count."""
        return (
            self.method_count + self.call_node_count + self.identifier_count +
            self.literal_count + self.local_count + self.param_count +
            self.return_count + self.block_count + self.control_structure_count +
            self.type_decl_count
        )

    def total_edges(self) -> int:
        """Get total edge count."""
        return (
            self.ast_edge_count + self.cfg_edge_count + self.call_edge_count +
            self.ref_edge_count + self.reaching_def_edge_count +
            self.argument_edge_count + self.receiver_edge_count +
            self.condition_edge_count
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'nodes': {
                'method': self.method_count,
                'call': self.call_node_count,
                'identifier': self.identifier_count,
                'literal': self.literal_count,
                'local': self.local_count,
                'param': self.param_count,
                'return': self.return_count,
                'block': self.block_count,
                'control_structure': self.control_structure_count,
                'type_decl': self.type_decl_count,
                'total': self.total_nodes()
            },
            'edges': {
                'ast': self.ast_edge_count,
                'cfg': self.cfg_edge_count,
                'call': self.call_edge_count,
                'ref': self.ref_edge_count,
                'reaching_def': self.reaching_def_edge_count,
                'argument': self.argument_edge_count,
                'receiver': self.receiver_edge_count,
                'condition': self.condition_edge_count,
                'total': self.total_edges()
            }
        }
