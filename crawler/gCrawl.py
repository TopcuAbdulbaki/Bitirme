import asyncio
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import json

# --- AYARLAR ---
TARGET_SITE = "bbc.com"
SEARCH_TERMS = "Turkey OR Türkiye OR Turkiye"
DAYS_BACK = 3 
KEYWORDS_TO_CHECK = ["türkiye", "turkiye"] # Anahtar kelimeleri artırdım

async def main_pipeline():
    google_url = f"https://www.google.com/search?q=site:{TARGET_SITE}+({SEARCH_TERMS})&tbs=qdr:d{DAYS_BACK}&hl=tr"
    
    print(f"🚀 {TARGET_SITE} taranıyor (Gelişmiş Mod)...")

    # headless=True yapabilirsin artık, regex modu stabil.
    browser_cfg = BrowserConfig(headless=True) 
    
    # Google araması için config
    search_run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for="css:div#search",
        delay_before_return_html=2.0, 
    )

    final_dataset = []

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        
        # --- ADIM 1: Google Linklerini Al ---
        print("⏳ Google taranıyor...")
        search_result = await crawler.arun(url=google_url, config=search_run_cfg)

        if not search_result.success:
            print("❌ Google açılamadı.")
            return

        html_content = search_result.html
        pattern = r'href=["\'](https?://[^"\']*bbc\.com[^"\']*)["\']'
        found_links = re.findall(pattern, html_content)

        candidate_links = []
        for link in found_links:
            if "/url?q=" in link:
                link = link.split("/url?q=")[1].split("&")[0]
            
            from urllib.parse import unquote
            link = unquote(link)

            # FİLTRE: Sadece gerçek makaleleri al, '/topics/', '/avaz/' vb. at
            if ("bbc.com" in link and 
                "google.com" not in link and 
                "/topics/" not in link and  # Kategori sayfalarını at
                "/brand/" not in link and   # Reklam sayfalarını at
                "webcache" not in link):
                candidate_links.append(link)

        candidate_links = list(set(candidate_links))
        print(f"🔎 {len(candidate_links)} adet potansiyel HABER linki bulundu.\n")

        # --- ADIM 2: İçerik Çekme (Kurtarıcı Mod) ---
        for link in candidate_links:
            print(f"📄 İndiriliyor: {link}")
            
            # Makale sayfaları için özel config (Resimleri yükleme, hızlı olsun)
            article_run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED, # Varsa cache kullan
                exclude_external_links=True,
                exclude_social_media_links=True,
                # BBC metni genelde 'main' veya 'article' tagindedir, orayı bekle
                wait_for="css:main", 
            )

            article = await crawler.arun(url=link, config=article_run_cfg)
            
            if not article.success:
                print("   ❌ Erişim hatası.")
                continue

            # --- KADEMELİ METİN ALMA STRATEJİSİ ---
            clean_text = ""
            source_method = ""

            # YÖNTEM 1: Yeni Versiyon fit_markdown
            try:
                if hasattr(article.markdown, 'fit_markdown') and article.markdown.fit_markdown:
                    clean_text = article.markdown.fit_markdown
                    source_method = "Smart Fit"
            except:
                pass

            # YÖNTEM 2: Eğer Yöntem 1 boşsa, Ham Markdown al
            if len(clean_text) < 200:
                try:
                    # Nesne ise str() çevir, string ise direkt al
                    clean_text = str(article.markdown)
                    source_method = "Raw Markdown"
                except:
                    pass

            # YÖNTEM 3: O da yoksa HTML'den metin sök (BeautifulSoup tarzı basit temizlik)
            if len(clean_text) < 200:
                # Basit HTML tag temizliği (Regex ile)
                clean_text = re.sub(r'<[^>]+>', ' ', article.html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                source_method = "Raw HTML Scrape"

            # --- SON KONTROL ---
            if len(clean_text) < 200:
                print(f"   ⚠️ İçerik yine boş veya çok kısa ({len(clean_text)} karakter). Atlanıyor.")
                continue
            
            # İçerik bulundu, şimdi kelime kontrolü
            clean_text_lower = clean_text.lower()
            match_found = next((kw for kw in KEYWORDS_TO_CHECK if kw in clean_text_lower), None)

            if match_found:
                print(f"   ✅ ONAYLANDI ({source_method}). Bulunan kelime: '{match_found}'")
                final_dataset.append({
                    "url": link,
                    "content": clean_text[:5000] # LLM için çok uzun olmasın diye kesebilirsin
                })
            else:
                print(f"   ❌ Kelime eşleşmedi ({source_method}).")

    print(f"\n🎯 TOPLAM {len(final_dataset)} HABER BAŞARIYLA ÇEKİLDİ.")
    
    # İstersen kaydet
    if final_dataset:
        with open("bbc_haberler.json", "w", encoding="utf-8") as f:
            json.dump(final_dataset, f, ensure_ascii=False, indent=2)
        print("📁 Sonuçlar 'bbc_haberler.json' dosyasına kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main_pipeline())