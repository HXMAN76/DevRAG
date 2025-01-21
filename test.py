# Standard Library Imports
import os
import re
import json
import time
import asyncio
import logging
import threading
import base64
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

# Third-Party Imports
import toml
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import PyPDF2
from playwright.async_api import async_playwright
from langchain.text_splitter import RecursiveCharacterTextSplitter
from mistralai import Mistral
from crawl4ai import AsyncWebCrawler

# Database and External Services
import snowflake.connector
from snowflake.snowpark import Session
from snowflake.core import Root
import firebase_admin
from firebase_admin import credentials, auth, firestore,initialize_app

# Streamlit
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

with open('secrets.toml','r') as file:
    secret = toml.load(file)

class ConfigManager:
    """Centralized configuration and environment management"""
    @staticmethod
    def load_config() -> Dict[str, str]:
        load_dotenv()

class ScraperBase:
    """Base class for all scrapers with common functionality"""
    def __init__(self, url: str = ''):
        self.url = url
        self.visited = set()
        self.crawler = AsyncWebCrawler()

    def is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        return re.match(r'^(http://|https://|file://|raw:).*', url) is not None

# class GithubScraper(ScraperBase):
#     """Specialized GitHub scraper with enhanced extraction"""
#     async def scrape_content(self) -> Optional[str]:
#         """Advanced GitHub content scraping with Playwright"""
#         try:
#             async with async_playwright() as p:
#                 browser = await p.chromium.launch(headless=True)
#                 page = await browser.new_page()
#                 await page.goto(self.url.replace('github', 'gitingest'), timeout=30000)
#                 await page.wait_for_timeout(5000)
#                 content = await page.content()
#                 await browser.close()
#                 return content
#         except Exception as e:
#             logger.error(f"GitHub Scraping Error: {e}")
#             return None

