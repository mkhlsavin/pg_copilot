-- Delta CPG Schema for Patch Review System
--
-- This schema extends the base CPG schema to support delta/virtual graphs
-- for patch-based code review. It enables tracking changes between patch
-- states without modifying the base CPG.
--
-- Phase: Core Infrastructure (Phase 1)

-- =============================================================================
-- REVIEW SESSION MANAGEMENT
-- =============================================================================

-- Review sessions track the lifecycle of a patch review
CREATE TABLE IF NOT EXISTS review_sessions (
    session_id VARCHAR PRIMARY KEY,
    patch_id VARCHAR NOT NULL,
    base_commit VARCHAR NOT NULL,
    head_commit VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending, analyzing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    persist_delta BOOLEAN DEFAULT FALSE,        -- Whether to keep delta after review
    verdict JSON,                               -- Final review verdict (JSON)
    metadata JSON                               -- Additional metadata (JSON)
);

-- Index for finding sessions by patch
CREATE INDEX IF NOT EXISTS idx_review_sessions_patch ON review_sessions(patch_id);

-- Index for finding incomplete sessions
CREATE INDEX IF NOT EXISTS idx_review_sessions_status ON review_sessions(status);

-- =============================================================================
-- DELTA NODES
-- =============================================================================

-- Delta nodes represent changed CPG nodes (added, modified, deleted)
CREATE TABLE IF NOT EXISTS delta_nodes (
    id BIGINT NOT NULL,
    session_id VARCHAR NOT NULL,
    node_type VARCHAR NOT NULL,                 -- METHOD, CALL, IDENTIFIER, etc.
    change_type VARCHAR NOT NULL,               -- added, modified, deleted
    original_node_id BIGINT,                    -- Reference to base CPG node (NULL if added)

    -- Core properties
    name VARCHAR,
    full_name VARCHAR,
    filename VARCHAR,
    line_number INTEGER,
    line_number_end INTEGER,
    code TEXT,

    -- For modified nodes: store changes
    old_values JSON,                            -- Original property values
    new_values JSON,                            -- New property values

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (session_id, id)
);

-- Index for finding delta nodes by session
CREATE INDEX IF NOT EXISTS idx_delta_nodes_session ON delta_nodes(session_id);

-- Index for finding delta nodes by original node
CREATE INDEX IF NOT EXISTS idx_delta_nodes_original ON delta_nodes(original_node_id);

-- Index for finding delta nodes by type
CREATE INDEX IF NOT EXISTS idx_delta_nodes_type ON delta_nodes(session_id, node_type);

-- Index for finding delta nodes by change type
CREATE INDEX IF NOT EXISTS idx_delta_nodes_change ON delta_nodes(session_id, change_type);

-- Index for finding delta nodes by file
CREATE INDEX IF NOT EXISTS idx_delta_nodes_file ON delta_nodes(session_id, filename);

-- =============================================================================
-- DELTA EDGES
-- =============================================================================

-- Delta edges represent changed relationships between nodes
CREATE TABLE IF NOT EXISTS delta_edges (
    id BIGINT NOT NULL,
    session_id VARCHAR NOT NULL,
    edge_type VARCHAR NOT NULL,                 -- AST, CFG, CALL, REACHING_DEF, etc.
    src BIGINT NOT NULL,                        -- Source node ID
    dst BIGINT NOT NULL,                        -- Destination node ID
    change_type VARCHAR NOT NULL,               -- added, deleted
    src_is_delta BOOLEAN DEFAULT FALSE,         -- True if src is a delta node
    dst_is_delta BOOLEAN DEFAULT FALSE,         -- True if dst is a delta node
    properties JSON,                            -- Edge properties (e.g., variable for REACHING_DEF)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (session_id, id)
);

-- Index for finding delta edges by session
CREATE INDEX IF NOT EXISTS idx_delta_edges_session ON delta_edges(session_id);

-- Index for finding delta edges by source
CREATE INDEX IF NOT EXISTS idx_delta_edges_src ON delta_edges(session_id, src);

-- Index for finding delta edges by destination
CREATE INDEX IF NOT EXISTS idx_delta_edges_dst ON delta_edges(session_id, dst);

-- Index for finding delta edges by type
CREATE INDEX IF NOT EXISTS idx_delta_edges_type ON delta_edges(session_id, edge_type);

-- =============================================================================
-- CHANGED METHODS TRACKING
-- =============================================================================

