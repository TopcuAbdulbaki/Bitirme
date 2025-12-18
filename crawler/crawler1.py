# crawler.py — "Türkiye" ile ilgili en yeni haberi getir (Reuters site-search + CNN + Guardian + Al Jazeera)
# AP YOK

import re, asyncio, datetime as dt
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

# -------- Yardımcılar --------
TR_TOKENS = [
    r"turkey\b", r"türkiye\b", r"turkiye\b", r"turkish\b"
]
TR_RX = re.compile("|".join(TR_TOKENS), re.IGNORECASE)

def extract_first_paragraph(md_text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", md_text or "") if len(p.strip()) > 60]
    for p in paras:
        low = p.lower()
        if low.startswith("skip to main content"): 
            continue
        if "](" in p and p.count("](") > 2:  # nav/link yağmuru
            continue
        if "." not in p and "!" not in p and "?" not in p:
            continue
        # Guardian çöp satırlarını ele
        if "support the guardian" in low or "back to top" in low:
            continue
        return p
    return ""

def extract_headline(md_text: str) -> str:
    for line in (md_text or "").splitlines():
        s = line.strip()
        if s.startswith("# "):  return s[2:].strip()
        if s.startswith("## "): return s[3:].strip()
    for line in (md_text or "").splitlines():
        s = line.strip()
        low = s.lower()
        if not s:
            continue
        if low.startswith("skip to main content") or "support the guardian" in low or "back to top" in low:
            continue
        if len(s) >= 20 and "](" not in s:
            return s
    return "News article"

def by_date_desc(get_date, urls):
    return sorted(urls, key=lambda u: get_date(u) or dt.date(1900,1,1), reverse=True)

# -------- 1) Reuters Site Search --------
# Çeşitli sıralama/filtre + ilk 2 sayfa (offset) deniyoruz:
REUTERS_SEARCH_URLS = [
    "https://www.reuters.com/site-search/?query=turkey&sort=date&date=past_week&offset=0",
    "https://www.reuters.com/site-search/?query=turkey&sort=date&date=past_week&offset=20",
    "https://www.reuters.com/site-search/?query=turkey&sort=date&offset=0",
    "https://www.reuters.com/site-search/?query=turkey&sort=date&offset=20",
    "https://www.reuters.com/site-search/?query=turkey&offset=0",
]

REUTERS_ART_RX = re.compile(
    r"/(world|business|markets|sustainability|technology|legal|pictures|graphics|lifestyle|sports)/[^?#]+(?:\d{4}-\d{2}-\d{2}|id[A-Za-z0-9]{6,})/?$"
)
REUTERS_DATE_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

def reuters_date(url: str):
    m = REUTERS_DATE_RX.search(url)
    if not m: 
        return None
    y, mo, d = map(int, m.groups())
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None

async def fetch_from_reuters_search(crawler, run):
    found = []
    for search_url in REUTERS_SEARCH_URLS:
        res = await crawler.arun(search_url, config=run)
        links = res.links.get("internal", []) + res.links.get("external", [])
        print(f"[DEBUG] Reuters search links: {len(links)} @ {search_url}")
        for lk in links:
            href = (lk.get("href") or "").split("?")[0].strip()
            if "reuters.com" in href and REUTERS_ART_RX.search(href):
                found.append(href)
        if found:
            break  # İlk dolu sayfada dur
    found = list(dict.fromkeys(found))
    if not found:
        return None

    for url in by_date_desc(reuters_date, found)[:60]:
        art = await crawler.arun(url, config=run)
        md  = getattr(art.markdown, "fit_markdown", None) or (art.markdown or "")
        s   = str(md)
        if TR_RX.search(s) or TR_RX.search(url):
            lead = extract_first_paragraph(s)
            if not lead:
                continue
            return {"title": extract_headline(s), "url": url, "lead": lead}
    return None

# -------- 2) CNN (edition) --------
CNN_SECTIONS = [
    "https://edition.cnn.com/world",
    "https://edition.cnn.com/europe",
    "https://edition.cnn.com/middleeast",
]
CNN_ART_RX   = re.compile(r"/\d{4}/\d{2}/\d{2}/[^?#]+/index\.html$")
CNN_DATE_RX  = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")

def cnn_date(url: str):
    m = CNN_DATE_RX.search(url)
    if not m: 
        return None
    y, mo, d = map(int, m.groups())
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None

async def fetch_from_cnn(crawler, run):
    urls = set()
    for sec in CNN_SECTIONS:
        res = await crawler.arun(sec, config=run)
        links = res.links.get("internal", []) + res.links.get("external", [])
        print(f"[DEBUG] CNN links: {len(links)} @ {sec}")
        for lk in links:
            href = (lk.get("href") or "").split("?")[0].strip()
            if "edition.cnn.com" in href and CNN_ART_RX.search(href):
                urls.add(href)
    if not urls:
        return None
    for url in by_date_desc(cnn_date, list(urls))[:40]:
        art = await crawler.arun(url, config=run)
        md  = getattr(art.markdown, "fit_markdown", None) or (art.markdown or "")
        s   = str(md)
        if TR_RX.search(s) or TR_RX.search(url):
            lead = extract_first_paragraph(s)
            if lead:
                return {"title": extract_headline(s), "url": url, "lead": lead}
    return None

# -------- 3) The Guardian (yalnızca Turkey sayfası) --------
GDN_SECTION = "https://www.theguardian.com/world/turkey"
# Sadece /world/turkey/YYYY/mmm/DD/... izin ver
GDN_ART_RX  = re.compile(r"/world/turkey/\d{4}/[a-z]{3}/\d{2}/[^?#]+$", re.IGNORECASE)
GDN_DATE_RX = re.compile(r"/world/turkey/(\d{4})/([a-z]{3})/(\d{2})/")
MONTHS = {m:i for i,m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], start=1)}

