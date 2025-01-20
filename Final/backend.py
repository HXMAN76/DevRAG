from typing import List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import PyPDF2
import snowflake.connector
from snowflake.core import Root
from snowflake.snowpark import Session
import os
from dotenv import load_dotenv
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
from mistralai import Mistral
from crawl4ai import AsyncWebCrawler
import logging
from bs4 import BeautifulSoup
from ..combined import get_user_id
from collections import deque
logging.basicConfig(level=logging.INFO)
from concurrent.futures import ThreadPoolExecutor, as_completed
import toml
# Set logging level to WARNING to suppress unwanted info logs
logging.getLogger("snowflake.connector").setLevel(logging.WARNING)
logging.getLogger("snowflake.snowpark").setLevel(logging.WARNING)
logging.getLogger("snowflake.core").setLevel(logging.WARNING)

with open('secrets.toml','r') as file:
    secret = toml.load(file)

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
        

class WebScraper:
    def __init__(self, url: str, max_depth: int = 3):
        self.url = url
        self.max_depth = max_depth
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact']
        self.social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
        self.scrape_content = []
        self.visited = set()  # To keep track of visited URLs
        self.crawler = AsyncWebCrawler()

    def is_valid_url(self, url: str) -> bool:
        """Check if the URL starts with valid schemes."""
        pattern = re.compile(r'^(http://|https://|file://|raw:).*')
        return bool(pattern.match(url))

    async def get_data(self, url: str) -> Optional[str]:
        """Fetch data from the specified URL using AsyncWebCrawler."""
        try:
            data = await self.crawler.arun(
                url=url,
                magic=True,
                simulate_user=True,
                override_navigator=True,
                exclude_external_images=True,
                exclude_social_media_links=True,
            )
            return data
        except Exception as e:
            logging.error(f"Error fetching data from {url}: {e}")
            return None

    async def extract_links(self, html_content: str) -> List[str]:
        """Extract all valid links from the HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            # Ensure that the link is absolute and valid
            if self.is_valid_url(link) and not any(word in link for word in self.unwanted + self.social_media):
                links.append(link)
        
        return links

    async def dfs(self, url: str, depth: int) -> None:
        """Recursively scrape using depth-first search."""
        if depth > self.max_depth or url in self.visited or not self.is_valid_url(url):
            return  # Base case for recursion
        
        self.visited.add(url)  # Mark this URL as visited
        
        data = await self.get_data(url)
        if data is None:
            return  # Skip if there's no valid data
        
        # Extract links from the current page's HTML content
        links = await self.extract_links(data.html)
        
        # Append current URL content (if needed)
        self.scrape_content.append(data.markdown)

        # Recursively visit each link found
        for link in links:
            await self.dfs(link, depth + 1)

    async def scrape(self) -> List[str]:
        """Start the scraping process using DFS."""
        await self.dfs(self.url, 0)  # Start DFS from the initial URL at depth 0
        return self.scrape_content
    
class PDFScraper:

    def clean_text(text):
        # Replace all types of whitespace (including newlines, tabs) with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,!?:;])', r'\1', text)
        
        # Remove spaces at the beginning and end
        text = text.strip()
        
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove spaces at the beginning of lines
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
        
        # Remove spaces at the end of lines
        text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
        
        return text

    def extract_data(self,pdf_path):
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""
            
            for page in reader.pages:
                page_text = page.extract_text()
                extracted_text += page_text + "\n"
            
            # Apply thorough cleaning after all text is extracted
            extracted_text = self.clean_text(extracted_text)
        return extracted_text
    
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
        chunks = text_splitter.split_text(text)
        return [chunk.replace('\n', '') for chunk in chunks]

class SnowflakeManager:
    def __init__(self):
        self.uid = None
        load_dotenv()
        self.connection_params = {
            "account": secret['SNOWFLAKE']['ACCOUNT'],
            "user": secret["SNOWFLAKE"]["USER"],
            "password": secret["SNOWFLAKE"]["PASSWORD"],
            "role": "ACCOUNTADMIN",
            "database": secret["SNOWFLAKE"]["DATABASE"],
            "warehouse": secret["SNOWFLAKE"]["WAREHOUSE"],
            "schema":secret["SNOWFLAKE"]["SCHEMA"]
        }
        self.session = None
        self.conn = None
        self.cursor = None
        self.uid = get_user_id()
        
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

    def _insert(self, table_name, contents):
        if contents:
            insert_queries = [f"INSERT INTO {table_name} (content) VALUES ('{content}')" for content in contents]
            for query in insert_queries:
                self.cursor.execute(query)
            self.conn.commit()
    
    def insert_into_github_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_github", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise an exception if the insert failed
                except Exception as e:
                    print(f"Error inserting into {user_id}_github: {e}")

    def insert_into_personal_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_rag", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_rag: {e}")

    def insert_into_pdf_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_pdf", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_pdf: {e}")

    def _search_service(self, user_id, service_name, query):
        root = Root(self.session)
        search_service = (
            root.databases[secret["SNOWFLAKE"]["DATABASE"]]
                .schemas[secret["SNOWFLAKE"]["SCHEMA"]]
                .cortex_search_services[service_name]
        )
        search_results = search_service.search(query=query, columns=["CONTENT"], limit=5)
        return json.dumps(search_results.to_dict())

    def search(self, user_id, query: str) -> list:
        services = {
            "common": secret["SNOWFLAKE"]["WAREHOUSE"],
            "personal": f"{user_id}_ragsearch",
            "github": f"{user_id}_githubsearch",
            "pdf": f"{user_id}_pdfsearch"
        }

        results = []
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._search_service, user_id, service_name, query): name for name, service_name in services.items()}
            
            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error searching in {service_name}: {e}")

        return results

    def generate(self, query,user_id):
        document_details = self.search(query)
        conversation_memory = Memory().retrieve_memory(user_id)
        
        instruction = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$  You are a helpful assistant using a Retrieval-Augmented Generation (RAG) method to answer user queries.  
                    Here are the inputs provided to you:  

                    ### Contextual Information
                    1. **Document Details**: 
                        {document_details}
                    2. **Memory (Previous Conversation History)**:  
                        {conversation_memory}
                    3. **User Query**:  
                        {query}
                    ### Instructions:  
                        - Use the provided **Document Details** as the primary source of truth to answer the query.  
                        - Refer to the **Memory** to maintain conversation context and continuity. Use this information to make your response coherent and contextual.  
                        - If relevant information from the **Memory** or **Document Details** is missing, clarify this in your response and guide the user on how to proceed.  
                    ### Response:  
                        - Be concise and accurate. If additional explanations are required, provide them clearly.  
                        - Ensure your response aligns with the user's intent as reflected in the query and conversation context.  
                        - Where applicable, suggest follow-up actions or related queries for deeper understanding.

                    --- 
                    **Example Input**:  

                        - **Document Details**:  
                                "This document is a developer's guide for integrating payment APIs. It includes sections on API authentication, error handling, and webhook configurations."  
                        - **Memory**:  
                            1.  User: "What are the common errors during payment API integration?"  
                                Assistant: "The common errors include invalid API keys, incorrect endpoint URLs, and missing webhook signatures."  
                            2.  User: "How do I fix invalid API key errors?"  
                                Assistant: "Ensure you're using the API key issued for your account and verify it matches the required permissions."  

                        - **User Query**:  
                                "What are webhook configurations, and how do they work?"  
                    **Example Output**:  
                                "Webhook configurations are settings that allow your application to receive real-time updates from the payment API when specific events occur (e.g., successful payments, refunds). Configure the webhook URL in your API dashboard, ensure it points to an accessible endpoint, and validate incoming requests using the signature provided in the header to ensure authenticity."$$,
                {
                    'temperature': 0.42
                }
            );"""

        generation = self.session.sql(instruction).collect()
        return generation[0][0]

