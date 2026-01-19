import asyncio
import re
import json
import os
import random  # Magic mod için eklendi
import aiohttp
from PIL import Image
from io import BytesIO
from datetime import datetime
from urllib.parse import unquote
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Distributed mode imports
# try:
from crawler.config import CRAWLER_MODE, CRAWLER_DEMO_MODE, CRAWLER_DEMO_LIMIT, POLL_INTERVAL
from crawler.services.grpc_client import GRPCClient, NodeStatus
# GRPCServer no longer needed - using poll model
DISTRIBUTED_AVAILABLE = True
# except ImportError:
#     DISTRIBUTED_AVAILABLE = False
#     CRAWLER_MODE = 'standalone'


# ⚙️ Configurations
Config = {
    "search_query": "Turkey OR Türkiye OR Turkiye",
    "time_unit": "h",    # h=hour, d=day, w=week, m=month
    "time_value": 1,     # e.g., 1 hour, 6 hours, 1 day, 3 days
    "required_keywords": ["turkey", "türkiye", "turkiye", "ankara", "istanbul", "turkish"],
    "max_images": 3  # Maximum images per article
}


# Global Block List 
GLOBAL_BLOCK_PATHS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", 
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".avi", ".mov", ".jpg", ".jpeg", ".png", ".gif",
    
    # --- Media and Gallery ---
    "/video/", "/videos/", "/tv/", "/watch/", 
    "/gallery/", "/photos/", "/images/", "/multimedia/",
    "/podcasts/", "/audio/", 
    
    # --- Technical and System ---
    "/search/", "/search;query", "/results/", 
    "/login/", "/signin/", "/register/", "/auth/", "/premium/",
    "/rss/", "/feed/", "/xml/", "/json/",
    "/newsletter/", "/subscribe/",
    
    # --- Unnecessary Pages ---
    "/author/", "/authors/", "/profile/", "/user/",
    "/tag/", "/topic/", "/category/", "/archive/",
    "/ads/", "/advertising/", "/advertisement/",
    "/comment/", "/comments/",
    "/print/", "/printarticle",
]


# Sources
SOURCES = [
    {
        "name": "BBC",
        "domain": "bbc.com",
        "country": "united kingdom",
        "block_paths": ["/topics/", "/avaz/", "/media/"],
        "allowed_paths": []
    },
    {
        "name": "CNN International",
        "domain": "edition.cnn.com",
        "country": "united states",
        "block_paths": ["/videos/", "/gallery/", "/travel/", "/style/"],
        "allowed_paths": []
    },
    {
        "name": "Al Jazeera",
        "domain": "aljazeera.com",
        "country": "qatar",
        "block_paths": ["/program/", "/author/", "/podcasts/", "/gallery/"],
        "allowed_paths": []
    },
    {
        "name": "Ekathimerini",
        "domain": "ekathimerini.com",
        "country": "greece",
        "block_paths": ["/opinion/", "/multimedia/"],
        "allowed_paths": []
    },
    {
        "name": "Greek Reporter",
        "domain": "greekreporter.com",
        "country": "greece",
        "block_paths": [],
        "allowed_paths": []
    },
    {
        "name": "Greek City Times",
        "domain": "greekcitytimes.com",
        "country": "greece",
        "block_paths": [],
        "allowed_paths": []
    },
    {
        "name": "Times of Israel",
        "domain": "timesofisrael.com",
        "country": "israel",
        "block_paths": ["/liveblog/"],
        "allowed_paths": []
    },
    {
        "name": "Haaretz",
        "domain": "haaretz.com",
        "country": "israel",
        "block_paths": [],
        "allowed_paths": []
    },
    {
        "name": "Jerusalem Post",
        "domain": "jpost.com",
        "country": "israel",
        "block_paths": [],
        "allowed_paths": []
    },
    {
        "name": "Israel National News",
        "domain": "israelnationalnews.com",
        "country": "israel",
        "block_paths": [],
        "allowed_paths": []
    },
    {
        "name": "Iran International",
        "domain": "iranintl.com",
        "country": "iran",
        "block_paths": [],
        "allowed_paths": []
    }
]


