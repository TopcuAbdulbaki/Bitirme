"""from crawl4ai import AsyncWebCrawler
import asyncio

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url = "https://www.haber7.com"
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
"""

import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    browser_config = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 1. Arama sayfasına terim gir
        run_config_search = CrawlerRunConfig(
            js_code = """
              document.querySelector('#search-input').value = 'Türkiye';
              document.querySelector('#search-form').submit();
            """,
            wait_for = "css:.search-results-item"
        )
        # Başlangıç URL arama sayfası
        search_url = "https://haber7.com/search"
        result_search = await crawler.arun(url=search_url, config=run_config_search)
        # Linkleri çıkar
        links = result_search.links.get("internal", [])
        for link in links:
            href = link["href"]
            # 2. Her bir linke gir ve içerikleri çıkar
            run_config_content = CrawlerRunConfig()
            result_content = await crawler.arun(url=href, config=run_config_content)
            print("URL:", href)
            print("Markdown:", result_content.markdown.raw_markdown[:200])

if __name__ == "__main__":
    asyncio.run(main())