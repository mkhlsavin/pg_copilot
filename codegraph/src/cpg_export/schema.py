"""CPG Schema Definition for DuckDB (CPG Spec v1.1)

This module contains all table definitions, indexes, and schema initialization
logic for the Code Property Graph database.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Node Table Definitions
# =============================================================================

NODE_TABLES = {
    # Existing core nodes
    'nodes_method': """
        CREATE TABLE IF NOT EXISTS nodes_method (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            full_name VARCHAR,
            signature VARCHAR,
            filename VARCHAR,
            line_number INTEGER,
            column_number INTEGER,
            line_number_end INTEGER,
            column_number_end INTEGER,
            code TEXT,
            is_external BOOLEAN,
            ast_parent_type VARCHAR,
            ast_parent_full_name VARCHAR,
            order_index INTEGER,
            hash VARCHAR
        )
    """,
    'nodes_call': """
        CREATE TABLE IF NOT EXISTS nodes_call (
            id BIGINT PRIMARY KEY,
            method_full_name VARCHAR,
            name VARCHAR,
            signature VARCHAR,
            type_full_name VARCHAR,
            dispatch_type VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            filename VARCHAR
        )
    """,
    'nodes_identifier': """
        CREATE TABLE IF NOT EXISTS nodes_identifier (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER
        )
    """,
    'nodes_literal': """
        CREATE TABLE IF NOT EXISTS nodes_literal (
            id BIGINT PRIMARY KEY,
            code TEXT,
            type_full_name VARCHAR,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER
        )
    """,
    'nodes_local': """
        CREATE TABLE IF NOT EXISTS nodes_local (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_param': """
        CREATE TABLE IF NOT EXISTS nodes_param (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            index INTEGER,
            is_variadic BOOLEAN,
            evaluation_strategy VARCHAR
        )
    """,
    'nodes_return': """
        CREATE TABLE IF NOT EXISTS nodes_return (
            id BIGINT PRIMARY KEY,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER
        )
    """,
    'nodes_block': """
        CREATE TABLE IF NOT EXISTS nodes_block (
            id BIGINT PRIMARY KEY,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER
        )
    """,
    'nodes_control_structure': """
        CREATE TABLE IF NOT EXISTS nodes_control_structure (
            id BIGINT PRIMARY KEY,
            control_structure_type VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            parser_type_name VARCHAR
        )
    """,
    'nodes_type_decl': """
        CREATE TABLE IF NOT EXISTS nodes_type_decl (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            full_name VARCHAR,
            is_external BOOLEAN,
            inherits_from_type_full_name VARCHAR[],
            alias_type_full_name VARCHAR,
            filename VARCHAR,
            code TEXT,
            ast_parent_type VARCHAR,
            ast_parent_full_name VARCHAR
        )
    """,
    'nodes_metadata': """
        CREATE TABLE IF NOT EXISTS nodes_metadata (
            id BIGINT PRIMARY KEY,
            language VARCHAR,
            version VARCHAR,
            overlays VARCHAR[],
            root VARCHAR
        )
    """,
    'nodes_comment': """
        CREATE TABLE IF NOT EXISTS nodes_comment (
            id BIGINT PRIMARY KEY,
            code TEXT,
            filename VARCHAR,
            line_number INTEGER,
            column_number INTEGER,
            "offset" INTEGER,
            "offset_end" INTEGER,
            order_index INTEGER
        )
    """,

    # P0 Nodes - Critical for code structure
    'nodes_file': """
        CREATE TABLE IF NOT EXISTS nodes_file (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            hash VARCHAR,
            content TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            size_bytes INTEGER,
            language VARCHAR
        )
    """,
    'nodes_namespace': """
        CREATE TABLE IF NOT EXISTS nodes_namespace (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_namespace_block': """
        CREATE TABLE IF NOT EXISTS nodes_namespace_block (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            full_name VARCHAR,
            filename VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_member': """
        CREATE TABLE IF NOT EXISTS nodes_member (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_type': """
        CREATE TABLE IF NOT EXISTS nodes_type (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            full_name VARCHAR,
            type_decl_full_name VARCHAR
        )
    """,

    # P1 Nodes - Important for analysis
    'nodes_method_parameter_out': """
        CREATE TABLE IF NOT EXISTS nodes_method_parameter_out (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            index INTEGER,
            is_variadic BOOLEAN,
            evaluation_strategy VARCHAR
        )
    """,
    'nodes_method_return': """
        CREATE TABLE IF NOT EXISTS nodes_method_return (
            id BIGINT PRIMARY KEY,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            evaluation_strategy VARCHAR
        )
    """,
    'nodes_field_identifier': """
        CREATE TABLE IF NOT EXISTS nodes_field_identifier (
            id BIGINT PRIMARY KEY,
            canonical_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,
    'nodes_type_argument': """
        CREATE TABLE IF NOT EXISTS nodes_type_argument (
            id BIGINT PRIMARY KEY,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_type_parameter': """
        CREATE TABLE IF NOT EXISTS nodes_type_parameter (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,

    # P2 Nodes - Supplementary
    'nodes_jump_label': """
        CREATE TABLE IF NOT EXISTS nodes_jump_label (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            parser_type_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_jump_target': """
        CREATE TABLE IF NOT EXISTS nodes_jump_target (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            parser_type_name VARCHAR,
            argument_index INTEGER,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_method_ref': """
        CREATE TABLE IF NOT EXISTS nodes_method_ref (
            id BIGINT PRIMARY KEY,
            method_full_name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,
    'nodes_modifier': """
        CREATE TABLE IF NOT EXISTS nodes_modifier (
            id BIGINT PRIMARY KEY,
            modifier_type VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_type_ref': """
        CREATE TABLE IF NOT EXISTS nodes_type_ref (
            id BIGINT PRIMARY KEY,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,
    'nodes_unknown': """
        CREATE TABLE IF NOT EXISTS nodes_unknown (
            id BIGINT PRIMARY KEY,
            contained_ref VARCHAR,
            parser_type_name VARCHAR,
            type_full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,

    # P3 Nodes - Low priority
    'nodes_binding': """
        CREATE TABLE IF NOT EXISTS nodes_binding (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            signature VARCHAR,
            method_full_name VARCHAR
        )
    """,
    'nodes_annotation': """
        CREATE TABLE IF NOT EXISTS nodes_annotation (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            full_name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,
    'nodes_annotation_literal': """
        CREATE TABLE IF NOT EXISTS nodes_annotation_literal (
            id BIGINT PRIMARY KEY,
            name VARCHAR,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            argument_name VARCHAR
        )
    """,
    'nodes_annotation_parameter': """
        CREATE TABLE IF NOT EXISTS nodes_annotation_parameter (
            id BIGINT PRIMARY KEY,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
    'nodes_annotation_parameter_assign': """
        CREATE TABLE IF NOT EXISTS nodes_annotation_parameter_assign (
            id BIGINT PRIMARY KEY,
            code TEXT,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER
        )
    """,
}

# =============================================================================
# Edge Table Definitions
# =============================================================================

EDGE_TABLES = {
    # Core edges
    'edges_ast': """
        CREATE TABLE IF NOT EXISTS edges_ast (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_cfg': """
        CREATE TABLE IF NOT EXISTS edges_cfg (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_call': """
        CREATE TABLE IF NOT EXISTS edges_call (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_ref': """
        CREATE TABLE IF NOT EXISTS edges_ref (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_reaching_def': """
        CREATE TABLE IF NOT EXISTS edges_reaching_def (
            src BIGINT,
            dst BIGINT,
            variable VARCHAR,
            PRIMARY KEY (src, dst, variable)
        )
    """,
    'edges_argument': """
        CREATE TABLE IF NOT EXISTS edges_argument (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_receiver': """
        CREATE TABLE IF NOT EXISTS edges_receiver (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_condition': """
        CREATE TABLE IF NOT EXISTS edges_condition (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_dominate': """
        CREATE TABLE IF NOT EXISTS edges_dominate (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_post_dominate': """
        CREATE TABLE IF NOT EXISTS edges_post_dominate (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_source_file': """
        CREATE TABLE IF NOT EXISTS edges_source_file (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,

    # P0 Edges - Critical for analysis
    'edges_cdg': """
        CREATE TABLE IF NOT EXISTS edges_cdg (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_contains': """
        CREATE TABLE IF NOT EXISTS edges_contains (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_eval_type': """
        CREATE TABLE IF NOT EXISTS edges_eval_type (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,

    # P1 Edges - OOP analysis
    'edges_inherits_from': """
        CREATE TABLE IF NOT EXISTS edges_inherits_from (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_alias_of': """
        CREATE TABLE IF NOT EXISTS edges_alias_of (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,

    # P2 Edges - Supplementary
    'edges_binds_to': """
        CREATE TABLE IF NOT EXISTS edges_binds_to (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_parameter_link': """
        CREATE TABLE IF NOT EXISTS edges_parameter_link (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,

    # P3 Edges - Low priority
    'edges_tagged_by': """
        CREATE TABLE IF NOT EXISTS edges_tagged_by (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
    'edges_binds': """
        CREATE TABLE IF NOT EXISTS edges_binds (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    """,
}

# =============================================================================
# Index Definitions
# =============================================================================

INDEXES = [
    # Node indexes
    "CREATE INDEX IF NOT EXISTS idx_method_full_name ON nodes_method(full_name)",
    "CREATE INDEX IF NOT EXISTS idx_method_name ON nodes_method(name)",
    "CREATE INDEX IF NOT EXISTS idx_method_filename ON nodes_method(filename)",
    "CREATE INDEX IF NOT EXISTS idx_call_method_full_name ON nodes_call(method_full_name)",
    "CREATE INDEX IF NOT EXISTS idx_call_name ON nodes_call(name)",
    "CREATE INDEX IF NOT EXISTS idx_identifier_name ON nodes_identifier(name)",
    "CREATE INDEX IF NOT EXISTS idx_local_name ON nodes_local(name)",
    "CREATE INDEX IF NOT EXISTS idx_param_name ON nodes_param(name)",
    "CREATE INDEX IF NOT EXISTS idx_type_decl_full_name ON nodes_type_decl(full_name)",
    "CREATE INDEX IF NOT EXISTS idx_comment_filename ON nodes_comment(filename)",
    "CREATE INDEX IF NOT EXISTS idx_comment_line ON nodes_comment(line_number)",

    # P0 Node indexes
    "CREATE INDEX IF NOT EXISTS idx_file_name ON nodes_file(name)",
    "CREATE INDEX IF NOT EXISTS idx_namespace_name ON nodes_namespace(name)",
    "CREATE INDEX IF NOT EXISTS idx_namespace_block_full_name ON nodes_namespace_block(full_name)",
    "CREATE INDEX IF NOT EXISTS idx_member_name ON nodes_member(name)",
    "CREATE INDEX IF NOT EXISTS idx_type_full_name ON nodes_type(full_name)",

    # P1 Node indexes
    "CREATE INDEX IF NOT EXISTS idx_field_identifier_canonical ON nodes_field_identifier(canonical_name)",
    "CREATE INDEX IF NOT EXISTS idx_method_ref_method ON nodes_method_ref(method_full_name)",

    # P2 Node indexes
    "CREATE INDEX IF NOT EXISTS idx_modifier_type ON nodes_modifier(modifier_type)",
    "CREATE INDEX IF NOT EXISTS idx_type_ref_type ON nodes_type_ref(type_full_name)",

    # Edge indexes
    "CREATE INDEX IF NOT EXISTS idx_ast_src ON edges_ast(src)",
    "CREATE INDEX IF NOT EXISTS idx_ast_dst ON edges_ast(dst)",
    "CREATE INDEX IF NOT EXISTS idx_cfg_src ON edges_cfg(src)",
    "CREATE INDEX IF NOT EXISTS idx_cfg_dst ON edges_cfg(dst)",
    "CREATE INDEX IF NOT EXISTS idx_call_edge_src ON edges_call(src)",
    "CREATE INDEX IF NOT EXISTS idx_call_edge_dst ON edges_call(dst)",
    "CREATE INDEX IF NOT EXISTS idx_ref_src ON edges_ref(src)",
    "CREATE INDEX IF NOT EXISTS idx_ref_dst ON edges_ref(dst)",
    "CREATE INDEX IF NOT EXISTS idx_reaching_def_src ON edges_reaching_def(src)",
    "CREATE INDEX IF NOT EXISTS idx_reaching_def_dst ON edges_reaching_def(dst)",
    "CREATE INDEX IF NOT EXISTS idx_reaching_def_variable ON edges_reaching_def(variable)",
    "CREATE INDEX IF NOT EXISTS idx_argument_src ON edges_argument(src)",
    "CREATE INDEX IF NOT EXISTS idx_argument_dst ON edges_argument(dst)",
    "CREATE INDEX IF NOT EXISTS idx_source_file_src ON edges_source_file(src)",
    "CREATE INDEX IF NOT EXISTS idx_source_file_dst ON edges_source_file(dst)",

    # P0-P3 Edge indexes
    "CREATE INDEX IF NOT EXISTS idx_cdg_src ON edges_cdg(src)",
    "CREATE INDEX IF NOT EXISTS idx_cdg_dst ON edges_cdg(dst)",
    "CREATE INDEX IF NOT EXISTS idx_contains_src ON edges_contains(src)",
    "CREATE INDEX IF NOT EXISTS idx_contains_dst ON edges_contains(dst)",
    "CREATE INDEX IF NOT EXISTS idx_eval_type_src ON edges_eval_type(src)",
    "CREATE INDEX IF NOT EXISTS idx_eval_type_dst ON edges_eval_type(dst)",
    "CREATE INDEX IF NOT EXISTS idx_inherits_from_src ON edges_inherits_from(src)",
    "CREATE INDEX IF NOT EXISTS idx_inherits_from_dst ON edges_inherits_from(dst)",
]

# All table names for iteration
ALL_NODE_TABLES = list(NODE_TABLES.keys())
ALL_EDGE_TABLES = list(EDGE_TABLES.keys())
ALL_TABLES = ALL_NODE_TABLES + ALL_EDGE_TABLES


def get_all_tables_to_drop() -> list:
    """Get list of all tables in drop order (edges first, then nodes)"""
    return ALL_EDGE_TABLES + ALL_NODE_TABLES + ['export_progress', 'cpg_nodes']


def initialize_schema(conn, force_recreate: bool = False):
    """Initialize DuckDB schema for CPG storage (CPG Spec v1.1)

    Args:
        conn: DuckDB connection
        force_recreate: If True, drop existing tables. If False, preserve existing data.
    """
    logger.info("Initializing CPG schema (CPG Spec v1.1)...")

    if force_recreate:
        logger.info("Force recreate: dropping existing tables...")
        for table in get_all_tables_to_drop():
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                logger.debug(f"Could not drop {table}: {e}")
    else:
        logger.info("Resume mode: preserving existing tables with data")

    # Create node tables
    logger.info("Creating node tables (IF NOT EXISTS)...")
    for table_name, create_sql in NODE_TABLES.items():
        try:
            conn.execute(create_sql)
        except Exception as e:
            logger.warning(f"Could not create {table_name}: {e}")

    # Create edge tables
    logger.info("Creating edge tables (IF NOT EXISTS)...")
    for table_name, create_sql in EDGE_TABLES.items():
        try:
            conn.execute(create_sql)
        except Exception as e:
            logger.warning(f"Could not create {table_name}: {e}")

    # Create indexes
    logger.info("Creating indexes (IF NOT EXISTS)...")
    for index_sql in INDEXES:
        try:
            conn.execute(index_sql)
        except Exception as e:
            logger.debug(f"Could not create index: {e}")

    logger.info("DuckDB schema initialized successfully (CPG Spec v1.1 compliant)")
