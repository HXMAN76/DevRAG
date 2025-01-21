import os
import re
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import toml
import tempfile
from functools import partial
import nest_asyncio
# Middleware Libraries

# Core Libraries
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2

# Database and External Services
import snowflake.connector
from snowflake.snowpark import Session
from snowflake.core import Root
import firebase_admin
from firebase_admin import credentials, firestore

# AI Integration
from mistralai import Mistral
from crawl4ai import AsyncWebCrawler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperBase:
    """Base class for all scrapers with common functionality"""
    def __init__(self, url: str = ''):
        self.url = url
        self.visited = set()
        self.crawler = AsyncWebCrawler()

    def is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        return re.match(r'^(http://|https://|file://|raw:).*', url) is not None

class WebScraper(ScraperBase):
    """Advanced web scraping with depth-first search"""
    def __init__(self, url: str, max_depth: int = 3):
        super().__init__(url)
        self.max_depth = max_depth
        self.scrape_content: List[str] = []
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact']
        self.social_media = ['youtube', 'twitter', 'facebook', 'linkedin']

    async def scrape(self) -> List[str]:
        """Orchestrate web scraping process"""
        await self._recursive_scrape(self.url, 0)
        return self.scrape_content

    async def _recursive_scrape(self, url: str, depth: int) -> None:
        """Recursive depth-first web scraping"""
        if depth > self.max_depth or url in self.visited:
            return

        self.visited.add(url)
        try:
            data = await self.crawler.run(
                url=url,
                magic=True,
                simulate_user=True,
                override_navigator=True,
                exclude_external_images=True,
                exclude_social_media_links=True,
            )
            if data and data.markdown:
                self.scrape_content.append(data.markdown)

                links = [
                    link for link in self._extract_links(data.html)
                    if self.is_valid_url(link)
                ]

                for link in links:
                    await self._recursive_scrape(link, depth + 1)
        except Exception as e:
            logger.error(f"Web Scraping Error: {e}")

    def _extract_links(self, html_content: str) -> List[str]:
        """Intelligent link extraction"""
        soup = BeautifulSoup(html_content, 'html.parser')
        return [
            link['href'] for link in soup.find_all('a', href=True)
            if not any(keyword in link['href'] for keyword in self.unwanted + self.social_media)
        ]

