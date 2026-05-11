((.venv) ) (main) root@C.36545716:~/Bitirme$ BROWSER_HEADLESS=false SEARCH_ENGINE=duckduckgo python -m cua.test_local   --mode surface   --query "Turkey economy 2026"   --max-articles 3   --max-cycles 15   --headless false   --engine duckduckgo   --lmstudio-url "$LMSTUDIO_URL"
/root/Bitirme/cua/.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
  from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
============================================================
CUA STANDALONE TEST
============================================================
  Mod:            surface
  Query/Topic:    Turkey economy 2026
  Max makale:     3
  Max döngü:      15
  Taray?c?:       GÖRÜNÜR
  Arama motoru:   duckduckgo
  Model modu:     local
============================================================

[Test] Model handler ba?lat?l?yor...
[ModelHandler] Test connection to: http://127.0.0.1:1235/v1
[ModelHandler] LM Studio connected. Models: ['Qwen/Qwen3.5-9B']
[ModelHandler] browser-use ChatOpenAI haz?r (model=Qwen/Qwen3.5-9B)
[Test] Taray?c? ba?lat?l?yor...
[BrowserTool] Playwright haz?r (Headless: False)
[Test] [OK] Taray?c? haz?r

[Test] Agent ba?lat?l?yor: mode=surface
------------------------------------------------------------
[ModelHandler] Query plan: ['Turkey economy 2026', 'Turkey economic outlook inflation rate predictions from international financial institutions covering period ending December thirty first two thousand twenty six', 'World Bank report analyzing structural reforms required for sustained GDP expansion in Turkey targeting fiscal year two thousand twenty six', 'Central Bank of Republic of Turkey interest rate decisions influence on long term borrowing costs projected scenario analysis', 'Trade balance deficit reduction strategy implementation progress reports published by Ministry of Economy regarding export diversification goals']
[Graph] Plan [1]: {'action': 'search', 'query': 'Turkey economy 2026', 'query_key': 'turkey economy 2026'}
[BrowserTool] DuckDuckGo: Turkey economy 2026
[Graph] Search 'Turkey economy 2026': 8 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=1/15, no_progress=0/3, dur=False
[Graph] Plan [2]: {'action': 'visit', 'url': 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/'}
[BrowserTool] Extract: https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/
[Graph] Makale eklendi: Türkiye Economic Outlook. March 2026
[Graph] Visit 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/': OK
[Graph] Evaluate: articles=1/3, searches=1/6, cycles=2/15, no_progress=0/3, dur=False
[Graph] Plan [3]: {'action': 'visit', 'url': 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057'}
[BrowserTool] Extract: https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057
[Graph] Page links queued: 12 article link kuyru?a eklendi
[Graph] Visit 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057': OK
[Graph] Evaluate: articles=1/3, searches=1/6, cycles=3/15, no_progress=0/3, dur=False
[Graph] Plan [4]: {'action': 'search', 'query': 'Turkey economic outlook inflation rate predictions from international financial institutions covering period ending December thirty first two thousand twenty six', 'query_key': 'turkey economic outlook inflation rate predictions from international financial institutions covering period ending december thirty first two thousand twenty six'}
[BrowserTool] DuckDuckGo: Turkey economic outlook inflation rate predictions from international financial institutions covering period ending December thirty first two thousand twenty six
[Graph] Search 'Turkey economic outlook inflation rate predictions from international financial institutions covering period ending December thirty first two thousand twenty six': 6 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=1/3, searches=2/6, cycles=4/15, no_progress=0/3, dur=False
[Graph] Plan [5]: {'action': 'search', 'query': 'World Bank report analyzing structural reforms required for sustained GDP expansion in Turkey targeting fiscal year two thousand twenty six', 'query_key': 'world bank report analyzing structural reforms required for sustained gdp expansion in turkey targeting fiscal year two thousand twenty six'}
[BrowserTool] DuckDuckGo: World Bank report analyzing structural reforms required for sustained GDP expansion in Turkey targeting fiscal year two thousand twenty six
[Graph] Search 'World Bank report analyzing structural reforms required for sustained GDP expansion in Turkey targeting fiscal year two thousand twenty six': 7 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=1/3, searches=3/6, cycles=5/15, no_progress=0/3, dur=False
[Graph] Plan [6]: {'action': 'search', 'query': 'Central Bank of Republic of Turkey interest rate decisions influence on long term borrowing costs projected scenario analysis', 'query_key': 'central bank of republic of turkey interest rate decisions influence on long term borrowing costs projected scenario analysis'}
[BrowserTool] DuckDuckGo: Central Bank of Republic of Turkey interest rate decisions influence on long term borrowing costs projected scenario analysis
[Graph] Search 'Central Bank of Republic of Turkey interest rate decisions influence on long term borrowing costs projected scenario analysis': 8 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=1/3, searches=4/6, cycles=6/15, no_progress=0/3, dur=False
[Graph] Plan [7]: {'action': 'search', 'query': 'Trade balance deficit reduction strategy implementation progress reports published by Ministry of Economy regarding export diversification goals', 'query_key': 'trade balance deficit reduction strategy implementation progress reports published by ministry of economy regarding export diversification goals'}
[BrowserTool] DuckDuckGo: Trade balance deficit reduction strategy implementation progress reports published by Ministry of Economy regarding export diversification goals
[Graph] Search 'Trade balance deficit reduction strategy implementation progress reports published by Ministry of Economy regarding export diversification goals': 6 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=1/3, searches=5/6, cycles=7/15, no_progress=0/3, dur=False
[ModelHandler] Query plan parse failed, raw='Thinking Process:

1.  **Analyze the Request:**
    *   **Task:** Generate 3 diverse web search queries for collecting news articles.
    *   **Topic:** Turkey economy 2026.
    *   **Already Collecte'
[Graph] Plan [8]: {'action': 'search', 'query': 'Turkey economy 2026 news', 'query_key': 'turkey economy 2026 news'}
[BrowserTool] DuckDuckGo: Turkey economy 2026 news
[Graph] Search 'Turkey economy 2026 news': 3 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=1/3, searches=6/6, cycles=8/15, no_progress=0/3, dur=True
[Graph] Sentezleniyor...
[ModelHandler] Report synthesized (521 chars)
[Graph] Rapor haz?r: mode=surface, anahtarlar=['mode', 'summary', 'article_count', 'sources', 'top_keywords', 'key_findings']

============================================================
SONUÇ
============================================================
Status: COMPLETED
Stop reason: max_searches_reached
Toplanan makale: 1
Özet: The Turkish economy grew by 3.6% in 2025 while successfully maintaining its disinflation process despite external pressures.

Makaleler:
  1. [bbvaresearch.com] Türkiye Economic Outlook. March 2026
     URL: https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/
     ?çerik (353 karakter)

[OK] Sonuç kaydedildi: cua_test_result_surface.json
[BrowserTool] Kapat?ld?


-----


{
  "mode": "surface",
  "summary": "The Turkish economy grew by 3.6% in 2025 while successfully maintaining its disinflation process despite external pressures.",
  "article_count": 1,
  "sources": [
    "bbvaresearch.com"
  ],
  "top_keywords": [
    "Turkish economy",
    "GDP growth",
    "disinflation",
    "Middle East conflict"
  ],
  "key_findings": [
    "Economic growth reached 3.6% in fiscal year ending December",
    "Disinflation process continued throughout the period",
    "Downside risks anticipated for March-April outlook due to regional instability"
  ],
  "status": "COMPLETED",
  "stop_reason": "max_searches_reached",
  "articles": [
    {
      "source": "bbvaresearch.com",
      "country": "unknown",
      "url": "https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T21:05:48.168819",
      "title": "TÃ¼rkiye Economic Outlook. March 2026",
      "content": "Published on Friday, March 27, 2026 | Updated on Wednesday, April 1, 2026\n\nThe Turkish economy grew by 3.6% in 2025, while the disinflation process was maintained. 2026 is set to be a challenging year, with downside risks stemming in particular from the recent Middle East conflict; however, a well-calibrated policy mix could help mitigate these risks.",
      "description": "The Turkish economy grew by 3.6% in 2025, while the disinflation process was maintained. 2026 is set to be a challenging year, with downside risks stemming in particular from the recent Middle East conflict; however, a well-calibrated policy mix could help mitigate these risks.",
      "media": {
        "main_image": "https://www.bbvaresearch.com/wp-content/uploads/image-gallery/164ec93077c37bb77aba8018fbe70c25.jpg",
        "content_images": [],
        "videos": []
      },
      "source_type": "agent_surface",
      "quality_gate": {
        "accept": 1,
        "reason": "Legitimate institutional economic report from BBVA Research specifically analyzing Turkey's economic performance and outlook for 2026.",
        "page_type": "report",
        "relevance": "high"
      },
      "llm_analysis": {
        "result": {
          "summary": "",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [],
          "entities": {},
          "category": "other",
          "relevance_to_topic": "medium"
        }
      },
      "vlm_analysis": {
        "results": [
          {
            "minio_path": null,
            "original_url": "https://www.bbvaresearch.com/wp-content/uploads/image-gallery/164ec93077c37bb77aba8018fbe70c25.jpg",
            "description": "The image shows industrial smokestacks emitting dark smoke against a yellow/orange sunset sky. There are multiple chimneys, some tall and thin, others shorter. The smoke is thick and dark, suggesting pollution or heavy industrial activity. Subject: Industrial pollution, manufacturing, factories, emissions.",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "medium"
          }
        ]
      }
    }
  ]
}