# 🕷️ Modular Crawler Class
class NewsCrawler:
    """Modular Crawler Class for NewsCrawler.
        Attributes:
            results (list): List of results.
            run_cfg (CrawlerRunConfig): Crawler run configuration.
            browser_cfg (BrowserConfig): Browser configuration.
    """

    def __init__(self):
        """Initialize the NewsCrawler with default configurations."""
        self.results = []
        # Semaphore paralellik limitini belirler (Aynı anda 3 sekme)
        self.semaphore = asyncio.Semaphore(3) 
        
        # gRPC client for distributed mode
        self.grpc_client = None
        if DISTRIBUTED_AVAILABLE and CRAWLER_MODE == 'distributed':
            self.grpc_client = GRPCClient()
        
        # 🪄 DÜZELTME: 'user_agent_generator' satırı kaldırıldı.
        self.browser_cfg = BrowserConfig(
            headless=True,
            verbose=False,
            user_agent_mode="random",  # Bu satır rastgele kimlik için yeterlidir
            viewport_width=1920,       
            viewport_height=1080,
            headers={
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Ch-Ua-Mobile": "?0",
            }
        )



    async def fetch_google_links(self, crawler, source):
        """Fetches links from Google for a specific site.
        
        Args:
            crawler (AsyncWebCrawler): The crawler instance.
            source (dict): The source dictionary containing the source name, domain, country and block paths.
        
        Returns:
            list: A list of links fetched from Google.
        """
        
        print(f"\n🌍 {source['name']} ({source['domain']}) taranıyor...")
        
        # Build time filter: qdr:h1, qdr:d3, qdr:w, etc.
        time_filter = f"qdr:{Config['time_unit']}{Config['time_value']}"
        
        google_url = (
            f"https://www.google.com/search?"
            f"q=site:{source['domain']}+({Config['search_query']})"
            f"&tbs={time_filter}&hl=tr&num=20"
        )

        # 🪄 MAGIC UPDATE: Google bot korumasını aşmak için özel ayarlar
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            magic=True,              # Anti-bot tespiti aç
            simulate_user=True,      # Mouse ve scroll simülasyonu
            override_navigator=True, # Bot bayrağını gizle
            wait_for="css:body",     # #search yerine body beklemek daha güvenli
            js_code="window.scrollTo(0, document.body.scrollHeight);",
            delay_before_return_html=random.uniform(4,5) # Rastgele bekleme
        )

        try:
            result = await crawler.arun(url=google_url, config=run_cfg)
        except Exception as e:
            print(f"   ❌ Google Arama Hatası: {e}")
            return []
        
        if not result.success:
            print(f"   ❌ {source['name']} için Google yanıt vermedi.")
            return []

        # Find links with regex (Güncellenmiş Regex)
        domain_escaped = re.escape(source['domain'])
        pattern = fr'href=["\'].*?(https?://[^"\']*{domain_escaped}[^"\']*)["\']'
        
        found_links = re.findall(pattern, result.html)
        
        clean_links = []
        all_blocked = GLOBAL_BLOCK_PATHS + source.get('block_paths', [])
        source_allowed_paths = source.get('allowed_paths', [])

        for link in found_links:
            if "/url?q=" in link:
                link = link.split("/url?q=")[1].split("&")[0]
            
            link = unquote(link)

            if "google.com" not in link and "webcache" not in link:
                is_blocked = any(blocked in link for blocked in all_blocked)
                if not is_blocked or any(allowed in link for allowed in source_allowed_paths):
                    clean_links.append(link)

        unique_links = list(set(clean_links))
        print(f"   🔎 {len(unique_links)} adet aday link bulundu.")
        
        # 🪄 MAGIC UPDATE: Google araması sonrası kısa bekleme
        await asyncio.sleep(random.uniform(1.5, 2.0))
        
        return unique_links

    def _is_valid_content_image(self, img_url, img_data=None):
        """Validates if an image is suitable for content (not icon/logo/ad).
        
        Args:
            img_url (str): The image URL to validate.
            img_data (dict, optional): Additional image metadata (score, dimensions).
        
        Returns:
            bool: True if the image is valid content, False otherwise.
        """
        if not img_url or len(img_url) < 20:
            return False
        
        img_lower = img_url.lower()
        
        # Filter 1: File extensions (exclude icons and animations)
        if any(ext in img_lower for ext in ['.svg', '.gif', '.ico', 'data:image/svg']):
            return False
        
        # Filter 2: Blocked keywords in URL
        blocked_keywords = [
            'logo', 'icon', 'avatar', 'sprite', 'emoji',
            'banner', 'ad-', 'advert', 'promo', 
            'button', 'arrow', 'play', 'pause',
            'thumb', 'thumbnail', '-thumb.',
            'placeholder', 'loading', 'spinner',
            'facebook', 'twitter', 'social', 'share',
            'pixel', 'tracker', '1x1',
            'header', 'footer', 'menu', 'nav'
        ]
        if any(keyword in img_lower for keyword in blocked_keywords):
            return False
        
        # Filter 3: BBC-specific size filtering (80, 100, 240 = thumbnails)
        if 'bbc.co' in img_lower:
            if any(f'/{size}/' in img_url for size in ['80', '100', '240']):
                return False
        
        # Filter 4: Check image score if available (Crawl4AI feature)
        if img_data and img_data.get('score', 0) < 3:
            return False
        
        return True

    async def _get_remote_image_size(self, session, url):
        """Fetches image size using a shared session.
        
        Args:
            session (aiohttp.ClientSession): The session to use for fetching.
            url (str): The URL of the image.
        
        Returns:
            tuple: (width, height)
        """
        try:
            async with session.get(url, timeout=5) as response:
                if response.status != 200:
                    return 0, 0
                data = await response.read()
                img = Image.open(BytesIO(data))
                return img.width, img.height
        except Exception:
            return 0, 0

    def _extract_main_image(self, html):
        """Extracts the main/hero image from Open Graph meta tags.
        
        Args:
            html (str): The HTML content to parse.
        
        Returns:
            str or None: The main image URL or None if not found.
        """
        og_patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']'
        ]
        
        for pattern in og_patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        
        return None

    def _calculate_image_importance(self, img_data):
        """Calculates image importance based on display dimensions.
        
        Args:
            img_data (dict): Image data from Crawl4AI containing width, height, score.
        
        Returns:
            int: Importance score (width × height), or 0 if dimensions unavailable.
        """
        width = img_data.get('width', 0)
        height = img_data.get('height', 0)
        
        # Convert string dimensions to int if needed
        try:
            if isinstance(width, str):
                width = int(width)
            if isinstance(height, str):
                height = int(height)
        except (ValueError, TypeError):
            width, height = 0, 0
        
        # Calculate area (importance)
        if width > 0 and height > 0:
            return width * height
        
        # Fallback: Use Crawl4AI's scoring system
        return img_data.get('score', 0) * 10000

    def _normalize_image_url(self, img_url):
        """Normalizes image URL by removing size variations and query parameters.
        
        Examples:
            /news/240/cpsprodpb/abc123.jpg -> /news/cpsprodpb/abc123.jpg
            image.jpg?width=800&height=600 -> image.jpg
        
        Args:
            img_url (str): The image URL to normalize.
        
        Returns:
            str: Normalized URL for duplicate detection.
        """
        # Remove query parameters
        base_url = img_url.split('?')[0]
        
        # Remove common size patterns in URL paths
        normalized = re.sub(r'/\d{2,4}/', '/', base_url)
        
        # Remove size suffixes before extension
        normalized = re.sub(r'[-_](thumb|small|medium|large|full|\d+x\d+)\.(jpg|jpeg|png|webp)', r'.\2', normalized, flags=re.IGNORECASE)
        
        return normalized

    async def _extract_media_content(self, article, session):
        """Extracts and filters media content (images and videos) from article.
        
        Args:
            article: The Crawl4AI article result object.
            session: Shared aiohttp session for size check.
        
        Returns:
            dict: Filtered media content with main_image, content_images, and videos.
        """
        media_content = {
            "main_image": None,
            "content_images": [],
            "videos": []
        }
        
        try:
            # Step 1: Extract main/hero image
            media_content['main_image'] = self._extract_main_image(article.html)
            
            # Step 2: Extract content images from Crawl4AI media object
            if hasattr(article, 'media') and article.media:
                raw_images = article.media.get('images', [])
                
                # Dictionary to track largest displayed version of each image
                image_versions = {}
                
                for img in raw_images:
                    src = img.get('src', '')
                    
                    if not src or len(src) < 20:
                        continue
                    
                    # Apply validation filters first
                    if not self._is_valid_content_image(src, img):
                        continue
                    
                    # Normalize URL for grouping
                    normalized_url = self._normalize_image_url(src)
                    
                    # --- GÜNCELLENEN KISIM BAŞLANGIÇ ---
                    # Boyutları al ve kontrol et
                    w = img.get('width')
                    h = img.get('height')
                    
                    # Eğer boyut bilgisi yoksa veya None ise, shared session kullanarak öğren
                    if w is None or h is None:
                        w, h = await self._get_remote_image_size(session, src)
                    else:
                        # String gelirse int'e çevir, hata varsa 0 yap
                        try:
                            w, h = int(w), int(h)
                        except (ValueError, TypeError):
                            w, h = 0, 0
                    
                    # Önemi hesapla (Alan = Genişlik x Yükseklik)
                    importance = w * h
                    
                    # Çok küçük resimleri (örn: 50x50 altı) önem hesaplasak bile filtreleyelim
                    if importance < 2500: 
                        # Eğer boyut 0 geldiyse (bulunamadıysa) crawl4ai skoruna şans verelim
                        score = img.get('score', 0)
                        if score > 5: # Skor yüksekse yine de al
                            importance = score * 1000
                        else:
                            continue
                    # --- GÜNCELLENEN KISIM BİTİŞ ---
                    
                    # Keep only the largest displayed version of each image
                    if normalized_url not in image_versions:
                        image_versions[normalized_url] = {
                            'url': src,
                            'importance': importance,
                            'width': w,
                            'height': h
                        }
                    else:
                        # If current image is displayed larger, replace it
                        if importance > image_versions[normalized_url]['importance']:
                            image_versions[normalized_url] = {
                                'url': src,
                                'importance': importance,
                                'width': w,
                                'height': h
                            }
                
                # Sort by importance (largest first) and filter out main image
                sorted_images = sorted(
                    image_versions.items(),
                    key=lambda x: x[1]['importance'],
                    reverse=True
                )
                
                for normalized_url, img_data in sorted_images:
                    actual_url = img_data['url']
                    
                    # Skip main image
                    if media_content['main_image']:
                        normalized_main = self._normalize_image_url(media_content['main_image'])
                        if normalized_url == normalized_main:
                            continue
                    
                    media_content['content_images'].append(actual_url)
                    
                    # Debug: Show dimensions
                    w, h = img_data['width'], img_data['height']
                    importance = img_data['importance']
                    # print(f"        📐 Resim: {w}x{h} (Alan: {importance:,}px²)")
                    
                    # Limit reached
                    if len(media_content['content_images']) >= Config['max_images']:
                        break
                
                # Step 3: Extract videos
                media_content['videos'] = [
                    vid.get('src') for vid in article.media.get('videos', [])
                    if vid.get('src')
                ][:3]
        
        except Exception as e:
            print(f"      ⚠️ Medya çıkarma hatası: {e}")
        
        return media_content

    async def verify_and_extract(self, crawler, url, source_name, session):
        """Opens the link, downloads the content, extracts the media and verifies it.
        Uses semaphore for concurrency control and jitter for safety.
        
        Args:
            crawler: Crawler instance.
            url: Target URL.
            source_name: Name of source.
            session: Shared aiohttp session.
        """
        
        # 🛡️ GÜVENLİK: Semaphore ile eşzamanlı işlemi sınırla
        async with self.semaphore:
            
            # 🛡️ JITTER: Tüm sekmeler aynı anda açılmasın diye rastgele bekleme
            await asyncio.sleep(random.uniform(0.1, 1.2))

            # Pre-validation: Skip obvious non-article URLs
            if any(url.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".zip", ".xls"]):
                return None

            # 🪄 MAGIC UPDATE: URL kontrolünü biraz gevşettik (3 slash yeterli olabilir)
            if url.count('/') < 3:
                return None
            
            print(f"   📄 İndiriliyor: {url}")
            
            # 🪄 MAGIC UPDATE: İçerik çekme için magic ayarlar
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                magic=True,              # İçeriği okurken de insan gibi davran
                exclude_external_links=True,
                excluded_tags=['nav', 'header', 'footer', 'aside', 'script', 'style', 'form', 'iframe'],
                remove_overlay_elements=True, # Popup temizle
                js_code="window.scrollTo(0, document.body.scrollHeight);",
                delay_before_return_html=1.0, # Paralel olunca süreyi azıcık kısalttık
                wait_for="css:body",
                page_timeout=60000
            )

            try:
                article = await crawler.arun(url=url, config=run_cfg)
            except Exception as e:
                print(f"      ⚠️ Timeout/Hata: {str(e)[:50]}")
                return None

            if not article.success:
                return None

            # Extract media content (Passing the shared session)
            media_content = await self._extract_media_content(article, session)
            
            # Extract text content with fallback strategy
            clean_text = ""
            
            try:
                if hasattr(article, 'markdown') and hasattr(article.markdown, 'fit_markdown'):
                    clean_text = article.markdown.fit_markdown or ""
            except:
                pass

            if len(clean_text) < 200:
                try:
                    clean_text = str(article.markdown) if hasattr(article, 'markdown') else ""
                except:
                    pass
            
            if len(clean_text) < 200:
                clean_text = re.sub(r'<[^>]+>', ' ', article.html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            # Content validation
            if len(clean_text) < 200:
                return None

            # Keyword matching
            clean_text_lower = clean_text.lower()
            match = next((kw for kw in Config['required_keywords'] if kw in clean_text_lower), None)

            if match:
                img_count = len(media_content['content_images'])
                vid_count = len(media_content['videos'])
                
                print(f"      ✅ ONAYLANDI ('{match}') | 📸 {img_count} Resim | 🎥 {vid_count} Video")
                
                return {
                    "source": source_name,
                    "country": next((s['country'] for s in SOURCES if s['name'] == source_name), "Unknown"),
                    "url": url,
                    "keyword_found": match,
                    "scraped_at": datetime.now().isoformat(),
                    "content": clean_text[:5000],
                    "media": media_content 
                }
            else:
                # print(f"      ❌ İLGİSİZ")
                return None

    async def execute_crawl_task(self, specific_urls=None):
        """
        Triggered by Orchestrator via gRPC (or runs directly in standalone).
        Executes the crawling pipeline.
        """
        print(f"🚀 CRAWL TASK STARTED ({len(SOURCES)} Sources)...")
        if CRAWLER_DEMO_MODE:
             print(f"🧪 DEMO MODE ACTIVE: Will stop after {CRAWLER_DEMO_LIMIT} items.")
             
        # 🚀 OPTIMIZATION: Create shared session
        async with aiohttp.ClientSession() as session:
            async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
                
                # If specific URLs provided, logic could be here to filter sources
                # For now, we run the full source list
                
                for source in SOURCES:
                    # 1. Fetch Links
                    links = await self.fetch_google_links(crawler, source)
                    
                    if not links:
                        continue

                    # 2. Process Links Parallel
                    tasks = []
                    for link in links:
                        task = self.verify_and_extract(crawler, link, source['name'], session)
                        tasks.append(task)
                    
                    if tasks:
                        print(f"   ⚡ Processing {len(tasks)} items...")
                        results = await asyncio.gather(*tasks)
                        valid_results = [r for r in results if r]
                        
                        for news_item in valid_results:
                            # Send to Orchestrator (FIXED: check _stub instead of is_connected)
                            if self.grpc_client and self.grpc_client._stub:
                                self.grpc_client.send_crawl_result(news_item)
                            
                            self.results.append(news_item)
                            
                            # DEMO LIMIT CHECK
                            if CRAWLER_DEMO_MODE and len(self.results) >= CRAWLER_DEMO_LIMIT:
                                print(f"\n🛑 DEMO MODE LIMIT REACHED - Stopping...")
                                return # Exit function

                    if CRAWLER_DEMO_MODE and len(self.results) >= CRAWLER_DEMO_LIMIT:
                        return
                    
                    await asyncio.sleep(random.uniform(3, 6))
        
        self.save_results()
        print("✅ Crawl Task Complete")
    async def run(self):
        """Main execution method."""
        print("🤖 CRAWLER NODE INITIALIZING...")
        
        # Connect Client & Register (no server needed - poll model!)
        if self.grpc_client:
            if self.grpc_client.connect():
                self.grpc_client.register()
                self.grpc_client.set_status(NodeStatus.IDLE)
                print("[Crawler] Connected & Registered. Polling for tasks...")
            else:
                raise ConnectionError("Could not connect to Orchestrator in DISTRIBUTED mode.")
        else:
            # Standalone mode - just run once immediately
            print("[Crawler] Standalone Mode - Running immediately.")
            await self.execute_crawl_task()
            return

        # Start heartbeat in background
        self._heartbeat_task = asyncio.create_task(self.grpc_client.start_heartbeat_loop())
        
        # Poll loop - ask Orchestrator for work
        try:
            while True:
                # Poll for task
                has_task, task_id, urls, config_json = self.grpc_client.get_crawl_task()
                
                if has_task:
                    print(f"[Crawler] *** TASK RECEIVED: {task_id} ***")
                    self.grpc_client.set_status(NodeStatus.BUSY)
                    
                    # Execute the crawl
                    await self.execute_crawl_task(urls if urls else None)
                    
                    self.grpc_client.set_status(NodeStatus.IDLE)
                    print(f"[Crawler] *** TASK COMPLETE: {task_id} ***")
                
                await asyncio.sleep(POLL_INTERVAL)
                
        except asyncio.CancelledError:
            print("[Crawler] Stopping...")
        finally:
            self._heartbeat_task.cancel()
            if self.grpc_client:
                self.grpc_client.stop()


    def save_results(self):
        """Saves the scraped results to a JSON file."""
        if not self.results:
            print("\n⚠️ Hiçbir sonuç bulunamadı.")
            return

        filename = "toplanan_haberler.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎯 İŞLEM BİTTİ! Toplam {len(self.results)} haber '{filename}' dosyasına kaydedildi.")


# ==========================================
# ▶️ RUN
# ==========================================
if __name__ == "__main__":
    bot = NewsCrawler()
    asyncio.run(bot.run())