"""CUA Agent State Definition using LangGraph"""
from typing import TypedDict, Literal, Optional
from langgraph.graph import MessagesState

class AgentState(TypedDict, total=False):
    """State for CUA agent (Surface and Research modes)"""
    # Task information
    mode: Literal["surface", "research"]
    query: str                          # For surface mode
    topic: str                          # For research mode
    params: dict                        # max_articles, max_searches, etc.
    
    # Navigation state
    visited_urls: list[str]             # URLs already visited
    exclude_urls: list[str]             # URLs to skip (from Orchestrator)
    
    # Collected data
    collected_articles: list[dict]      # Mode 1: news articles found
    findings: list[dict]                # Mode 2: research findings
    current_hypothesis: str             # Mode 2: current theory/direction
    
    # Control flow
    cycle_count: int                    # Number of loops executed
    confidence: float                   # Mode 2: self-evaluation confidence (0.0-1.0)
    should_stop: bool                   # Flag to stop iteration
    final_report: Optional[dict]        # Synthesized output
    error: Optional[str]                # Error message if any
    
    # Internal agent tracking memory (required for LangGraph state passing)
    _last_action: dict
    _search_results: list
    _searched_queries: list      # Sorgu çeşitleme koruması: daha önce yapılan aramalar