class Memory:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            self.firebase_credentials = {
                "type": secret["FIREBASE"]["TYPE"],
                "project_id": secret["FIREBASE"]["PROJECT_ID"],
                "private_key_id": secret["FIREBASE"]["PRIVATE_KEY_ID"],
                "private_key": secret["FIREBASE"]["PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": secret["FIREBASE"]["CLIENT_EMAIL"],
                "client_id": secret["FIREBASE"]["CLIENT_ID"],
                "auth_uri": secret["FIREBASE"]["AUTH_URI"],
                "token_uri": secret["FIREBASE"]["TOKEN_URI"],
                "auth_provider_x509_cert_url": secret["FIREBASE"]["AUTH_PROVIDER_X509_CERT_URL"],
                "client_x509_cert_url": ["FIREBASE"]["CLIENT_X509_CERT_URL"],
                "universe_domain": secret["FIREBASE"]["UNIVERSE_DOMAIN"]
            }
            cred = credentials.Certificate(self.firebase_credentials)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.api_key = secret["FIREBASE"]["API_KEY"]
    
    def create_summary(conversations):
        """
        Creates a summary of conversations using Mistral AI
        """
        try:
            api = secret["MISTRAL"]["API_KEY"]
            if not api:
                raise ValueError("SUMMARIZER API key not found in environment variables")
                
