export MODEL_MODE=local
export MODEL_NAME="Qwen/Qwen3.5-9B"
export LMSTUDIO_URL="http://127.0.0.1:1235/v1"
export LMSTUDIO_API_KEY="lm-studio"
export SEARCH_ENGINE="duckduckgo"
export BROWSER_HEADLESS="false"
export CUA_MAX_QUERY_PLAN=10
export CUA_MAX_IMAGES_PER_ARTICLE=3

python -m cua.test_local \
  --mode surface \
  --query "Turkey economy 2026" \
  --max-articles 3 \
  --max-cycles 6 \
  --headless false \
  --engine duckduckgo \
  --lmstudio-url "$LMSTUDIO_URL"
Already up to date.
/root/Bitirme/cua/.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
  from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
============================================================
CUA STANDALONE TEST
============================================================
  Mod:            surface
  Query/Topic:    Turkey economy 2026
  Max makale:     3
  Max döngü:      6
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
[ModelHandler] Query plan: ['Turkey economy 2026']
[Graph] Plan [1]: {'action': 'search', 'query': 'Turkey economy 2026', 'query_key': 'turkey economy 2026'}
[BrowserTool] DuckDuckGo: Turkey economy 2026
[Graph] Search 'Turkey economy 2026': 7 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=1/6, no_progress=0/3, dur=False
[Graph] Plan [2]: {'action': 'visit', 'url': 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/'}
[BrowserTool] Extract: https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/
[Graph] Category/list page: 9 article link kuyru?a eklendi
[Graph] Visit 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/': OK
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=2/6, no_progress=0/3, dur=False
[Graph] Plan [3]: {'action': 'visit', 'url': 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057'}
[BrowserTool] Extract: https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057
[Graph] Category/list page: 12 article link kuyru?a eklendi
[Graph] Visit 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057': OK
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=3/6, no_progress=0/3, dur=False
[Graph] Plan [4]: {'action': 'visit', 'url': 'https://www.trmonitor.net/what-awaits-turkeys-economy-in-2026/'}
[BrowserTool] Extract: https://www.trmonitor.net/what-awaits-turkeys-economy-in-2026/
[ModelHandler] Article analysis parse failed, raw='Thinking Process:

1.  **Analyze the Request:**
    *   Role: News analysis assistant specialized in sentiment classification.
    *   Task: Analyze the provided news article and respond ONLY with val'
[Graph] Makale eklendi: What Awaits Turkey?s Economy in 2026? - TR MONITOR
[Graph] Visit 'https://www.trmonitor.net/what-awaits-turkeys-economy-in-2026/': OK
[Graph] Evaluate: articles=1/3, searches=1/6, cycles=4/6, no_progress=0/3, dur=False
[Graph] Plan [5]: {'action': 'visit', 'url': 'https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/'}
[BrowserTool] Extract: https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/
[ModelHandler] Article analysis parse failed, raw='Thinking Process:

1.  **Analyze the Request:**
    *   Role: News analysis assistant specialized in sentiment classification.
    *   Task: Analyze the provided news article and respond ONLY with val'
[Graph] Makale eklendi: Web server is returning an unknown error Error code 520
[Graph] Visit 'https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/': OK
[Graph] Evaluate: articles=2/3, searches=1/6, cycles=5/6, no_progress=0/3, dur=False
[Graph] Plan [6]: {'action': 'visit', 'url': 'https://www.paturkey.com/news/2025/turkey-sets-2026-economic-roadmap-growth-target-at-3-8-inflation-goal-at-16-24773/'}
[BrowserTool] Extract: https://www.paturkey.com/news/2025/turkey-sets-2026-economic-roadmap-growth-target-at-3-8-inflation-goal-at-16-24773/
[Graph] Makale eklendi: Origin is unreachable Error code 523
[Graph] Visit 'https://www.paturkey.com/news/2025/turkey-sets-2026-economic-roadmap-growth-target-at-3-8-inflation-goal-at-16-24773/': OK
[Graph] Evaluate: articles=3/3, searches=1/6, cycles=6/6, no_progress=0/3, dur=True
[Graph] Sentezleniyor...
[ModelHandler] Synthesize parse failed, building fallback report
[Graph] Rapor haz?r: mode=surface, anahtarlar=['mode', 'summary', 'article_count', 'articles']

============================================================
SONUÇ
============================================================
Status: COMPLETED
Stop reason: max_articles_reached
Toplanan makale: 3
Özet: Agent surface search completed.

Makaleler:
  1. [trmonitor.net] What Awaits Turkey?s Economy in 2026? - TR MONITOR
     URL: https://www.trmonitor.net/what-awaits-turkeys-economy-in-2026/
     ?çerik (1904 karakter)
  2. [balavidyamandir.org] Web server is returning an unknown error Error code 520
     URL: https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/
     ?çerik (624 karakter)
  3. [paturkey.com] Origin is unreachable Error code 523
     URL: https://www.paturkey.com/news/2025/turkey-sets-2026-economic-roadmap-growth-target-at-3-8-inflation-goal-at-16-24773/
     ?çerik (470 karakter)

[OK] Sonuç kaydedildi: cua_test_result_surface.json
[BrowserTool] Kapat?ld?





{
  "mode": "surface",
  "summary": "Agent surface search completed.",
  "article_count": 3,
  "articles": [
    {
      "source": "trmonitor.net",
      "country": "unknown",
      "url": "https://www.trmonitor.net/what-awaits-turkeys-economy-in-2026/",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T18:34:28.077741",
      "title": "What Awaits Turkeyâs Economy in 2026? - TR MONITOR",
      "content": "For millions of workers, retirees and businesses, the economy dominated Turkeyâs agenda in 2025 and it is set to remain the key issue in 2026. The inflation fighting program led by Treasury and Finance Minister Mehmet ÅimÅek, in place since mid 2023, is expected to continue shaping economic policy.\n\nAfter peaking at 75% in May 2024, annual inflation is expected to end 2025 at around 30-31%. Although the Central Bank of the Republic of Turkey has cut its policy rate from 50% to 38%, real interest rates remain high. Business groups are calling for structural reforms and policy continuity, while concerns persist that an early election could undermine recent gains. The main expectation for 2026 is a return to economic and political balance.\n\nTurkey grew by 4.5% in 2023 and 3.2% in 2024. Growth moderated in 2025 but investment in machinery and equipment rose by 11.3%, a key leading indicator. As a result, growth in 2026 is expected to exceed the Medium Term Program forecast of 3.8%, reaching around 4â4.5%.\n\nDespite a rare monthly inflation reading below 1% in November 2025, Turkey remains among the worldâs highest inflation economies. While the government targets 16-19% inflation by end 2026, market expectations and international forecasts point to levels closer to 25%. With base effects fading, inflation may remain stuck in the 25-30% range.\n\nHeadline unemployment stands at 8.5%, but broad unemployment, measuring idle labor has climbed to nearly 30%, meaning three in ten working-age people are effectively jobless. Projections by the OECD and International Monetary Fund suggest unemployment will remain broadly unchanged in 2026.\n\nThe current account deficit is projected at $20.9 billion for 2025, around 1.4% of GDP, easing slightly in 2026. Meanwhile, the budget deficit is expected to rise to 2.7 trillion TL in 2026, up 22% from 2025, highlighting persistent fiscal challenges.",
      "description": "For millions of workers, retirees and businesses, the economy dominated Turkeyâs agenda in 2025 and it is set to remain the key issue in 2026. The inflation fighting program led by Treasury and Finance Minister Mehmet ÅimÅek, in place since mid 2023, is expected to continue shaping economic policy.ContentsA year of balanceGrowth outlookInflation risks remainLabor [â¦]",
      "media": {
        "main_image": "https://www.trmonitor.net/storage/2025/12/what-awaits-turkeys-economy-in-2026_cover.webp",
        "content_images": [
          "https://www.trmonitor.net/storage/2023/09/newsletter.webp",
          "https://www.trmonitor.net/storage/2026/01/bofa-warns-dollar-could-lose-value-this-year_cover-150x150.png",
          "https://www.trmonitor.net/storage/2026/01/%E2%82%BA24-trillion-in-card-spending-recorded-in-turkiye-in-2025_cover-150x150.webp"
        ],
        "videos": []
      },
      "source_type": "agent_surface",
      "llm_analysis": {
        "result": {
          "summary": "For millions of workers, retirees and businesses, the economy dominated Turkeyâs agenda in 2025 and it is set to remain the key issue in 2026. The inflation fighting program led by Treasury and Finance Minister Mehmet ÅimÅek, in place since mid 2023, is expected to continue shaping economic policy.ContentsA year of balanceGrowth outlookInflation risks remainLabor [â¦]",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [
            "millions",
            "workers",
            "retirees",
            "businesses",
            "economy"
          ],
          "entities": {
            "countries": [],
            "organizations": [],
            "people": []
          },
          "category": "other",
          "relevance_to_topic": "medium"
        }
      },
      "vlm_analysis": {
        "results": [
          {
            "minio_path": null,
            "original_url": "https://www.trmonitor.net/storage/2025/12/what-awaits-turkeys-economy-in-2026_cover.webp",
            "description": "",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "low",
            "error": "image analysis parse failed: The user wants me to analyze the provided image in the context of the news article.\n\n**1. Analyze the Image:**\n*   **Visuals:** A close-up shot of a person's ha"
          },
          {
            "minio_path": null,
            "original_url": "https://www.trmonitor.net/storage/2023/09/newsletter.webp",
            "description": "",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "low",
            "error": "image analysis parse failed: The user wants me to analyze an image in the context of a provided news article.\n\n**1. Analyze the Image:**\n*   **Visuals:** The image shows a stylized globe, s"
          },
          {
            "minio_path": null,
            "original_url": "https://www.trmonitor.net/storage/2026/01/bofa-warns-dollar-could-lose-value-this-year_cover-150x150.png",
            "description": "",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "low",
            "error": "image analysis parse failed: The user wants me to analyze an image of US dollar bills in the context of a news article about Turkey's economy.\n\n1.  **Analyze the Image:**\n    *   The image "
          }
        ]
      }
    },
    {
      "source": "balavidyamandir.org",
      "country": "unknown",
      "url": "https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T18:39:34.706729",
      "title": "Web server is returning an unknown error Error code 520",
      "content": "There is an unknown connection issue between Cloudflare and the origin web server. As a result, the web page can not be displayed.\n\nThere is an issue between Cloudflare's cache and your origin web server. Cloudflare monitors for these errors and automatically investigates the cause. To help support the investigation, you can pull the corresponding error log from your web server and submit it our support team. Please include the Ray ID (which is at the bottom of this error page). Additional troubleshooting resources.\n\nCloudflare Ray ID: 9fa34e880e2a11fd â¢ Your IP: Click to reveal â¢ Performance & security by Cloudflare",
      "description": "There is an unknown connection issue between Cloudflare and the origin web server. As a result, the web page can not be displayed.",
      "media": {
        "main_image": "",
        "content_images": [],
        "videos": []
      },
      "source_type": "agent_surface",
      "llm_analysis": {
        "result": {
          "summary": "There is an unknown connection issue between Cloudflare and the origin web server. As a result, the web page can not be displayed.",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [
            "There",
            "unknown",
            "connection",
            "issue",
            "between"
          ],
          "entities": {
            "countries": [],
            "organizations": [],
            "people": []
          },
          "category": "other",
          "relevance_to_topic": "medium"
        }
      },
      "vlm_analysis": {
        "results": []
      }
    },
    {
      "source": "paturkey.com",
      "country": "unknown",
      "url": "https://www.paturkey.com/news/2025/turkey-sets-2026-economic-roadmap-growth-target-at-3-8-inflation-goal-at-16-24773/",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T18:42:17.689770",
      "title": "Origin is unreachable Error code 523",
      "content": "Check your DNS Settings. A 523 error means that Cloudflare could not reach your host web server. The most common cause is that your DNS settings are incorrect. Please contact your hosting provider to confirm your origin IP and then make sure the correct IP is listed for your A record in your Cloudflare DNS Settings page. Additional troubleshooting information here.\n\nCloudflare Ray ID: 9fa35282b8392c1d â¢ Your IP: Click to reveal â¢ Performance & security by Cloudflare",
      "description": "The origin web server is not reachable.",
      "media": {
        "main_image": "",
        "content_images": [],
        "videos": []
      },
      "source_type": "agent_surface",
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
        "results": []
      }
    }
  ],
  "status": "COMPLETED",
  "stop_reason": "max_articles_reached"
}