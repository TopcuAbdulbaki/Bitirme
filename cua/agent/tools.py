"""
LangGraph tool tanımları — browser-use BrowserTool'u saran LangChain tools.

Bu tools LangGraph'ın plan_node'u içinde LLM tool-call olarak çağrılabilir.
Ancak ana akışımızda graph.py doğrudan BrowserTool'u kullandığı için
bu dosya alternatif/ek entegrasyon için saklanmaktadır.
"""
import asyncio
import json
from typing import List, Dict, Any
from langchain_core.tools import tool


# BrowserTool singleton (graph context dışında kullanım için)
_browser_tool = None


def set_browser_tool(bt):
    """graph.py dışından BrowserTool enjekte et."""
    global _browser_tool
    _browser_tool = bt


def _get_browser():
    if _browser_tool is None:
        raise RuntimeError(
            "BrowserTool başlatılmadı. "
            "set_browser_tool() çağrısını önce yapın."
        )
    return _browser_tool


def _run_async(coro):
    """Sync context'ten async fonksiyon çalıştır."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # LangGraph içinde running event loop var
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                fut = pool.submit(asyncio.run, coro)
                return fut.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@tool
def search_web(query: str, engine: str = "google") -> List[Dict[str, Any]]:
    """
    Web'de arama yap ve sonuçları döndür.

    Args:
        query:  Arama sorgusu
        engine: "google" veya "duckduckgo"

    Returns:
        [{"title": ..., "url": ..., "snippet": ...}, ...]
    """
    print(f"[Tool] search_web: '{query}' via {engine}")
    browser = _get_browser()
    results = _run_async(browser.search(query, num_results=8, engine=engine))
    return results


@tool
def visit_page(url: str) -> Dict[str, Any]:
    """
    URL'yi ziyaret et ve makale içeriğini çıkar.

    Args:
        url: Ziyaret edilecek tam URL

    Returns:
        {"title": ..., "content": ..., "media": {...}, ...}
    """
    print(f"[Tool] visit_page: {url}")
    browser = _get_browser()
    result  = _run_async(browser.extract_page(url))
    return result


@tool
def mark_complete() -> str:
    """
    Mevcut görevin tamamlandığını işaretle.
    Yeterli makale toplandığında veya araştırma bittğinde çağırılır.

    Returns:
        Tamamlanma mesajı
    """
    print("[Tool] mark_complete çağrıldı")
    return json.dumps({"status": "complete", "message": "Task marked as complete"})


# LangGraph bind_tools() için export listesi
TOOLS = [search_web, visit_page, mark_complete]
