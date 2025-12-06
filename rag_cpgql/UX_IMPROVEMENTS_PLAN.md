# ФАЗА 3: UX Improvements - Enhanced Interactivity

**Дата:** 25 ноября 2025
**Длительность:** 2 недели (10 рабочих дней)
**Приоритет:** P2 - СРЕДНИЙ
**Статус:** Готов к реализации

---

## 🎯 Цель фазы

**Значительно улучшить пользовательский опыт** через интерактивность, streaming, conversation memory, и визуализацию.

**Метрики успеха:**
- Users can ask clarifying questions when ambiguous
- Progressive streaming for all long operations
- Conversation context preserved across sessions
- Interactive visualizations operational (optional)

---

## 📋 Компоненты для реализации

### Week 5: Interactivity
1. **Clarifying Questions Node** → Reduce ambiguity
2. **Progressive Streaming** → Better perceived performance

### Week 6: Memory & Visualization
3. **Long-term Conversation Memory** → Context across sessions
4. **Interactive Call Graph Visualization** → Better understanding (optional)

---

## 📅 Week 5: Interactivity

### Task 1: Clarifying Questions Node (Day 1-3)

#### Motivation
**Problem:** Ambiguous questions lead to poor answers
**Solution:** Detect ambiguity and ask clarifying questions

#### Architecture
```python
# Add to LangGraph workflow

def should_clarify(state: WorkflowState) -> bool:
    """Check if question needs clarification."""
    analysis = state['analysis']

    # Heuristics for ambiguity:
    # - Low confidence (<0.5)
    # - Multiple possible intents
    # - Missing key information

    if analysis.get('confidence', 1.0) < 0.5:
        return True

    if len(analysis.get('possible_intents', [])) > 1:
        return True

    return False


def generate_clarifying_questions(state: WorkflowState) -> List[str]:
    """Generate clarifying questions using LLM."""
    question = state['question']
    analysis = state['analysis']

    prompt = f"""The user asked: "{question}"

This question is ambiguous. Generate 2-3 clarifying questions to understand their intent better.

Context:
- Possible intents: {analysis.get('possible_intents', [])}
- Domain: {analysis.get('domain', 'unknown')}
- Confidence: {analysis.get('confidence', 0)}

Format: Return JSON list of questions.
"""

    response = llm.generate_simple(prompt)
    questions = json.loads(response)

    return questions


# LangGraph workflow with clarification
workflow = StateGraph(WorkflowState)

# Nodes
workflow.add_node("analyze", analyze_question)
workflow.add_node("clarify", clarify_if_needed)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_answer)

# Conditional edge
workflow.add_conditional_edges(
    "analyze",
    should_clarify,
    {
        True: "clarify",      # Ask questions
        False: "retrieve"     # Continue normally
    }
)

# After clarification, re-analyze with additional context
workflow.add_edge("clarify", "analyze")
workflow.add_edge("retrieve", "generate")
```

**Implementation Steps:**

**Day 1: Ambiguity Detection (3-4 hours)**
- Implement confidence scoring in AnalyzerAgent
- Add heuristics for ambiguity detection
- Unit tests for detection logic

**Day 2: Question Generation (3-4 hours)**
- Implement LLM-based question generator
- Create question templates for common ambiguities
- Test with ambiguous examples

**Day 3: LangGraph Integration (3-4 hours)**
- Add clarification node to workflows
- Implement conditional routing
- Test end-to-end flow

**Deliverables:**
- `src/workflow/clarification_node.py` (200-300 lines)
- Integration in all 14 workflows
- UI/API for presenting questions to user

---

### Task 2: Progressive Streaming (Day 4-5)

#### Motivation
**Problem:** Long operations appear "frozen" to user
**Solution:** Stream intermediate progress in real-time

