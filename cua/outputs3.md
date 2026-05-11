

((.venv) ) (main) root@C.36545716:~/Bitirme$ BROWSER_HEADLESS=false SEARCH_ENGINE=duckduckgo python -m cua.test_local \
  --mode surface \
  --query "Turkey economy 2026" \
  --max-articles 3 \
  --max-cycles 15 \
  --headless false \
  --engine duckduckgo \
  --lmstudio-url "$LMSTUDIO_URL"
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
[ModelHandler] Query plan: ['Turkey economy 2026', 'Turkey economy 2026 news', 'Turkey economy 2026 latest news', 'Turkey economy 2026 breaking news', 'Turkey economy 2026 today', 'recent Turkey economy 2026 developments', 'Turkey economy 2026 update', 'Turkey economy 2026 headlines', 'Turkey economy 2026 news analysis']
[Graph] Plan [1]: {'action': 'search', 'query': 'Turkey economy 2026', 'query_key': 'turkey economy 2026'}
[BrowserTool] DuckDuckGo: Turkey economy 2026
[Graph] Search 'Turkey economy 2026': 8 yeni URL kuyru?a eklendi
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=1/15, no_progress=0/3, dur=False
[Graph] Plan [2]: {'action': 'visit', 'url': 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/'}
[BrowserTool] Extract: https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/
[Graph] Category/list page: 10 article link kuyru?a eklendi
[Graph] Visit 'https://www.bbvaresearch.com/en/publicaciones/turkiye-economic-outlook-march-2026/': OK
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=2/15, no_progress=0/3, dur=False
[Graph] Plan [3]: {'action': 'visit', 'url': 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057'}
[BrowserTool] Extract: https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057
[Graph] Category/list page: 12 article link kuyru?a eklendi
[Graph] Visit 'https://www.hurriyetdailynews.com/imf-cuts-turkiyes-2026-growth-forecast-221057': OK
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=3/15, no_progress=0/3, dur=False
[Graph] Plan [4]: {'action': 'visit', 'url': 'https://www.turkiyetoday.com/opinion/how-is-turkish-economy-entering-2026-with-early-signs-of-recovery-3212383'}
[BrowserTool] Extract: https://www.turkiyetoday.com/opinion/how-is-turkish-economy-entering-2026-with-early-signs-of-recovery-3212383
[Graph] Category/list page: 12 article link kuyru?a eklendi
[Graph] Visit 'https://www.turkiyetoday.com/opinion/how-is-turkish-economy-entering-2026-with-early-signs-of-recovery-3212383': OK
[Graph] Evaluate: articles=0/3, searches=1/6, cycles=4/15, no_progress=0/3, dur=False
[Graph] Plan [5]: {'action': 'visit', 'url': 'https://money.usnews.com/investing/news/articles/2026-04-14/imf-cuts-turkey-2026-economic-growth-forecast-on-weaker-momentum-energy-prices'}
[BrowserTool] Extract: https://money.usnews.com/investing/news/articles/2026-04-14/imf-cuts-turkey-2026-economic-growth-forecast-on-weaker-momentum-energy-prices
[Graph] Makale eklendi: Our company keeps high security standards and one of our sec
[Graph] Visit 'https://money.usnews.com/investing/news/articles/2026-04-14/imf-cuts-turkey-2026-economic-growth-forecast-on-weaker-momentum-energy-prices': OK
[Graph] Evaluate: articles=1/3, searches=1/6, cycles=5/15, no_progress=0/3, dur=False
[Graph] Plan [6]: {'action': 'visit', 'url': 'https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/'}
[BrowserTool] Extract: https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/
[Graph] Visit 'https://balavidyamandir.org/gdp-per-capita-turkey-2025-gdp-per-country/': OK
[Graph] Evaluate: articles=1/3, searches=1/6, cycles=6/15, no_progress=1/3, dur=False
[Graph] Plan [7]: {'action': 'visit', 'url': 'https://www.creativefabrica.com/pt/product/turkey-economy-infographic-charts/'}
[BrowserTool] Extract: https://www.creativefabrica.com/pt/product/turkey-economy-infographic-charts/
[ModelHandler] Article analysis parse failed, raw='Thinking Process:

1.  **Analyze the Request:**
    *   Role: News analysis assistant specialized in sentiment classification.
    *   Task: Analyze the provided text (news article/content) and respon'
[Graph] Makale eklendi: Turkey Economy Infographic Charts Gráfico por terrabismail ·
[Graph] Visit 'https://www.creativefabrica.com/pt/product/turkey-economy-infographic-charts/': OK
[Graph] Evaluate: articles=2/3, searches=1/6, cycles=7/15, no_progress=0/3, dur=False
[Graph] Plan [8]: {'action': 'visit', 'url': 'https://storage.googleapis.com/doszvmntbhmfke/turkey-economy-overview.html'}
[BrowserTool] Extract: https://storage.googleapis.com/doszvmntbhmfke/turkey-economy-overview.html
[ModelHandler] Article analysis parse failed, raw='Thinking Process:

1.  **Analyze the Request:**
    *   Role: News analysis assistant specialized in sentiment classification.
    *   Task: Analyze the provided news article content.
    *   Output F'
[Graph] Makale eklendi: Turkey Economy Overview at Jason Lindstrom blog
[Graph] Visit 'https://storage.googleapis.com/doszvmntbhmfke/turkey-economy-overview.html': OK
[Graph] Evaluate: articles=3/3, searches=1/6, cycles=8/15, no_progress=0/3, dur=True
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
  1. [usnews.com] Our company keeps high security standards and one of our security tools has flag
     URL: https://money.usnews.com/investing/news/articles/2026-04-14/imf-cuts-turkey-2026-economic-growth-forecast-on-weaker-momentum-energy-prices
     ?çerik (416 karakter)
  2. [creativefabrica.com] Turkey Economy Infographic Charts Gráfico por terrabismail · Creative Fabrica
     URL: https://www.creativefabrica.com/pt/product/turkey-economy-infographic-charts/
     ?çerik (1400 karakter)
  3. [googleapis.com] Turkey Economy Overview at Jason Lindstrom blog
     URL: https://storage.googleapis.com/doszvmntbhmfke/turkey-economy-overview.html
     ?çerik (3328 karakter)

[OK] Sonuç kaydedildi: cua_test_result_surface.json
[BrowserTool] Kapat?ld?



{
  "mode": "surface",
  "summary": "Agent surface search completed.",
  "article_count": 3,
  "articles": [
    {
      "source": "usnews.com",
      "country": "unknown",
      "url": "https://money.usnews.com/investing/news/articles/2026-04-14/imf-cuts-turkey-2026-economic-growth-forecast-on-weaker-momentum-energy-prices",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T19:21:01.545337",
      "title": "Our company keeps high security standards and one of our security tools has flagged this request as exhibiting automated behavior. To protect our platform's integrity, we restrict programmatic access from unauthorized commercial tools.",
      "content": "Our company keeps high security standards and one of our security tools has flagged this request as exhibiting automated behavior. To protect our platform's integrity, we restrict programmatic access from unauthorized commercial tools. If you believe this is an error, please contact Helpdesk or use this form. Please provide the URL you were trying, your public IP and this error code: 0.8caa3717.1778527257.9380810",
      "description": "If you believe this is an error, please contact Helpdesk or use this form. Please provide the URL you were trying, your public IP and this error code: 0.8caa3717.1778527257.9380810",
      "media": {
        "main_image": "",
        "content_images": [],
        "videos": []
      },
      "source_type": "agent_surface",
      "llm_analysis": {
        "result": {
          "summary": "This text appears to be an automated error message from a website indicating that programmatic access was blocked due to suspected automated behavior violating security standards.",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [
            "security standards",
            "automated behavior",
            "programmatic access"
          ],
          "entities": {
            "countries": [],
            "organizations": [],
            "people": []
          },
          "category": "technology",
          "relevance_to_topic": "low"
        }
      },
      "vlm_analysis": {
        "results": []
      }
    },
    {
      "source": "creativefabrica.com",
      "country": "unknown",
      "url": "https://www.creativefabrica.com/pt/product/turkey-economy-infographic-charts/",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T19:23:19.258645",
      "title": "Turkey Economy Infographic Charts GrÃ¡fico por terrabismail Â· Creative Fabrica",
      "content": "Os itens no seu carrinho no esto disponveis na moeda selecionada. Deseja continuar na moeda selecionada e remover estes produtos do seu carrinho?\n\nSobre Turkey Economy Infographic Charts Grfico\n\nTurkey Economy Infographic, Economic Statistics Data Of Turkey charts Presentation, Visual representations of information, data, and knowledge For Advertising, marketing, Education Courses, And All Kinds Of Projects.\n\nYou will get the below format on source files : Eps SVG DXF PNG JPG\n\nVoc fez algo usando este produto? Compartilhe uma imagem de seu projeto para que outros possam se inspirar em sua criao! Sua postagem ficar visvel para outras pessoas nesta pgina e em seu prprio feed social.\n\nA Creative Fabrica foi criada em Amsterd, uma das cidades mais inspiradoras do mundo.\n\nTrazemos as melhores ferramentas possveis para melhorar sua criatividade e produtividade.\n\nNos encontre no: Westerstraat 187, 1015 MA Amsterdam, The Netherlands\n\nCmara do Comrcio: 70114412 Tributo: NL858147877B01\n\nSeus dados so tratados com segurana por nossos parceiros\n\nUm novo cdigo foi enviado para o seu e-mail.\n\nNo recebeu nenhum e-mail? Reenviar o cdigo\n\nAinda no tem conta? Inscreva-se gratuitamente\n\nPerdeu sua senha? Digite seu nome de usurio ou endereo de e-mail. Voc receber um link por e-mail para criar uma nova senha.\n\nUm novo cdigo foi enviado para o seu e-mail.\n\nNo recebeu nenhum e-mail? Reenviar o cdigo",
      "description": "Clique aqui e baixe a Turkey Economy Infographic Charts grÃ¡fico Â· Window, Mac, Linux Â· Ãltima atualizaÃ§Ã£o 2026 Â· LicenÃ§a comercial incluÃ­da â",
      "media": {
        "main_image": "https://cdn.creativefabrica.com/2023/01/27/Turkey-Economy-Infographic-charts-Graphics-59077412-1.jpg",
        "content_images": [
          "https://cdn.creativefabrica.com/2021/06/15/get-all-access.jpg",
          "https://cdn.creativefabrica.com/2023/01/27/Turkey-Economy-Infographic-charts-Graphics-59077412-1-1-580x390.jpg",
          "https://cdn.creativefabrica.com/2023/01/27/Turkey-Economy-Infographic-charts-Graphics-59077412-2-580x411.jpg"
        ],
        "videos": []
      },
      "source_type": "agent_surface",
      "llm_analysis": {
        "result": {
          "summary": "Clique aqui e baixe a Turkey Economy Infographic Charts grÃ¡fico Â· Window, Mac, Linux Â· Ãltima atualizaÃ§Ã£o 2026 Â· LicenÃ§a comercial incluÃ­da â",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [
            "itens",
            "carrinho",
            "disponveis",
            "moeda",
            "selecionada"
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
            "original_url": "https://cdn.creativefabrica.com/2023/01/27/Turkey-Economy-Infographic-charts-Graphics-59077412-1.jpg",
            "description": "Title: \"TURKEY ECONOMY\" Visuals: Map of Turkey with the flag. Turkish flag icons. Various charts and icons representing economic data. Sections: Labor Force and Unemployment: Unemployment rate (2021): 13.39% Total Population (2021): 84.78 Million Labor Force (2021): 32.62 Million Unemployed: 4.37 Million Gross Domestic Product (GDP): GDP (per capital) (2021): $9,661.24 GDP (2021): $819 Billion Real growth rate: 11.4% House Hold Income and Poverty: Median Income (2021): $40,094 Per Household (Per Year) Minimum Wage (2023): $455 Per Month Gini Index (2019): 0.42 Population below poverty line (2019): 10.2% Balance of Trade: Exports 2021: $288.57 Billion Imports 2021: $292.01 Billion Trade Deficit: $3.44 Billion Debt and Inflation: External Debt (2022): $442.9 Billion (54.08% of GDP) Inflation Rate (Dec 2022): 64.3% 2. Contextualize with Article: The article title is \"Turkey Economy Infographic Charts GrÃ¡fico por terrabismail Â· Creative Fabrica\". The",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "medium"
          },
          {
            "minio_path": null,
            "original_url": "https://cdn.creativefabrica.com/2021/06/15/get-all-access.jpg",
            "description": "Content: The image is a collage of many different digital design assets. It looks like a screenshot of a marketplace or a collection of digital downloads. Specific Items: Fonts (e.g., \"Angelica\", \"Boyfriend\", \"Hello Homework\", \"Sunday Morning\", \"Hey Hearts\", \"LOVER\"). Clipart/Icons (e.g., turtles, mice, gnomes, deer, cats in cups, unicorns, hummingbirds). Graphics/Patterns (e.g., \"Vintage Onomatopoeia\", \"Summer Chimes\", \"Bee Bundle\", \"Fairytale Bundle\"). Templates (e.g., \"Turkey Economy Infographic Charts\" - wait, looking closely at the top left, there's a \"Turkey Economy Infographic\" mentioned in the prompt, but looking at the image itself, I see a \"Turkey Economy Infographic\" isn't explicitly the main focus, but rather a general collection of fonts and graphics. Wait, let me re-examine the prompt's article title vs the image. Correction: The prompt says \"Article title: Turkey Economy Infographic Charts GrÃ¡fico por terrabismail Â· Creative Fabrica\". This suggests the article is about a specific product called \"Turkey Economy Infographic Charts\". However, the image provided is a massive collage of many different products (fonts, clipart, bundles). It looks like a homepage or a \"feat",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "medium"
          },
          {
            "minio_path": null,
            "original_url": "https://cdn.creativefabrica.com/2023/01/27/Turkey-Economy-Infographic-charts-Graphics-59077412-1-1-580x390.jpg",
            "description": "Title: \"TURKEY ECONOMY\" in a red banner at the top. Visual Elements: A large red map of Turkey with the white crescent and star. Turkish flags. Various icons representing economic concepts (people, money bags, graphs, houses, etc.). Data Points (Left Column): Labor Force and Unemployment: Unemployment rate: 13.39% (13.39% Unemployed, 86.61% Employed). Population & Labor Force: Total Population 84.78 Million, Labor Force 32.62 Million. Unemployed: 4.37 Million. House Hold Income and Poverty: Income and Distribution: Median Income $40,094 Per Household, Minimum Wage $455 Per Month. Gini Index: 0.42. Population below poverty line: 10.2%. Data Points (Right Column - Top): Gross Domestic Product (GDP): GDP (per capita): $9,661.24. GDP: $819 Billion. Real growth rate: 11.4%. Data Points (Right Column - Bottom): Balance of Trade: Exports 2021: $288.57 Billion. Imports 2021: $292.01 Billion. Trade Deficit: $3.44 Billion. Debt and Inflation: External Debt: $442.9 Billion (54.08% of GDP). Inflation Rate: 64.3% (Dec 2022). 2. Contextualize with Article: The",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "medium"
          }
        ]
      }
    },
    {
      "source": "googleapis.com",
      "country": "unknown",
      "url": "https://storage.googleapis.com/doszvmntbhmfke/turkey-economy-overview.html",
      "keyword_found": "Turkey economy 2026",
      "scraped_at": "2026-05-11T19:28:33.052962",
      "title": "Turkey Economy Overview at Jason Lindstrom blog",
      "content": "Turkey Economy Overview. According to the ranking by gross domestic product, turkey became the 19th largest economy in the world in 2022 with its gdp amounting to 905 billion u.s. The snapshot offers a concise summary of tÃ¼rkiye's economic trends and prospects, drawing from the oecd economic survey, economic. Turkey has large external financing needs, and its private sector is heavily indebted in foreign currency, raising risks to financial stability. TÃ¼rkiye is the 17 th largest economy in the world, according to imf, with a gdp of $1.024 trillion as of 2023. The key tables by country statistical profiles include a wide range of indicators on economy, education, energy, environment, foreign aid,. Overview in 2022, turkey was the number 19 economy in the world in terms of gdp (current us$), the number 29 in total exports, the number 22 in total imports, the number 75 economy in terms. It is a member of the. Turkeyâs economic growth slows to weakest level since covid crisis high interest rates meant to cool runaway inflation heaps.\n\nThe key tables by country statistical profiles include a wide range of indicators on economy, education, energy, environment, foreign aid,. Overview in 2022, turkey was the number 19 economy in the world in terms of gdp (current us$), the number 29 in total exports, the number 22 in total imports, the number 75 economy in terms. TÃ¼rkiye is the 17 th largest economy in the world, according to imf, with a gdp of $1.024 trillion as of 2023. According to the ranking by gross domestic product, turkey became the 19th largest economy in the world in 2022 with its gdp amounting to 905 billion u.s. Turkey has large external financing needs, and its private sector is heavily indebted in foreign currency, raising risks to financial stability. The snapshot offers a concise summary of tÃ¼rkiye's economic trends and prospects, drawing from the oecd economic survey, economic. It is a member of the. Turkeyâs economic growth slows to weakest level since covid crisis high interest rates meant to cool runaway inflation heaps.\n\nPPT ECONOMY OF TURKEY PowerPoint Presentation, free download ID2479180\n\nTurkey Economy Overview The key tables by country statistical profiles include a wide range of indicators on economy, education, energy, environment, foreign aid,. According to the ranking by gross domestic product, turkey became the 19th largest economy in the world in 2022 with its gdp amounting to 905 billion u.s. Turkeyâs economic growth slows to weakest level since covid crisis high interest rates meant to cool runaway inflation heaps. The key tables by country statistical profiles include a wide range of indicators on economy, education, energy, environment, foreign aid,. Overview in 2022, turkey was the number 19 economy in the world in terms of gdp (current us$), the number 29 in total exports, the number 22 in total imports, the number 75 economy in terms. It is a member of the. Turkey has large external financing needs, and its private sector is heavily indebted in foreign currency, raising risks to financial stability. The snapshot offers a concise summary of tÃ¼rkiye's economic trends and prospects, drawing from the oecd economic survey, economic. TÃ¼rkiye is the 17 th largest economy in the world, according to imf, with a gdp of $1.024 trillion as of 2023.",
      "description": "Turkey Economy Overview. According to the ranking by gross domestic product, turkey became the 19th largest economy in the world in 2022 with its gdp amounting to 905 billion u.s. The snapshot offers a concise summary of tÃ¼rkiye's economic trends and prospects, drawing from the oecd economic survey, economic. Turkey has large external financing needs, and its private sector is heavily indebted in foreign currency, raising risks to financial stability. TÃ¼rkiye is the 17 th largest economy in the world, according to imf, with a gdp of $1.024 trillion as of 2023. The key tables by country statistical profiles include a wide range of indicators on economy, education, energy, environment, foreign aid,. Overview in 2022, turkey was the number 19 economy in the world in terms of gdp (current us$), the number 29 in total exports, the number 22 in total imports, the number 75 economy in terms. It is a member of the. Turkeyâs economic growth slows to weakest level since covid crisis high interest rates meant to cool runaway inflation heaps.",
      "media": {
        "main_image": "https://image1.slideserve.com/2479180/economy-of-turkey-l.jpg",
        "content_images": [],
        "videos": []
      },
      "source_type": "agent_surface",
      "llm_analysis": {
        "result": {
          "summary": "Turkey Economy Overview. According to the ranking by gross domestic product, turkey became the 19th largest economy in the world in 2022 with its gdp amounting to 905 billion u.s. The snapshot offers a concise summary of tÃ¼rkiye's economic trends and prospects, drawing from the oecd economic survey, economic. Turkey has large external financing needs, and its private sector is heavily indebted in foreign currency, raising risks to financial stability. TÃ¼rkiye is the 17 th largest economy in the ",
          "sentiment": 0,
          "sentiment_label": "neutral",
          "keywords": [
            "Turkey",
            "Economy",
            "Overview",
            "According",
            "ranking"
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
            "original_url": "https://image1.slideserve.com/2479180/economy-of-turkey-l.jpg",
            "description": "Text: \"ECONOMY OF TURKEY\" in large, black, serif font. Visuals: Red vertical bars of varying heights, resembling a bar chart or graph. A large white crescent moon and a white five-pointed star superimposed over the bars. These are the symbols of the Turkish flag. The background is a mix of white and red, reinforcing the flag colors. Overall Theme: It's a title slide or a header image for a presentation or article about the Turkish economy. 2. Analyze the Article Context: Title: \"Turkey Economy Overview at Jason Lindstrom blog\" Content: Discusses Turkey's GDP ranking (19th in 2022, 17th in 2023), GDP amounts ($905 billion, $1.024 trillion), external financing needs, private sector debt, and references OECD and IMF data. Relevance: The image is a direct visual representation of the article's topic. It serves as a title card. 3. Synthesize the Analysis: Description: The image features the text \"ECONOMY OF TURKEY\" overlaid on a graphic combining a bar chart with the crescent moon and star symbol of the Turkish flag. Objects: Text (\"ECONOMY OF TURKEY\"), Bar chart (red bars), Crescent moon (white), Star (white), Flag elements. Sentiment: The image itself is neutral. It's an informational",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "medium"
          }
        ]
      }
    }
  ],
  "status": "COMPLETED",
  "stop_reason": "max_articles_reached"