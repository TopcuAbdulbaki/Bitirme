"""
LangGraph CUA Agent — tüm node'lar async, ainvoke kullanır.
Plan → Execute → Evaluate → Synthesize döngüsü.
"""
import asyncio
from langgraph.graph import StateGraph, END

from cua.agent.state import AgentState
from cua.agent.browser_tool import BrowserTool
from cua.agent.model_handler import CUAModelHandler
from cua.agent.content_extractor import ContentExtractor
from cua.config import MAX_RESEARCH_CYCLES, RESEARCH_CONFIDENCE_THRESHOLD, SEARCH_DELAY_SECONDS


# ---------------------------------------------------------------------------
# Context holder
# ---------------------------------------------------------------------------

class GraphContext:
    def __init__(self, browser: BrowserTool, model: CUAModelHandler):
        self.browser = browser
        self.model   = model


# ---------------------------------------------------------------------------
# Async node factory functions
# ---------------------------------------------------------------------------

def make_plan_node(ctx: GraphContext):
    async def plan_node(state: AgentState) -> AgentState:
        cycle = state.get("cycle_count", 0)

        if cycle >= MAX_RESEARCH_CYCLES:
            print(f"[Graph] Max cycle ({MAX_RESEARCH_CYCLES}) → force complete")
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
        mode   = state.get("mode", "surface")

        if action.get("action") == "complete":
            state["should_stop"] = True
            return state

        # Döngüler arası gecikme (rate limit koruması)
        await asyncio.sleep(SEARCH_DELAY_SECONDS)

        # ── SEARCH ──────────────────────────────────────────────
        if action.get("action") == "search":
            query   = action.get("query", state.get("query", state.get("topic", "")))
            results = await ctx.browser.search(query, num_results=8)

            visited  = set(state.get("visited_urls", []))
            new_urls = [r for r in results if r.get("url") and r["url"] not in visited]
            state["_search_results"] = new_urls
            print(f"[Graph] Search '{query}': {len(new_urls)} yeni sonuç")

            # Surface modda ilk uygun sonucu hemen çek
            if mode == "surface":
                for result in new_urls[:3]:
                    url       = result["url"]
                    page_data = await ctx.browser.extract_page(url)

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
                            visited_list = state.get("visited_urls", [])
                            visited_list.append(url)
                            state["visited_urls"] = visited_list
                            print(f"[Graph] Makale eklendi: {article.get('title','')[:60]}")
                            break  # her döngüde 1 makale yeter

        # ── VISIT ───────────────────────────────────────────────
        elif action.get("action") == "visit":
            url      = action.get("url", "")
            visited  = state.get("visited_urls", [])

            if url and url not in visited:
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
                    if mode == "surface":
                        if ContentExtractor.is_valid_article(article):
                            articles = state.get("collected_articles", [])
                            articles.append(article)
                            state["collected_articles"] = articles
                    else:  # research
                        findings = state.get("findings", [])
                        findings.append(article)
                        state["findings"]             = findings
                        state["current_hypothesis"]   = await ctx.model.update_hypothesis(state)

                print(f"[Graph] Visit '{url}': {'OK' if not page_data.get('error') else page_data['error']}")

        return state

    return execute_node


def make_evaluate_node(ctx: GraphContext):
    async def evaluate_node(state: AgentState) -> AgentState:
        if state.get("should_stop"):
            return state

        mode = state.get("mode", "surface")

        if mode == "surface":
            max_articles = state.get("params", {}).get("max_articles", 10)
            collected    = len(state.get("collected_articles", []))
            should_stop  = collected >= max_articles
            print(f"[Graph] Evaluate: {collected}/{max_articles} makale, dur={should_stop}")
        else:
            confidence          = await ctx.model.evaluate_confidence(state)
            state["confidence"] = confidence
            should_stop         = confidence >= RESEARCH_CONFIDENCE_THRESHOLD
            print(f"[Graph] Evaluate: confidence={confidence:.2f}, dur={should_stop}")

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
        mode:    "surface" | "research"
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
    graph = create_agent_graph(mode, browser, model)

    initial_state: AgentState = {
        "mode":               mode,
        "query":              task_data.get("query", task_data.get("topic", "")),
        "topic":              task_data.get("topic", task_data.get("query", "")),
        "params":             task_data.get("params", {}),
        "visited_urls":       [],
        "exclude_urls":       task_data.get("exclude_urls", []),
        "collected_articles": [],
        "findings":           [],
        "current_hypothesis": "Henüz hipotez yok",
        "cycle_count":        0,
        "confidence":         0.0,
        "should_stop":        False,
        "final_report":       None,
        "error":              None,
    }

    try:
        # Async invoke — tüm node'lar async olduğundan ainvoke kullanıyoruz
        final_state = await graph.ainvoke(initial_state)
        report = final_state.get("final_report") or {}
        report["mode"]   = mode
        report["status"] = "COMPLETED"
        return report
    except Exception as e:
        print(f"[Graph] Agent hatası: {e}")
        import traceback
        traceback.print_exc()
        return {"mode": mode, "status": "FAILED", "error": str(e)}
