"""
BrowserTool — browser-use 0.12.x uyumlu versiyon.

browser-use'un kendi ChatOpenAI wrapper'ı kullanılır (langchain değil).
Her search/extract işlemi için yeni bir Agent oluşturulur.
"""
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from cua.config import DEFAULT_SEARCH_ENGINE, LMSTUDIO_URL


def _build_default_llm():
    """browser-use'un native ChatOpenAI ile LM Studio bağlantısı."""
    from browser_use.llm.openai.chat import ChatOpenAI
    return ChatOpenAI(
        model="local-model",
        base_url=LMSTUDIO_URL,
        api_key="lm-studio",
        temperature=0.2,
        timeout=200.0,        # <-- Timeout süresini 75'ten 200 saniyeye çıkardık (Local model gecikmeleri için)
        max_retries=2
    )


class BrowserTool:
    """
    browser-use Agent tabanlı web gezinme aracı (v0.12.x uyumlu).

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
            # Browser parametreleri
            self._browser = Browser(
                headless=self.headless,
                channel="chrome",
                args=["--start-maximized"] if not self.headless else []
            )
            self._initialized = True
            print(f"[BrowserTool] browser-use hazır (v0.12.x) - Chrome Motoru (Headless: {self.headless})")
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
        return Agent(
            task=task,
            llm=self._llm,
            browser=self._browser,
            max_steps=max_steps,
            llm_timeout=600,
            step_timeout=600,  # <-- 300'den 600 saniyeye (10 dakika) çıkardık
        )

    # ------------------------------------------------------------------
    # Arama
    # ------------------------------------------------------------------

    async def search(
        self, query: str, num_results: int = 8, engine: str = None
    ) -> List[Dict[str, str]]:
        """Arama yap, sonuçları döndür."""
        engine = engine or DEFAULT_SEARCH_ENGINE
        if engine == "duckduckgo":
            return await self.search_duckduckgo(query, num_results)
        if engine == "bing":
            return await self.search_bing(query, num_results)
        return await self.search_google(query, num_results)

    async def search_google(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] Google: {query}")
        task = (
            f"Search for: {query}\n"
            f"You can use google.com or any alternative search engine if blocked.\n"
            f"Collect the first {num_results} organic result links.\n"
            f"Skip ads and internal domain links.\n"
            f"Return ONLY a JSON array like: "
            f'[{{"title":"...","url":"...","snippet":"..."}}]'
        )
        return await self._run_search(task, query)

    async def search_duckduckgo(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        print(f"[BrowserTool] DuckDuckGo: {query}")
        task = (
            f"Go to duckduckgo.com and search for: {query}\n"
            f"Collect the first {num_results} result links.\n"
            f"Return ONLY a JSON array like: "
            f'[{{"title":"...","url":"...","snippet":"..."}}]'
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
            # 10 adımda sonuç bulamazsa çok dağılmasın
            agent  = self._agent(task, max_steps=10)
            result = await agent.run()
            raw    = result.final_result() or ""
            return self._parse_search_results(raw)
        except Exception as e:
            print(f"[BrowserTool] Arama hatası ({query}): {e}")
            return []

    def _parse_search_results(self, raw: str) -> List[Dict[str, str]]:
        # En dıştaki [ ] bloğunu bulmaya çalış
        match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", raw)
        if not match:
            # Belki sadece { } dönmüştür, listeye saralım
            match = re.search(r"\{[\s\S]*\}", raw)
        
        if match:
            clean_json = match.group()
            # Bazen Türkçe karakterler _ olmuşsa JSON'ı bozabiliyor, düzelterek dene
            try:
                items = json.loads(clean_json)
                if isinstance(items, dict): items = [items]
                return self._process_items(items)
            except json.JSONDecodeError:
                # Son bir çaba: tırnak içindeki bozuklukları temizlemeyi dene
                try:
                    # Sadece yapısal olmayan alt çizgileri temizlemeyi dene (şüpheli bir işlem ama denemeye değer)
                    items = json.loads(clean_json.replace('"_', '"')) 
                    if isinstance(items, dict): items = [items]
                    return self._process_items(items)
                except: pass
                
        print(f"[BrowserTool] Sonuç parse hatası (Raw: {raw[:150]}...)")
        return []

    def _process_items(self, items: List[Any]) -> List[Dict[str, str]]:
        return [
            {
                "title":   str(i.get("title", "")).replace("_", ""),
                "url":     str(i.get("url", "")),
                "snippet": str(i.get("snippet", i.get("description", ""))).replace("_", ""),
            }
            for i in items if isinstance(i, dict) and i.get("url")
        ]

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
        """Screenshot almak için ayrı bir agent kullanılır."""
        try:
            task = "Take a screenshot of the current page and return the file path."
            agent  = self._agent(task, max_steps=3)
            result = await agent.run()
            # Screenshot bytes burada döndürülemez, None dönüyoruz
            # Captcha çözme görevi ayrı agent task'a devredilir
            return None
        except Exception:
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
