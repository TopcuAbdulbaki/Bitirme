"""
BrowserTool for CUA surface tasks.

The CUA agent keeps a single Playwright browser/page alive for the whole task.
Search and extraction are mechanical browser actions; LLMs decide query strategy
and produce analysis, not low-level browser actions.
"""
import json
import re
import os
import xml.etree.ElementTree as ET
from html import unescape
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from cua.config import DEFAULT_SEARCH_ENGINE


class BrowserTool:
    """Single-session browser tool for search and article extraction."""

    def __init__(self, llm=None, headless: bool = True):
        self._llm = llm
        self.headless = headless
        self._initialized = False
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._last_search_url = ""

    async def initialize(self):
        """Start one browser session for the task/node lifetime."""
        if self._initialized:
            return

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ] + (["--start-maximized"] if not self.headless else []),
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                ),
                locale="en-US",
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(15000)
            self._page.set_default_navigation_timeout(45000)
            print(f"[BrowserTool] Playwright hazır (Headless: {self.headless})")
            self._initialized = True
        except ImportError as e:
            raise RuntimeError(
                f"playwright yüklü değil veya import hatası: {e}\n"
                "`python -m playwright install chromium --with-deps` komutunu çalıştır."
            )

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_page(self):
        if not self._initialized or self._page is None:
            await self.initialize()
        return self._page

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self, query: str, num_results: int = 8, engine: str = None
    ) -> List[Dict[str, str]]:
        """Search according to engine policy."""
        engine = (engine or DEFAULT_SEARCH_ENGINE).lower()
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
        print(f"[BrowserTool] Search (DDG): {query}")
        return await self.search_duckduckgo(query, num_results)

    async def search_duckduckgo(
        self, query: str, num_results: int = 8
    ) -> List[Dict[str, str]]:
        """Visible deterministic DDG search on the persistent page."""
        print(f"[BrowserTool] DuckDuckGo: {query}")
        page = await self._ensure_page()
        try:
            url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
            self._last_search_url = url
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

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

    # ------------------------------------------------------------------
    # Article extraction
    # ------------------------------------------------------------------

    async def extract_page(self, url: str) -> Dict[str, Any]:
        """Visit URL on the persistent page and extract article data."""
        print(f"[BrowserTool] Extract: {url}")
        page = await self._ensure_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            status_code = response.status if response else 0
            await page.wait_for_timeout(2000)
            await self._dismiss_common_popups(page)
            await page.evaluate("window.scrollTo(0, Math.min(document.body.scrollHeight, 2400))")
            await page.wait_for_timeout(800)

            data = await page.evaluate(
                """() => {
                    const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                    const meta = (name) => {
                        const el = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
                        return el ? el.getAttribute('content') || '' : '';
                    };
                    const title =
                        clean(meta('og:title')) ||
                        clean(document.querySelector('h1')?.innerText) ||
                        clean(document.title);
                    const description =
                        clean(meta('og:description')) ||
                        clean(meta('description')) ||
                        clean(document.querySelector('article p, main p, p')?.innerText);
                    const articleRoot =
                        document.querySelector('article') ||
                        document.querySelector('main') ||
                        document.querySelector('[class*="article"], [class*="content"], [class*="post"]') ||
                        document.body;
                    const paragraphs = Array.from(articleRoot.querySelectorAll('p, h2, h3'))
                        .map((el) => clean(el.innerText))
                        .filter((text) => text.length > 40);
                    let content = paragraphs.join('\\n\\n');
                    if (content.length < 200) {
                        content = clean(articleRoot.innerText || document.body.innerText || '');
                    }
                    const imageCandidates = Array.from(articleRoot.querySelectorAll('img')).map((img) => {
                        const rect = img.getBoundingClientRect();
                        const parent = img.closest('figure, article, section, div') || img.parentElement;
                        return {
                            url: img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '',
                            alt: img.getAttribute('alt') || '',
                            title: img.getAttribute('title') || '',
                            width: Math.round(rect.width || img.naturalWidth || 0),
                            height: Math.round(rect.height || img.naturalHeight || 0),
                            natural_width: img.naturalWidth || 0,
                            natural_height: img.naturalHeight || 0,
                            class_name: img.className || '',
                            parent_class: parent?.className || '',
                            near_text: clean(parent?.innerText || '').slice(0, 300)
                        };
                    }).filter((img) => img.url && /^https?:/.test(img.url));
                    const articleLinks = Array.from(document.querySelectorAll('a[href]')).map((a) => {
                        const href = a.href || '';
                        const text = clean(a.innerText || a.getAttribute('aria-label') || '');
                        return { title: text, url: href, snippet: text };
                    }).filter((a) => a.url.startsWith('http') && a.title.length > 12);
                    return {
                        title,
                        content,
                        description,
                        main_image: meta('og:image') || meta('twitter:image') || '',
                        image_candidates: imageCandidates,
                        article_links: articleLinks,
                        paragraph_count: paragraphs.length,
                        body_text: clean(document.body.innerText || '').slice(0, 12000)
                    };
                }"""
            )

            media = self._select_media(data)
            article_links = self._extract_article_links(data.get("article_links", []), url)
            is_error_page = self._looks_like_error_page(data, status_code)
            is_article = not is_error_page and self._looks_like_article_page(data, article_links)
            result = {
                "url": url,
                "title": self._repair_text(data.get("title", "")),
                "content": self._repair_text(data.get("content", ""))[:50_000],
                "description": self._repair_text(data.get("description", "")),
                "media": media,
                "article_links": article_links,
                "is_article": is_article,
                "is_error_page": is_error_page,
                "http_status": status_code,
                "timestamp": datetime.now().isoformat(),
            }
            return result
        except Exception as e:
            print(f"[BrowserTool] Extract hatası ({url}): {e}")
            return {"url": url, "error": str(e)}
        finally:
            await self._return_to_search_page()

    async def _return_to_search_page(self):
        if not self._last_search_url:
            return
        try:
            page = await self._ensure_page()
            if page.url != self._last_search_url:
                await page.goto(self._last_search_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[BrowserTool] Search sayfasına dönülemedi: {e}")

    # ------------------------------------------------------------------
    # Media selection - mirrors crawler image filtering
    # ------------------------------------------------------------------

    def _select_media(self, data: Dict[str, Any]) -> Dict[str, Any]:
        main_image = self._clean_image_url(data.get("main_image", ""))
        if main_image and not self._is_valid_content_image(
            main_image,
            {"alt": data.get("title", ""), "title": data.get("title", ""), "class_name": ""},
        ):
            main_image = ""

        image_versions: Dict[str, Dict[str, Any]] = {}
        for img in data.get("image_candidates", []):
            src = self._clean_image_url(img.get("url", ""))
            if not self._is_valid_content_image(src, img):
                continue

            normalized = self._normalize_image_url(src)
            width, height = self._image_dimensions(img)
            importance = width * height
            if importance < 2500:
                continue

            existing = image_versions.get(normalized)
            if not existing or importance > existing["importance"]:
                image_versions[normalized] = {
                    "url": src,
                    "importance": importance,
                    "width": width,
                    "height": height,
                }

        main_normalized = self._normalize_image_url(main_image) if main_image else ""
        content_images = []
        for normalized, img_data in sorted(
            image_versions.items(),
            key=lambda item: item[1]["importance"],
            reverse=True,
        ):
            if main_normalized and normalized == main_normalized:
                continue
            content_images.append(img_data["url"])
            if len(content_images) >= 3:
                break

        if not main_image and content_images:
            main_image = content_images.pop(0)

        return {
            "main_image": main_image or "",
            "content_images": content_images,
            "videos": [],
        }

    def _is_valid_content_image(self, img_url: str, img_data: Dict[str, Any] = None) -> bool:
        if not img_url or len(img_url) < 20:
            return False

        img_lower = img_url.lower()
        if self._is_blocked_image_type(img_lower):
            return False

        blocked_keywords = [
            "logo", "icon", "avatar", "sprite", "emoji",
            "banner", "ad-", "advert", "promo",
            "button", "arrow", "play", "pause",
            "thumb", "thumbnail", "-thumb.",
            "150x150", "120x120", "100x100", "80x80",
            "placeholder", "loading", "spinner",
            "facebook", "twitter", "social", "share",
            "pixel", "tracker", "1x1",
            "header", "footer", "menu", "nav",
            "flag", "comment-input", "newsletter", "related",
            "sidebar", "popular", "recommended", "most-read",
        ]
        if any(keyword in img_lower for keyword in blocked_keywords):
            return False

        if img_data:
            text = " ".join([
                str(img_data.get("alt", "")),
                str(img_data.get("title", "")),
                str(img_data.get("class_name", "")),
                str(img_data.get("parent_class", "")),
                str(img_data.get("near_text", ""))[:120],
            ]).lower()
            if any(keyword in text for keyword in blocked_keywords):
                return False

        if "bbc.co" in img_lower and any(f"/{size}/" in img_url for size in ["80", "100", "240"]):
            return False

        return True

    def _is_blocked_image_type(self, img_url: str) -> bool:
        img_lower = (img_url or "").lower()
        return any(ext in img_lower for ext in [".svg", ".gif", ".ico", "data:image/svg"])

    def _image_dimensions(self, img_data: Dict[str, Any]) -> tuple[int, int]:
        for width_key, height_key in [("width", "height"), ("natural_width", "natural_height")]:
            try:
                width = int(img_data.get(width_key) or 0)
                height = int(img_data.get(height_key) or 0)
                if width > 0 and height > 0:
                    return width, height
            except (ValueError, TypeError):
                continue
        return 0, 0

    def _normalize_image_url(self, img_url: str) -> str:
        base_url = (img_url or "").split("?", 1)[0]
        normalized = re.sub(r"/\d{2,4}/", "/", base_url)
        normalized = re.sub(
            r"[-_](thumb|small|medium|large|full|\d+x\d+)\.(jpg|jpeg|png|webp)",
            r".\2",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized

    def _clean_image_url(self, url: str) -> str:
        url = unescape((url or "").strip())
        if url.startswith("//"):
            url = "https:" + url
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ""
        return url

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _dismiss_common_popups(self, page):
        labels = [
            "Accept", "I Accept", "Accept All", "Agree", "OK",
            "Got it", "Allow all", "Reject all", "Continue",
        ]
        for label in labels:
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I)).first
                if await button.count():
                    await button.click(timeout=1500)
                    await page.wait_for_timeout(300)
                    return
            except Exception:
                continue

    def _looks_like_captcha(self, text: str) -> bool:
        lowered = (text or "").lower()
        markers = [
            "captcha",
            "select all squares",
            "verify you are human",
            "unusual traffic",
            "anomaly detected",
            "are you a robot",
        ]
        return any(marker in lowered for marker in markers)

    def _looks_like_article_page(self, data: Dict[str, Any], article_links: List[Dict[str, str]]) -> bool:
        title = (data.get("title") or "").strip()
        content = (data.get("content") or "").strip()
        paragraph_count = int(data.get("paragraph_count") or 0)
        if not title or len(content) < 250 or paragraph_count < 2:
            return False
        if len(article_links) >= 8 and paragraph_count <= 3:
            return False
        return True

    def _looks_like_error_page(self, data: Dict[str, Any], status_code: int = 0) -> bool:
        title = (data.get("title") or "")
        content = (data.get("content") or "")
        body = (data.get("body_text") or "")
        text = f"{title}\n{content}\n{body}".lower()
        markers = [
            "web server is returning an unknown error",
            "origin is unreachable",
            "error code 520",
            "error code 521",
            "error code 522",
            "error code 523",
            "cloudflare ray id",
            "performance & security by cloudflare",
            "there is an unknown connection issue",
            "could not reach your host web server",
            "check your dns settings",
            "verify you are human",
            "human verification",
            "are you a robot",
            "captcha challenge",
            "complete the captcha",
            "solve captcha",
        ]
        if status_code >= 400:
            return True
        return any(marker in text for marker in markers)

    def _extract_article_links(self, links: List[Dict[str, str]], current_url: str) -> List[Dict[str, str]]:
        current_host = urlparse(current_url).netloc.lower().removeprefix("www.")
        processed = []
        seen = set()
        for link in links:
            url = self._clean_result_url(link.get("url", ""))
            if not url or url.rstrip("/") == current_url.rstrip("/"):
                continue
            host = urlparse(url).netloc.lower().removeprefix("www.")
            if current_host and host != current_host:
                continue
            if not self._looks_like_article_url(url):
                continue
            key = self.canonicalize_url(url)
            if key in seen:
                continue
            seen.add(key)
            processed.append({
                "title": self._repair_text(link.get("title", ""))[:200],
                "url": url,
                "snippet": self._repair_text(link.get("snippet", ""))[:400],
            })
            if len(processed) >= 12:
                break
        return processed

    def _looks_like_article_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        if not path or path in {"/", ""}:
            return False
        blocked = [
            "/tag/", "/tags/", "/category/", "/categories/", "/topic/", "/topics/",
            "/author/", "/authors/", "/search", "/video/", "/videos/", "/gallery/",
            "/photo/", "/photos/", "/live", "/weather", "/privacy", "/about",
        ]
        if any(part in path for part in blocked):
            return False
        return len([part for part in path.split("/") if part]) >= 2 or bool(re.search(r"\d{4,}", path))

    @staticmethod
    def canonicalize_url(url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(query="", fragment="").geturl().rstrip("/")

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
            key = self.canonicalize_url(url)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    def _process_items(self, items: List[Any]) -> List[Dict[str, str]]:
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = self._clean_result_url(str(item.get("url", "")).strip())
            if not url or len(url) > 500:
                continue
            result.append({
                "title": self._repair_text(str(item.get("title", "")))[:200],
                "url": url,
                "snippet": self._repair_text(str(item.get("snippet", item.get("description", ""))))[:400],
            })
        return result

    @staticmethod
    def filter_excluded_domains(
        items: List[Dict[str, str]], excluded_domains: List[str]
    ) -> List[Dict[str, str]]:
        if not excluded_domains:
            return items

        filtered = []
        for item in items:
            host = urlparse(item.get("url", "")).netloc.lower().removeprefix("www.")
            if any(host == domain or host.endswith(f".{domain}") for domain in excluded_domains):
                continue
            filtered.append(item)
        return filtered

    def _repair_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\\'", "'").replace("\\\\", "\\")
        if self._mojibake_score(text) > 0:
            candidates = [text]
            for encoding in ("latin1", "cp1252"):
                try:
                    candidates.append(text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore"))
                except Exception:
                    pass
            text = min(
                (candidate for candidate in candidates if len(candidate) >= len(text) * 0.6),
                key=lambda candidate: (self._mojibake_score(candidate), -len(candidate)),
                default=text,
            )
        return text.strip()

    @staticmethod
    def _mojibake_score(text: str) -> int:
        markers = ("Ã", "Ä", "Å", "Â", "â", "�")
        score = sum(text.count(marker) for marker in markers)
        score += len(re.findall(r"[\u0080-\u009f]", text)) * 3
        return score

    async def take_screenshot(self) -> Optional[bytes]:
        try:
            page = await self._ensure_page()
            return await page.screenshot(full_page=False)
        except Exception as e:
            print(f"[BrowserTool] Screenshot hatası: {e}")
            return None

    async def close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception as e:
                print(f"[BrowserTool] Context kapatılırken hata: {e}")
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                print(f"[BrowserTool] Browser kapatılırken hata: {e}")
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                print(f"[BrowserTool] Playwright kapatılırken hata: {e}")
        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None
        self._initialized = False
        print("[BrowserTool] Kapatıldı")