#     @staticmethod
#     def process_content(content: str) -> List[str]:
#         """Extract text from textarea elements"""
#         soup = BeautifulSoup(content, 'html.parser')
#         return [text.text for text in soup.find_all('textarea')] or []

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
            data = await self.crawler.arun(
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

# Additional classes like PDFScraper, TextProcessor, etc. remain similar to original implementation
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
                await page.goto(modified_url, timeout=2000)
                await page.wait_for_timeout(3000)
                content = await page.content()
                await browser.close()
                return content
        except Exception as e:
            print(f"Scraping error: {e}")
            return None
        finally:
            if 'browser' in locals():
                await browser.close()
    
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

class PDFScraper:
    @staticmethod
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
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                extracted_text = ""
            except Exception as e:
                print(f"Error reading PDF: {e}")
                return ""
            
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
        self.login_page = LoginPage(auth)
        self.user_id = self.login_page.get_user_id()
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

    @contextmanager
    def get_connection(self):
        """Context manager for getting a new connection"""
        conn = snowflake.connector.connect(**self.connection_params)
        try:
            yield conn
        finally:
            conn.close()

    async def _execute_insert(self, query):
        """Execute a single insert query with its own connection"""
        loop = asyncio.get_event_loop()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                await loop.run_in_executor(None, cursor.execute, query)
                await loop.run_in_executor(None, conn.commit)
            finally:
                cursor.close()
    
    async def insert_into_rag(self, content, table_name):
        if not content:
            return

        # Create all insert queries
        insert_queries = [
            f"""INSERT INTO {self.user_id}_{table_name} (content) VALUES ('{i.replace("'", "''")}')"""
            for i in content
        ]

        # Execute all inserts concurrently with separate connections
        await asyncio.gather(
            *[self._execute_insert(query) for query in insert_queries]
        )

    async def _perform_search(self, search_type, query):
        """Execute a single search operation with its own session"""
        loop = asyncio.get_event_loop()
        
        # Create a new session for this search operation
        session = await loop.run_in_executor(
            None,
            lambda: Session.builder.configs(self.connection_params).create()
        )
        
        try:
            root = Root(session)
            db = root.databases[secret["SNOWFLAKE"]["DATABASE"]]
            schema = db.schemas[secret["SNOWFLAKE"]["SCHEMA"]]
            
            # Get appropriate search service based on type
            if search_type == 'common':
                service_name = secret["SNOWFLAKE"]["WAREHOUSE"]
            else:
                service_name = f"{self.user_id}_{search_type}search"
            
            search_service = schema.cortex_search_services[service_name]
            
            search_results = await loop.run_in_executor(
                None,
                lambda: search_service.search(
                    query=query,
                    columns=["CONTENT"],
                    limit=5
                )
            )
            return json.dumps(search_results.to_dict())
        finally:
            session.close()

    async def search(self, query: str) -> list:
        # Execute all searches concurrently with separate sessions
        search_types = ['common', 'rag', 'github', 'pdf']
        results = await asyncio.gather(*[
            self._perform_search(search_type, query)
            for search_type in search_types
        ])
        
        return results

    def generate(self, query):
        document_details = self.search(query)
        conversation_memory = Memory().retrieve_memory()
        
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
                "client_x509_cert_url": secret["FIREBASE"]["CLIENT_X509_CERT_URL"],
                "universe_domain": secret["FIREBASE"]["UNIVERSE_DOMAIN"]
            }
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.firebase_credentials)
                initialize_app(cred)
        
        self.db = firestore.AsyncClient()  # Use AsyncClient instead of regular client
        self.api_key = secret["FIREBASE"]["API_KEY"]
        self.mistral_client = Mistral(api_key=secret["MISTRAL"]["API_KEY"])
        self.user_id = LoginPage.get_user_id()

    async def create_summary(self, conversations: List[Dict[str, str]]) -> str:
        """
        Asynchronously creates a summary of conversations using Mistral AI
        
        Args:
            conversations: List of conversation dictionaries containing 'query' and 'response'
            
        Returns:
            str: Summary of the conversations
        """
        try:
            # Format conversations for Mistral
            formatted_conversations = [
                f"User: {conv['query']}\nAssistant: {conv['response']}"
                for conv in conversations
            ]
            conversation_text = "\n\n".join(formatted_conversations)
            
            # Run Mistral API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            chat = await loop.run_in_executor(
                None,
                lambda: self.mistral_client.chat.completions.create(
                    model="mistral-large-v2",
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
            )
            
            return chat.choices[0].message.content
            
        except Exception as e:
            return f"Error creating summary with Mistral: {str(e)}"

    async def manage_conversations(
        self,  
        query: str, 
        response: str
    ) -> bool:
        """
        Asynchronously manages conversations by:
        1. Adding new conversation
        2. Checking if there are 5 conversations
        3. If yes, summarizes them using Mistral AI
        4. Clears the conversations list
        
        Args:
            user_id: The user's unique identifier
            query: The user's query
            response: The assistant's response
            
        Returns:
            bool: True if operation was successful
            
        Raises:
            Exception: If conversation management fails
        """
        try:
            # Get user document reference
            user_ref = self.db.collection('user_data').document(self.user_id)
            user_doc = await user_ref.get()
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
                summary_text = await self.create_summary(conversations)
                summary = {
                    'summary_text': summary_text,
                    'original_conversations': conversations
                }
                
                # Update document with summary and clear conversations
                await user_ref.update({
                    'conversation_summary': firestore.ArrayUnion([summary]),
                    'past_conversations': [] # Clear the conversations list
                })
            else:
                # Just update with new conversation
                await user_ref.update({
                    'past_conversations': conversations
                })
                
            return True
            
        except Exception as e:
            raise Exception(f"Failed to manage conversations: {str(e)}")

    async def retrieve_memory(self) -> List[Dict[str, Any]]:
        """
        Asynchronously retrieves user's conversation history and summaries
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            List[Dict[str, Any]]: List of conversations and summaries
        """
        user_ref = self.db.collection('user_data').document(self.user_id)
        user_doc = await user_ref.get()
        user_data = user_doc.to_dict()
        
        conversations = user_data.get('past_conversations', [])
        summary_conversations = user_data.get('conversation_summary', [])
        
        if summary_conversations:
            conversations.append(summary_conversations[0])
            
        return conversations
        
