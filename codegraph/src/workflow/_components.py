"""LangGraph Workflow Components

Lazy-loaded singleton components used by the LangGraph workflow.
These are initialized once and reused across workflow executions.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Agent imports
from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.interpreter_agent import InterpreterAgent
from src.agents.adaptive_refiner import AdaptiveQueryRefiner

# Phase 7: Control Flow Analysis imports
from src.agents.control_flow_generator import ControlFlowGenerator
from src.agents.call_chain_analyzer import CallChainAnalyzer
from src.agents.logic_synthesizer import LogicSynthesizer

# LLM and generation imports
from src.llm.llm_interface_compat import LLMInterface
from src.generation.sql_query_generator import SQLQueryGenerator
from src.retrieval.vector_store_real import VectorStoreReal

logger = logging.getLogger(__name__)


# ============================================================================
# LAZY-LOADED COMPONENTS
# ============================================================================

_ANALYZER: Optional[AnalyzerAgent] = None
_VECTOR_STORE: Optional[VectorStoreReal] = None
_RETRIEVER: Optional[RetrieverAgent] = None
_ENRICHMENT_AGENT: Optional[EnrichmentAgent] = None
_LLM_INTERFACE: Optional[LLMInterface] = None
_SQL_GENERATOR: Optional[SQLQueryGenerator] = None
_GENERATOR_AGENT: Optional[GeneratorAgent] = None
_INTERPRETER_AGENT: Optional[InterpreterAgent] = None
_ADAPTIVE_REFINER: Optional[AdaptiveQueryRefiner] = None

# Phase 7: Control Flow Analysis components
_CONTROL_FLOW_GENERATOR: Optional[ControlFlowGenerator] = None
_CALL_CHAIN_ANALYZER: Optional[CallChainAnalyzer] = None
_LOGIC_SYNTHESIZER: Optional[LogicSynthesizer] = None


def get_analyzer() -> AnalyzerAgent:
    """Return a shared AnalyzerAgent instance."""
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = AnalyzerAgent()
    return _ANALYZER


def get_vector_store() -> VectorStoreReal:
    """Return an initialized VectorStoreReal instance."""
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        _VECTOR_STORE = VectorStoreReal()
        try:
            _VECTOR_STORE.initialize_collections()
        except Exception as exc:
            logger.warning(f"Vector store initialization failed: {exc}")
    return _VECTOR_STORE


def get_retriever() -> RetrieverAgent:
    """Return a retriever that shares analyzer and vector store state."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = RetrieverAgent(
            vector_store=get_vector_store(),
            analyzer_agent=get_analyzer()
        )
    return _RETRIEVER


def get_enrichment_agent() -> EnrichmentAgent:
    """Return a shared EnrichmentAgent instance."""
    global _ENRICHMENT_AGENT
    if _ENRICHMENT_AGENT is None:
        _ENRICHMENT_AGENT = EnrichmentAgent()
    return _ENRICHMENT_AGENT


def get_llm_interface() -> LLMInterface:
    """Return a shared LLMInterface instance."""
    global _LLM_INTERFACE
    if _LLM_INTERFACE is None:
        _LLM_INTERFACE = LLMInterface()
    return _LLM_INTERFACE


def get_sql_generator() -> SQLQueryGenerator:
    """Return a shared SQLQueryGenerator instance."""
    global _SQL_GENERATOR
    if _SQL_GENERATOR is None:
        llm = get_llm_interface()
        _SQL_GENERATOR = SQLQueryGenerator(llm=llm)
    return _SQL_GENERATOR


def get_generator_agent() -> GeneratorAgent:
    """Return a GeneratorAgent backed by SQLQueryGenerator."""
    global _GENERATOR_AGENT
    if _GENERATOR_AGENT is None:
        sql_generator = get_sql_generator()
        _GENERATOR_AGENT = GeneratorAgent(
            sql_generator=sql_generator
        )
    return _GENERATOR_AGENT


def get_interpreter_agent() -> InterpreterAgent:
    """Return an InterpreterAgent backed by a shared LLM for answer synthesis."""
    global _INTERPRETER_AGENT
    if _INTERPRETER_AGENT is None:
        _INTERPRETER_AGENT = InterpreterAgent(llm_interface=get_llm_interface())
    return _INTERPRETER_AGENT


def get_adaptive_refiner() -> AdaptiveQueryRefiner:
    """Return a shared AdaptiveQueryRefiner instance with persistent learning."""
    global _ADAPTIVE_REFINER
    if _ADAPTIVE_REFINER is None:
        persistence_path = Path("data/adaptive_query_patterns.json")
        _ADAPTIVE_REFINER = AdaptiveQueryRefiner(persistence_path=str(persistence_path))
        logger.info(f"AdaptiveQueryRefiner initialized with {_ADAPTIVE_REFINER.get_statistics()['total_patterns_learned']} learned patterns")
    return _ADAPTIVE_REFINER


def get_control_flow_generator() -> ControlFlowGenerator:
    """Return a shared ControlFlowGenerator instance."""
    global _CONTROL_FLOW_GENERATOR
    if _CONTROL_FLOW_GENERATOR is None:
        _CONTROL_FLOW_GENERATOR = ControlFlowGenerator()
        logger.info("ControlFlowGenerator initialized")
    return _CONTROL_FLOW_GENERATOR


def get_call_chain_analyzer() -> CallChainAnalyzer:
    """Return a shared CallChainAnalyzer instance."""
    global _CALL_CHAIN_ANALYZER
    if _CALL_CHAIN_ANALYZER is None:
        _CALL_CHAIN_ANALYZER = CallChainAnalyzer()
        logger.info("CallChainAnalyzer initialized")
    return _CALL_CHAIN_ANALYZER


def get_logic_synthesizer() -> LogicSynthesizer:
    """Return a shared LogicSynthesizer instance."""
    global _LOGIC_SYNTHESIZER
    if _LOGIC_SYNTHESIZER is None:
        _LOGIC_SYNTHESIZER = LogicSynthesizer(llm=get_llm_interface().model)
        logger.info("LogicSynthesizer initialized")
    return _LOGIC_SYNTHESIZER


def reset_all_components():
    """Reset all cached components. Useful for testing."""
    global _ANALYZER, _VECTOR_STORE, _RETRIEVER, _ENRICHMENT_AGENT
    global _LLM_INTERFACE, _SQL_GENERATOR, _GENERATOR_AGENT
    global _INTERPRETER_AGENT, _ADAPTIVE_REFINER
    global _CONTROL_FLOW_GENERATOR, _CALL_CHAIN_ANALYZER, _LOGIC_SYNTHESIZER

    _ANALYZER = None
    _VECTOR_STORE = None
    _RETRIEVER = None
    _ENRICHMENT_AGENT = None
    _LLM_INTERFACE = None
    _SQL_GENERATOR = None
    _GENERATOR_AGENT = None
    _INTERPRETER_AGENT = None
    _ADAPTIVE_REFINER = None
    _CONTROL_FLOW_GENERATOR = None
    _CALL_CHAIN_ANALYZER = None
    _LOGIC_SYNTHESIZER = None


__all__ = [
    'get_analyzer',
    'get_vector_store',
    'get_retriever',
    'get_enrichment_agent',
    'get_llm_interface',
    'get_sql_generator',
    'get_generator_agent',
    'get_interpreter_agent',
    'get_adaptive_refiner',
    'get_control_flow_generator',
    'get_call_chain_analyzer',
    'get_logic_synthesizer',
    'reset_all_components',
]
