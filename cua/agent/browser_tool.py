"""
BrowserTool — browser-use 0.12.x uyumlu versiyon.

browser-use'un kendi ChatOpenAI wrapper'ı kullanılır (langchain değil).
Her search/extract işlemi için yeni bir Agent oluşturulur.
Her search/extract işlemi için yeni bir Agent oluşturur.
"""
import json
import re
import os
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from cua.config import DEFAULT_SEARCH_ENGINE, LMSTUDIO_URL, MODEL_NAME


def _build_default_llm():
    """browser-use'un native ChatOpenAI ile LM Studio / vLLM bağlantısı."""
    from browser_use.llm.openai.chat import ChatOpenAI
    current_url = os.environ.get("LMSTUDIO_URL", LMSTUDIO_URL)
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=current_url,
        api_key="lm-studio",
        temperature=0.2,
        timeout=200.0,
        max_retries=2
    )


class BrowserTool:
    """
    browser-use Agent tabanlı web gezinme aracı (v0.11.x ve v0.12.x uyumlu).

    Her search() / extract_page() çağrısı:
      1. browser-use Agent oluşturur
      2. Görevi doğal dil olarak verir
      3. agent.run() → result.final_result() okur
      4. JSON parse eder
    """

    def __init__(self, llm=None, headless: bool = True):
        self._llm = llm
        self.headless = headless
        self.visited_urls: set = set()
        self._initialized = False
        self._browser = None

    async def initialize(self):
        """browser-use'un import edilebilir olduğunu doğrula."""
        try:
            from browser_use import Agent, Browser
            if self._llm is None:
                self._llm = _build_default_llm()
            
            self._browser = None
            print(f"[BrowserTool] browser-use hazır (Headless: {self.headless})")
            self._initialized = True
        except ImportError as e:
            raise RuntimeError(
                f"browser-use yüklü değil veya import hatası: {e}\n"
                "`uv pip install browser-use` komutunu çalıştır."
            )

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _agent(self, task: str, max_steps: int = 15):
        """Verilen task için browser-use Agent döndürür."""
        from browser_use import Agent
        # llm_timeout / step_timeout browser-use 0.11.x'te desteklenmez
        return Agent(
            task=task,
            llm=self._llm,
            browser=self._new_browser(),
            max_steps=max_steps,
            use_vision=True,
            vision_detail_level="high",
        )

    def _new_browser(self):
        """Create a fresh browser session for each browser-use Agent run."""
        from browser_use import Browser

        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
        ] + (["--start-maximized"] if not self.headless else [])

        try:
            return Browser(
                headless=self.headless,
                disable_security=True,
                args=args,
                keep_alive=False,
            )
        except TypeError:
            from browser_use.browser.browser import BrowserConfig

            config = BrowserConfig(
                headless=self.headless,
                disable_security=True,
                extra_chromium_args=args,
            )
            return Browser(config=config)

    # ------------------------------------------------------------------
    # Arama
    # ------------------------------------------------------------------

    async def search(
        self, query: str, num_results: int = 8, engine: str = None
    ) -> List[Dict[str, str]]:
        """Arama yap, sonuçları döndür. 0 sonuç gelirse Bing'e fallback yapar."""
        engine = engine or DEFAULT_SEARCH_ENGINE
        if engine == "bing":
            return await self.search_bing(query, num_results)
        # DDG önce dene (CAPTCHA yok)
        results = await self.search_duckduckgo(query, num_results)
        if results:
            return results
        # DDG 0 sonuç → Bing fallback
        print(f"[BrowserTool] DDG 0 sonuç, Bing'e geçiliyor: {query}")
        return await self.search_bing(query, num_results)

    async def search_google(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        """Google yerine DDG'den başla — CAPTCHA riski yok."""
        print(f"[BrowserTool] Search (DDG): {query}")
        return await self.search_duckduckgo(query, num_results)

    async def search_duckduckgo(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] DuckDuckGo: {query}")
        encoded = query.replace(" ", "+")
        task = (
            f"Navigate directly to https://duckduckgo.com/?q={encoded} "
            f"and wait for the search results page to load.\n"
            f"DO NOT go to Google, Bing or any other search engine.\n"
            f"Collect the first {num_results} organic result links (skip ads and DDG internal links).\n"
            f"IMPORTANT: You MUST return ONLY a valid JSON array, nothing else:\n"
            f'[{{"title":"...","url":"https://...","snippet":"..."}}]'
        )
        return await self._run_search(task, query)

    async def search_bing(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] Bing: {query}")
        task = (
            f"Go to bing.com and search for: {query}\n"
            f"Collect the first {num_results} result links.\n"
            f"Return ONLY a JSON array like: "
            f'[{{"title":"...","url":"...","snippet":"..."}}]'
        )
        return await self._run_search(task, query)

    async def _run_search(self, task: str, query: str) -> List[Dict[str, str]]:
        try:
            agent  = self._agent(task, max_steps=12)
            result = await agent.run()
            raw    = result.final_result() or ""
            cleaned = self._sanitize_encoding(raw)
            return self._parse_search_results(cleaned)
        except Exception as e:
            print(f"[BrowserTool] Arama hatası ({query}): {e}")
            return []

    def _sanitize_encoding(self, text: str) -> str:
        """
        vLLM / Qwen tokenizer kaynaklı encoding bozulmalarını temizler.
        Örnek: T_rkiye → Türkiye, b_y_me → büyüme
        Strateji: escape sequence'leri decode etmeyi dene, çözemezsen olduğu gibi bırak.
        """
        if not text:
            return text
        # \n kaçışlarını gerçek newline'a çevir (bazen model escape eder)
        try:
            text = text.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass
        # Bozuk JSON escape'leri düzelt (\' → ')
        text = text.replace("\\'", "'").replace("\\\\", "\\")
        return text

    def _parse_search_results(self, raw: str) -> List[Dict[str, str]]:
        """JSON veya numaralı liste formatını parse eder."""
        # --- 1. Deneme: JSON array (greedy — tüm array'i yakala) ---
        match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", raw)
        if match:
            try:
                items = json.loads(match.group())
                if isinstance(items, list) and items:
                    return self._process_items(items)
            except json.JSONDecodeError:
                pass

        # --- 2. Deneme: \n kaçışlı JSON (agent bazen \n ile kaçırır) ---
        escaped_match = re.search(r"\\n\[\\n", raw)
        if escaped_match:
            try:
                unescaped = raw.encode('utf-8').decode('unicode_escape')
                inner = re.search(r"\[\s*\{[\s\S]*\}\s*\]", unescaped)
                if inner:
                    items = json.loads(inner.group())
                    if isinstance(items, list) and items:
                        return self._process_items(items)
            except Exception:
                pass

        # --- 3. Deneme: Tek JSON objesi ---
        match = re.search(r"\{[\s\S]*?\}", raw)
        if match:
            try:
                item = json.loads(match.group())
                if "url" in item:
                    return self._process_items([item])
            except json.JSONDecodeError:
                pass

        # --- 4. Deneme: Numaralı liste ("1. Title: ...\n   URL: ...\n   Snippet: ...") ---
        items = []
        blocks = re.split(r"\n?\d+\.\s+", raw)
        for block in blocks[1:]:  # ilk boş bloğu atla
            title_m   = re.search(r"Title:\s*(.+)", block)
            url_m     = re.search(r"URL:\s*(https?://\S+)", block)
            snippet_m = re.search(r"Snippet:\s*(.+)", block, re.DOTALL)
            if url_m:
                items.append({
                    "title":   (title_m.group(1).strip()   if title_m   else ""),
                    "url":     url_m.group(1).strip(),
                    "snippet": (snippet_m.group(1).strip() if snippet_m else "")[:300],
                })
        if items:
            return self._process_items(items)

        print(f"[BrowserTool] Sonuç parse hatası (Raw: {raw[:200]}...)")
        return []

    def _process_items(self, items: List[Any]) -> List[Dict[str, str]]:
        result = []
        for i in items:
            if not isinstance(i, dict):
                continue
            url = str(i.get("url", "")).strip()
            # Hallucinated / çok uzun URL'leri filtrele
            if not url.startswith("http") or len(url) > 300:
                continue
            result.append({
                "title":   str(i.get("title",   ""))[:200],
                "url":     url,
                "snippet": str(i.get("snippet", i.get("description", "")))[:400],
            })
        return result

    @staticmethod
    def filter_excluded_domains(
        items: List[Dict[str, str]], excluded_domains: List[str]
    ) -> List[Dict[str, str]]:
        """Filter results whose host matches a crawler-owned domain."""
        if not excluded_domains:
            return items

        filtered = []
        for item in items:
            host = urlparse(item.get("url", "")).netloc.lower().removeprefix("www.")
            if any(host == domain or host.endswith(f".{domain}") for domain in excluded_domains):
                continue
            filtered.append(item)
        return filtered


    # ------------------------------------------------------------------
    # Sayfa içeriği
    # ------------------------------------------------------------------

    async def extract_page(self, url: str) -> Dict[str, Any]:
        """URL'yi ziyaret et, makale içeriğini çıkar."""
        if url in self.visited_urls:
            return {"url": url, "error": "already_visited"}

        self.visited_urls.add(url)
        print(f"[BrowserTool] Extract: {url}")

        task = (
            f"Go to: {url}\n"
            f"Extract article information and return as JSON:\n"
            f"- title: page/article title\n"
            f"- content: full article text (minimum 200 chars)\n"
            f"- description: meta description or first paragraph\n"
            f"- main_image: URL of the primary image\n"
            f"- images: list of image URLs in the article (max 5)\n"
            f"If you see a captcha or cookie consent, dismiss it first.\n"
            f"Return ONLY valid JSON with fields: title, content, description, main_image, images"
        )

        try:
            agent  = self._agent(task, max_steps=12)
            result = await agent.run()
            raw    = result.final_result() or ""
            return self._parse_page(raw, url)
        except Exception as e:
            print(f"[BrowserTool] Extract hatası ({url}): {e}")
            return {"url": url, "error": str(e)}

    def _parse_page(self, raw: str, url: str) -> Dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group())
                return {
                    "url":         url,
                    "title":       data.get("title", ""),
                    "content":     data.get("content", ""),
                    "description": data.get("description", ""),
                    "media": {
                        "main_image":    data.get("main_image", ""),
                        "content_images": data.get("images", []),
                        "videos":        [],
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            except json.JSONDecodeError:
                pass
        # Fallback: raw text
        return {
            "url":         url,
            "title":       "",
            "content":     raw[:10_000],
            "description": "",
            "media":       {"main_image": "", "content_images": [], "videos": []},
            "timestamp":   datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Vision / CAPTCHA
    # ------------------------------------------------------------------

    async def take_screenshot(self) -> Optional[bytes]:
        """Return current browser screenshot bytes when browser-use exposes a session."""
        try:
            target = self._browser
            if target is None:
                return None

            session = getattr(target, "browser_session", target)
            if hasattr(session, "take_screenshot"):
                return await session.take_screenshot(full_page=False)

            if hasattr(session, "get_browser_state_summary"):
                state = await session.get_browser_state_summary(include_screenshot=True)
                if state.screenshot:
                    return base64.b64decode(state.screenshot)
        except Exception as e:
            print(f"[BrowserTool] Screenshot hatası: {e}")
            return None
        return None

    async def solve_captcha_with_vision(
        self, url: str, screenshot_bytes: bytes = None
    ) -> Dict[str, Any]:
        """Captcha varsa browser-use agent'a çözdür."""
        task = (
            f"Go to {url}\n"
            f"If there is a CAPTCHA or cookie consent, solve/dismiss it.\n"
            f"Then extract: title, content, main_image as JSON."
        )
        try:
            agent  = self._agent(task, max_steps=15)
            result = await agent.run()
            raw    = result.final_result() or ""
            return self._parse_page(raw, url)
        except Exception as e:
            return {"url": url, "error": f"captcha_failed: {e}"}

    async def close(self):
        """Tarayıcıyı ve oluşturulan kaynakları kapatır."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                print(f"[BrowserTool] Browser kapatılırken hata: {e}")
            finally:
                self._browser = None
        
        # httpx vs. gibi arka planda askıda kalan kısımlar için
        print("[BrowserTool] Kapatıldı")