def gdn_date(url: str):
    m = GDN_DATE_RX.search(url.lower())
    if not m: 
        return None
    y = int(m.group(1)); mo = MONTHS.get(m.group(2), 0); d = int(m.group(3))
    if mo == 0: 
        return None
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None

async def fetch_from_guardian(crawler, run):
    res = await crawler.arun(GDN_SECTION, config=run)
    links = res.links.get("internal", []) + res.links.get("external", [])
    print(f"[DEBUG] Guardian links: {len(links)}")
    urls = []
    for lk in links:
        href = (lk.get("href") or "").split("?")[0].strip()
        if "theguardian.com" in href and GDN_ART_RX.search(href.lower()):
            urls.append(href)
    if not urls:
        return None
    for url in by_date_desc(gdn_date, urls)[:30]:
        art = await crawler.arun(url, config=run)
        md  = getattr(art.markdown, "fit_markdown", None) or (art.markdown or "")
        s   = str(md)
        lead = extract_first_paragraph(s)
        if lead:
            return {"title": extract_headline(s), "url": url, "lead": lead}
    return None

# -------- 4) Al Jazeera --------
AJ_SECTION = "https://www.aljazeera.com/tag/turkey/"
AJ_ART_RX  = re.compile(r"/\d{4}/\d{1,2}/\d{1,2}/[^?#/]+/?$")

def aj_date(url: str):
    m = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
    if not m: 
        return None
    y, mo, d = map(int, m.groups())
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None

async def fetch_from_aj(crawler, run):
    res = await crawler.arun(AJ_SECTION, config=run)
    links = res.links.get("internal", []) + res.links.get("external", [])
    print(f"[DEBUG] Al Jazeera links: {len(links)}")
    urls = []
    for lk in links:
        href = (lk.get("href") or "").split("?")[0].strip()
        if "aljazeera.com" in href and AJ_ART_RX.search(href):
            urls.append(href)
    if not urls:
        return None
    for url in by_date_desc(aj_date, urls)[:30]:
        art = await crawler.arun(url, config=run)
        md  = getattr(art.markdown, "fit_markdown", None) or (art.markdown or "")
        s   = str(md)
        lead = extract_first_paragraph(s)
        if lead:
            return {"title": extract_headline(s), "url": url, "lead": lead}
    return None

# -------- main --------
async def main():
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, process_iframes=True)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for fetcher in (fetch_from_reuters_search, fetch_from_cnn, fetch_from_guardian, fetch_from_aj):
            try:
                res = await fetcher(crawler, run)
                if res:
                    print(res["title"])
                    print(res["url"])
                    print()
                    print(res["lead"])
                    return
            except Exception as e:
                print(f"[WARN] {fetcher.__name__} hata: {e}")
    print("Hiç haber bulunamadı.")

if __name__ == "__main__":
    asyncio.run(main())