#### Architecture
```python
# Server-Sent Events (SSE) endpoint

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.post("/query/stream")
async def query_with_streaming(question: str):
    """Execute query with progressive streaming."""

    async def event_generator():
        # Yield progress updates
        yield f"data: {json.dumps({'stage': 'analyzing', 'progress': 10})}\n\n"

        # Analyze
        analysis = await analyzer.analyze_async(question)
        yield f"data: {json.dumps({'stage': 'analyzed', 'progress': 20, 'result': analysis})}\n\n"

        # Retrieve
        yield f"data: {json.dumps({'stage': 'retrieving', 'progress': 30})}\n\n"
        context = await retriever.retrieve_async(question, analysis)
        yield f"data: {json.dumps({'stage': 'retrieved', 'progress': 50, 'count': len(context)})}\n\n"

        # Generate
        yield f"data: {json.dumps({'stage': 'generating', 'progress': 60})}\n\n"
        query = await generator.generate_async(question, context)
        yield f"data: {json.dumps({'stage': 'generated', 'progress': 70, 'query': query})}\n\n"

        # Execute
        yield f"data: {json.dumps({'stage': 'executing', 'progress': 80})}\n\n"
        results = await executor.execute_async(query)
        yield f"data: {json.dumps({'stage': 'executed', 'progress': 90, 'count': len(results)})}\n\n"

        # Interpret
        yield f"data: {json.dumps({'stage': 'interpreting', 'progress': 95})}\n\n"
        answer = await interpreter.interpret_async(question, results)

        # Final result
        yield f"data: {json.dumps({'stage': 'complete', 'progress': 100, 'answer': answer})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Client-side (JavaScript):**
```javascript
const eventSource = new EventSource('/query/stream', {
    method: 'POST',
    body: JSON.stringify({question: "How does MVCC work?"})
});

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Update UI
    updateProgressBar(data.progress);
    updateStageIndicator(data.stage);

    if (data.stage === 'complete') {
        displayAnswer(data.answer);
        eventSource.close();
    }
};
```

**Deliverables:**
- `src/api/streaming.py` (150-200 lines)
- Async versions of key agents
- Example client implementation
- Documentation

---

## 📅 Week 6: Memory & Visualization

### Task 3: Long-term Conversation Memory (Day 1-3)

#### Motivation
**Problem:** System forgets past interactions
**Solution:** Store and retrieve conversation history

#### Implementation
```python
# src/memory/conversation_memory.py

import chromadb
from datetime import datetime

