"""PostgreSQL Default Subsystem Definitions.

Fallback subsystem definitions when YAML configuration is not available.
"""
from ..base import SubsystemInfo


def get_default_subsystems() -> dict:
    """
    Get fallback subsystem definitions if YAML not available.

    Returns:
        Dictionary mapping subsystem name to SubsystemInfo
    """
    return {
        "executor": SubsystemInfo(
            name="executor",
            description="Query execution engine - executes query plans",
            key_functions=["ExecProcNode", "ExecInitNode", "ExecEndNode"],
            patterns=["backend/executor", "execMain", "execProc"],
        ),
        "parser": SubsystemInfo(
            name="parser",
            description="SQL parser and analyzer - converts SQL to parse tree",
            key_functions=["raw_parser", "pg_parse_query", "transformStmt"],
            patterns=["backend/parser", "gram.y", "scan.l"],
        ),
        "optimizer": SubsystemInfo(
            name="optimizer",
            description="Query optimizer/planner - generates query plans",
            key_functions=["standard_planner", "subquery_planner", "query_planner"],
            patterns=["backend/optimizer", "planner", "path", "cost"],
        ),
        "storage": SubsystemInfo(
            name="storage",
            description="Storage manager - handles file and buffer I/O",
            key_functions=["BufferAlloc", "ReadBuffer", "WriteBuffer"],
            patterns=["backend/storage", "smgr", "bufmgr"],
        ),
        "access": SubsystemInfo(
            name="access",
            description="Access methods - heap tables and index implementations",
            key_functions=["heap_insert", "heap_fetch", "index_insert"],
            patterns=["backend/access", "heap", "index", "nbtree"],
        ),
        "catalog": SubsystemInfo(
            name="catalog",
            description="System catalogs - metadata about database objects",
            key_functions=["SearchSysCache", "heap_open", "relation_open"],
            patterns=["backend/catalog", "pg_class", "syscache"],
        ),
        "commands": SubsystemInfo(
            name="commands",
            description="SQL commands - DDL and utility command implementations",
            key_functions=["ProcessUtility", "DefineRelation", "AlterTable"],
            patterns=["backend/commands", "tablecmds", "vacuum"],
        ),
        "utils": SubsystemInfo(
            name="utils",
            description="Utilities - memory management, error handling",
            key_functions=["palloc", "pfree", "elog", "ereport"],
            patterns=["backend/utils", "memutils", "palloc"],
        ),
        "replication": SubsystemInfo(
            name="replication",
            description="Replication - WAL shipping and logical replication",
            key_functions=["WalSndLoop", "WalReceiverMain"],
            patterns=["backend/replication", "walsender", "walreceiver"],
        ),
        "transactions": SubsystemInfo(
            name="transactions",
            description="Transaction management - ACID properties and WAL",
            key_functions=["StartTransaction", "CommitTransaction", "XLogInsert"],
            patterns=["backend/access/transam", "xact", "xlog"],
        ),
    }
