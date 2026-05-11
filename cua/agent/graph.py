"""
LangGraph CUA Agent — tüm node'lar async, ainvoke kullanır.
Plan → Execute → Evaluate → Synthesize döngüsü.
"""
import asyncio
import re
from langgraph.graph import StateGraph, END

from cua.agent.state import AgentState
from cua.agent.browser_tool import BrowserTool
from cua.agent.model_handler import CUAModelHandler
from cua.agent.content_extractor import ContentExtractor
from cua.agent.search_strategy import SearchStrategy
from cua.config import (
    SEARCH_DELAY_SECONDS,
    SURFACE_EXCLUDED_DOMAINS,
    SURFACE_BLOCKED_DOMAINS,
)


# ---------------------------------------------------------------------------
# Context holder
# ---------------------------------------------------------------------------

class GraphContext:
    def __init__(self, browser: BrowserTool, model: CUAModelHandler):
        self.browser = browser
        self.model   = model


# ---------------------------------------------------------------------------
# Guardrail helpers
# ---------------------------------------------------------------------------

_GENERIC_QUERIES = {
    "news",
    "latest news",
    "today news",
    "breaking news",
    "latest",
    "update",
}


def _params(state: AgentState) -> dict:
    return state.get("params", {}) or {}


def _max_cycles(state: AgentState) -> int:
    return max(1, int(_params(state).get("max_cycles", 8)))


def _max_searches(state: AgentState) -> int:
    params = _params(state)
    default = max(2, int(params.get("max_articles", 5)) * 2)
    return max(1, int(params.get("max_searches", default)))


def _normalize_query(query: str) -> str:
    query = (query or "").strip().lower()
    query = re.sub(r"[\"'`]+", "", query)
    query = re.sub(r"\s+", " ", query)
    return query


def _query_too_weak(query: str, base_query: str) -> bool:
    normalized = _normalize_query(query)
    if not normalized or normalized in _GENERIC_QUERIES:
        return True
    base_terms = [part for part in _normalize_query(base_query).split() if len(part) > 2]
    if base_terms and not any(term in normalized for term in base_terms[:3]):
        return True
    return len(normalized) < 4


def _keywords_from_state(state: AgentState) -> list[str]:
    text_parts = []
    for item in state.get("collected_articles", [])[-3:]:
        text_parts.append(item.get("title", ""))
        text_parts.append(item.get("content", "")[:300])
    for item in state.get("_search_results", [])[-5:]:
        text_parts.append(item.get("title", ""))
        text_parts.append(item.get("snippet", ""))

    seen = set()
    keywords = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", " ".join(text_parts)):
        lowered = word.lower()
        if lowered not in seen:
            seen.add(lowered)
            keywords.append(word)
    return keywords[:4]