class ConversationMemory:
    def __init__(self, collection_name: str = "conversation_history"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)

    def add_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        metadata: Dict = None
    ):
        """Store conversation interaction."""
        interaction = {
            'session_id': session_id,
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat(),
            **(metadata or {})
        }

        self.collection.add(
            documents=[f"Q: {question}\nA: {answer}"],
            metadatas=[interaction],
            ids=[f"{session_id}_{interaction['timestamp']}"]
        )

    def get_relevant_history(
        self,
        session_id: str,
        current_question: str,
        top_k: int = 3
    ) -> List[Dict]:
        """Retrieve relevant past interactions."""
        results = self.collection.query(
            query_texts=[current_question],
            where={'session_id': session_id},
            n_results=top_k
        )

        return [
            {
                'question': r['metadatas']['question'],
                'answer': r['metadatas']['answer'],
                'timestamp': r['metadatas']['timestamp']
            }
            for r in results['metadatas'][0]
        ]

    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get full conversation history for session."""
        results = self.collection.get(
            where={'session_id': session_id}
        )

        return sorted(
            results['metadatas'],
            key=lambda x: x['timestamp']
        )
```

**Usage in workflows:**
```python
# Enhanced workflow with memory

def scenario_with_memory(state: WorkflowState):
    session_id = state.get('session_id', 'default')
    question = state['question']

    # Retrieve relevant history
    memory = ConversationMemory()
    history = memory.get_relevant_history(session_id, question, top_k=3)

    # Add history to context
    state['conversation_history'] = history

    # Execute workflow with history context
    result = execute_workflow(state)

    # Store interaction
    memory.add_interaction(
        session_id=session_id,
        question=question,
        answer=result['answer'],
        metadata={
            'scenario': state.get('scenario'),
            'success': result.get('success')
        }
    )

    return result
```

**Deliverables:**
- `src/memory/conversation_memory.py` (250-300 lines)
- ChromaDB collection for history
- Integration in workflows
- Session management API

---

### Task 4: Interactive Call Graph Visualization (Day 4-5) - OPTIONAL

#### Motivation
**Problem:** Text-only results hard to understand
**Solution:** Interactive graph visualization

#### Architecture
```
Backend (Python) → Graph Data (JSON)
                      ↓
            Frontend (D3.js/Cytoscape)
                      ↓
            Interactive Visualization
```

#### Implementation

**Backend (FastAPI):**
```python
# src/api/visualization.py

@app.get("/call-graph/{method_name}")
def get_call_graph(method_name: str, depth: int = 2):
    """Get call graph for visualization."""
    analyzer = CallGraphAnalyzer(cpg_service)

    # Get call graph
    callees = analyzer.get_callees_recursive(method_name, max_depth=depth)
    callers = analyzer.get_callers_recursive(method_name, max_depth=depth)

    # Format for visualization
    nodes = []
    edges = []

    # Add center node
    nodes.append({
        'id': method_name,
        'label': method_name,
        'type': 'center',
        'size': 30
    })

    # Add callee nodes
    for callee in callees:
        nodes.append({
            'id': callee['name'],
            'label': callee['name'],
            'type': 'callee',
            'size': 20
        })
        edges.append({
            'source': method_name,
            'target': callee['name']
        })

    # Add caller nodes
    for caller in callers:
        nodes.append({
            'id': caller['name'],
            'label': caller['name'],
            'type': 'caller',
            'size': 20
        })
        edges.append({
            'source': caller['name'],
            'target': method_name
        })

    return {
        'nodes': nodes,
        'edges': edges
    }
```

**Frontend (React + Cytoscape):**
```javascript
import Cytoscape from 'cytoscape';

function CallGraphVisualization({methodName}) {
    const [graphData, setGraphData] = useState(null);

    useEffect(() => {
        fetch(`/call-graph/${methodName}`)
            .then(res => res.json())
            .then(data => {
                const cy = Cytoscape({
                    container: document.getElementById('cy'),
                    elements: {
                        nodes: data.nodes.map(n => ({data: n})),
                        edges: data.edges.map(e => ({data: e}))
                    },
                    style: [
                        {
                            selector: 'node',
                            style: {
                                'label': 'data(label)',
                                'width': 'data(size)',
                                'height': 'data(size)'
                            }
                        }
                    ],
                    layout: {name: 'cose'}
                });

                setGraphData(cy);
            });
    }, [methodName]);

    return <div id="cy" style={{width: '100%', height: '600px'}} />;
}
```

**Deliverables (if implemented):**
- `src/api/visualization.py` (200-300 lines)
- Frontend visualization component
- Interactive features (zoom, pan, filter)
- Export functionality (SVG/PNG)

---

## 📈 Success Criteria

### Interactivity
- [ ] Ambiguous questions trigger clarification (>80% accuracy)
- [ ] Users can answer clarifying questions
- [ ] System re-analyzes with additional context

### Streaming
- [ ] Progress updates stream in real-time
- [ ] No "frozen" UI during long operations
- [ ] Latency perceived as <1s even for slow operations

### Memory
- [ ] Conversation history stored and retrieved
- [ ] Relevant history included in context
- [ ] Session management works correctly

### Visualization (optional)
- [ ] Call graphs render correctly
- [ ] Interactive features work (zoom, pan, filter)
- [ ] Export functionality works

---

## 📊 Deliverables Checklist

### Code
- [ ] Clarification node (`src/workflow/clarification_node.py`)
- [ ] Streaming API (`src/api/streaming.py`)
- [ ] Conversation memory (`src/memory/conversation_memory.py`)
- [ ] Visualization API (`src/api/visualization.py`) - optional

### Testing
- [ ] Clarification tests (ambiguity detection)
- [ ] Streaming tests (SSE functionality)
- [ ] Memory tests (storage/retrieval)
- [ ] Visualization tests (graph generation) - optional

### Documentation
- [ ] Clarification usage guide
- [ ] Streaming API documentation
- [ ] Memory management guide
- [ ] Visualization guide - optional

---

**Last Updated:** November 25, 2025
**Status:** Ready for Implementation
**Next:** [DEPLOYMENT_READINESS_PLAN.md](DEPLOYMENT_READINESS_PLAN.md) - Phase 4