-- Track methods that were added, modified, or deleted
CREATE TABLE IF NOT EXISTS delta_changed_methods (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    method_name VARCHAR NOT NULL,
    full_name VARCHAR,
    filepath VARCHAR,
    change_type VARCHAR NOT NULL,               -- added, modified, deleted
    line_start INTEGER,
    line_end INTEGER,
    base_method_id BIGINT,                      -- ID in base CPG (NULL if added)
    delta_node_id BIGINT,                       -- ID in delta_nodes
    old_signature VARCHAR,
    new_signature VARCHAR,
    complexity_before INTEGER,
    complexity_after INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id)
);

-- Index for finding changed methods by session
CREATE INDEX IF NOT EXISTS idx_delta_methods_session ON delta_changed_methods(session_id);

-- Index for finding changed methods by file
CREATE INDEX IF NOT EXISTS idx_delta_methods_file ON delta_changed_methods(session_id, filepath);

-- =============================================================================
-- REVIEW FINDINGS
-- =============================================================================

-- Store findings from the review for persistence and trend analysis
CREATE TABLE IF NOT EXISTS review_findings (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    category VARCHAR NOT NULL,                  -- security, performance, error, architecture
    severity VARCHAR NOT NULL,                  -- critical, high, medium, low, info
    title VARCHAR NOT NULL,
    description TEXT,
    location VARCHAR,                           -- file:line format
    code_snippet TEXT,
    recommendation TEXT,
    confidence FLOAT,
    pattern_id VARCHAR,                         -- Pattern that detected this
    cwe_id VARCHAR,                             -- For security findings
    is_new BOOLEAN DEFAULT TRUE,                -- Introduced by this patch
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id)
);

-- Index for finding findings by session
CREATE INDEX IF NOT EXISTS idx_findings_session ON review_findings(session_id);

-- Index for finding findings by severity
CREATE INDEX IF NOT EXISTS idx_findings_severity ON review_findings(session_id, severity);

-- Index for finding findings by category
CREATE INDEX IF NOT EXISTS idx_findings_category ON review_findings(session_id, category);

-- =============================================================================
-- HISTORICAL TRACKING (for persisted reviews)
-- =============================================================================

-- Track review history for trend analysis
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY,
    patch_id VARCHAR NOT NULL,
    session_id VARCHAR NOT NULL,
    overall_score FLOAT,
    security_score FLOAT,
    performance_score FLOAT,
    error_score FLOAT,
    architecture_score FLOAT,
    recommendation VARCHAR,
    critical_count INTEGER,
    high_count INTEGER,
    medium_count INTEGER,
    low_count INTEGER,
    blast_radius_score FLOAT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id)
);

-- Index for finding history by patch
CREATE INDEX IF NOT EXISTS idx_history_patch ON review_history(patch_id);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_history_time ON review_history(reviewed_at);

-- =============================================================================
-- CLEANUP FUNCTIONS
-- =============================================================================

-- View to find sessions that should be cleaned up (old, completed, not persisted)
CREATE VIEW IF NOT EXISTS cleanup_candidates AS
SELECT
    session_id,
    patch_id,
    status,
    created_at,
    completed_at
FROM review_sessions
WHERE persist_delta = FALSE
  AND status IN ('completed', 'failed')
  AND completed_at < CURRENT_TIMESTAMP - INTERVAL 24 HOURS;

-- =============================================================================
-- UTILITY VIEWS
-- =============================================================================

-- View combining delta nodes with their session info
CREATE VIEW IF NOT EXISTS delta_nodes_with_session AS
SELECT
    dn.*,
    rs.patch_id,
    rs.base_commit,
    rs.head_commit,
    rs.status as session_status
FROM delta_nodes dn
JOIN review_sessions rs ON dn.session_id = rs.session_id;

-- View for active review sessions (not completed)
CREATE VIEW IF NOT EXISTS active_review_sessions AS
SELECT * FROM review_sessions
WHERE status NOT IN ('completed', 'failed');

-- View for session statistics
CREATE VIEW IF NOT EXISTS session_statistics AS
SELECT
    rs.session_id,
    rs.patch_id,
    rs.status,
    COUNT(DISTINCT dn.id) as delta_nodes_count,
    COUNT(DISTINCT de.id) as delta_edges_count,
    COUNT(DISTINCT dcm.id) as changed_methods_count,
    COUNT(DISTINCT rf.id) as findings_count,
    rs.created_at,
    rs.completed_at
FROM review_sessions rs
LEFT JOIN delta_nodes dn ON rs.session_id = dn.session_id
LEFT JOIN delta_edges de ON rs.session_id = de.session_id
LEFT JOIN delta_changed_methods dcm ON rs.session_id = dcm.session_id
LEFT JOIN review_findings rf ON rs.session_id = rf.session_id
GROUP BY rs.session_id, rs.patch_id, rs.status, rs.created_at, rs.completed_at;
