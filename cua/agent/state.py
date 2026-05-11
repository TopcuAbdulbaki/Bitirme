"""CUA Agent State Definition using LangGraph"""
from typing import TypedDict, Literal, Optional

class AgentState(TypedDict, total=False):
    """State for CUA surface agent tasks."""
    # Task information
    mode: Literal["surface"]
    query: str
    topic: str
    params: dict                        # max_articles, max_searches, etc.
    
    # Navigation state
    visited_urls: list[str]             # URLs already visited
    exclude_urls: list[str]             # URLs to skip (from Orchestrator)
    
    # Collected data
    collected_articles: list[dict]
    
    # Control flow
    cycle_count: int                    # Number of loops executed
    should_stop: bool                   # Flag to stop iteration
    final_report: Optional[dict]        # Synthesized output
    error: Optional[str]                # Error message if any
    
    # Internal agent tracking memory (required for LangGraph state passing)
    _last_action: dict
    _search_results: list
    _searched_queries: list      # Sorgu çeşitleme koruması: daha önce yapılan aramalar
    _searched_query_keys: list
    _query_queue: list
    _pending_urls: list
    _query_plan_initialized: bool
    _search_count: int
    _no_progress_cycles: int
