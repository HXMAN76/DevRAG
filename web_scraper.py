import asyncio
from crawl4ai import AsyncWebCrawler
from langchain.text_splitter import RecursiveCharacterTextSplitter

class WebScraper:
    def __init__(self):
        pass

    async def webscrape(self, url: str):
        async with AsyncWebCrawler() as crawler:
            try:
                result = await crawler.arun(
                    url=f"{url}",
                    magic=True,
                    simulate_user=True,
                    override_navigator=True,
                    exclude_external_images=True,
                    exclude_social_media_links=True,
                )
                return result
            except Exception as e:
                print(f"Error during web crawling: {e}")
                return None

    def wrapper(self, url: str):
        scrape_data = ''
        data = asyncio.run(self.webscrape(url))
        unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact', 'sign up', 'sign in', 'expert services']
        social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
        if data and data.markdown:
            scrape_data += data.markdown
        for key in data.links:
            for link in data.links[key]:
                text = link.get('text', '').casefold()
                href = link.get('href', '')
                if text in unwanted or any(platform in href for platform in social_media):
                    continue 

                sub_data = asyncio.run(self.webscrape(link["href"]))
                if sub_data and sub_data.markdown:
                    scrape_data += sub_data.markdown
        return scrape_data

    def semantic_chunking(self, text: str, chunk_size: int = 512, chunk_overlap: int = 50):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_text(text)
        return chunks