import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter

async def recursive_crawl(start_url: str, max_pages: int = 200, max_concurrent: int = 20, chunk_size: int = 512, chunk_overlap: int = 50) -> list:
    """
    Recursive web crawler with semantic chunking of content.
    :param start_url: The URL to start crawling from
    :param max_pages: Total number of pages to crawl
    :param max_concurrent: Maximum concurrent requests
    :param chunk_size: Maximum size of each chunk for semantic splitting
    :param chunk_overlap: Overlap size between chunks for context
    :return: List of dictionaries containing crawled data
    """
    # Extract the main domain using regex
    main_domain_match = re.search(r"https?://(?:www\.)?([^/]+)", start_url)
    main_domain = main_domain_match.group(1) if main_domain_match else urlparse(start_url).netloc

    visited = set()
    content = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
        """Fetch the HTML content of a URL."""
        async with semaphore:
            try:
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10) as response:
                    if response.status == 200 and "text/html" in response.headers.get("content-type", "").lower():
                        return await response.text()
            except Exception:
                pass
        return None

    async def crawl(session: aiohttp.ClientSession, urls: list, page_count: list):
        """Crawl URLs iteratively until the max_pages limit is reached."""
        while urls and page_count[0] < max_pages:
            url = urls.pop(0)  # Process the first URL in the list
            if url in visited or page_count[0] >= max_pages:
                continue
            visited.add(url)
            page_count[0] += 1

            html = await fetch_page(session, url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()

            # Extract content
            main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|article"))
            text = main_content.get_text() if main_content else soup.get_text()
            clean_text = "\n\n".join(
                re.sub(r"[^\w\s.,!?-]", "", re.sub(r"\s+", " ", line)).strip()
                for line in text.splitlines() if len(line.strip()) > 20
            )

            if len(clean_text) > 50:
                # Perform semantic chunking
                chunks = semantic_chunking(clean_text, chunk_size, chunk_overlap)
                content.append({
                    "url": url,
                    "title": (soup.title.string.strip() if soup.title else url),
                    "chunks": chunks,
                    "crawled_at": datetime.now().isoformat(),
                })

            # Add new links to the queue
            new_links = {urljoin(url, a["href"]) for a in soup.find_all("a", href=True)}
            for link in new_links:
                if urlparse(link).netloc == main_domain and link not in visited and len(visited) < max_pages:
                    urls.append(link)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=max_concurrent)) as session:
        page_count = [0]
        await crawl(session, [start_url], page_count)

    return content

def semantic_chunking(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list:
    """
    Split text into semantic chunks using RecursiveCharacterTextSplitter.
    :param text: The full text to split
    :param chunk_size: Maximum size of each chunk
    :param chunk_overlap: Overlap size between chunks for context
    :return: List of chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return text_splitter.split_text(text)

async def main():
    url = input("Enter website URL to crawl: ")
    try:
        result = await recursive_crawl(url, max_pages=200, max_concurrent=20, chunk_size=512, chunk_overlap=50)
        with open("crawled_data.json", "w") as f:
            json.dump(result, f, indent=4)
    except Exception as e:
        print(f"Error during crawling: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
