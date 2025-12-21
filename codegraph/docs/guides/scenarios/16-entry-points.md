# Scenario 16: Entry Point Discovery

> Security engineer mapping attack surface and API boundaries.

## Quick Start

```bash
# Select Entry Points Scenario
/select 16
```

## Attack Surface Mapping

### Network Entry Points

```
> Find all network-accessible entry points

╭─────────────── Network Entry Points ────────────────────────╮
│                                                              │
│  Network-Accessible Entry Points:                            │
│                                                              │
│  Protocol Layer:                                             │
│    ProcessStartupPacket()   - Connection handshake           │
│    ProcessClientRead()      - Main data receive              │
│    pq_getmsgstring()        - Read string from client        │
│    pq_getmsgint()           - Read integer from client       │
│                                                              │
│  Query Processing:                                           │
│    exec_simple_query()      - Direct SQL execution           │
│    exec_parse_message()     - Prepared statement             │
│    exec_bind_message()      - Parameter binding              │
│    exec_execute_message()   - Execute prepared               │
│                                                              │
│  Replication:                                                │
│    WalSndWaitForWal()       - WAL streaming                  │
│    ProcessWalRcvInterrupts() - WAL receiver                  │
│                                                              │
│  Total network entry points: 23                              │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### File System Entry Points

```
> Find file system entry points

╭─────────────── File System Entry Points ────────────────────╮
│                                                              │
│  File System Access Points:                                  │
│                                                              │
│  SQL-Callable Functions:                                     │
│    pg_read_file()           - Read arbitrary file            │
│    pg_read_binary_file()    - Read binary file               │
│    pg_ls_dir()              - List directory                 │
│    pg_stat_file()           - Get file stats                 │
│                                                              │
│  COPY Command:                                               │
│    DoCopy() → CopyFrom()    - Read from file                 │
│    DoCopy() → CopyTo()      - Write to file                  │
│                                                              │
│  Extension Loading:                                          │
│    load_external_function() - Load shared library            │
│    pg_dlopen()              - Dynamic library loading        │
│                                                              │
│  Risk Level: HIGH                                            │
│  Requires: Superuser privilege for most                      │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## API Boundary Analysis

### Public API Functions

```
> List all public API entry points

╭─────────────── Public API ──────────────────────────────────╮
│                                                              │
│  PostgreSQL Extension API:                                   │
│                                                              │
│  PG_FUNCTION_INFO_V1 Exported Functions: 1,234               │
│                                                              │
│  Categories:                                                 │
│    Data types:        234 functions                          │
│    Operators:         189 functions                          │
│    Aggregate:         67 functions                           │
│    Window:            23 functions                           │
│    Procedural:        45 functions                           │
│                                                              │
│  SPI Interface (Internal Extension API):                     │
│    SPI_connect()      - Connect to SPI                       │
│    SPI_execute()      - Execute SQL                          │
│    SPI_prepare()      - Prepare statement                    │
│    SPI_finish()       - Disconnect from SPI                  │
│                                                              │
│  Hook Points:                                                │
│    ProcessUtility_hook    - Utility command processing       │
│    ExecutorRun_hook       - Query execution                  │
│    planner_hook           - Query planning                   │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Internal API Boundaries

```
> Show internal module boundaries

╭─────────────── Module Boundaries ───────────────────────────╮
│                                                              │
│  Internal API Boundaries:                                    │
│                                                              │
│  Executor → Storage:                                         │
│    heap_insert()          - Insert tuple                     │
│    heap_update()          - Update tuple                     │
│    heap_delete()          - Delete tuple                     │
│    index_insert()         - Index maintenance                │
│                                                              │
│  Parser → Catalog:                                           │
│    SearchSysCache()       - Cache lookup                     │
│    ScanPgRelation()       - Relation scan                    │
│    GetRelationIds()       - OID resolution                   │
│                                                              │
│  Planner → Statistics:                                       │
│    get_relation_stats()   - Table statistics                 │
│    estimate_num_groups()  - Cardinality estimation           │
│                                                              │
│  Total internal APIs: 456 functions                          │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Trust Boundary Analysis

### Privilege Escalation Paths

```
> Find functions that change privilege level

╭─────────────── Privilege Transitions ───────────────────────╮
│                                                              │
│  Privilege Escalation Points:                                │
│                                                              │
│  SECURITY DEFINER Functions:                                 │
│    Total: 23 functions                                       │
│    Risk: Execute with owner privileges                       │
│                                                              │
│  Superuser-Only Functions Called by Non-Superusers:          │
│    pg_reload_conf()       via reload_conf wrapper            │
│    pg_terminate_backend() via admin wrapper                  │
│                                                              │
│  SET ROLE Transitions:                                       │
│    SetRole()              - Role switching                   │
│    check_role_grantor()   - Permission check                 │
│                                                              │
│  Row-Level Security Bypass:                                  │
│    check_enable_rls()     - RLS check point                  │
│    ExecCheckRTPerms()     - Permission validation            │
│                                                              │
│  Audit Points: 45 locations                                  │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

### Untrusted Input Handlers

```
> Find functions that handle untrusted input

╭─────────────── Untrusted Input Handlers ────────────────────╮
│                                                              │
│  Direct Client Input Handling:                               │
│                                                              │
│  String Input:                                               │
│    pq_getmsgstring()      - Raw string from client           │
│    pq_getmsgtext()        - Text with encoding               │
│    pg_client_to_server()  - Encoding conversion              │
│                                                              │
│  Binary Input:                                               │
│    pq_getmsgbyte()        - Single byte                      │
│    pq_getmsgint()         - Integer (various sizes)          │
│    pq_getmsgbytes()       - Raw bytes                        │
│                                                              │
│  SQL Input:                                                  │
│    pg_parse_query()       - SQL parsing                      │
│    eval_const_expressions() - Expression evaluation          │
│                                                              │
│  Validation Points:                                          │
│    check_object_ownership() - ACL check                      │
│    has_table_privilege()    - Table access                   │
│    pg_aclcheck()            - General ACL                    │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Example Questions

- "Find all network entry points"
- "List file system access functions"
- "Show public API functions"
- "Find privilege escalation paths"
- "Identify untrusted input handlers"
- "Map trust boundaries"

## CLI Commands

```bash
# Entry point analysis
python -m src.cli.security entry-points --type network
python -m src.cli.security entry-points --type file
python -m src.cli.security entry-points --type api
python -m src.cli.security trust-boundaries
```

## Related Scenarios

- [Security Audit](./02-security-audit.md) - Vulnerability analysis
- [Incident Response](./14-incident-response.md) - Attack investigation
- [Architecture](./11-architecture.md) - System boundaries
