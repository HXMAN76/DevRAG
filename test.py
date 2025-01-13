import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, Tuple, Optional
import re

class WebCrawler:
    def __init__(self, max_depth: int = 3, max_concurrent: int = 10):
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent
        self.visited = set()
        self.results = []
        
        # Compile regex patterns
        self.skip_extensions = re.compile(r'\.(pdf|jpg|jpeg|png|gif|css|js|xml|ico)$', re.I)
        
    async def fetch_page(self, url: str, session: aiohttp.ClientSession) -> Tuple[Optional[str], Optional[str], Set[str]]:
        """Fetch and parse a single page."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return None, None, set()
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract title
                title = soup.title.string if soup.title else url
                
                # Extract content
                for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                    element.decompose()
                content = ' '.join(text.strip() for text in soup.stripped_strings if text.strip())
                
                # Extract links
                base_domain = urlparse(url).netloc
                links = set()
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if not href or href.startswith(('#', 'mailto:', 'tel:')):
                        continue
                        
                    try:
                        full_url = urljoin(url, href)
                        parsed = urlparse(full_url)
                        
                        # Only include links to the same domain without excluded extensions
                        if (parsed.netloc == base_domain and 
                            not self.skip_extensions.search(parsed.path)):
                            links.add(full_url)
                    except Exception:
                        continue
                
                return title, content, links
                
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None, None, set()

    async def crawl(self, start_url: str) -> str:
        """Crawl the website starting from the given URL."""
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Start with initial URL
            to_visit = [(start_url, 0)]  # (url, depth)
            
            while to_visit:
                current_batch = []
                next_batch = []
                
                # Group URLs by current depth
                current_depth = min(depth for _, depth in to_visit)
                
                for url, depth in to_visit:
                    if depth == current_depth:
                        current_batch.append(url)
                    else:
                        next_batch.append((url, depth))
                
                if current_depth >= self.max_depth:
                    break
                               
                # Process current batch
                async def process_url(url):
                    async with semaphore:
                        return url, await self.fetch_page(url, session)
                
                tasks = [process_url(url) for url in current_batch]
                results = await asyncio.gather(*tasks)
                
                # Process results and collect new URLs
                to_visit = next_batch
                
                for url, (title, content, links) in results:
                    if not content:
                        continue
                        
                    self.visited.add(url)
                    self.results.append({
                        'depth': current_depth,
                        'url': url,
                        'title': title,
                        'content': content
                    })
                    
                    # Add new links to visit
                    if current_depth + 1 < self.max_depth:
                        new_links = links - self.visited
                        to_visit.extend((link, current_depth + 1) 
                                     for link in new_links)
            
            # Generate output sorted by depth
            output = []
            for depth in range(self.max_depth):
                depth_content = [item for item in self.results if item['depth'] == depth]
                for item in depth_content:
                    output.append(f"{item['content']}\n\n")
            
            return '\n'.join(output)

async def main():
    try:
        url = "https://docs.github.com/en"  # Replace with target website
        crawler = WebCrawler(max_depth=3, max_concurrent=5)
        result = await crawler.crawl(url)
        
        with open('output.md', 'w', encoding='utf-8') as f:
            f.write(result)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())