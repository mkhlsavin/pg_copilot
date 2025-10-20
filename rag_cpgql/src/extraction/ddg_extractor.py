"""
DDG Pattern Extractor for Phase 3

Extracts data dependency patterns from Joern CPG:
1. Parameter data flow (param -> identifiers, calls, returns)
2. Local variable dependencies (assignment chains)
3. Return value sources (what flows to returns)
4. Call argument sources (what reaches function arguments)
5. Control dependencies (CDG edges)

Based on: PHASE3_DDG_API_FINDINGS.md
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
class ParameterFlowPattern:
    """Parameter data flow pattern."""
    pattern_type: str = "parameter_flow"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    parameter_name: str = ""
    parameter_type: str = ""
    flows_to_type: str = ""  # IDENTIFIER, CALL, RETURN, METHOD_RETURN
    flows_to_line: int = -1
    flows_to_code: str = ""
    description: str = ""


@dataclass
class LocalVariableChain:
    """Local variable assignment/reassignment chain."""
    pattern_type: str = "variable_chain"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    source_var: str = ""
    source_line: int = -1
    target_var: str = ""
    target_line: int = -1
    chain_type: str = ""  # REASSIGNMENT, PARAM_TO_VAR, CALL_TO_VAR
    description: str = ""


@dataclass
class ReturnValueSource:
    """Data source for return statement."""
    pattern_type: str = "return_source"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    return_code: str = ""
    return_line: int = -1
    source_type: str = ""  # IDENTIFIER, CALL, PARAMETER, etc.
    source_code: str = ""
    description: str = ""


@dataclass
class CallArgumentSource:
    """Data source for call argument."""
    pattern_type: str = "call_argument_source"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    call_name: str = ""
    argument_index: int = -1
    argument_code: str = ""
    source_type: str = ""
    description: str = ""


@dataclass
class ControlDependency:
    """Control dependency (CDG) pattern."""
    pattern_type: str = "control_dependency"
    method_name: str = ""
    file_path: str = ""
    line_number: int = -1
    control_type: str = ""  # IF, WHILE, FOR, etc.
    control_code: str = ""
    dependent_type: str = ""
    dependent_count: int = 0
    description: str = ""


class DDGPatternExtractor:
    """Extract data dependency patterns from Joern CPG."""

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

    def extract_parameter_flows(self, batch_size: int = 100, total_limit: int = 20000) -> List[ParameterFlowPattern]:
        """Extract parameter data flow patterns."""
        self.logger.info(f"Extracting parameter flows (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .flatMap {{ m =>
                val methodName = m.name
                val filePath = m.file.name.headOption.getOrElse("UNKNOWN")
                val methodLine = m.lineNumber.getOrElse(-1)

                m.parameter.flatMap {{ param =>
                  param._reachingDefOut.map {{ target =>
                    val paramName = param.name
                    val paramType = param.typeFullName
                    val targetType = target.label
                    val targetLine = target.property("LINE_NUMBER").toString.toIntOption.getOrElse(-1)
                    val targetCode = target.property("CODE").toString
                    s"${{methodName}}|||${{filePath}}|||${{methodLine}}|||${{paramName}}|||${{paramType}}|||${{targetType}}|||${{targetLine}}|||${{targetCode}}"
                  }}.take(10)
                }}
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
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} parameter flows")

            for parts in parsed:
                if len(parts) >= 8:
                    method, file_path, method_line_str, param_name, param_type, \
                        target_type, target_line_str, target_code = parts[:8]

                    desc = self._describe_parameter_flow(
                        param_name, param_type, target_type, target_code
                    )

                    pattern = ParameterFlowPattern(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(method_line_str.strip()) if method_line_str.strip().lstrip('-').isdigit() else -1,
                        parameter_name=param_name.strip(),
                        parameter_type=param_type.strip(),
                        flows_to_type=target_type.strip(),
                        flows_to_line=int(target_line_str.strip()) if target_line_str.strip().lstrip('-').isdigit() else -1,
                        flows_to_code=target_code.strip()[:100],  # Limit code length
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"[OK] Extracted {len(patterns)} parameter flows")
        return patterns

    def extract_variable_chains(self, batch_size: int = 100, total_limit: int = 15000) -> List[LocalVariableChain]:
        """Extract local variable assignment chains."""
        self.logger.info(f"Extracting variable chains (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .flatMap {{ m =>
                val methodName = m.name
                val filePath = m.file.name.headOption.getOrElse("UNKNOWN")
                val methodLine = m.lineNumber.getOrElse(-1)

                m.ast.isIdentifier.flatMap {{ ident =>
                  ident._reachingDefOut.collect {{
                    case targetIdent: io.shiftleft.codepropertygraph.generated.nodes.Identifier =>
                      val sourceVar = ident.code
                      val sourceLine = ident.lineNumber.map(_.toString).getOrElse("unknown")
                      val targetVar = targetIdent.code
                      val targetLine = targetIdent.lineNumber.map(_.toString).getOrElse("unknown")
                      s"${{methodName}}|||${{filePath}}|||${{methodLine}}|||${{sourceVar}}|||${{sourceLine}}|||${{targetVar}}|||${{targetLine}}|||REASSIGNMENT"
                  }}.take(5)
                }}
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
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} variable chains")

            for parts in parsed:
                if len(parts) >= 8:
                    method, file_path, method_line_str, source_var, source_line_str, \
                        target_var, target_line_str, chain_type = parts[:8]

                    desc = self._describe_variable_chain(
                        source_var, source_line_str, target_var, target_line_str, chain_type
                    )

                    pattern = LocalVariableChain(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(method_line_str.strip()) if method_line_str.strip().lstrip('-').isdigit() else -1,
                        source_var=source_var.strip(),
                        source_line=int(source_line_str.strip()) if source_line_str.strip().lstrip('-').isdigit() else -1,
                        target_var=target_var.strip(),
                        target_line=int(target_line_str.strip()) if target_line_str.strip().lstrip('-').isdigit() else -1,
                        chain_type=chain_type.strip(),
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"[OK] Extracted {len(patterns)} variable chains")
        return patterns

    def extract_return_sources(self, batch_size: int = 100, total_limit: int = 10000) -> List[ReturnValueSource]:
        """Extract return value data sources."""
        self.logger.info(f"Extracting return sources (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .flatMap {{ m =>
                val methodName = m.name
                val filePath = m.file.name.headOption.getOrElse("UNKNOWN")
                val methodLine = m.lineNumber.getOrElse(-1)

                m.ast.isReturn.flatMap {{ ret =>
                  val retCode = ret.code
                  val retLine = ret.lineNumber.map(_.toString).getOrElse("unknown")

                  ret._reachingDefIn.take(3).map {{ source =>
                    val sourceType = source.label
                    val sourceCode = source.property("CODE").toString
                    s"${{methodName}}|||${{filePath}}|||${{methodLine}}|||${{retCode}}|||${{retLine}}|||${{sourceType}}|||${{sourceCode}}"
                  }}
                }}
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
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} return sources")

            for parts in parsed:
                if len(parts) >= 7:
                    method, file_path, method_line_str, ret_code, ret_line_str, \
                        source_type, source_code = parts[:7]

                    desc = self._describe_return_source(ret_code, source_type, source_code)

                    pattern = ReturnValueSource(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(method_line_str.strip()) if method_line_str.strip().lstrip('-').isdigit() else -1,
                        return_code=ret_code.strip()[:80],
                        return_line=int(ret_line_str.strip()) if ret_line_str.strip().lstrip('-').isdigit() else -1,
                        source_type=source_type.strip(),
                        source_code=source_code.strip()[:100],
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"[OK] Extracted {len(patterns)} return sources")
        return patterns

    def extract_call_argument_sources(self, batch_size: int = 50, total_limit: int = 10000) -> List[CallArgumentSource]:
        """Extract call argument data sources."""
        self.logger.info(f"Extracting call argument sources (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.call.name(".*").drop({offset}).take({batch_size})
              .flatMap {{ call =>
                val callName = call.name
                val methodName = call.method.name.head
                val filePath = call.file.name.headOption.getOrElse("UNKNOWN")
                val callLine = call.lineNumber.getOrElse(-1)

                call.argument.take(5).flatMap {{ arg =>
                  val argIndex = arg.argumentIndex
                  val argCode = arg.code

                  arg._reachingDefIn.take(2).map {{ source =>
                    val sourceType = source.label
                    s"${{methodName}}|||${{filePath}}|||${{callLine}}|||${{callName}}|||${{argIndex}}|||${{argCode}}|||${{sourceType}}"
                  }}
                }}
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
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} call argument sources")

            for parts in parsed:
                if len(parts) >= 7:
                    method, file_path, call_line_str, call_name, arg_index_str, \
                        arg_code, source_type = parts[:7]

                    desc = self._describe_call_argument_source(
                        call_name, arg_index_str, arg_code, source_type
                    )

                    pattern = CallArgumentSource(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(call_line_str.strip()) if call_line_str.strip().lstrip('-').isdigit() else -1,
                        call_name=call_name.strip(),
                        argument_index=int(arg_index_str.strip()) if arg_index_str.strip().lstrip('-').isdigit() else -1,
                        argument_code=arg_code.strip()[:60],
                        source_type=source_type.strip(),
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"[OK] Extracted {len(patterns)} call argument sources")
        return patterns

    def extract_control_dependencies(self, batch_size: int = 100, total_limit: int = 15000) -> List[ControlDependency]:
        """Extract control dependency (CDG) patterns."""
        self.logger.info(f"Extracting control dependencies (batch_size={batch_size}, limit={total_limit})")
        patterns = []
        offset = 0
        empty_batches = 0

        while offset < total_limit and empty_batches < 3:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .flatMap {{ m =>
                val methodName = m.name
                val filePath = m.file.name.headOption.getOrElse("UNKNOWN")
                val methodLine = m.lineNumber.getOrElse(-1)

                m.ast.isControlStructure.map {{ ctrl =>
                  val ctrlType = ctrl.controlStructureType
                  val ctrlCode = ctrl.code
                  val ctrlLine = ctrl.lineNumber.map(_.toString).getOrElse("unknown")
                  val dependentCount = ctrl._cdgOut.size
                  val dependentType = ctrl._cdgOut.headOption.map(_.label).getOrElse("NONE")
                  s"${{methodName}}|||${{filePath}}|||${{methodLine}}|||${{ctrlType}}|||${{ctrlCode}}|||${{dependentCount}}|||${{dependentType}}|||${{ctrlLine}}"
                }}.take(20)
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
            self.logger.info(f"  Batch {offset//batch_size + 1}: {len(parsed)} control dependencies")

            for parts in parsed:
                if len(parts) >= 8:
                    method, file_path, method_line_str, ctrl_type, ctrl_code, \
                        dependent_count_str, dependent_type, ctrl_line_str = parts[:8]

                    desc = self._describe_control_dependency(
                        ctrl_type, ctrl_code, dependent_count_str, dependent_type
                    )

                    pattern = ControlDependency(
                        method_name=method.strip(),
                        file_path=file_path.strip(),
                        line_number=int(ctrl_line_str.strip()) if ctrl_line_str.strip().lstrip('-').isdigit() else -1,
                        control_type=ctrl_type.strip(),
                        control_code=ctrl_code.strip()[:100],
                        dependent_type=dependent_type.strip(),
                        dependent_count=int(dependent_count_str.strip()) if dependent_count_str.strip().isdigit() else 0,
                        description=desc
                    )
                    patterns.append(pattern)

            offset += batch_size

        self.logger.info(f"[OK] Extracted {len(patterns)} control dependencies")
        return patterns

    # Description generators

    def _describe_parameter_flow(self, param_name: str, param_type: str,
                                 target_type: str, target_code: str) -> str:
        """Generate natural language description of parameter flow."""
        code_short = target_code[:50] + "..." if len(target_code) > 50 else target_code

        if target_type == "IDENTIFIER":
            return f"Parameter '{param_name}' (type {param_type}) flows to identifier: {code_short}"
        elif target_type == "CALL":
            return f"Parameter '{param_name}' (type {param_type}) flows to function call: {code_short}"
        elif target_type == "METHOD_RETURN" or target_type == "RETURN":
            return f"Parameter '{param_name}' (type {param_type}) flows to return statement"
        elif target_type == "METHOD_PARAMETER_OUT":
            return f"Parameter '{param_name}' (type {param_type}) flows to output parameter"
        else:
            return f"Parameter '{param_name}' (type {param_type}) flows to {target_type}"

    def _describe_variable_chain(self, source_var: str, source_line: str,
                                target_var: str, target_line: str, chain_type: str) -> str:
        """Generate natural language description of variable chain."""
        if chain_type == "REASSIGNMENT":
            return f"Variable '{source_var}' from line {source_line} flows to '{target_var}' at line {target_line}"
        elif chain_type == "PARAM_TO_VAR":
            return f"Parameter '{source_var}' flows to variable '{target_var}' at line {target_line}"
        elif chain_type == "CALL_TO_VAR":
            return f"Function call result flows from line {source_line} to variable '{target_var}' at line {target_line}"
        else:
            return f"Data flows from '{source_var}' (line {source_line}) to '{target_var}' (line {target_line})"

    def _describe_return_source(self, ret_code: str, source_type: str, source_code: str) -> str:
        """Generate natural language description of return source."""
        ret_short = ret_code[:40] + "..." if len(ret_code) > 40 else ret_code
        source_short = source_code[:50] + "..." if len(source_code) > 50 else source_code

        if source_type == "CALL":
            return f"Return statement '{ret_short}' receives value from function call: {source_short}"
        elif source_type == "IDENTIFIER":
            return f"Return statement '{ret_short}' receives value from variable: {source_short}"
        elif source_type == "METHOD_PARAMETER_IN":
            return f"Return statement '{ret_short}' receives value from parameter: {source_short}"
        else:
            return f"Return statement '{ret_short}' receives value from {source_type}: {source_short}"

    def _describe_call_argument_source(self, call_name: str, arg_index: str,
                                       arg_code: str, source_type: str) -> str:
        """Generate natural language description of call argument source."""
        arg_short = arg_code[:40] + "..." if len(arg_code) > 40 else arg_code

        return f"Argument {arg_index} of call '{call_name}' ({arg_short}) receives value from {source_type}"

    def _describe_control_dependency(self, ctrl_type: str, ctrl_code: str,
                                    dependent_count: str, dependent_type: str) -> str:
        """Generate natural language description of control dependency."""
        code_short = ctrl_code[:60] + "..." if len(ctrl_code) > 60 else ctrl_code
        count = dependent_count if dependent_count.isdigit() else "0"

        return f"{ctrl_type} control structure ({code_short}) has {count} dependent nodes of type {dependent_type}"

    def extract_all_patterns(self, output_file: str, param_limit: int = 20000,
                            variable_limit: int = 15000, return_limit: int = 10000,
                            call_arg_limit: int = 10000, control_dep_limit: int = 15000):
        """Extract all DDG patterns and save to file."""
        self.logger.info("="*80)
        self.logger.info("DDG PATTERN EXTRACTION")
        self.logger.info("="*80)

        all_patterns = {}

        # Extract each pattern type
        all_patterns['parameter_flows'] = [
            asdict(p) for p in self.extract_parameter_flows(total_limit=param_limit)
        ]

        all_patterns['variable_chains'] = [
            asdict(p) for p in self.extract_variable_chains(total_limit=variable_limit)
        ]

        all_patterns['return_sources'] = [
            asdict(p) for p in self.extract_return_sources(total_limit=return_limit)
        ]

        all_patterns['call_argument_sources'] = [
            asdict(p) for p in self.extract_call_argument_sources(total_limit=call_arg_limit)
        ]

        all_patterns['control_dependencies'] = [
            asdict(p) for p in self.extract_control_dependencies(total_limit=control_dep_limit)
        ]

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(all_patterns, f, indent=2)

        self.logger.info("="*80)
        self.logger.info("EXTRACTION COMPLETE")
        self.logger.info(f"  Parameter flows: {len(all_patterns['parameter_flows'])}")
        self.logger.info(f"  Variable chains: {len(all_patterns['variable_chains'])}")
        self.logger.info(f"  Return sources: {len(all_patterns['return_sources'])}")
        self.logger.info(f"  Call argument sources: {len(all_patterns['call_argument_sources'])}")
        self.logger.info(f"  Control dependencies: {len(all_patterns['control_dependencies'])}")
        self.logger.info(f"  Total patterns: {sum(len(v) for v in all_patterns.values())}")
        self.logger.info(f"  Output: {output_file}")
        self.logger.info("="*80)

        return all_patterns


def main():
    """Main entry point for DDG extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract DDG patterns from Joern CPG")
    parser.add_argument('--output', default='data/ddg_patterns.json', help='Output JSON file')
    parser.add_argument('--param-limit', type=int, default=20000, help='Max parameter flow patterns')
    parser.add_argument('--variable-limit', type=int, default=15000, help='Max variable chain patterns')
    parser.add_argument('--return-limit', type=int, default=10000, help='Max return source patterns')
    parser.add_argument('--call-arg-limit', type=int, default=10000, help='Max call argument patterns')
    parser.add_argument('--control-dep-limit', type=int, default=15000, help='Max control dependency patterns')
    parser.add_argument('--joern-endpoint', default='localhost:8080', help='Joern server endpoint')

    args = parser.parse_args()

    # Initialize Joern client
    client = JoernClient(args.joern_endpoint)

    try:
        # Connect to Joern
        logger.info("Connecting to Joern server...")
        client.connect()
        logger.info("[OK] Connected to Joern")

        # Create extractor
        extractor = DDGPatternExtractor(client)

        # Extract all patterns
        extractor.extract_all_patterns(
            output_file=args.output,
            param_limit=args.param_limit,
            variable_limit=args.variable_limit,
            return_limit=args.return_limit,
            call_arg_limit=args.call_arg_limit,
            control_dep_limit=args.control_dep_limit
        )

        logger.info("[OK] DDG pattern extraction complete!")

    except Exception as e:
        logger.error(f"[FAILED] Extraction failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
