-- Migration: Add edges_include table for file-level include/import relationships
-- Sprint 3 - Scenario 11 Enhancement: Module Dependencies
--
-- This table stores #include directives and file-level dependencies
-- to support queries like "files including postgres.h" and "modules depending on X"

-- File-level include/import relationships
CREATE TABLE IF NOT EXISTS edges_include (
    id BIGINT PRIMARY KEY,                -- Unique edge ID (auto-generated or from Joern)
    src BIGINT NOT NULL,                  -- Source file node ID (file that has the #include)
    dst BIGINT,                           -- Included file node ID (may be NULL if file not in CPG)
    include_path VARCHAR NOT NULL,        -- Path as written in #include (e.g., "postgres.h" or <stdio.h>)
    resolved_path VARCHAR,                -- Fully resolved absolute path (if available)
    is_system BOOLEAN DEFAULT FALSE,      -- True for <...> includes, false for "..." includes
    line_number INTEGER,                  -- Line number where #include appears
    src_filename VARCHAR,                 -- Source filename (for easier querying)
    dst_filename VARCHAR,                 -- Destination filename (for easier querying)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_include_src ON edges_include(src);
CREATE INDEX IF NOT EXISTS idx_include_dst ON edges_include(dst);
CREATE INDEX IF NOT EXISTS idx_include_path ON edges_include(include_path);
CREATE INDEX IF NOT EXISTS idx_include_src_filename ON edges_include(src_filename);
CREATE INDEX IF NOT EXISTS idx_include_dst_filename ON edges_include(dst_filename);
CREATE INDEX IF NOT EXISTS idx_include_is_system ON edges_include(is_system);

-- Create composite index for file dependency queries
CREATE INDEX IF NOT EXISTS idx_include_dependency ON edges_include(src_filename, dst_filename);

-- Create a view for easier querying of file dependencies
CREATE OR REPLACE VIEW v_file_dependencies AS
SELECT DISTINCT
    ei.src_filename AS dependent_file,
    ei.dst_filename AS included_file,
    ei.include_path,
    ei.is_system,
    ei.line_number
FROM edges_include ei
WHERE ei.src_filename IS NOT NULL
  AND ei.dst_filename IS NOT NULL;

-- Create a view for counting include relationships
CREATE OR REPLACE VIEW v_include_counts AS
SELECT
    dst_filename AS included_file,
    COUNT(DISTINCT src_filename) AS includer_count,
    COUNT(*) AS total_includes
FROM edges_include
WHERE dst_filename IS NOT NULL
GROUP BY dst_filename
ORDER BY includer_count DESC;

-- Create a view for detecting circular includes (self-referencing patterns)
CREATE OR REPLACE VIEW v_circular_includes AS
SELECT DISTINCT
    e1.src_filename AS file1,
    e2.src_filename AS file2
FROM edges_include e1
JOIN edges_include e2 ON e1.src_filename = e2.dst_filename
                      AND e1.dst_filename = e2.src_filename
WHERE e1.src_filename < e1.dst_filename;  -- Avoid duplicates

-- Sample data comment (for documentation)
-- INSERT INTO edges_include (id, src, dst, include_path, is_system, line_number, src_filename, dst_filename)
-- VALUES (1, 100, 200, 'postgres.h', FALSE, 10, 'src/backend/executor.c', 'src/include/postgres.h');

COMMENT ON TABLE edges_include IS 'File-level include/import relationships extracted from #include directives';
COMMENT ON COLUMN edges_include.include_path IS 'The path as written in the source code (e.g., <stdio.h> or "postgres.h")';
COMMENT ON COLUMN edges_include.is_system IS 'TRUE for angle-bracket includes (<>), FALSE for quoted includes ("")';