            # Format conversations for Mistral
            formatted_conversations = []
            for conv in conversations:
                formatted_conversations.append(f"User: {conv['query']}\nAssistant: {conv['response']}")
            
            conversation_text = "\n\n".join(formatted_conversations)
            
            client = Mistral(api_key=api)  # Corrected parameter name
            
            chat = client.chat.completions.create(  # Corrected method name
                model="mistral-large-v2",  # Corrected model name
                messages=[
                    {
                        "role": "system",
                        "content": "Please summarize the following conversations into a concise paragraph that captures the main topics discussed and key points from both the user's queries and the assistant's responses."
                    },
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ],
                temperature=0.5
            )
            
            return chat.choices[0].message.content
            
        except Exception as e:
            # Fallback to basic summary if Mistral API fails
            return f"Error creating summary with Mistral: {str(e)}"
    
    def manage_conversations(self, user_id, query, response):
        """
        Manages conversations by:
        1. Adding new conversation
        2. Checking if there are 5 conversations
        3. If yes, summarizes them using Mistral AI
        4. Clears the conversations list
        """
        try:
            # Get user document reference
            user_ref = self.db.collection('user_data').document(user_id)
            user_doc = user_ref.get()
            user_data = user_doc.to_dict()
            
            # Add new conversation
            conversation = {
                'query': query,
                'response': response
            }
            
            # Get current conversations
            conversations = user_data.get('past_conversations', [])
            conversations.append(conversation)
            
            # Check if we've reached 5 conversations
            if len(conversations) >= 5:
                # Create summary of conversations
                summary = {
                    'summary_text':self.create_summary(conversations),
                    'original_conversations': conversations
                }
                
                # Update document with summary and clear conversations
                user_ref.update({
                    'conversation_summary': firestore.ArrayUnion([summary]),
                    'past_conversations': [] # Clear the conversations list
                })
            else:
                # Just update with new conversation
                user_ref.update({
                    'past_conversations': conversations
                })
                
            return True
            
        except Exception as e:
            raise Exception(f"Failed to manage conversations: {str(e)}")
        
    def retrieve_memory(self,user_id):
        user_ref = self.db.collection('user_data').document(user_id)
        user_doc = user_ref.get()
        user_data = user_doc.to_dict()
        conversations = user_data.get('past_conversations', [])
        summary_conversations = user_data.get('conversation_summary', [])
        if summary_conversations:
            conversations.append(summary_conversations[0])
        return conversations
        
class LLMcalls:
    def __init__(self):
        pass
    
class Backend:
    def __init__(self):
        self.chunker = TextProcessor()
    async def main(self):
        # github scraping 
        url = input("Enter url for github scraping:")
        github_scraper = GithubScraper(url)
        data = await github_scraper.get_data()
        print(self.chunker.chunk_text(data))
        # url = input("Enter url for web scraping:")
        # scraper = WebScraper(url)
        # data = await scraper.scrape()
        # print(data)
        
        #github scraping 
        # url = input("Enter url for github scraping:")
        # github_scraper = GithubScraper(url)
        # data = await github_scraper.get_data()
        # print(self.chunker.chunk_text(data))
        pass
    
if __name__ == '__main__':
    backend = Backend()
    asyncio.run(backend.main())