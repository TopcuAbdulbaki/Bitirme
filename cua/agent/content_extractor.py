"""
ContentExtractor — browser-use Agent çıktısını Crawler uyumlu JSON'a dönüştürür.

Crawler node'unun ürettiği format birebir korunur; kaynak belirteci
`source_type='agent_surface'` olarak eklenir. Bu sayede downstream
VLM → LLM → DB pipeline'ı herhangi bir değişiklik gerektirmez.
"""
import hashlib
import json
import re
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
        title   = ContentExtractor._clean_text(raw.get("title", ""))
        content = ContentExtractor._clean_content(raw.get("content", raw.get("description", "")))
        description = ContentExtractor._clean_text(raw.get("description", ""))

        if not title:
            title = ContentExtractor._title_from_content(content)

        # İçeriği kırp (50KB limit — DB uyumu)
        if content:
            content = content[:50_000]

        # Meta bilgiler
        source  = ContentExtractor._extract_source(url)
        country = ContentExtractor._infer_country(url)

        # Medya
        media_raw = raw.get("media", {})
        main_image = media_raw.get("main_image", "") or ""
        content_images = ContentExtractor._dedupe_images(
            media_raw.get("content_images", []),
            main_image,
        )
        media = {
            "main_image":    main_image,
            "content_images": content_images[:10],
            "videos":        media_raw.get("videos", []),
        }

        article = {
            "source":        source,
            "country":       country,
            "url":           url,
            "keyword_found": search_keywords,
            "scraped_at":    datetime.now().isoformat(),
            "title":         title,
            "content":       content,
            "description":   description,
            "media":         media,
            "source_type":   "agent_surface",  # CUA kökenini işaretle
        }
        if raw.get("llm_analysis"):
            article["llm_analysis"] = raw["llm_analysis"]
        if raw.get("vlm_analysis"):
            article["vlm_analysis"] = raw["vlm_analysis"]
        return article

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
        title   = article.get("title", "")
        if not url or not title or len(content) < min_content_length:
            return False
        bad_prefixes = (
            "successfully extracted",
            "article information extracted successfully",
            "the user wants me to extract",
        )
        return not content.strip().lower().startswith(bad_prefixes)

    @staticmethod
    def _clean_content(content: Any) -> str:
        if isinstance(content, dict):
            return ContentExtractor._clean_content(content.get("content", ""))
        text = str(content or "").strip()
        parsed = ContentExtractor._parse_jsonish_text(text)
        if isinstance(parsed, dict):
            title = parsed.get("title", "")
            body = parsed.get("content") or parsed.get("article") or parsed.get("text") or ""
            if body:
                return ContentExtractor._clean_text(str(body))
            if title:
                return ContentExtractor._clean_text(str(title))

        text = re.sub(r"^Article information extracted successfully:\s*", "", text, flags=re.I)
        text = re.sub(r"^Successfully extracted article data from [^\n]+\.?\s*", "", text, flags=re.I)
        text = re.sub(r"\*\*(Article )?Title:\*\*.*?(?=\n\n|\r\n\r\n)", "", text, flags=re.I | re.S)
        text = re.sub(r"\*\*Content:\*\*", "", text, flags=re.I)
        text = re.sub(r"\*\*Description:\*\*.*", "", text, flags=re.I | re.S)
        text = re.sub(r"\*\*Main Image:\*\*.*", "", text, flags=re.I | re.S)
        text = re.sub(r"\*\*Images:\*\*.*", "", text, flags=re.I | re.S)
        return ContentExtractor._clean_text(text)

    @staticmethod
    def _parse_jsonish_text(text: str):
        if not text or not text.lstrip().startswith("{"):
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _clean_text(text: Any) -> str:
        text = str(text or "")
        text = text.replace("\\n", "\n").replace("\\t", "\t")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        mojibake_markers = ("Ã", "Ä", "Å", "â", "Â")
        if any(marker in text for marker in mojibake_markers):
            try:
                repaired = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
                if repaired and len(repaired) >= len(text) * 0.6:
                    text = repaired
            except Exception:
                pass
        return text.strip()

    @staticmethod
    def _title_from_content(content: str) -> str:
        for line in (content or "").splitlines():
            line = line.strip(" #*\t")
            if 12 <= len(line) <= 180:
                return line
        return ""

    @staticmethod
    def _dedupe_images(images: list, main_image: str = "") -> list:
        result = []
        seen = {ContentExtractor._normalize_image_url(main_image)} if main_image else set()
        for image in images or []:
            url = image.get("original_url") if isinstance(image, dict) else image
            url = str(url or "").strip()
            key = ContentExtractor._normalize_image_url(url)
            if not url or key in seen:
                continue
            seen.add(key)
            result.append(url)
        return result

    @staticmethod
    def _normalize_image_url(url: str) -> str:
        base_url = (url or "").split("?", 1)[0]
        base_url = re.sub(r"/\d{2,4}/", "/", base_url)
        return re.sub(
            r"[-_](thumb|small|medium|large|full|\d+x\d+)\.(jpg|jpeg|png|webp)",
            r".\2",
            base_url,
            flags=re.IGNORECASE,
        )
