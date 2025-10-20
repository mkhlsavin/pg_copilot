"""
CFG Pattern Extractor for Phase 2

Extracts control flow patterns from Joern CPG:
1. Control structures (IF/WHILE/FOR) with conditions
2. Error handling patterns (NULL checks, elog calls)
3. Lock/unlock patterns
4. Transaction boundaries
5. CFG complexity metrics

Based on: PHASE2_CFG_PATTERN_DESIGN.md
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.execution.joern_client import JoernClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ControlStructurePattern:
    """Control structure pattern (IF/WHILE/FOR)."""
    pattern_type: str = "control_structure"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    control_type: str = ""  # IF, WHILE, FOR, etc.
    condition: str = ""
    description: str = ""


@dataclass
class ErrorHandlingPattern:
    """Error handling pattern (NULL checks, elog)."""
    pattern_type: str = "error_handling"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    check_type: str = ""  # NULL_CHECK, ELOG, etc.
    condition: str = ""
    description: str = ""


@dataclass
class LockPattern:
    """Lock acquisition/release pattern."""
    pattern_type: str = "lock_pattern"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    lock_function: str = ""
    lock_args: str = ""
    unlock_count: int = 0
    description: str = ""


@dataclass
class TransactionPattern:
    """Transaction boundary pattern."""
    pattern_type: str = "transaction"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    transaction_call: str = ""
    description: str = ""


@dataclass
class ComplexityMetric:
    """CFG complexity metrics for a method."""
    pattern_type: str = "complexity"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    cfg_nodes: int = 0
    call_count: int = 0
    control_structures: int = 0
    return_count: int = 0
    description: str = ""


class CFGPatternExtractor:
    """Extract control flow patterns from Joern CPG."""

    def __init__(self, joern_client: JoernClient):
        self.client = joern_client
        self.logger = logging.getLogger(__name__)

    def _parse_delimited_result(self, result: Dict, delimiter: str = "|||") -> List[List[str]]:
        """Parse Joern query result with delimiter."""
        if not result.get('success'):
            self.logger.warning(f"Query failed: {result.get('error')}")
            return []

        output = result.get('result', '')
        if not output:
            return []

        # Extract triple-quoted string content
        matches = re.findall(r'"""((?:[^"]|"")*?)"""', output, re.DOTALL)
        if not matches:
            # Try alternative format: List("item1", "item2", ...)
            matches = re.findall(r'"([^"]*)"', output)

        parsed_items = []
        for match in matches:
            # Split by delimiter
            parts = match.split(delimiter)
            if len(parts) > 1:  # Valid delimited result
                parsed_items.append(parts)

        return parsed_items

    def extract_control_structures(self, batch_size: int = 100, total_limit: int = 10000) -> List[ControlStructurePattern]:
        """Extract control structure patterns (IF/WHILE/FOR)."""
        self.logger.info(f"Extracting control structures (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .controlStructure
              .map {{ cs =>
                val method = cs.method.name.head
                val file = cs.file.name.headOption.getOrElse("UNKNOWN")
                val line = cs.lineNumber.getOrElse(-1)
                val csType = cs.controlStructureType
                val condition = cs.condition.code.headOption.getOrElse("NO_COND")
                s"${{method}}|||${{file}}|||${{line}}|||${{csType}}|||${{condition}}"
              }}
              .l
            """

            result = self.client.execute_query(query)
            parsed = self._parse_delimited_result(result)

            if not parsed:
                empty_batches += 1
                self.logger.info(f"  Batch {offset//batch_size + 1}: Empty (consecutive: {empty_batches})")
                offset += batch_size
                continue

            empty_batches = 0
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} control structures")

            for parts in parsed:
                if len(parts) >= 5:
                    method, file_path, line_str, control_type, condition = parts[:5]

                    # Generate description
                    desc = self._describe_control_structure(control_type, condition)

                    pattern = ControlStructurePattern(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(line_str.strip()) if line_str.strip().lstrip('-').isdigit() else -1,
                        control_type=control_type.strip(),
                        condition=condition.strip(),
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"✅ Extracted {len(patterns)} control structures")
        return patterns

    def extract_error_handling(self, batch_size: int = 100, total_limit: int = 5000) -> List[ErrorHandlingPattern]:
        """Extract error handling patterns (NULL checks, elog)."""
        self.logger.info(f"Extracting error handling patterns (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .controlStructure.controlStructureType("IF")
              .where(_.condition.code(".*== NULL.*|.*!= NULL.*|.*elog.*|.*ereport.*"))
              .map {{ ifStmt =>
                val method = ifStmt.method.name.head
                val file = ifStmt.file.name.headOption.getOrElse("UNKNOWN")
                val line = ifStmt.lineNumber.getOrElse(-1)
                val condition = ifStmt.condition.code.head
                s"${{method}}|||${{file}}|||${{line}}|||${{condition}}"
              }}
              .l
            """

            result = self.client.execute_query(query)
            parsed = self._parse_delimited_result(result)

            if not parsed:
                empty_batches += 1
                self.logger.info(f"  Batch {offset//batch_size + 1}: Empty (consecutive: {empty_batches})")
                offset += batch_size
                continue

            empty_batches = 0
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} error handling patterns")

            for parts in parsed:
                if len(parts) >= 4:
                    method, file_path, line_str, condition = parts[:4]

                    # Determine check type
                    check_type = self._classify_error_check(condition)

                    # Generate description
                    desc = self._describe_error_handling(check_type, condition)

                    pattern = ErrorHandlingPattern(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(line_str.strip()) if line_str.strip().lstrip('-').isdigit() else -1,
                        check_type=check_type,
                        condition=condition.strip(),
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"✅ Extracted {len(patterns)} error handling patterns")
        return patterns

    def extract_lock_patterns(self, batch_size: int = 100, total_limit: int = 3000) -> List[LockPattern]:
        """Extract lock/unlock patterns."""
        self.logger.info(f"Extracting lock patterns (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        lock_functions = "LockBuffer|UnlockBuffer|LWLockAcquire|LWLockRelease|LockRelationOid|UnlockRelationOid"

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.call.name("{lock_functions}").drop({offset}).take({batch_size})
              .map {{ lockCall =>
                val method = lockCall.method.name.head
                val file = lockCall.file.name.headOption.getOrElse("UNKNOWN")
                val line = lockCall.lineNumber.getOrElse(-1)
                val lockFunc = lockCall.name
                val args = lockCall.argument.code.l.mkString(", ")
                val unlockCount = lockCall.method.call.name("UnlockBuffer|LWLockRelease|UnlockRelationOid").size
                s"${{method}}|||${{file}}|||${{line}}|||${{lockFunc}}|||${{args}}|||${{unlockCount}}"
              }}
              .l
            """

            result = self.client.execute_query(query)
            parsed = self._parse_delimited_result(result)

            if not parsed:
                empty_batches += 1
                self.logger.info(f"  Batch {offset//batch_size + 1}: Empty (consecutive: {empty_batches})")
                offset += batch_size
                continue

            empty_batches = 0
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} lock patterns")

            for parts in parsed:
                if len(parts) >= 6:
                    method, file_path, line_str, lock_func, args, unlock_count_str = parts[:6]

                    # Generate description
                    desc = self._describe_lock_pattern(lock_func, args)

                    pattern = LockPattern(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(line_str.strip()) if line_str.strip().lstrip('-').isdigit() else -1,
                        lock_function=lock_func.strip(),
                        lock_args=args.strip(),
                        unlock_count=int(unlock_count_str.strip()) if unlock_count_str.strip().isdigit() else 0,
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"✅ Extracted {len(patterns)} lock patterns")
        return patterns

    def extract_transaction_boundaries(self, batch_size: int = 100, total_limit: int = 2000) -> List[TransactionPattern]:
        """Extract transaction start/commit/abort patterns."""
        self.logger.info(f"Extracting transaction boundaries (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        txn_functions = "StartTransactionCommand|CommitTransactionCommand|AbortTransaction.*"

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.call.name("{txn_functions}").drop({offset}).take({batch_size})
              .map {{ txnCall =>
                val method = txnCall.method.name.head
                val file = txnCall.file.name.headOption.getOrElse("UNKNOWN")
                val line = txnCall.lineNumber.getOrElse(-1)
                val txnFunc = txnCall.name
                s"${{method}}|||${{file}}|||${{line}}|||${{txnFunc}}"
              }}
              .l
            """

            result = self.client.execute_query(query)
            parsed = self._parse_delimited_result(result)

            if not parsed:
                empty_batches += 1
                self.logger.info(f"  Batch {offset//batch_size + 1}: Empty (consecutive: {empty_batches})")
                offset += batch_size
                continue

            empty_batches = 0
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} transaction patterns")

            for parts in parsed:
                if len(parts) >= 4:
                    method, file_path, line_str, txn_func = parts[:4]

                    # Generate description
                    desc = self._describe_transaction(txn_func)

                    pattern = TransactionPattern(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(line_str.strip()) if line_str.strip().lstrip('-').isdigit() else -1,
                        transaction_call=txn_func.strip(),
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"✅ Extracted {len(patterns)} transaction patterns")
        return patterns

    def extract_complexity_metrics(self, batch_size: int = 100, total_limit: int = 5000) -> List[ComplexityMetric]:
        """Extract CFG complexity metrics for methods."""
        self.logger.info(f"Extracting complexity metrics (batch_size={batch_size}, limit={total_limit})")
        metrics = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .map {{ m =>
                val name = m.name
                val file = m.file.name.headOption.getOrElse("UNKNOWN")
                val line = m.lineNumber.getOrElse(-1)
                val cfgNodes = m.cfgNode.size
                val calls = m.call.size
                val control = m.controlStructure.size
                val returns = m.methodReturn.size
                s"${{name}}|||${{file}}|||${{line}}|||${{cfgNodes}}|||${{calls}}|||${{control}}|||${{returns}}"
              }}
              .l
            """

            result = self.client.execute_query(query)
            parsed = self._parse_delimited_result(result)

            if not parsed:
                empty_batches += 1
                self.logger.info(f"  Batch {offset//batch_size + 1}: Empty (consecutive: {empty_batches})")
                offset += batch_size
                continue

            empty_batches = 0
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} complexity metrics")

            for parts in parsed:
                if len(parts) >= 7:
                    name, file_path, line_str, cfg_str, calls_str, control_str, returns_str = parts[:7]

                    cfg_nodes = int(cfg_str.strip()) if cfg_str.strip().isdigit() else 0
                    call_count = int(calls_str.strip()) if calls_str.strip().isdigit() else 0
                    control_count = int(control_str.strip()) if control_str.strip().isdigit() else 0
                    return_count = int(returns_str.strip()) if returns_str.strip().isdigit() else 0

                    # Generate description
                    desc = self._describe_complexity(name, cfg_nodes, call_count, control_count)

                    metric = ComplexityMetric(
                        method_name=name.strip(),
                        file_path=file_path.strip(),
                        line_number=int(line_str.strip()) if line_str.strip().lstrip('-').isdigit() else -1,
                        cfg_nodes=cfg_nodes,
                        call_count=call_count,
                        control_structures=control_count,
                        return_count=return_count,
                        description=desc
                    )
                    metrics.append(metric)

            offset += batch_size

        self.logger.info(f"✅ Extracted {len(metrics)} complexity metrics")
        return metrics

    # Description generators

    def _describe_control_structure(self, control_type: str, condition: str) -> str:
        """Generate natural language description of control structure."""
        condition_short = condition[:60] + "..." if len(condition) > 60 else condition

        if control_type == "IF":
            return f"IF statement checks condition: {condition_short}"
        elif control_type == "WHILE":
            return f"WHILE loop iterates while: {condition_short}"
        elif control_type == "FOR":
            return f"FOR loop iterates with condition: {condition_short}"
        elif control_type == "SWITCH":
            return f"SWITCH statement on: {condition_short}"
        else:
            return f"{control_type} control structure with condition: {condition_short}"

    def _classify_error_check(self, condition: str) -> str:
        """Classify error check type."""
        if "== NULL" in condition or "!= NULL" in condition:
            return "NULL_CHECK"
        elif "elog" in condition or "ereport" in condition:
            return "ERROR_LOG"
        else:
            return "VALIDATION"

    def _describe_error_handling(self, check_type: str, condition: str) -> str:
        """Generate natural language description of error handling."""
        condition_short = condition[:60] + "..." if len(condition) > 60 else condition

        if check_type == "NULL_CHECK":
            return f"NULL pointer validation: {condition_short}"
        elif check_type == "ERROR_LOG":
            return f"Error logging call: {condition_short}"
        else:
            return f"Input validation check: {condition_short}"

    def _describe_lock_pattern(self, lock_func: str, args: str) -> str:
        """Generate natural language description of lock pattern."""
        args_short = args[:40] + "..." if len(args) > 40 else args

        if "Lock" in lock_func and "Unlock" not in lock_func:
            return f"Acquires {lock_func} with arguments: {args_short}"
        elif "Unlock" in lock_func:
            return f"Releases {lock_func} with arguments: {args_short}"
        else:
            return f"{lock_func} call with arguments: {args_short}"

    def _describe_transaction(self, txn_func: str) -> str:
        """Generate natural language description of transaction boundary."""
        if "Start" in txn_func:
            return f"Begins transaction with {txn_func}"
        elif "Commit" in txn_func:
            return f"Commits transaction with {txn_func}"
        elif "Abort" in txn_func:
            return f"Aborts transaction with {txn_func}"
        else:
            return f"Transaction operation: {txn_func}"

    def _describe_complexity(self, method_name: str, cfg_nodes: int, calls: int, controls: int) -> str:
        """Generate natural language description of complexity."""
        complexity_level = "simple" if controls < 5 else "moderate" if controls < 20 else "complex"
        return f"Method {method_name} has {complexity_level} control flow with {cfg_nodes} CFG nodes, {calls} calls, and {controls} control structures"

    def extract_all_patterns(self, output_file: str, control_limit: int = 10000,
                            error_limit: int = 5000, lock_limit: int = 3000,
                            txn_limit: int = 2000, complexity_limit: int = 5000):
        """Extract all CFG patterns and save to file."""
        self.logger.info("="*80)
        self.logger.info("CFG PATTERN EXTRACTION")
        self.logger.info("="*80)

        all_patterns = {}

        # Extract each pattern type
        all_patterns['control_structures'] = [
            asdict(p) for p in self.extract_control_structures(total_limit=control_limit)
        ]

        all_patterns['error_handling'] = [
            asdict(p) for p in self.extract_error_handling(total_limit=error_limit)
        ]

        all_patterns['lock_patterns'] = [
            asdict(p) for p in self.extract_lock_patterns(total_limit=lock_limit)
        ]

        all_patterns['transaction_boundaries'] = [
            asdict(p) for p in self.extract_transaction_boundaries(total_limit=txn_limit)
        ]

        all_patterns['complexity_metrics'] = [
            asdict(p) for p in self.extract_complexity_metrics(total_limit=complexity_limit)
        ]

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(all_patterns, f, indent=2)

        self.logger.info("="*80)
        self.logger.info("EXTRACTION COMPLETE")
        self.logger.info(f"  Control structures: {len(all_patterns['control_structures'])}")
        self.logger.info(f"  Error handling: {len(all_patterns['error_handling'])}")
        self.logger.info(f"  Lock patterns: {len(all_patterns['lock_patterns'])}")
        self.logger.info(f"  Transaction boundaries: {len(all_patterns['transaction_boundaries'])}")
        self.logger.info(f"  Complexity metrics: {len(all_patterns['complexity_metrics'])}")
        self.logger.info(f"  Total patterns: {sum(len(v) for v in all_patterns.values())}")
        self.logger.info(f"  Output: {output_file}")
        self.logger.info("="*80)

        return all_patterns


def main():
    """Main entry point for CFG extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract CFG patterns from Joern CPG")
    parser.add_argument('--output', default='data/cfg_patterns.json', help='Output JSON file')
    parser.add_argument('--control-limit', type=int, default=10000, help='Max control structures')
    parser.add_argument('--error-limit', type=int, default=5000, help='Max error patterns')
    parser.add_argument('--lock-limit', type=int, default=3000, help='Max lock patterns')
    parser.add_argument('--txn-limit', type=int, default=2000, help='Max transaction patterns')
    parser.add_argument('--complexity-limit', type=int, default=5000, help='Max complexity metrics')
    parser.add_argument('--joern-endpoint', default='localhost:8080', help='Joern server endpoint')

    args = parser.parse_args()

    # Initialize Joern client
    client = JoernClient(args.joern_endpoint)

    try:
        # Connect to Joern
        logger.info("Connecting to Joern server...")
        client.connect()
        logger.info("✅ Connected to Joern")

        # Create extractor
        extractor = CFGPatternExtractor(client)

        # Extract all patterns
        extractor.extract_all_patterns(
            output_file=args.output,
            control_limit=args.control_limit,
            error_limit=args.error_limit,
            lock_limit=args.lock_limit,
            txn_limit=args.txn_limit,
            complexity_limit=args.complexity_limit
        )

        logger.info("✅ CFG pattern extraction complete!")

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
