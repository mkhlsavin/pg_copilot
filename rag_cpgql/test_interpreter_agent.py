"""Quick test of the new InterpreterAgent class."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.interpreter_agent import InterpreterAgent

def test_interpreter_empty_result():
    """Test handling of empty results."""
    print("=" * 80)
    print("TEST 1: Empty Result Handling")
    print("=" * 80)

    interpreter = InterpreterAgent(llm_interface=None)  # No LLM, template mode

    result = interpreter.interpret(
        question="Find functions related to memory management",
        query="cpg.method.where(_.tag.nameExact(\"function-purpose\").valueExact(\"memory-management\")).name.l",
        execution_success=True,
        execution_result={"result": "List()"},
        execution_error=None,
        enrichment_hints={"tags": [{"tag_name": "function-purpose", "tag_value": "memory-management"}]},
        used_fallback=False,
        fallback_query=None
    )

    print(f"Answer: {result['answer'][:200]}...")
    print(f"Confidence: {result['confidence']}")
    print(f"Summary Type: {result['summary_type']}")
    print()


def test_interpreter_with_functions():
    """Test handling of function list results."""
    print("=" * 80)
    print("TEST 2: Function List Handling")
    print("=" * 80)

    interpreter = InterpreterAgent(llm_interface=None)  # No LLM, template mode

    result = interpreter.interpret(
        question="Find buffer management functions",
        query="cpg.method.where(_.tag.nameExact(\"data-structure\").valueExact(\"buffer\")).name.l",
        execution_success=True,
        execution_result={
            "result": "List(BufferAlloc, BufferGetPage, BufferReadPage, ReleaseBuffer, "
                     "InvalidateBuffer, MarkBufferDirty, LockBuffer, UnlockBuffer)"
        },
        execution_error=None,
        enrichment_hints={
            "tags": [
                {"tag_name": "data-structure", "tag_value": "buffer"},
                {"tag_name": "function-purpose", "tag_value": "buffer-management"}
            ]
        },
        used_fallback=False,
        fallback_query=None
    )

    print(f"Answer:\n{result['answer']}")
    print(f"\nConfidence: {result['confidence']}")
    print(f"Summary Type: {result['summary_type']}")
    print(f"Function Count: {result.get('function_count', 'N/A')}")
    print()


def test_interpreter_with_fallback():
    """Test handling of fallback query scenarios."""
    print("=" * 80)
    print("TEST 3: Fallback Query Handling")
    print("=" * 80)

    interpreter = InterpreterAgent(llm_interface=None)  # No LLM, template mode

    result = interpreter.interpret(
        question="Find BRIN index functions",
        query="cpg.method.where(_.tag.nameExact(\"feature\").valueExact(\"brin\")).name.l",
        execution_success=True,
        execution_result={
            "result": "List(brinbuild, brininsert, bringetbitmap, brinoptions, brinvacuumcleanup)"
        },
        execution_error=None,
        enrichment_hints={"tags": [{"tag_name": "feature", "tag_value": "brin"}]},
        used_fallback=True,
        fallback_query='cpg.method.name(".*brin.*").l.take(20)'
    )

    print(f"Answer:\n{result['answer']}")
    print(f"\nConfidence: {result['confidence']}")
    print(f"Summary Type: {result['summary_type']}")
    print()


def test_interpreter_error():
    """Test handling of execution errors."""
    print("=" * 80)
    print("TEST 4: Execution Error Handling")
    print("=" * 80)

    interpreter = InterpreterAgent(llm_interface=None)  # No LLM, template mode

    result = interpreter.interpret(
        question="Find invalid query test",
        query="cpg.invalid.syntax.l",
        execution_success=False,
        execution_result={},
        execution_error="Query syntax error: 'invalid' is not a valid CPG step",
        enrichment_hints=None,
        used_fallback=False,
        fallback_query=None
    )

    print(f"Answer: {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Summary Type: {result['summary_type']}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INTERPRETER AGENT TESTS")
    print("=" * 80 + "\n")

    test_interpreter_empty_result()
    test_interpreter_with_functions()
    test_interpreter_with_fallback()
    test_interpreter_error()

    print("=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
