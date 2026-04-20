"""
ContentExtractor — browser-use Agent çıktısını Crawler uyumlu JSON'a dönüştürür.

Crawler node'unun ürettiği format birebir korunur; kaynak belirteci
`source_type='agent_surface'` olarak eklenir. Bu sayede downstream
VLM → LLM → DB pipeline'ı herhangi bir değişiklik gerektirmez.
"""
import hashlib
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse


# Bilinen haber kaynaklarına ülke eşlemesi
_DOMAIN_COUNTRY: Dict[str, str] = {
    "bbc.com":          "uk",
    "bbc.co.uk":        "uk",
    "reuters.com":      "us",
    "apnews.com":       "us",
    "ap.org":           "us",
    "nytimes.com":      "us",
    "washingtonpost.com": "us",
    "cnn.com":          "us",
    "foxnews.com":      "us",
    "theguardian.com":  "uk",
    "aljazeera.com":    "qa",
    "dw.com":           "de",
    "euronews.com":     "eu",
    "france24.com":     "fr",
    "lemonde.fr":       "fr",
    "spiegel.de":       "de",
    "nikkei.com":       "jp",
    "scmp.com":         "hk",
    "xinhuanet.com":    "cn",
    "globaltimes.cn":   "cn",
    "tass.com":         "ru",
    "rt.com":           "ru",
    "aa.com.tr":        "tr",
    "hurriyet.com.tr":  "tr",
    "milliyet.com.tr":  "tr",
    "sabah.com.tr":     "tr",
    "ntv.com.tr":       "tr",
    "haberturk.com":    "tr",
    "sozcu.com.tr":     "tr",
    "cumhuriyet.com.tr": "tr",
    "bloomberght.com":  "tr",
    "bloomberg.com":    "us",
    "ft.com":           "uk",
    "wsj.com":          "us",
    "economist.com":    "uk",
    "hurriyetdailynews.com": "tr",
    "dailysabah.com":   "tr",
    "middleeasteye.net": "uk",
    "arabnews.com":     "sa",
    "timesofisrael.com": "il",
    "haaretz.com":      "il",
    "thenationalnews.com": "ae",
    "gulfnews.com":     "ae",
}


class ContentExtractor:
    """
    Sayfadan çıkarılan ham veriyi Crawler-uyumlu makalelere dönüştürür.

    Dönüştürülen format (pipeline beklentisi):
    {
        "source":        "reuters",
        "country":       "us",
        "url":           "https://reuters.com/...",
        "keyword_found": "turkey economy",
        "scraped_at":    "2026-04-13T...",
        "title":         "...",
        "content":       "...",
        "media": {
            "main_image":    "https://...",
            "content_images": [...],
            "videos":        []
        },
        "source_type":   "agent_surface"   ← CUA kökenini işaretler
    }
    """

    @staticmethod
    def extract_from_raw(raw: Dict[str, Any], search_keywords: str = "") -> Dict[str, Any]:
        """
        browser-use Agent çıktısını Crawler-uyumlu dict'e dönüştür.

        Args:
            raw:             BrowserTool.extract_page() çıktısı
            search_keywords: Bu makalenin bulunmasını sağlayan arama terimi

        Returns:
            Crawler-uyumlu article dict
        """
        url     = raw.get("url", "")
        title   = raw.get("title", "")
        content = raw.get("content", raw.get("description", ""))

        # İçeriği kırp (50KB limit — DB uyumu)
        if content:
            content = content[:50_000]

        # Meta bilgiler
        source  = ContentExtractor._extract_source(url)
        country = ContentExtractor._infer_country(url)

        # Medya
        media_raw = raw.get("media", {})
        media = {
            "main_image":    media_raw.get("main_image", ""),
            "content_images": media_raw.get("content_images", [])[:10],
            "videos":        media_raw.get("videos", []),
        }

        return {
            "source":        source,
            "country":       country,
            "url":           url,
            "keyword_found": search_keywords,
            "scraped_at":    datetime.now().isoformat(),
            "title":         title,
            "content":       content,
            "media":         media,
            "source_type":   "agent_surface",  # CUA kökenini işaretle
        }

    @staticmethod
    def _extract_source(url: str) -> str:
        """URL'den kaynak domain adını çıkar (www. olmadan, kısa)."""
        try:
            host = urlparse(url).netloc.lower()
            host = host.replace("www.", "")
            # İlk iki parçayı al (örn. "bbc.com", "reuters.com")
            parts = host.split(".")
            if len(parts) >= 2:
                return ".".join(parts[-2:])  # son iki segment
            return host or "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _infer_country(url: str) -> str:
        """
        Domain'e bakarak haber kaynağının ülkesini tahmin et.
        Bilinmeyen domainler için ccTLD kullan, yoksa 'unknown' döndür.
        """
        try:
            host = urlparse(url).netloc.lower().replace("www.", "")
            # Tam eşleşme
            for domain, country in _DOMAIN_COUNTRY.items():
                if domain in host:
                    return country
            # ccTLD tahmini (örn. ".de", ".fr", ".tr")
            parts = host.split(".")
            if len(parts) >= 2:
                tld = parts[-1]
                if len(tld) == 2 and tld.isalpha():
                    return tld  # ISO 3166-1 alpha-2
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def generate_article_id(url: str) -> str:
        """URL hash'inden tekil 16 karakter ID üret (DB news_id ile uyumlu)."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    @staticmethod
    def is_valid_article(article: Dict[str, Any], min_content_length: int = 200) -> bool:
        """
        Makale pipeline'a gönderilmeye değer mi?
        URL ve yeterli içerik var mı kontrol eder.
        """
        url     = article.get("url", "")
        content = article.get("content", "")
        return bool(url) and len(content) >= min_content_length