class GithubScraper:
    def __init__(self, url: str):
        self.url = self.url_changer(url)

    def url_changer(self, url) -> str:
        """Change GitHub URL to alternative domain"""
        return url.replace('github', 'gitingest')

    async def scrape_content(self) -> Optional[str]:
        """Scrape webpage content using Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Use modified URL from url_changer
                await page.goto(self.url, timeout=30000)

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
        data = ''
        if content:
            processed_content = self.process_content(content)
            data = ''.join(text for text in processed_content)
        return data

class PDFScraper:
    @staticmethod
    def clean_text(text: str) -> str:
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

    def extract_data(self, pdf_path) -> str:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""

            for page in reader.pages:
                page_text = page.extract_text()
                extracted_text += page_text + "\n"

            # Apply thorough cleaning after all text is extracted
            extracted_text = self.clean_text(extracted_text)
        return extracted_text
    
    def handle_pdf_upload(self,pdf_file):
        if pdf_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                tmp_file_path = tmp_file.name
            
            content = self.extract_data(tmp_file_path)
            
            os.unlink(tmp_file_path)
            return content
        return None

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
        chunks = text_splitter.split_text(text)
        return [chunk.replace('\n', '') for chunk in chunks]

class SnowflakeManager:
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SnowflakeManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, user_id: str):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.user_id = user_id
        print(f"Initializing Snowflake Manager... : userid {user_id}")
        with open('secrets.toml', 'r') as f:
            self.secrets = toml.load(f)
        
        self.connection_params = {
            "account": self.secrets["SNOWFLAKE"]["ACCOUNT"],
            "user": self.secrets["SNOWFLAKE"]["USER"],
            "password": self.secrets["SNOWFLAKE"]["PASSWORD"],
            "role": "ACCOUNTADMIN",
            "database": self.secrets["SNOWFLAKE"]["DATABASE"],
            "warehouse": self.secrets["SNOWFLAKE"]["WAREHOUSE"],
            "schema": self.secrets["SNOWFLAKE"]["SCHEMA"],
        }
        self.session = None
        self.conn = None
        self.cursor = None
        self._initialized = True

    def connect(self):
        """Connect to Snowflake (only once)."""
        if self.conn is None or self.session is None or self.cursor is None:
            try:
                print("Connecting to Snowflake...")
                self.conn = snowflake.connector.connect(**self.connection_params)
                self.cursor = self.conn.cursor()
                self.session = Session.builder.configs(self.connection_params).create()
                print("Snowflake connection established successfully.")
            except Exception as e:
                print(f"Failed to connect to Snowflake: {e}")
                self.conn = None
                self.cursor = None
                self.session = None

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        if self.session:
            self.session.close()
        self.conn = None
        self.cursor = None
        self.session = None

    def ensure_connected(self):
        """Ensure connection is active."""
        if self.conn is None or self.session is None or self.cursor is None:
            self.connect()

    def _insert(self, table_name: str, contents: List[str]) -> None:
        self.ensure_connected()
        if contents:
            try:
                insert_queries = [f"INSERT INTO {table_name} (content) VALUES ('{content}')" for content in contents]
                for query in insert_queries:
                    self.cursor.execute(query)
                self.conn.commit()
            except Exception as e:
                print(f"Error inserting into {table_name}: {e}")

    def insert_into_github_rag(self, user_id ,contents: List[str]) -> None:
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_github", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise an exception if the insert failed
                except Exception as e:
                    print(f"Error inserting into {user_id}_github: {e}")

    def insert_into_personal_rag(self, user_id, contents: List[str]) -> None:
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_rag", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_rag: {e}")

    def insert_into_pdf_rag(self, user_id ,contents: List[str]) -> None:
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_pdf", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_pdf: {e}")

    def _search_service(self, service_name: str, query: str) -> str:
        self.ensure_connected
        try:
            root = Root(self.session)
            search_service = (
                root.databases[self.secrets["SNOWFLAKE"]["DATABASE"]]
                .schemas[self.secrets["SNOWFLAKE"]["SCHEMA"]]
                .cortex_search_services[service_name]
            )
            search_results = search_service.search(query=query, columns=["CONTENT"], limit=5)
            return json.dumps(search_results.to_dict())
        except Exception as e:
            print(f"Error searching in {service_name}: {e}")
            return json.dump([])
        

    def search(self, query: str,user_id) -> List[str]:
        services = {
            "common": self.secrets["SNOWFLAKE"]["WAREHOUSE"],
            "personal": f"{user_id}_ragsearch",
            "github": f"{user_id}_githubsearch",
            "pdf": f"{user_id}_pdfsearch"
        }

        results = []

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._search_service, service_name, query): name for name, service_name in services.items()}

            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error searching in {service_name}: {e}")

        return results

    def generate(self,user_id, query: str) -> str:
        self.ensure_connected()
        if self.session is None:  
            raise Exception("Failed to connect to Snowflake.")
        
        document_details = self.search(query,user_id)
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
                        - Provide a concise and informative response that addresses the user query effectively.
                        - Use the provided **Document Details** as the primary source of truth to answer the query.
                        - Refer to the **Memory** to maintain conversation context. Use this information to make your response coherent and contextual.
                        - Dont use the **Memory** as the primary source of information unless the query explicitly asks for it.
                        - If relevant information from the **Memory** or **Document Details** is missing, clarify this in your response and guide the user on how to proceed.
                        - Don't provide verbatim responses from the **Document Details** or **Memory**. Instead, paraphrase and summarize the information to enhance user understanding.
                        - Don't greet user frequently. Be friendly in your responses.
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
                                "Webhook configurations are settings that allow your application to receive real-time updates from the payment API when specific events occur (e.g., successful payments, refunds). Configure the webhook URL in your API dashboard, ensure it points to an accessible endpoint, and validate incoming requests using the signature provided in the header to ensure authenticity."$$
            );"""

        try:
            generation = self.session.sql(instruction).collect()
            return generation[0][0]
        except Exception as e:
            raise Exception(f"Error during query generation: {e}")

