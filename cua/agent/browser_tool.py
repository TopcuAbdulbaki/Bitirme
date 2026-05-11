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
import xml.etree.ElementTree as ET
from html import unescape
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from cua.config import (
    CUA_LLM_MAX_COMPLETION_TOKENS,
    DEFAULT_SEARCH_ENGINE,
    LMSTUDIO_API_KEY,
    LMSTUDIO_URL,
    MODEL_NAME,
)


def _build_default_llm():
    """browser-use'un native ChatOpenAI ile LM Studio / vLLM bağlantısı."""
    from browser_use.llm.openai.chat import ChatOpenAI
    current_url = os.environ.get("LMSTUDIO_URL", LMSTUDIO_URL)
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=current_url,
        api_key=LMSTUDIO_API_KEY,
        temperature=0.2,
        timeout=200.0,
        max_retries=2,
        max_completion_tokens=CUA_LLM_MAX_COMPLETION_TOKENS,
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
        """Search according to engine policy.

        duckduckgo uses visible/browser-use navigation when headless is false.
        auto keeps HTTP/RSS fallback available for unattended runs.
        """
        engine = engine or DEFAULT_SEARCH_ENGINE
        engine = engine.lower()
        if engine == "bing":
            return await self.search_bing(query, num_results)
        if engine == "auto":
            results = await self.search_duckduckgo(query, num_results)
            if results:
                return results

            print(f"[BrowserTool] DDG 0 sonuç, DDG HTTP deneniyor: {query}")
            results = await self.search_duckduckgo_http(query, num_results)
            if results:
                return results

            print(f"[BrowserTool] DDG HTTP 0 sonuç, Bing RSS'e geçiliyor: {query}")
            return await self.search_bing(query, num_results)

        return await self.search_duckduckgo(query, num_results)

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
        return await self._playwright_duckduckgo_search(query, num_results)

    async def search_duckduckgo_agent(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        """Legacy browser-use search path. Kept for debugging, not default."""
        encoded = query.replace(" ", "+")
        task = (
            f"Your FIRST browser action MUST be navigate to https://duckduckgo.com/?q={encoded}.\n"
            f"Do not wait before navigating. After navigating, wait at most once for 3 seconds.\n"
            f"DO NOT go to Google, Bing or any other search engine.\n"
            f"If you see a CAPTCHA, human verification, empty page, or anti-bot challenge, stop immediately and return [] only.\n"
            f"Do not try to solve CAPTCHA. Do not keep waiting after the page is still empty.\n"
            f"Collect the first {num_results} organic NEWS ARTICLE result links (skip ads, DDG internal links, encyclopedias, statistics pages, and country profile pages).\n"
            f"IMPORTANT: You MUST return ONLY a valid JSON array, nothing else:\n"
            f'[{{"title":"...","url":"https://...","snippet":"..."}}]'
        )
        return await self._run_search(task, query)

    async def _playwright_duckduckgo_search(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        """Visible, deterministic DuckDuckGo browser search.

        browser-use can decide to wait on about:blank before navigating. Search is
        a bounded tool action, so drive navigation directly and keep LLM agency
        for query choice, URL choice, extraction and synthesis.
        """
        from playwright.async_api import async_playwright

        browser = None
        playwright = None
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            page = await browser.new_page(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                ),
                locale="en-US",
            )
            url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            body_text = (await page.locator("body").inner_text(timeout=5000)).lower()
            if self._looks_like_captcha(body_text):
                print("[BrowserTool] DuckDuckGo CAPTCHA/challenge detected")
                return []

            items = await page.evaluate(
                """(limit) => {
                    const anchors = Array.from(document.querySelectorAll('a'));
                    const rows = [];
                    for (const a of anchors) {
                        const href = a.href || '';
                        const title = (a.innerText || '').replace(/\\s+/g, ' ').trim();
                        if (!href.startsWith('http') || title.length < 8) continue;
                        const host = new URL(href).hostname.replace(/^www\\./, '');
                        if (host.includes('duckduckgo.com')) continue;
                        const container = a.closest('article, div, li') || a.parentElement;
                        const snippet = container ? (container.innerText || '').replace(/\\s+/g, ' ').trim() : '';
                        rows.push({ title, url: href, snippet });
                        if (rows.length >= limit) break;
                    }
                    return rows;
                }""",
                num_results * 2,
            )
            return self._dedupe_results(self._process_items(items), num_results)
        except Exception as e:
            print(f"[BrowserTool] DuckDuckGo Playwright search error ({query}): {e}")
            return []
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    async def search_duckduckgo_http(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] DuckDuckGo HTTP: {query}")
        try:
            html = await self._fetch_text(
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            )
            if self._looks_like_captcha(html):
                print("[BrowserTool] DuckDuckGo CAPTCHA/challenge detected, skipping browser retry")
                return []
            return self._dedupe_results(self._parse_duckduckgo_html(html), num_results)
        except Exception as e:
            print(f"[BrowserTool] DuckDuckGo HTTP search error ({query}): {e}")
            return []

    async def search_bing(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] Bing: {query}")
        try:
            rss = await self._fetch_text(
                f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss"
            )
            return self._dedupe_results(self._parse_bing_news_rss(rss), num_results)
        except Exception as e:
            print(f"[BrowserTool] Bing RSS search error ({query}): {e}")
            return []

    async def _fetch_text(self, url: str) -> str:
        import aiohttp

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        }
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                return await response.text(errors="ignore")

    def _looks_like_captcha(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(marker in lowered for marker in [
            "captcha",
            "challenge",
            "select all squares",
            "anomaly",
            "verify you are human",
        ])

    def _parse_duckduckgo_html(self, html: str) -> List[Dict[str, str]]:
        items = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        matches = list(pattern.finditer(html or ""))
        for idx, match in enumerate(matches):
            raw_url = unescape(match.group(1))
            title = self._strip_html(match.group(2))
            snippet = ""
            next_start = match.end()
            next_end = matches[idx + 1].start() if idx + 1 < len(matches) else next_start + 2000
            block = html[next_start:next_end]
            snippet_match = re.search(
                r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|'
                r'<div[^>]+class="result__snippet"[^>]*>(.*?)</div>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if snippet_match:
                snippet = self._strip_html(snippet_match.group(1) or snippet_match.group(2) or "")
            url = self._clean_result_url(raw_url)
            if url:
                items.append({"title": title, "url": url, "snippet": snippet})
        return self._process_items(items)

    def _parse_bing_news_rss(self, rss: str) -> List[Dict[str, str]]:
        items = []
        root = ET.fromstring(rss)
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            url = item.findtext("link") or ""
            snippet = item.findtext("description") or ""
            cleaned_url = self._clean_result_url(url)
            if cleaned_url:
                items.append({
                    "title": self._strip_html(title),
                    "url": cleaned_url,
                    "snippet": self._strip_html(snippet),
                })
        return self._process_items(items)

    def _clean_result_url(self, raw_url: str) -> str:
        url = unescape((raw_url or "").strip())
        if not url:
            return ""
        if url.startswith("//"):
            url = "https:" + url

        parsed = urlparse(url)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            url = unquote(target)

        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if parsed.scheme not in {"http", "https"}:
            return ""
        if any(domain in host for domain in ["duckduckgo.com", "bing.com", "microsoft.com"]):
            return ""
        return url

    def _strip_html(self, text: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text or "", flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _dedupe_results(self, items: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        deduped = []
        seen = set()
        for item in items:
            url = item.get("url", "")
            key = url.split("#", 1)[0].rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    async def _run_search(self, task: str, query: str) -> List[Dict[str, str]]:
        try:
            agent  = self._agent(task, max_steps=8)
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
        if not (raw or "").strip():
            return []

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
            agent  = self._agent(task, max_steps=8)
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
