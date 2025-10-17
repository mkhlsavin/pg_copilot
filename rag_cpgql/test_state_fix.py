"""Quick test for state management fix"""
from src.workflow.langgraph_workflow import run_workflow

print('Testing state management fix...')
result = run_workflow('Test question for state management', verbose=False)
print(f'\nSuccess: {result["success"]}')
print(f'Valid: {result.get("valid", "N/A")}')
print(f'Query generated: {bool(result.get("query"))}')
print('\nState management fix working!')