class Backend:
    """Centralized backend processing"""
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.text_processor = TextProcessor()
        self.snowflake_manager = SnowflakeManager()
        self.memory = Memory()

    async def webcrawler(self,url):
        """Main Webcrawler processing method"""
        scraper = WebScraper(url)
        data = await scraper.scrape()
        processed_chunks = ''.join(chunk for data_item in data for chunk in self.text_processor.chunk_text(data_item))
        # call insert docs from snowflake manager
        self.snowflake_manager.insert_into_personal_rag(self.user_id,processed_chunks)

    async def github_scraper(self,url):
        """Main GitHub scraper processing method"""
        scraper = GithubScraper(url)
        data = await scraper.get_data()
        processed_chunks = ''.join(chunk for chunk in self.text_processor.chunk_text(data))
        self.snowflake_manager.insert_into_github_rag(self.user_id,processed_chunks)
        
    def pdf_scraper(self, pdf_path):
        scraper = PDFScraper()
        data = scraper.extract_data(pdf_path)
        processed_chunks = ''.join(chunk for chunk in self.text_processor.chunk_text(data))
        self.snowflake_manager.insert_into_pdf_rag(self.user_id,processed_chunks)
    
    def process_query(self, query):
        response = self.snowflake_manager.generate(query,self.user_id)
        self.memory.manage_conversations(self.user_id,query,response)
        return response

