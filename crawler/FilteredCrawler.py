import asyncio
import re
import json
import os
from datetime import datetime
from urllib.parse import unquote
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


# ⚙️ Configurations
Config = {
    "search_query": "Turkey OR Türkiye OR Turkiye",
    "days_back": 3,
    "required_keywords": ["turkey", "türkiye", "turkiye", "ankara", "istanbul", "turkish"],
    "max_images": 5  # Maximum images per article
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
        "block_paths": ["/topics/", "/avaz/", "/media/"]
    },
    {
        "name": "CNN International",
        "domain": "edition.cnn.com",
        "country": "united states",
        "block_paths": ["/videos/", "/gallery/", "/travel/", "/style/"]
    },
    {
        "name": "Al Jazeera",
        "domain": "aljazeera.com",
        "country": "qatar",
        "block_paths": ["/program/", "/author/", "/podcasts/", "/gallery/"]
    },
    {
        "name": "Ekathimerini",
        "domain": "ekathimerini.com",
        "country": "greece",
        "block_paths": ["/opinion/", "/multimedia/"]
    },
    {
        "name": "Greek Reporter",
        "domain": "greekreporter.com",
        "country": "greece",
        "block_paths": []
    },
    {
        "name": "Greek City Times",
        "domain": "greekcitytimes.com",
        "country": "greece",
        "block_paths": []
    },
    {
        "name": "Times of Israel",
        "domain": "timesofisrael.com",
        "country": "israel",
        "block_paths": ["/liveblog/"]
    },
    {
        "name": "Haaretz",
        "domain": "haaretz.com",
        "country": "israel",
        "block_paths": []
    },
    {
        "name": "Jerusalem Post",
        "domain": "jpost.com",
        "country": "israel",
        "block_paths": []
    },
    {
        "name": "Israel National News",
        "domain": "israelnationalnews.com",
        "country": "israel",
        "block_paths": []
    },
    {
        "name": "Iran International",
        "domain": "iranintl.com",
        "country": "iran",
        "block_paths": []
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
        self.run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        ) 
        self.browser_cfg = BrowserConfig(headless=True) 

    async def fetch_google_links(self, crawler, source):
        """Fetches links from Google for a specific site.
        
        Args:
            crawler (AsyncWebCrawler): The crawler instance.
            source (dict): The source dictionary containing the source name, domain, country and block paths.
        
        Returns:
            list: A list of links fetched from Google.
        """
        
        print(f"\n🌍 {source['name']} ({source['domain']}) taranıyor...")
        
        google_url = (
            f"https://www.google.com/search?"
            f"q=site:{source['domain']}+({Config['search_query']})"
            f"&tbs=qdr:d{Config['days_back']}&hl=tr"
        )

        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for="css:div#search",
            delay_before_return_html=2.0
        )

        try:
            result = await crawler.arun(url=google_url, config=run_cfg)
        except Exception as e:
            print(f"   ❌ Google Arama Hatası: {e}")
            return []
        
        if not result.success:
            print(f"   ❌ {source['name']} için Google yanıt vermedi.")
            return []

        # Find links with regex
        domain_escaped = re.escape(source['domain'])
        pattern = fr'href=["\'](https?://[^"\']*{domain_escaped}[^"\']*)["\']'
        
        found_links = re.findall(pattern, result.html)
        
        clean_links = []
        all_blocked = GLOBAL_BLOCK_PATHS + source.get('block_paths', [])

        for link in found_links:
            if "/url?q=" in link:
                link = link.split("/url?q=")[1].split("&")[0]
            
            link = unquote(link)

            if "google.com" not in link and "webcache" not in link:
                is_blocked = any(blocked in link for blocked in all_blocked)
                if not is_blocked:
                    clean_links.append(link)

        unique_links = list(set(clean_links))
        print(f"   🔎 {len(unique_links)} adet aday link bulundu.")
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

    def _extract_image_size(self, img_url):
        """Extracts image size from URL path or returns 0 if not found.
        
        Args:
            img_url (str): The image URL to analyze.
        
        Returns:
            int: The size value found in URL, or 0 if not determinable.
        """
        # Pattern 1: /240/, /320/, /480/, /640/, /800/, /1024/ etc.
        path_size_match = re.search(r'/(\d{2,4})/', img_url)
        if path_size_match:
            return int(path_size_match.group(1))
        
        # Pattern 2: image-300x200.jpg, image_640x480.png
        dimension_match = re.search(r'[-_](\d+)x(\d+)\.(jpg|jpeg|png|webp)', img_url, re.IGNORECASE)
        if dimension_match:
            width = int(dimension_match.group(1))
            return width
        
        # Pattern 3: Query parameters (?width=800, ?w=640)
        query_match = re.search(r'[?&](width|w)=(\d+)', img_url)
        if query_match:
            return int(query_match.group(2))
        
        return 0

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

    def _extract_media_content(self, article):
        """Extracts and filters media content (images and videos) from article.
        
        Args:
            article: The Crawl4AI article result object.
        
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
                
                # Dictionary to track best version of each image
                # Key: normalized_url, Value: {'url': actual_url, 'size': size_value}
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
                    
                    # Extract size from URL
                    size = self._extract_image_size(src)
                    
                    # Keep only the largest version of each image
                    if normalized_url not in image_versions:
                        image_versions[normalized_url] = {'url': src, 'size': size}
                    else:
                        # If current image is larger, replace it
                        if size > image_versions[normalized_url]['size']:
                            image_versions[normalized_url] = {'url': src, 'size': size}
                
                # Filter out main image and convert to list
                for normalized_url, img_data in image_versions.items():
                    actual_url = img_data['url']
                    
                    # Skip main image
                    if media_content['main_image']:
                        normalized_main = self._normalize_image_url(media_content['main_image'])
                        if normalized_url == normalized_main:
                            continue
                    
                    media_content['content_images'].append(actual_url)
                    
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

    async def verify_and_extract(self, crawler, url, source_name):
        """Opens the link, downloads the content, extracts the media and verifies it.
        
        Args:
            crawler (AsyncWebCrawler): The crawler instance.
            url (str): The URL to open.
            source_name (str): The name of the source.
        
        Returns:
            dict: The extracted content.
        """
        
        # Pre-validation: Skip obvious non-article URLs
        if any(url.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".zip", ".xls"]):
            return None

        if url.count('/') < 4:
            return None
        
        print(f"   📄 İndiriliyor: {url}")
        
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            exclude_external_links=True,
            excluded_tags=['nav', 'header', 'footer', 'aside', 'script', 'style', 'form', 'iframe'],
            remove_overlay_elements=True,
            js_code="window.scrollTo(0, document.body.scrollHeight);",
            delay_before_return_html=2.5,
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

        # Extract media content
        media_content = self._extract_media_content(article)
        
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
            print(f"      ❌ İLGİSİZ")
            return None

    async def run(self):
        """Main execution method that orchestrates the crawling process."""
        print(f"🚀 ÇOKLU TARAMA BAŞLATILIYOR ({len(SOURCES)} Site)...")
        
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
            for source in SOURCES:
                links = await self.fetch_google_links(crawler, source)
                
                for link in links:
                    data = await self.verify_and_extract(crawler, link, source['name'])
                    if data:
                        self.results.append(data)
                
                await asyncio.sleep(2)

        self.save_results()

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