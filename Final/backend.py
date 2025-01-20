from typing import List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
from langchain.text_splitter import RecursiveCharacterTextSplitter

class GithubScraper:
    def __init__(self, url: str):
        self.url = url
    
    def url_changer(self) -> str:
        """Change GitHub URL to alternative domain"""
        return self.url.replace('github', 'gitingest')
    
    async def scrape_content(self) -> Optional[str]:
        """Scrape webpage content using Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Use modified URL from url_changer
                modified_url = self.url_changer()
                await page.goto(modified_url, timeout=30000)
                
                await page.wait_for_timeout(5000)
                content = await page.content()
                await browser.close()
                return content
        except Exception as e:
            print(f"Scraping error: {e}")
            return None
    
    @staticmethod
    def process_content(content: str) -> List[str]:
        """Extract text from textarea elements"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            data = soup.find_all('textarea')
            return [text.text for text in data] if data else []
        except Exception as e:
            print(f"Parsing error: {e}")
            return []
    
    async def get_data(self) -> List[str]:
        """Orchestrate scraping and processing"""
        content = await self.scrape_content()
        processed_content = self.process_content(content)
        data = ''
        if content:
            data += ''.join(text for text in processed_content)
        return data
        
class Web_Scraper:
    def __init__(self):
        pass
        
    def recursive_scraper(self, links):
        pass
        
    def get_data(self, url):
        pass
    
    def scrape_content(self, url):
        data , struc = self.get_data(url)
        data += self.recursive_scraper(struc.links)
        return data
    
class PDFScraper:
    def __init__(self):
        pass
    def extract_data(pdf_path):
        pass
    
class TextProcessor:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_text(text)

class SnowflakeManager:
    def __init__(self):
        self.uid = None
    
    def get_uid(self):
        # returns data from auth page
        pass
    def set_uid(self, uid):
        self.uid = uid
        
    def connect(self):
        # returns connection object
        pass       
    def disconnect(self):
        # disconnects the connection
        pass
    def insert_data(self,data,source):
        # inserts data into the database
        if source.casefold() == 'Github':
            # insert into github table
            pass
        elif source.casefold() == 'Web':
            # insert into web table
            pass
        elif source.casefold() == 'PDF':
            # insert into pdf table
            pass
    def search(self, query):
        # both common and user data
        pass
    
    def generate(self, query):
        response = self.search(query)
        INSTRUCTION = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
                Document: {response}
                Query: {query}$$
            );
        """
        generation = None # fill up
        return generation

class Memory:
    def __init__(self):
        pass

class LLMcalls:
    def __init__(self):
        pass
    
class Backend:
    def __init__(self):
        pass
    async def main(self):
        url = input("Enter url for github scraping:")
        github_scraper = GithubScraper(url)
        chunker = TextProcessor()
        data = await github_scraper.get_data()
        print(data)
        print(chunker.chunk_text(data))
    
if __name__ == '__main__':
    backend = Backend()
    asyncio.run(backend.main())