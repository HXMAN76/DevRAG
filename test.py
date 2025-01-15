import asyncio
import json
import os
from typing import List, Optional, Set, Tuple
import snowflake.connector
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from snowflake.core import Root
from snowflake.snowpark import Session
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import aiohttp

class GithubScraper:
    def __init__(self, url):
        self.url = url

    def webscrape_content(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)
            page.wait_for_timeout(5000)  # Wait for content to load
            
            html_content = page.content()  # Get the page content
            browser.close()
            return html_content

    @staticmethod
    def extract_main_content(html):
        soup = BeautifulSoup(html, 'html.parser')
        textareas = soup.find_all('textarea')  # Find all <textarea> elements
        if textareas:
            return textareas

    @staticmethod
    def replace_hub_with_ingest(url):
        if "github.com" in url:
            return url.replace("github.com", "gitingest.com")
        return url

    def scrape_github(self):
        self.url = self.replace_hub_with_ingest(self.url)
        html_content = self.webscrape_content()
        return self.extract_main_content(html_content)
    
class DomainExtractor:
    @staticmethod
    def extract_domain(url):
        match = re.search(r"https?://(?:www\.)?([^./]+)\.([^./]+)\.", url)
        if match:
            return match.group(2)
        return None

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

class TextProcessor:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def chunk_text(self, text: str) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_text(text)

class SnowflakeManager:
    def __init__(self):
        load_dotenv()
        self.connection_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "role": "ACCOUNTADMIN",
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        }
        self.session = None
        self.conn = None
        self.cursor = None
        
    def connect(self):
        self.conn = snowflake.connector.connect(**self.connection_params)
        self.cursor = self.conn.cursor()
        self.session = Session.builder.configs(self.connection_params).create()
        
    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        if self.session:
            self.session.close()
            
    def insert_document(self, web_url: str, content: str):
        query = "INSERT INTO DEVRAG_SCHEMA.DOCUMENT (WEBSITE_URL, CONTENT) VALUES (%s, %s)"
        self.cursor.execute(query, (web_url, content))
        self.conn.commit()
        
    def search_and_generate(self, query: str) -> str:
        root = Root(self.session)
        search_service = (
            root
            .databases["DEVRAG_DB"]
            .schemas["DEVRAG_SCHEMA"]
            .cortex_search_services["DEVRAG"]
        )
        
        search_results = search_service.search(
            query=query,
            columns=["CONTENT"],
            limit=5
        )
        
        response = json.dumps(search_results.to_dict())
        generation_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
                Document: {response}
                Query: {query}$$
            );
        """
        
        try:
            generation = self.session.sql(generation_query).collect()
            return generation[0][0]
        except Exception as e:
            return f"Error: {e}"

def main():
    website_link = "https://docs.github.com/en"  # Replace with the URL you want to scrape
    query = input("Enter the query: ")
    
    crawler = WebCrawler(max_depth=3, max_concurrent=5)
    processor = TextProcessor()
    snowflake = SnowflakeManager()
    git = GithubScraper(website_link)
    domain_name = DomainExtractor().extract_domain(website_link)
    
    try:
        # Connect to Snowflake
        snowflake.connect()
        
        if website_link:
            # Scrape and process content
            content = asyncio.run(crawler.crawl(website_link))
            chunks = processor.chunk_text(content)
            
            # Store chunks in Snowflake
            for chunk in chunks:
                snowflake.insert_document(website_link, chunk)
            
        # Generate response
        response = snowflake.search_and_generate(query)
        print(response)  
    
    finally:
        snowflake.disconnect()
    

if __name__ == "__main__":
    main()