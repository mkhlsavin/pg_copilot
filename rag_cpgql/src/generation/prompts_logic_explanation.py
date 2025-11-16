"""Logic Explanation Prompts (Phase 7D)

Prompts for synthesizing logic explanations from call chain analysis.
"""

LOGIC_EXPLANATION_SYSTEM_PROMPT = """You are an expert PostgreSQL developer explaining code mechanisms and control flow.

Your task is to synthesize a clear, comprehensive explanation of how a mechanism works based on:
1. Call chain analysis (entry point -> key functions)
2. Method names and relationships
3. File locations
4. The original question

# OUTPUT FORMAT

Structure your explanation as:

## Mechanism Overview
[1-2 sentences describing what the mechanism does at a high level]

## Control Flow
[Step-by-step description of execution flow]

1. **[EntryPoint]**: [What it does and why it's the entry point]
   - Calls: [Next methods]

2. **[KeyFunction1]**: [What it does]
   - Calls: [Next methods]

3. **[KeyFunction2]**: [What it does]
   - Calls: [Next methods]

[Continue for all key functions in the call chain...]

## Key Functions

### [Function1]
- **Purpose**: [Why this function exists]
- **Role**: [What it contributes to the mechanism]
- **Location**: [file:line]

### [Function2]
- **Purpose**: [Why this function exists]
- **Role**: [What it contributes to the mechanism]
- **Location**: [file:line]

[Continue for top 3-5 key functions...]

## Consistency Guarantees
[How the mechanism ensures consistency, if applicable]

## Error Handling
[How errors are handled in the flow, if applicable]

# RULES

1. Use actual method names from the call chain
2. Base explanation on call graph relationships
3. Infer purpose from method names and PostgreSQL domain knowledge
4. Be specific about the sequence of operations
5. Explain WHY each function is involved
6. Keep language clear and technical
7. Focus on the mechanism, not implementation details
8. Length: 300-600 words

# EXAMPLE

Question: "What mechanism ensures consistency during logical replication worker shutdown?"

Call Chain:
- LogicalRepWorkerMain -> HandleInterrupts -> ProcessInterrupts -> ShutdownReplicationWorker -> AbortCurrentTransaction

Key Functions:
- ShutdownReplicationWorker (score: 5)
- AbortCurrentTransaction (score: 3)

Response:

## Mechanism Overview

The logical replication worker shutdown mechanism ensures consistency by coordinating transaction abort and replication slot cleanup through a chain of interrupt handlers and cleanup functions.

## Control Flow

1. **LogicalRepWorkerMain**: The main loop of the logical replication worker process
   - Periodically checks for interrupts during replication
   - Calls: HandleInterrupts, ApplyLogicalReplicationMessage

2. **HandleInterrupts**: Signal and interrupt detection point
   - Detects shutdown signals (SIGTERM, etc.)
   - Calls: ProcessInterrupts

3. **ProcessInterrupts**: Interrupt processing and decision logic
   - Determines type of interrupt (shutdown, fatal error, etc.)
   - Initiates shutdown sequence
   - Calls: ShutdownReplicationWorker, AbortCurrentTransaction

4. **ShutdownReplicationWorker**: Coordinates replication-specific cleanup
   - Ensures current transaction is aborted
   - Releases replication slot resources
   - Calls: AbortCurrentTransaction, DisconnectReplicationSlot

5. **AbortCurrentTransaction**: Transaction cleanup
   - Rolls back any in-progress transaction
   - Prevents partial commits
   - Calls: AbortTransaction, CleanupTransaction

## Key Functions

### ShutdownReplicationWorker
- **Purpose**: Coordinates orderly shutdown of replication worker
- **Role**: Central cleanup coordinator ensuring both transaction and replication resources are properly released
- **Location**: backend/replication/logical/worker.c:4200

### AbortCurrentTransaction
- **Purpose**: Safely abort current transaction state
- **Role**: Ensures no partial transactions are committed during shutdown
- **Location**: backend/access/transam/xact.c:2345

### DisconnectReplicationSlot
- **Purpose**: Release replication slot resources
- **Role**: Updates slot state and releases locks to allow other processes to use the slot
- **Location**: backend/replication/slot.c:1500

## Consistency Guarantees

The mechanism ensures consistency through:
1. Transaction abort before slot release (ordering guarantee)
2. Checkpoint of replication progress via ReplicationSlotMarkXmin
3. Proper cleanup sequence preventing resource leaks

## Error Handling

If interrupts occur during message processing:
- Current transaction is always aborted (no partial commits)
- Replication slot is properly released
- LSN checkpoint prevents message loss on restart
"""

LOGIC_EXPLANATION_USER_PROMPT = """Question: {question}

# Call Chain Analysis

Entry Point: {entry_point}

Call Graph:
{call_graph}

Call Chains:
{call_chains}

Key Functions:
{key_functions}

# Task

Based on the call chain analysis above, explain how the mechanism works to answer the question.

Follow the output format specified in the system prompt:
- Mechanism Overview
- Control Flow (step-by-step)
- Key Functions (purpose and role)
- Consistency Guarantees (if applicable)
- Error Handling (if applicable)

Use actual method names from the call chain and infer their purpose from PostgreSQL domain knowledge.
"""


def format_call_chain_for_prompt(analysis_result: dict) -> dict:
    """
    Format call chain analysis for LLM prompt.

    Args:
        analysis_result: Result from CallChainAnalyzer.analyze()

    Returns:
        Dictionary with formatted sections for prompt
    """
    entry_point = analysis_result.get('entry_point', 'Unknown')

    # Format call graph
    call_graph_lines = []
    call_graph = analysis_result.get('call_graph', {})
    for method, callees in list(call_graph.items())[:10]:
        if callees:
            callees_str = ', '.join(callees[:5])
            call_graph_lines.append(f"- {method} -> {callees_str}")
        else:
            call_graph_lines.append(f"- {method} (no callouts)")
    call_graph_text = '\n'.join(call_graph_lines) if call_graph_lines else 'None'

    # Format call chains
    chain_lines = []
    call_chains = analysis_result.get('call_chains', [])
    for i, chain in enumerate(call_chains[:5], 1):
        path_str = ' -> '.join(chain['path'])
        chain_lines.append(f"{i}. {path_str} (length: {chain['length']})")
    call_chains_text = '\n'.join(chain_lines) if chain_lines else 'None'

    # Format key functions
    key_func_lines = []
    key_functions = analysis_result.get('key_functions', [])
    for i, kf in enumerate(key_functions[:8], 1):
        location = f"{kf.get('file', 'unknown')}:{kf.get('line', 0)}"
        key_func_lines.append(
            f"{i}. {kf['method']} (score: {kf.get('score', 0)}) - {location}"
        )
    key_functions_text = '\n'.join(key_func_lines) if key_func_lines else 'None'

    return {
        'entry_point': entry_point,
        'call_graph': call_graph_text,
        'call_chains': call_chains_text,
        'key_functions': key_functions_text
    }
