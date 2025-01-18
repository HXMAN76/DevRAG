import asyncio
import json
import os
import re
from typing import List, Optional
import logging
import streamlit as st
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from playwright.sync_api import sync_playwright
from snowflake.core import Root
from snowflake.snowpark import Session
import snowflake.connector
import PyPDF2
import tempfile

# Set logging level to WARNING to suppress unwanted info logs
logging.getLogger("snowflake.connector").setLevel(logging.WARNING)
logging.getLogger("snowflake.snowpark").setLevel(logging.WARNING)
logging.getLogger("snowflake.core").setLevel(logging.WARNING)

class GithubScraper:
    def __init__(self, url: str):
        self.url = url

    def webscrape_content(self) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)
            page.wait_for_timeout(5000)
            html_content = page.content()
            browser.close()
            return html_content

    @staticmethod
    def extract_main_content(html: str) -> Optional[List[str]]:
        soup = BeautifulSoup(html, 'html.parser')
        textareas = soup.find_all('textarea')
        return textareas if textareas else None

    @staticmethod
    def replace_hub_with_ingest(url: str) -> str:
        return url.replace("github.com", "gitingest.com") if "github.com" in url else url

    def scrape_github(self) -> Optional[List[str]]:
        self.url = self.replace_hub_with_ingest(self.url)
        html_content = self.webscrape_content()
        return self.extract_main_content(html_content)

class WebScraper:
    def __init__(self, url: str):
        self.url = url
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact']
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

    def process_text(self, text: str) -> List[str]:
        text_parser = TextProcessor()
        return text_parser.chunk_text(text)

    async def scrape(self) -> List[str]:
        scrape_data = ''
        data = await self._webscrape(self.url)

        if data and data.markdown:
            scrape_data += data.markdown

        if data and data.links:
            for key in data.links:
                for link in data.links[key]:
                    text = link.get('text', '').casefold()
                    href = link.get('href', '')

                    if text in self.unwanted or any(platform in href for platform in self.social_media):
                        continue

                    sub_data = await self._webscrape(link["href"])
                    if sub_data and sub_data.markdown:
                        scrape_data += sub_data.markdown

        return self.process_text(scrape_data)

class PDFScraper:
    @staticmethod
    def extract_text_from_pdf(pdf_file) -> str:
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            return "".join(page.extract_text() for page in reader.pages)
        except Exception as e:
            return f"An error occurred: {e}"

    def process_pdf(self, pdf_file):
        pdf_text = self.extract_text_from_pdf(pdf_file)
        text_parser = TextProcessor()
        return text_parser.chunk_text(pdf_text)

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

    def insert_document(self, source_url: str, content: str):
        query = "INSERT INTO DEVRAG_SCHEMA.DOCUMENT (WEBSITE_URL, CONTENT) VALUES (%s, %s)"
        self.cursor.execute(query, (source_url, content))
        self.conn.commit()

    def search_and_generate(self, query: str) -> str:
        root = Root(self.session)
        search_service = (
            root
            .databases[os.getenv("SNOWFLAKE_DATABASE")]
            .schemas[os.getenv("SNOWFLAKE_SCHEMA")]
            .cortex_search_services[os.getenv("SNOWFLAKE_WAREHOUSE")]
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

async def handle_github_url(url: str) -> List[str]:
    git = GithubScraper(url)
    content = git.scrape_github()
    if content:
        processor = TextProcessor()
        return [chunk for text in content for chunk in processor.chunk_text(text)]
    return []

async def handle_website_url(url: str) -> List[str]:
    scraper = WebScraper(url)
    return await scraper.scrape()

def handle_pdf_upload(uploaded_file) -> List[str]:
    pdf_scraper = PDFScraper()
    return pdf_scraper.process_pdf(uploaded_file)

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'snowflake_manager' not in st.session_state:
        st.session_state.snowflake_manager = SnowflakeManager()
        st.session_state.snowflake_manager.connect()
    if 'show_github' not in st.session_state:
        st.session_state.show_github = False
    if 'show_website' not in st.session_state:
        st.session_state.show_website = False
    if 'show_pdf' not in st.session_state:
        st.session_state.show_pdf = False

def main():
    st.title("RAG Chatbot")
    initialize_session_state()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            response = st.session_state.snowflake_manager.search_and_generate(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.markdown(response)

    # Create three columns for the buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("GitHub"):
            st.session_state.show_github = True
            st.session_state.show_website = False
            st.session_state.show_pdf = False
    
    with col2:
        if st.button("Website"):
            st.session_state.show_github = False
            st.session_state.show_website = True
            st.session_state.show_pdf = False
    
    with col3:
        if st.button("Attach"):
            st.session_state.show_github = False
            st.session_state.show_website = False
            st.session_state.show_pdf = True

    # Show appropriate input field based on button clicks
    if st.session_state.get('show_github', False):
        github_url = st.text_input("Enter GitHub URL")
        if github_url:
            with st.spinner("Processing GitHub content..."):
                content = asyncio.run(handle_github_url(github_url))
                if content:
                    for chunk in content:
                        st.session_state.snowflake_manager.insert_document(github_url, chunk)
                    st.success("GitHub content processed successfully!")

    if st.session_state.get('show_website', False):
        website_url = st.text_input("Enter website URL")
        if website_url:
            with st.spinner("Processing website content..."):
                content = asyncio.run(handle_website_url(website_url))
                for chunk in content:
                    st.session_state.snowflake_manager.insert_document(website_url, chunk)
                st.success("Website content processed successfully!")

    if st.session_state.get('show_pdf', False):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        if uploaded_file:
            with st.spinner("Processing PDF..."):
                content = handle_pdf_upload(uploaded_file)
                if content:
                    for chunk in content:
                        st.session_state.snowflake_manager.insert_document(uploaded_file.name, chunk)
                    st.success("PDF processed successfully!")

if __name__ == "__main__":
    main()