class Memory:
    def __init__(self):
        with open('secrets.toml', 'r') as f:
            self.secrets = toml.load(f)

        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            self.firebase_credentials = {
                "type": self.secrets["FIREBASE"]["TYPE"],
                "project_id": self.secrets["FIREBASE"]["PROJECT_ID"],
                "private_key_id": self.secrets["FIREBASE"]["PRIVATE_KEY_ID"],
                "private_key":  self.secrets["FIREBASE"]["PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": self.secrets["FIREBASE"]["CLIENT_EMAIL"],
                "client_id": self.secrets["FIREBASE"]["CLIENT_ID"],
                "auth_uri": self.secrets["FIREBASE"]["AUTH_URI"],
                "token_uri": self.secrets["FIREBASE"]["TOKEN_URI"],
                "auth_provider_x509_cert_url": self.secrets["FIREBASE"]["AUTH_PROVIDER_X509_CERT_URL"],
                "client_x509_cert_url": self.secrets["FIREBASE"]["CLIENT_X509_CERT_URL"],
                "universe_domain": self.secrets["FIREBASE"]["UNIVERSE_DOMAIN"]
            }
            cred = credentials.Certificate(self.firebase_credentials)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        self.api_key = self.secrets["FIREBASE"]["API_KEY"]

    def create_summary(self, conversations: List[Dict[str, str]]) -> str:
        """
        Creates a summary of conversations using Mistral AI
        """
        try:
            # Format conversations for Mistral
            formatted_conversations = []
            for conv in conversations:
                formatted_conversations.append(f"User: {conv['query']}\nAssistant: {conv['response']}")

            conversation_text = "\n\n".join(formatted_conversations)

            client = Mistral(self.secrets["MISTRAL"]["API_KEY"])  # Corrected parameter name

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

    def manage_conversations(self, user_id: str, query: str, response: str) -> bool:
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
                    'summary_text': self.create_summary(conversations),
                    'original_conversations': conversations
                }

                # Update document with summary and clear conversations
                user_ref.update({
                    'conversation_summary': firestore.ArrayUnion([summary]),
                    'past_conversations': []  # Clear the conversations list
                })
            else:
                # Just update with new conversation
                user_ref.update({
                    'past_conversations': conversations
                })

            return True

        except Exception as e:
            raise Exception(f"Failed to manage conversations: {str(e)}")

    def retrieve_memory(self, user_id: str) -> List[Dict[str, str]]:
        user_ref = self.db.collection('user_data').document(user_id)
        user_doc = user_ref.get()
        user_data = user_doc.to_dict()
        conversations = user_data.get('past_conversations', [])
        summary_conversations = user_data.get('conversation_summary', [])
        if summary_conversations:
            conversations.append(summary_conversations[0])
        return conversations

class Backend:
    """Centralized backend processing"""
    def __init__(self, user_id: str):
        self.text_processor = TextProcessor()
        self.snowflake_manager = SnowflakeManager(user_id)
        self.memory = Memory()
        self.user_id = user_id

    async def web_crawler(self, url: str) -> None:
        """Main Web Crawler processing method"""
        scraper = WebScraper(url)
        data = await scraper.scrape()
        processed_chunks = self.text_processor.chunk_text(data)
        # Call insert docs from Snowflake manager
        self.snowflake_manager.insert_into_personal_rag(processed_chunks)

    async def github_scraper(self, url: str) -> None:
        """Main GitHub scraper processing method"""
        scraper = GithubScraper(url)
        data = await scraper.get_data()
        if not data:
            raise Exception("Failed to scrape GitHub data.")
        processed_chunks = self.text_processor.chunk_text(data)
        if not processed_chunks:
            raise Exception("Failed to process GitHub data to chunks.")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, partial(self.snowflake_manager.insert_into_github_rag, self.user_id, processed_chunks))
        return True

    def pdf_scraper(self, pdf) -> None:
        scraper = PDFScraper()
        data = scraper.handle_pdf_upload(pdf)
        if data:
            processed_chunks = self.text_processor.chunk_text(data)
        self.snowflake_manager.insert_into_pdf_rag(self.user_id,processed_chunks)

    def query(self, query: str) -> str:
        response = self.snowflake_manager.generate(self.user_id,query)
        self.memory.manage_conversations(self.user_id, query, response)
        return response

async def run():
    """Async entry point"""
    user_id = "sample_user_id"  # Replace with actual user_id retrieval logic
    backend = Backend(user_id)
    await backend.github_scraper("https://github.com/example/repo")

if __name__ == '__main__':
    asyncio.run(run())