def _fallback_queries(state: AgentState, rejected_query: str = "") -> list[str]:
    base_query = state.get("query", state.get("topic", "")).strip()
    cycle = state.get("cycle_count", 0)
    candidates = []

    if rejected_query:
        candidates.append(rejected_query)

    candidates.extend(
        SearchStrategy.generate_queries(
            topic=base_query,
            mode="surface",
            existing_findings=state.get("collected_articles", []),
            cycle=cycle,
            current_hypothesis="",
        )
    )

    for keyword in _keywords_from_state(state):
        candidates.append(f"{base_query} {keyword}")

    candidates.extend([
        f"{base_query} latest developments",
        f"{base_query} market reaction",
        f"{base_query} official statement",
        f"{base_query} analysis",
    ])

    unique = []
    seen = set()
    for candidate in candidates:
        normalized = _normalize_query(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(candidate)
    return unique


def _choose_search_query(state: AgentState, proposed_query: str) -> tuple[str, str]:
    searched = set(state.get("_searched_query_keys", []))
    base_query = state.get("query", state.get("topic", ""))
    proposed_query = (proposed_query or base_query).strip()
    proposed_key = _normalize_query(proposed_query)

    if proposed_key and proposed_key not in searched and not _query_too_weak(proposed_query, base_query):
        return proposed_query, proposed_key

    for candidate in _fallback_queries(state, proposed_query):
        key = _normalize_query(candidate)
        if key and key not in searched and not _query_too_weak(candidate, base_query):
            print(f"[Graph] Query guardrail: '{proposed_query}' -> '{candidate}'")
            return candidate, key

    return "", ""


def _terminal_status(state: AgentState) -> str:
    if state.get("error"):
        return state["error"]
    params = _params(state)
    collected = len(state.get("collected_articles", []))
    if collected >= int(params.get("max_articles", 10)):
        return "max_articles_reached"
    if state.get("_search_count", 0) >= _max_searches(state):
        return "max_searches_reached"
    if state.get("cycle_count", 0) >= _max_cycles(state):
        return "max_cycles_reached"
    if state.get("_no_progress_cycles", 0) >= int(params.get("max_no_progress_cycles", 3)):
        return "no_progress"
    return "complete"


# ---------------------------------------------------------------------------
# Async node factory functions
# ---------------------------------------------------------------------------

def make_plan_node(ctx: GraphContext):
    async def plan_node(state: AgentState) -> AgentState:
        cycle = state.get("cycle_count", 0)

        if cycle >= _max_cycles(state):
            print(f"[Graph] Max cycle ({_max_cycles(state)}) -> force complete")
            state["should_stop"]   = True
            state["_last_action"]  = {"action": "complete"}
            return state

        if state.get("_search_count", 0) >= _max_searches(state):
            print(f"[Graph] Max searches ({_max_searches(state)}) -> force complete")
            state["should_stop"]   = True
            state["_last_action"]  = {"action": "complete"}
            return state

        # LLM'e sor: ne yapılacak?
        decision = await ctx.model.plan_next_action(state)
        state["_last_action"]  = decision
        state["cycle_count"]   = cycle + 1
        print(f"[Graph] Plan [{cycle+1}]: {decision}")
        return state

    return plan_node


def make_execute_node(ctx: GraphContext):
    async def execute_node(state: AgentState) -> AgentState:
        action = state.get("_last_action", {})

        if action.get("action") == "complete":
            state["should_stop"] = True
            return state

        # Döngüler arası gecikme (rate limit koruması)
        await asyncio.sleep(SEARCH_DELAY_SECONDS)

        # ── SEARCH ──────────────────────────────────────────────
        if action.get("action") == "search":
            query, query_key = _choose_search_query(
                state,
                action.get("query", state.get("query", state.get("topic", ""))),
            )
            if not query:
                state["error"] = "no usable search query left"
                state["should_stop"] = True
                return state

            state.setdefault("_searched_queries", []).append(query)
            state.setdefault("_searched_query_keys", []).append(query_key)
            state["_search_count"] = state.get("_search_count", 0) + 1

            results  = await ctx.browser.search(
                query,
                num_results=8,
                engine=_params(state).get("search_engine"),
            )
            excluded = state.get("exclude_domains", SURFACE_EXCLUDED_DOMAINS) + SURFACE_BLOCKED_DOMAINS
            results = ctx.browser.filter_excluded_domains(results, excluded)
            visited  = set(state.get("visited_urls", []))
            excluded_urls = set(state.get("exclude_urls", []))
            new_urls = [
                r for r in results
                if r.get("url") and r["url"] not in visited and r["url"] not in excluded_urls
            ]
            state["_search_results"] = new_urls
            print(f"[Graph] Search '{query}': {len(new_urls)} yeni sonuç")

            # Surface modda ilk uygun sonucu hemen çek
            progress = False
            for result in new_urls[:3]:
                url       = result["url"]
                page_data = await ctx.browser.extract_page(url)

                visited_list = state.get("visited_urls", [])
                if url not in visited_list:
                    visited_list.append(url)
                    state["visited_urls"] = visited_list

                if page_data.get("requires_vision"):
                    page_data = await ctx.browser.solve_captcha_with_vision(
                        url, page_data.get("screenshot_bytes", b"")
                    )

                if not page_data.get("error"):
                    article = ContentExtractor.extract_from_raw(page_data, search_keywords=query)
                    if ContentExtractor.is_valid_article(article):
                        articles = state.get("collected_articles", [])
                        articles.append(article)
                        state["collected_articles"] = articles
                        progress = True
                        print(f"[Graph] Makale eklendi: {article.get('title','')[:60]}")
                        break  # her döngüde 1 makale yeter

            state["_no_progress_cycles"] = 0 if progress else state.get("_no_progress_cycles", 0) + 1

        # ── VISIT ───────────────────────────────────────────────
        elif action.get("action") == "visit":
            url      = action.get("url", "")
            visited  = state.get("visited_urls", [])

            if url and url not in visited:
                excluded = state.get("exclude_domains", SURFACE_EXCLUDED_DOMAINS) + SURFACE_BLOCKED_DOMAINS
                allowed = ctx.browser.filter_excluded_domains([{"url": url}], excluded)
                if not allowed or url in set(state.get("exclude_urls", [])):
                    print(f"[Graph] Surface mode skipped excluded URL/domain: {url}")
                    state["_no_progress_cycles"] = state.get("_no_progress_cycles", 0) + 1
                    return state

                page_data = await ctx.browser.extract_page(url)
                visited.append(url)
                state["visited_urls"] = visited

                if page_data.get("requires_vision"):
                    page_data = await ctx.browser.solve_captcha_with_vision(
                        url, page_data.get("screenshot_bytes", b"")
                    )

                if not page_data.get("error"):
                    article = ContentExtractor.extract_from_raw(
                        page_data,
                        search_keywords=state.get("query", state.get("topic", ""))
                    )
                    if ContentExtractor.is_valid_article(article):
                        articles = state.get("collected_articles", [])
                        articles.append(article)
                        state["collected_articles"] = articles
                        state["_no_progress_cycles"] = 0
                    else:
                        state["_no_progress_cycles"] = state.get("_no_progress_cycles", 0) + 1
                else:
                    state["_no_progress_cycles"] = state.get("_no_progress_cycles", 0) + 1

                print(f"[Graph] Visit '{url}': {'OK' if not page_data.get('error') else page_data['error']}")
            else:
                state["_no_progress_cycles"] = state.get("_no_progress_cycles", 0) + 1
                print(f"[Graph] Visit skipped: {url or 'empty url'}")

        return state

    return execute_node


def make_evaluate_node(ctx: GraphContext):
    async def evaluate_node(state: AgentState) -> AgentState:
        if state.get("should_stop"):
            return state

        params = _params(state)
        max_articles = int(params.get("max_articles", 10))
        max_no_progress = int(params.get("max_no_progress_cycles", 3))
        collected = len(state.get("collected_articles", []))
        searches = state.get("_search_count", 0)
        cycles = state.get("cycle_count", 0)
        no_progress = state.get("_no_progress_cycles", 0)

        should_stop = (
            collected >= max_articles
            or searches >= _max_searches(state)
            or cycles >= _max_cycles(state)
            or no_progress >= max_no_progress
        )
        print(
            "[Graph] Evaluate: "
            f"articles={collected}/{max_articles}, "
            f"searches={searches}/{_max_searches(state)}, "
            f"cycles={cycles}/{_max_cycles(state)}, "
            f"no_progress={no_progress}/{max_no_progress}, dur={should_stop}"
        )

        state["should_stop"] = should_stop
        return state

    return evaluate_node


def make_synthesize_node(ctx: GraphContext):
    async def synthesize_node(state: AgentState) -> AgentState:
        print("[Graph] Sentezleniyor...")
        report              = await ctx.model.synthesize_report(state)
        state["final_report"] = report
        mode = report.get("mode", state.get("mode", "?"))
        print(f"[Graph] Rapor hazır: mode={mode}, anahtarlar={list(report.keys())}")
        return state

    return synthesize_node


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route(state: AgentState) -> str:
    return "synthesize" if state.get("should_stop", False) else "plan"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------

def create_agent_graph(mode: str, browser: BrowserTool, model: CUAModelHandler):
    """
    StateGraph oluştur ve derleme.

    Args:
        mode:    "surface"
        browser: Başlatılmış BrowserTool
        model:   CUAModelHandler

    Returns:
        Derlenmiş LangGraph (ainvoke için hazır)
    """
    ctx = GraphContext(browser=browser, model=model)

    workflow = StateGraph(AgentState)
    workflow.add_node("plan",      make_plan_node(ctx))
    workflow.add_node("execute",   make_execute_node(ctx))
    workflow.add_node("evaluate",  make_evaluate_node(ctx))
    workflow.add_node("synthesize", make_synthesize_node(ctx))

    workflow.set_entry_point("plan")
    workflow.add_edge("plan",    "execute")
    workflow.add_edge("execute", "evaluate")
    workflow.add_conditional_edges(
        "evaluate", route,
        {"plan": "plan", "synthesize": "synthesize"}
    )
    workflow.add_edge("synthesize", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Public runner (main.py tarafından çağrılır)
# ---------------------------------------------------------------------------

async def run_agent(task_data: dict, browser: BrowserTool, model: CUAModelHandler) -> dict:
    """
    Bir görevi çalıştırır.

    Args:
        task_data: {"mode": ..., "query"|"topic": ..., "params": {...}}
        browser:   Başlatılmış BrowserTool
        model:     CUAModelHandler

    Returns:
        final_report dict
    """
    mode  = task_data.get("mode", "surface")
    if mode != "surface":
        return {
            "mode": mode,
            "status": "FAILED",
            "error": "research mode is disabled; CUA only accepts surface agent tasks",
        }

    graph = create_agent_graph(mode, browser, model)

    initial_state: AgentState = {
        "mode":               mode,
        "query":              task_data.get("query", task_data.get("topic", "")),
        "topic":              task_data.get("topic", task_data.get("query", "")),
        "params":             task_data.get("params", {}),
        "visited_urls":       [],
        "exclude_urls":       task_data.get("exclude_urls", []),
        "exclude_domains":    task_data.get("exclude_domains", SURFACE_EXCLUDED_DOMAINS if mode == "surface" else []),
        "collected_articles": [],
        "cycle_count":        0,
        "should_stop":        False,
        "final_report":       None,
        "error":              None,
        "_searched_queries":  [],   # Sorgu çeşitleme koruma listesi
        "_searched_query_keys": [],
        "_search_count":      0,
        "_no_progress_cycles": 0,
    }

    try:
        # Async invoke — tüm node'lar async olduğundan ainvoke kullanıyoruz
        final_state = await graph.ainvoke(initial_state)
        report = final_state.get("final_report") or {}
        if mode == "surface" and not final_state.get("collected_articles"):
            return {
                "mode": mode,
                "status": "FAILED",
                "error": final_state.get("error") or "no valid articles collected",
                "stop_reason": _terminal_status(final_state),
            }
        report["mode"]   = mode
        report["status"] = "COMPLETED"
        report["stop_reason"] = _terminal_status(final_state)
        report["articles"] = final_state.get("collected_articles", [])
        return report
    except Exception as e:
        print(f"[Graph] Agent hatası: {e}")
        import traceback
        traceback.print_exc()
        return {"mode": mode, "status": "FAILED", "error": str(e)}