class FirebaseAuth:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate({
                "type": secret["FIREBASE"]["TYPE"],
                "project_id": secret["FIREBASE"]["PROJECT_ID"],
                "private_key_id": secret["FIREBASE"]["PRIVATE_KEY_ID"],
                "private_key": secret["FIREBASE"]["PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": secret["FIREBASE"]["CLIENT_EMAIL"],
                "client_id": secret["FIREBASE"]["CLIENT_ID"],
                "auth_uri": secret["FIREBASE"]["AUTH_URI"],
                "token_uri": secret["FIREBASE"]["TOKEN_URI"],
                "auth_provider_x509_cert_url": secret["FIREBASE"]["AUTH_PROVIDER_X509_CERT_URL"],
                "client_x509_cert_url": secret["FIREBASE"]["CLIENT_X509_CERT_URL"],
                "universe_domain": secret["FIREBASE"]["UNIVERSE_DOMAIN"]
            })
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.api_key = secret["FIREBASE"]["API_KEY"]

    # Methods for Snowflake connections, login, registration, password reset, etc., as defined earlier
    def _get_snowflake_connection(self):
        """Create and return a Snowflake connection"""
        return snowflake.connector.connect(
            user=secret["SNOWFLAKE"]["USER"],
            password=secret["SNOWFLAKE"]["PASSWORD"],
            account=secret['SNOWFLAKE']['ACCOUNT'],
            database=secret["SNOWFLAKE"]["DATABASE"],
            schema=secret["SNOWFLAKE"]["SCHEMA"],
            warehouse=secret["SNOWFLAKE"]["WAREHOUSE"]
        )

    def _setup_snowflake_resources(self, user_id):
        """Set up Snowflake tables and search services for a user"""
        try:
            conn = self._get_snowflake_connection()
            cursor = conn.cursor()

            # Create tables
            tables = ['pdf', 'github', 'rag']
            for table in tables:
                create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS {user_id}_{table} (
                    id INT PRIMARY KEY,
                    content STRING
                    );"""
                cursor.execute(create_table_query)

            # Create search services
            for service in tables:
                create_search_query = f"""
                    CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_{service}search
                    ON content
                    WAREHOUSE = '{secret["SNOWFLAKE"]["WAREHOUSE"]}'
                    TARGET_LAG = '1 minutes'
                    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
                    AS (
                        SELECT content
                        FROM {user_id}_{service}
                    );"""
                cursor.execute(create_search_query)

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error setting up Snowflake resources: {e}")

    def validate_email(self, email):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    def validate_password(self, password):
        """Validate password requirements"""
        return len(password) >= 6

    def login_user(self, email, password):
        """Login user with email and password using Firebase Auth REST API"""
        try:
            # Firebase Auth REST API endpoint for email/password sign-in
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
            
            # Request payload
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            # Make the authentication request
            response = requests.post(auth_url, json=payload)
            data = response.json()
            
            # Check for errors
            if response.status_code != 200:
                error_message = data.get('error', {}).get('message', 'Authentication failed')
                if error_message:
                    raise Exception("Login Failed. Check the Credential")

            # Get the user ID from the response
            user_id = data.get('localId')
            if not user_id:
                raise Exception("Failed to get user information")
                
            return user_id
            
        except requests.exceptions.RequestException as e:
            raise Exception("Network error. Please check your connection.")
        except Exception as e:
            raise e

    def register_user(self, email, password, additional_data=None):
        """Register new user with email and password"""
        try:
            user = auth.create_user(
                email=email,
                password=password
            )
            
            # Store additional user information in Firestore
            if additional_data:
                user_data = {
                    'email': email,
                    'created_at': datetime.now(),
                    **additional_data,
                    "past_converations": [],
                    "conversation_summary":[]
                }
                self.db.collection('user_data').document(user.uid).set(user_data)
            
            # Start Snowflake setup in background thread
            threading.Thread(
                target=self._setup_snowflake_resources,
                args=(user.uid,),
                daemon=True
            ).start()
            
            return user.uid
        except Exception as e:
            if 'EMAIL_EXISTS' in str(e):
                raise Exception("Email already registered")
            raise Exception("Registration failed. Please try again.")

    def reset_password(self, email):

        """Send password reset email using Firebase Authentication REST API"""
        try:
            # Firebase Auth REST API endpoint for password reset
            reset_password_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={self.api_key}"
            
            # Request payload
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }
            
            # Send the request to Firebase
            response = requests.post(reset_password_url, json=payload)
            data = response.json()
            
            # Check if the request was successful
            if response.status_code == 200:
                print(f"Password reset email sent to {email}")
            else:
                error_message = data.get('error', {}).get('message', 'Failed to send reset email')
                raise Exception(error_message)
        except requests.exceptions.RequestException:
            raise Exception("Network error. Please check your connection.")
        except Exception as e:
            raise Exception(f"Failed to send reset email. {str(e)}")

    def get_user_info(self, user_id):
        """Get user information from Firestore"""
        try:
            user_data = self.db.collection('user_data').document(user_id).get()
            return user_data.to_dict()
        except Exception as e:
            return None
        
class BasePage:
    def __init__(self):
        self.load_styles()

    def load_styles(self):
        with open('static/login.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


class LoginPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def get_user_id(self):
        return st.session_state.user_id

    def validate_input(self, email, password=None):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        if password is not None:
            if not password:
                errors.append("Password is required")
            elif not self.auth.validate_password(password):
                errors.append("Password must be at least 6 characters")

        return errors

    def show(self):
        st.subheader("Login", anchor=False)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                errors = self.validate_input(email, password)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        user_id = self.auth.login_user(email, password)
                        st.session_state.user_id = user_id
                        st.success("Login successful!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot Password?", key="forgot-password"):
                st.session_state.current_page = 'forgot_password'
                st.rerun()
        with col2:
            if st.button("New User? Sign Up", key="new-user"):
                st.session_state.current_page = 'signup'
                st.rerun()
    
class SignupPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def validate_input(self, email, password=None):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        if password is not None:
            if not password:
                errors.append("Password is required")
            elif not self.auth.validate_password(password):
                errors.append("Password must be at least 6 characters")

        return errors

    def show(self):
        st.subheader("\U0001F31F Ready to supercharge your development?", anchor=False)
        st.markdown("Sign up now to get full access to DevRag and boost your coding productivity!")
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            occupation = st.selectbox("Occupation",
                                      ["Student", "Software Developer", "Data Scientist", "Researcher",
                                       "Teacher/Professor", "Business Professional", "Other"])
            description = st.text_area("Description")
            submit = st.form_submit_button("Sign Up")

            if submit:
                errors = self.validate_input(email, password)
                if not name:
                    errors.append("Name is required")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        additional_data = {
                            "name": name,
                            "occupation": occupation,
                            "description": description
                        }
                        user_id = self.auth.register_user(email, password, additional_data)
                        st.success("Registration successful! Snowflake resources are being set up in the background.")
                        st.info("You can proceed to login while we complete the setup.")
                        time.sleep(2)
                        st.session_state.current_page = 'login'
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if st.button("Already Registered? Login Now", key="back-to-login"):
            st.session_state.current_page = 'login'
            st.rerun()


class ForgotPasswordPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def validate_input(self, email):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        return errors

    def show(self):
        st.subheader("Reset Password", anchor=False)
        with st.form("forgot_password_form"):
            email = st.text_input("Email")
            submit = st.form_submit_button("Send Reset Link")

            if submit:
                errors = self.validate_input(email)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        self.auth.reset_password(email)
                        st.success("Password reset link sent to your email!")
                        time.sleep(2)
                        st.session_state.current_page = 'login'
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if st.button("Back to Login", key="back-to-login"):
            st.session_state.current_page = 'login'
            st.rerun()

class Landing:
    PAGE_TITLE = "DevRag"
    PAGE_ICON = "static/favicon-32.png"
    BG_IMAGE = "static/bg.jpg"

    def __init__(self):
        self.hide_dev_options()
        self.set_background(self.BG_IMAGE)
        self.load_custom_css()

    def hide_dev_options(self):
        st.markdown(
            """
            <style>
                header{
                    visibility: hidden;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

    def set_background(self, image_path):
        image_ext = "bg.jpg"
        st.markdown(
            f"""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <style>
            [data-testid="stMain"]{{
                background: url(data:image/{image_ext};base64,{base64.b64encode(open(image_path, "rb").read()).decode()});
                background-size: cover;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    def load_custom_css(self):
        with open('static/styles.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def create_navbar(self):
        st.markdown("""
        <div class="navbar">
            <a href="#home">Home</a>
            <a href="#features">Features</a>
            <a href="#contact-us">Team</a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div id='home'></div>", unsafe_allow_html=True)

    def create_hero_section(self):
        st.title("Welcome to Dev", anchor=False)
        st.subheader(
            "Empowering developers with instant, AI-driven insights by combining "
            "Retrieval-Augmented Generation and dynamic web-scraped knowledge.",
            anchor=False
        )

        if st.button("Get Started ↗", key="get-started", type="primary"):
            st.session_state.current_page = "login"
            st.rerun()

    def create_features_section(self):
        st.markdown("<div id='features'></div>", unsafe_allow_html=True)
        st.header("Features", anchor=False)
        st.markdown("""
        <ul class="features-list">
            <li><strong>Accurate Insights</strong>: Get precise answers from a vast database of developer documentation.</li>
            <li><strong>Customizable Knowledge Base</strong>: Add your own links to keep the knowledge base up-to-date.</li>
            <li><strong>Instant Responses</strong>: Chatbot interface provides quick and contextual answers.</li>
            <li><strong>Comprehensive Solutions</strong>: Solve coding challenges, understand frameworks, and stay updated with the latest tools.</li>
        </ul>
        """, unsafe_allow_html=True)

    def create_tech_stack_section(self):
        st.header("Tech Stack", anchor=False)
        st.markdown("""
        <div class="tech-stack">
            <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" alt="streamlit_logo" style="width: 15%;height: 15%">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png" alt="snowflake" id="snowflake" style="width: 20%;height: 20%;">
            <img src="https://static1.squarespace.com/static/65c726ca17f84d5307a0dda1/65da1a93a8e8634b664835c9/65f6a87476d8e45fc3010249/1711102391682/announcing-mistral.png?format=1500w" alt="mistral" style="width: 10%;height: 10%">
            <img src="https://ml.globenewswire.com/Resource/Download/3034f6cd-48c3-4b5e-bd7f-242dbaecaab4?size=2" alt="trulens" style="width: 8%;height: 8%">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png" alt="python" style="width: 8%;height: 8%">
            <img src="https://www.ichdata.com/wp-content/uploads/2017/06/2024070803153850.png" alt="fireBase" style="width: 15%;height: 15%">
        </div>
        """, unsafe_allow_html=True)

    def create_about_section(self):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("📚 Vast Knowledge Base", anchor=False)
            st.write("Access information from various programming languages, frameworks, and libraries.")

        with col2:
            st.subheader("🔍 Smart Code Search", anchor=False)
            st.write("Find relevant code snippets and examples quickly and efficiently.")

        with col3:
            st.subheader("💡 Intelligent Suggestions", anchor=False)
            st.write("Get context-aware recommendations and best practices for your code.")

        st.markdown("<br><hr id='hr-1'>", unsafe_allow_html=True)

    def create_team_section(self):
        st.markdown("<div id='contact-us'></div>", unsafe_allow_html=True)
        st.header("Team", anchor=False)

        profiles = [
            {"name": "Raghav", "role": "Frontend Developer", "image": "Raghav_profile.jpg", "linkedin": "https://www.linkedin.com/in/raghav--n/", "github": "https://github.com/Rag-795", "email": "balaji.saragesh@gmail.com"},
            {"name": "Dev Bala Saragesh", "role": "Backend Developer", "image": "saragesh.jpg", "linkedin": "https://www.linkedin.com/in/devbalasarageshbs/", "github": "https://github.com/dbsaragesh-bs", "email": "balaji.saragesh@gmail.com"},
            {"name": "Hari Heman", "role": "Backend Developer", "image": "Hari_Profile_Pic.jpg", "linkedin": "https://www.linkedin.com/in/hari-heman/", "github": "https://github.com/HXMAN76", "email": "hariheman76@gmail.com"},
            {"name": "SriRanjana", "role": "Backend Developer", "image": "Ranjana_Profile_Pic.jpg", "linkedin": "https://www.linkedin.com/in/sriranjana-chitraboopathy-50b88828a/", "github": "https://github.com/sriranjanac", "email": "sriranjanac@gmail.com"}
        ]

        for profile in profiles:
            self._create_profile_card(**profile)

    def _create_profile_card(self, name, role, image, linkedin, github, email):
        st.markdown(
            f"""<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/{image}" alt="placeholder">
            <p class="name">{name}</p>
            <p class="role">{role}</p>
            <div class="social-media-handles">
                <a href="{linkedin}"><i class="fa-brands fa-linkedin"></i></a>
                <a href="{github}"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:{email}"><i class="fa-regular fa-envelope"></i></a>
            </div>
            </div>""",
            unsafe_allow_html=True
        )

    def create_footer_section(self):
        st.markdown("<br><hr id='hr-2'>", unsafe_allow_html=True)
        st.markdown("<span id='footer'>© 2025 DevRag. All rights reserved.</span>", unsafe_allow_html=True)

    def run(self):
        self.create_navbar()
        self.create_hero_section()
        self.create_about_section()
        self.create_features_section()
        self.create_tech_stack_section()
        self.create_team_section()
        self.create_footer_section()

class ChatbotPage:
    def __init__(self):
        self.load_custom_css()
        # if "messages" not in st.session_state:
        #     st.session_state.messages = []
        # if "show_sidebar" not in st.session_state:
        #     st.session_state.show_sidebar = False
        # if "sidebar_type" not in st.session_state:
        #     st.session_state.sidebar_type = None
        self.backend = Backend()

    def load_custom_css(self):
        with open('static/chatbot.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def handle_sidebar_input(self, input_type):
        with st.sidebar:
            st.title(f"Process {input_type}")
            if input_type == "PDF":
                uploaded_file = st.file_uploader("Upload PDF", type="pdf")
                if uploaded_file:
                    st.success("PDF uploaded successfully!")
                    self.backend.pdf_scraper(uploaded_file)
            elif input_type == "GitHub":
                github_input = st.text_input(f"Enter {input_type} URL")
                if github_input:
                    st.success(f"{input_type} Repository processed successfully!")
                    asyncio.run(self.backend.github_scraper(github_input))
            elif input_type == "Website":
                url_input = st.text_input(f"Enter {input_type} URL")
                if url_input:
                    st.success(f"{input_type} URL processed successfully!")
                    asyncio.run(self.backend.webcrawler(url_input))
        return None

    def show(self):
        self.load_custom_css()

        user_info = FirebaseAuth.get_user_info(st.session_state.user_id)
        st.title(f"{user_info.get('name', 'N/A')}", anchor=False)

        for message in st.session_state.messages:
            avatar_url = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png" if message["role"] == "user" else "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
            with st.chat_message(message["role"], avatar=avatar_url):
                st.write(message["content"])

        with st.container(key="chat_input"):
            with st.form("User query", border=False, clear_on_submit=True):
                user_query, send_button = st.columns([0.9, 0.1])
                prompt = user_query.text_input("Prompt", label_visibility="collapsed", placeholder="Ask your question...")
                submit_button = send_button.form_submit_button(label="ᯓ➤")

            col1, _ = st.columns([2, 3])
            with col1:
                web, github, pdf = st.columns(3)

                if web.button("🌐", key="web"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "Website"
                    st.rerun()

                if github.button("Git", key="github"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "GitHub"
                    st.rerun()

                if pdf.button("🔗", key="pdf"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "PDF"
                    st.rerun()

        if st.session_state.show_sidebar:
            result = self.handle_sidebar_input(st.session_state.sidebar_type)

        if prompt and submit_button:
            st.session_state.messages.append({
                "role": "user", 
                "content": prompt,
                "avatar": "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"
            })
            with st.chat_message("user", avatar="https://cdn-icons-png.flaticon.com/512/1144/1144760.png"):
                st.write(prompt)

            response = f"DevRAG: {asyncio.run(self.backend.process_query(prompt))}"
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "avatar": "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
            })
            with st.chat_message("assistant", avatar="https://cdn-icons-png.flaticon.com/512/4711/4711987.png"):
                st.write(response)

class App:
    def __init__(self):
            
        # Initialize session state
        self.initialize_session_state()
        self.title = "DevRag"
        self.layout = "wide"
        self.handle_page_config()
        # Set page config once at the app level
        st.set_page_config(
            page_title=self.title,
            page_icon="static/favicon-32.png",
            layout=self.layout
        )
        # Initialize Authorization 
        self.auth = FirebaseAuth()
        # Initialize components without page config
        self.landing = Landing()
        self.login = LoginPage(self.auth)
        self.signup = SignupPage(self.auth)
        self.forgot_password = ForgotPasswordPage(self.auth)
        self.chatbot = ChatbotPage()

    def handle_page_config(self):
        if st.session_state.current_page == 'landing':
            self.title = "DevRag"
            self.layout = "wide"

        elif st.session_state.current_page in ['login', 'signup', 'forgot_password']:
            self.title = "DevRag - Authentication"
            self.layout = "centered"

        elif st.session_state.current_page == 'chatbot':
            self.title = "DevRag - Chatbot"
            self.layout = "wide"

    def initialize_session_state(self):
        """Initialize all required session state variables"""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'landing'
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "show_sidebar" not in st.session_state:
            st.session_state.show_sidebar = False
        if "sidebar_type" not in st.session_state:
            st.session_state.sidebar_type = None

    def handle_navigation(self):
        """Handle navigation between pages based on session state"""
        # Reset page if user logs out
        if st.session_state.user_id is None and st.session_state.current_page not in ['landing', 'login', 'signup', 'forgot_password']:
            st.session_state.current_page = 'landing'
            st.rerun()

        # Redirect to DevRAG - chatbot if user is authenticated but on auth pages
        if (st.session_state.user_id is not None and 
            st.session_state.current_page in ['login', 'signup', 'forgot_password']):
            st.session_state.current_page = 'chatbot'
            st.rerun()

    def run(self):
        """Main application loop"""
        # Handle navigation first
        self.handle_navigation()

        # Route to appropriate page
        if st.session_state.current_page == 'landing':
            self.landing.run()
        elif st.session_state.current_page == 'login':
            self.login.show()
        elif st.session_state.current_page == 'signup':
            self.signup.show()
        elif st.session_state.current_page == 'forgot_password':
            self.forgot_password.show()
        elif st.session_state.current_page == 'chatbot':
            self.chatbot.show()

        # Debug information (remove in production)
        # st.sidebar.write("Debug Info:")
        # st.sidebar.write(f"Current Page: {st.session_state.current_page}")
        # st.sidebar.write(f"User ID: {st.session_state.user_id}")
        # st.sidebar.write(f"Auth Status: {st.session_state.authentication_status}")

if __name__ == '__main__':
    app = App()
    app.run()