import asyncio
import json
import os
from typing import List, Optional
import snowflake.connector
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from snowflake.core import Root
from snowflake.snowpark import Session
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

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
    
class WebScraper:
    def __init__(self):
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 
                        'pricing', 'contact', 'sign up', 'sign in', 'expert services']
        self.social_media = ['youtube', 'twitter', 'facebook', 'linkedin']

    async def _webscrape(self, url: str) -> Optional[object]:
        async with AsyncWebCrawler() as crawler:
            try:
                return await crawler.arun(
                    url=url,
                    magic=True,
                    simulate_user=True, 
                    override_navigator=True,
                    exclude_external_images=True,
                    exclude_social_media_links=True,
                )
            except Exception as e:
                print(f"Error during web crawling: {e}")
                return None

    def scrape(self, url: str) -> str:
        scrape_data = ''
        data = asyncio.run(self._webscrape(url))
        
        if data and data.markdown:
            scrape_data += data.markdown
            
        for key in data.links:
            for link in data.links[key]:
                text = link.get('text', '').casefold()
                href = link.get('href', '')
                
                if text in self.unwanted or any(platform in href for platform in self.social_media):
                    continue
                    
                sub_data = asyncio.run(self._webscrape(link["href"]))
                if sub_data and sub_data.markdown:
                    scrape_data += sub_data.markdown
                    
        return scrape_data

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
    website_link = ""
    query = input("Enter the query: ")
    
    scraper = WebScraper()
    processor = TextProcessor()
    snowflake = SnowflakeManager()
    git = GithubScraper(website_link)
    domain_name = DomainExtractor()
    
    try:
        
        # Connect to Snowflake
        snowflake.connect()
        
        if website_link:
            # Scrape and process content
            content = scraper.scrape(website_link)
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