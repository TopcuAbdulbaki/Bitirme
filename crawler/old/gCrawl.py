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
    "required_keywords": ["turkey", "türkiye", "turkiye", "ankara", "istanbul", "turkish"]
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
            # Note: text_mode=False is legacy if you need to fast crawl make it True
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
        # Combine all blocked paths
        all_blocked = GLOBAL_BLOCK_PATHS + source.get('block_paths', [])

        for link in found_links:
            if "/url?q=" in link:
                link = link.split("/url?q=")[1].split("&")[0]
            
            link = unquote(link)

            # Filtreleme: Google değilse, webcache değilse ve yasaklı kelime yoksa
            if "google.com" not in link and "webcache" not in link:
                is_blocked = any(blocked in link for blocked in all_blocked)
                if not is_blocked:
                    clean_links.append(link)

        unique_links = list(set(clean_links))
        print(f"   🔎 {len(unique_links)} adet aday link bulundu.")
        return unique_links

    async def verify_and_extract(self, crawler, url, source_name):
        """Opens the link, downloads the content, extracts the media and verifies it.
        
        Args:
            crawler (AsyncWebCrawler): The crawler instance.
            url (str): The URL to open.
            source_name (str): The name of the source.
        
        Returns:
            dict: The extracted content.
        """
        
        # 1. Prevent PDF, DOC, DOCX, ZIP, XLS files
        if any(url.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".zip", ".xls"]):
            return None

        if url.count('/') < 4: return None
        
        print(f"   📄 İndiriliyor: {url}")
        
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            exclude_external_links=True,
            
            # Wait for Lazy Load Images
            js_code="window.scrollTo(0, document.body.scrollHeight);",
            
            # Wait for DOM to load
            delay_before_return_html=2.5,
            
            wait_for="css:body",
            # Timeout Protection: Cancel if no response in 15 seconds
            page_timeout=15000 
        )

        try:
            article = await crawler.arun(url=url, config=run_cfg)
        except Exception as e:
            print(f"      ⚠️ Timeout/Hata: {str(e)[:50]}")
            return None

        if not article.success:
            return None

        # --- NATIVE MEDIA EXTRACTION (Crawl4AI Feature) ---
       # --- SMART MEDIA EXTRACTION V2 (Daha Agresif Temizlik) ---
        media_content = { 
            "main_image": None, # En önemli resim buraya gelecek
            "content_images": [], # Yazı içindeki diğer resimler
            "videos": [] 
        }
        
        try:
            # 1. ADIM: Haber'in "Kapak Resmini" (og:image) Bul
            # Bu, sosyal medyada paylaşılan o büyük, güzel resimdir.
            import re
            og_match = re.search(r'<meta property=["\']og:image["\'] content=["\']([^"\']+)["\']', article.html)
            if og_match:
                media_content['main_image'] = og_match.group(1)
                print(f"      ⭐ Ana Resim Bulundu: {media_content['main_image'][:50]}...")

            # 2. ADIM: İçerik Resimlerini Filtrele
            if hasattr(article, 'media') and article.media:
                
                # Videoları al (Aynı kalıyor)
                media_content['videos'] = [
                    vid.get('src') for vid in article.media.get('videos', [])
                    if vid.get('src')
                ]

                raw_images = article.media.get('images', [])
                
                for img in raw_images:
                    src = img.get('src', '')
                    score = img.get('score', 0)
                    
                    if not src or len(src) < 20: continue
                    
                    # FİLTRE 1: Dosya Uzantıları (SVG ve GIF ikonlarını çöpe at)
                    # Haber resimleri genelde .jpg, .jpeg, .png veya .webp olur.
                    src_lower = src.lower()
                    if any(ext in src_lower for ext in ['.svg', '.gif', '.ico', 'data:image']): 
                        continue

                    # FİLTRE 2: Yasaklı Kelimeler
                    bad_words = [
                        'logo', 'icon', 'avatar', 'user', 'profile', # Kullanıcı/Site arayüzü
                        'button', 'arrow', 'play', 'pause', # Oynatıcı butonları
                        'ad-', 'advert', 'promo', # Reklamlar
                        'sprite', 'pixel', 'tracker', 'footer', 'header' # Teknik çöp
                    ]
                    if any(bad in src_lower for bad in bad_words): continue

                    # FİLTRE 3: Boyut Tahmini (BBC Özel)
                    # BBC linklerinde '100', '240' gibi genişlikler yazar. Çok küçükleri at.
                    # Örn: /news/240/cpsprodpb/... (Çok küçük)
                    if 'bbc.co' in src and ('/80/' in src or '/100/' in src or '/240/' in src):
                        continue

                    # FİLTRE 4: Ana resimle aynıysa tekrar ekleme
                    if media_content['main_image'] and src == media_content['main_image']:
                        continue

                    media_content['content_images'].append(src)

        except Exception as e:
            print(f"      ⚠️ Medya hatası: {e}")
        # --- TEXT EXTRACTION (Fallback Strategy) ---
        clean_text = ""
        
        # Method 1: Fit Markdown
        # If the article has a fit_markdown attribute, use it
        try:
            if hasattr(article.markdown, 'fit_markdown') and article.markdown.fit_markdown:
                clean_text = article.markdown.fit_markdown
        except:
            pass

        # Method 2: Raw Markdown
        # If the article has a markdown attribute, use it
        if len(clean_text) < 200:
            try:
                clean_text = str(article.markdown)
            except:
                pass
        
        # Method 3: HTML Regex Cleanup
        # If the article has an html attribute, use it
        if len(clean_text) < 200:
            clean_text = re.sub(r'<[^>]+>', ' ', article.html)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # Empty content check
        if len(clean_text) < 200:
            return None

        # --- Validation ---
        clean_text_lower = clean_text.lower()
        match = next((kw for kw in Config['required_keywords'] if kw in clean_text_lower), None)

        if match:
            # Log the number of images and videos
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
        print(f"🚀 ÇOKLU TARAMA BAŞLATILIYOR ({len(SOURCES)} Site)...")
        
        async with AsyncWebCrawler(config=self.browser_cfg) as crawler:
            for source in SOURCES:
                links = await self.fetch_google_links(crawler, source)
                
                for link in links:
                    data = await self.verify_and_extract(crawler, link, source['name'])
                    if data:
                        self.results.append(data)
                
                # Siteler arası kısa bekleme
                await asyncio.sleep(2)

        self.save_results()

    def save_results(self):
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