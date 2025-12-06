"""
Update DuckDB CPG schema with comment and tag tables.
Creates empty tables and updates property graph.
"""

import duckdb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    conn = duckdb.connect('cpg.duckdb')

    # Load duckpgq extension for property graph support
    try:
        conn.execute("LOAD duckpgq")
        print("Loaded duckpgq extension")
    except Exception as e:
        print(f"Note: duckpgq extension not available: {e}")
        print("Property graph will be skipped, but tables are still created.")

    # Create nodes_comment table if not exists
    print('Creating nodes_comment table...')
    conn.execute('''
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
    ''')

    # Create edges_source_file table if not exists
    print('Creating edges_source_file table...')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS edges_source_file (
            src BIGINT,
            dst BIGINT,
            PRIMARY KEY (src, dst)
        )
    ''')

    # Create indexes
    print('Creating indexes...')
    try:
        conn.execute('CREATE INDEX IF NOT EXISTS idx_comment_filename ON nodes_comment(filename)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_comment_line ON nodes_comment(line_number)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_source_file_src ON edges_source_file(src)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_source_file_dst ON edges_source_file(dst)')
    except Exception as e:
        print(f'Index creation note: {e}')

    # Check counts
    comment_count = conn.execute('SELECT COUNT(*) FROM nodes_comment').fetchone()[0]
    edge_count = conn.execute('SELECT COUNT(*) FROM edges_source_file').fetchone()[0]
    tag_count = conn.execute('SELECT COUNT(*) FROM nodes_tag').fetchone()[0]

    print(f'\nTable Status:')
    print(f'  nodes_comment: {comment_count:,} rows')
    print(f'  edges_source_file: {edge_count:,} rows')
    print(f'  nodes_tag: {tag_count:,} rows')

    # Now recreate the cpg_nodes materialized table and property graph
    print('\nRecreating cpg_nodes table with COMMENT and TAG...')

    # Drop and recreate cpg_nodes
    conn.execute('DROP TABLE IF EXISTS cpg_nodes')
    conn.execute("""
        CREATE TABLE cpg_nodes AS
        SELECT id, 'METHOD' as node_type FROM nodes_method
        UNION ALL SELECT id, 'CALL' FROM nodes_call
        UNION ALL SELECT id, 'IDENTIFIER' FROM nodes_identifier
        UNION ALL SELECT id, 'LITERAL' FROM nodes_literal
        UNION ALL SELECT id, 'LOCAL' FROM nodes_local
        UNION ALL SELECT id, 'PARAM' FROM nodes_param
        UNION ALL SELECT id, 'RETURN' FROM nodes_return
        UNION ALL SELECT id, 'BLOCK' FROM nodes_block
        UNION ALL SELECT id, 'CONTROL_STRUCTURE' FROM nodes_control_structure
        UNION ALL SELECT id, 'TYPE_DECL' FROM nodes_type_decl
        UNION ALL SELECT id, 'METADATA' FROM nodes_metadata
        UNION ALL SELECT id, 'COMMENT' FROM nodes_comment
        UNION ALL SELECT id, 'TAG' FROM nodes_tag
    """)

    # Add primary key
    conn.execute('ALTER TABLE cpg_nodes ADD PRIMARY KEY (id)')
    conn.execute('CREATE INDEX idx_cpg_nodes_type ON cpg_nodes(node_type)')

    cpg_nodes_count = conn.execute('SELECT COUNT(*) FROM cpg_nodes').fetchone()[0]
    print(f'  cpg_nodes: {cpg_nodes_count:,} rows')

    # Drop and recreate property graph
    print('\nRecreating property graph with comment/tag support...')
    try:
        conn.execute('DROP PROPERTY GRAPH IF EXISTS cpg')
    except:
        pass

    try:
        conn.execute("""
            CREATE PROPERTY GRAPH cpg
        VERTEX TABLES (
            nodes_method LABEL METHOD,
            nodes_call LABEL CALL_NODE,
            nodes_identifier LABEL IDENTIFIER,
            nodes_literal LABEL LITERAL,
            nodes_local LABEL LOCAL,
            nodes_param LABEL PARAM,
            nodes_return LABEL RETURN_NODE,
            nodes_block LABEL BLOCK,
            nodes_control_structure LABEL CONTROL_STRUCTURE,
            nodes_type_decl LABEL TYPE_DECL,
            nodes_metadata LABEL METADATA,
            nodes_comment LABEL COMMENT,
            nodes_tag LABEL TAG,
            cpg_nodes LABEL CPG_NODE
        )
        EDGE TABLES (
            edges_ast
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL AST,
            edges_cfg
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL CFG,
            edges_ref
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL REF,
            edges_reaching_def
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL REACHING_DEF,
            edges_argument
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL ARGUMENT,
            edges_dominate
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL DOMINATE,
            edges_post_dominate
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL POST_DOMINATE,
            edges_call
                SOURCE KEY (src) REFERENCES nodes_call (id)
                DESTINATION KEY (dst) REFERENCES nodes_method (id)
                LABEL CALLS,
            edges_receiver
                SOURCE KEY (src) REFERENCES nodes_call (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL RECEIVER,
            edges_condition
                SOURCE KEY (src) REFERENCES nodes_control_structure (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL CONDITION,
            edges_source_file
                SOURCE KEY (src) REFERENCES nodes_comment (id)
                DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
                LABEL SOURCE_FILE,
            edges_tagged_by
                SOURCE KEY (src) REFERENCES cpg_nodes (id)
                DESTINATION KEY (dst) REFERENCES nodes_tag (id)
                LABEL TAGGED_BY
        )
        """)
        print('[OK] Property graph created with COMMENT, TAG, SOURCE_FILE, TAGGED_BY!')
    except Exception as e:
        print(f'[WARN] Property graph creation skipped: {e}')
        print('Tables are still created and usable via SQL.')

    conn.close()
    print('\nDone! DuckDB updated successfully.')


if __name__ == '__main__':
    main()
