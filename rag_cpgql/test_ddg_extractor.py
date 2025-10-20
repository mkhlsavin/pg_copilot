"""Test DDG extractor with small batch"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.execution.joern_client import JoernClient
from src.extraction.ddg_extractor import DDGPatternExtractor

# Initialize client
client = JoernClient('localhost:8080')
client.connect()

# Create extractor
extractor = DDGPatternExtractor(client)

print("="*80)
print("DDG Extractor Test - Small Batch (limit=100)")
print("="*80)
print()

# Test each pattern type with small limits
print("[1/5] Testing parameter flows...")
param_flows = extractor.extract_parameter_flows(batch_size=10, total_limit=100)
print(f"  Result: {len(param_flows)} patterns")
if param_flows:
    print(f"  Sample: {param_flows[0].description}")
print()

print("[2/5] Testing variable chains...")
var_chains = extractor.extract_variable_chains(batch_size=10, total_limit=100)
print(f"  Result: {len(var_chains)} patterns")
if var_chains:
    print(f"  Sample: {var_chains[0].description}")
print()

print("[3/5] Testing return sources...")
return_sources = extractor.extract_return_sources(batch_size=10, total_limit=100)
print(f"  Result: {len(return_sources)} patterns")
if return_sources:
    print(f"  Sample: {return_sources[0].description}")
print()

print("[4/5] Testing call argument sources...")
call_args = extractor.extract_call_argument_sources(batch_size=10, total_limit=100)
print(f"  Result: {len(call_args)} patterns")
if call_args:
    print(f"  Sample: {call_args[0].description}")
print()

print("[5/5] Testing control dependencies...")
control_deps = extractor.extract_control_dependencies(batch_size=10, total_limit=100)
print(f"  Result: {len(control_deps)} patterns")
if control_deps:
    print(f"  Sample: {control_deps[0].description}")
print()

print("="*80)
print("TEST SUMMARY")
print("="*80)
total = len(param_flows) + len(var_chains) + len(return_sources) + len(call_args) + len(control_deps)
print(f"Total patterns extracted: {total}")
print(f"  - Parameter flows: {len(param_flows)}")
print(f"  - Variable chains: {len(var_chains)}")
print(f"  - Return sources: {len(return_sources)}")
print(f"  - Call argument sources: {len(call_args)}")
print(f"  - Control dependencies: {len(control_deps)}")
print()

if total > 0:
    print("[OK] DDG extractor test PASSED!")
else:
    print("[FAILED] DDG extractor test FAILED - no patterns extracted")
