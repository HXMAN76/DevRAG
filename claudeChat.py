import streamlit as st
from backend import PDFScraper, SnowflakeManager
import tempfile
import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import nest_asyncio
from crawl4ai import AsyncWebCrawler

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class AsyncGithubScraper:
    def __init__(self, url: str):
        self.url = url

    async def webscrape_content(self) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.url)
            await page.wait_for_timeout(5000)
            html_content = await page.content()
            await browser.close()
            return html_content

    @staticmethod
    def extract_main_content(html: str):
        soup = BeautifulSoup(html, 'html.parser')
        textareas = soup.find_all('textarea')
        return [textarea.text for textarea in textareas] if textareas else None

    @staticmethod
    def replace_hub_with_ingest(url: str) -> str:
        return url.replace("github.com", "gitingest.com") if "github.com" in url else url

    async def scrape_github(self):
        self.url = self.replace_hub_with_ingest(self.url)
        html_content = await self.webscrape_content()
        return self.extract_main_content(html_content)

class AsyncWebScraper:
    def __init__(self, url: str):
        self.url = url
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact']
        self.social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
        self.crawler = AsyncWebCrawler()

    async def scrape(self):
        try:
            async with AsyncWebCrawler() as crawler:
                data = await crawler.arun(
                    url=self.url,
                    magic=True,
                    simulate_user=True,
                    override_navigator=True,
                    exclude_external_images=True,
                    exclude_social_media_links=True,
                )

                if not data:
                    return []

                scrape_data = data.markdown if data.markdown else ''

                # Process links
                if hasattr(data, 'links'):
                    for key in data.links:
                        for link in data.links[key]:
                            text = link.get('text', '').casefold()
                            href = link.get('href', '')

                            if text in self.unwanted or any(platform in href for platform in self.social_media):
                                continue

                            try:
                                sub_data = await crawler.arun(
                                    url=href,
                                    magic=True,
                                    simulate_user=True,
                                    override_navigator=True,
                                    exclude_external_images=True,
                                    exclude_social_media_links=True,
                                )
                                if sub_data and sub_data.markdown:
                                    scrape_data += sub_data.markdown
                            except Exception as e:
                                print(f"Error processing sub-link {href}: {e}")
                                continue

                from backend import TextProcessor
                processor = TextProcessor()
                return processor.chunk_text(scrape_data)
        except Exception as e:
            print(f"Error during web scraping: {e}")
            return []

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'snowflake_manager' not in st.session_state:
        st.session_state.snowflake_manager = SnowflakeManager()
        st.session_state.snowflake_manager.connect()

async def handle_github_url(github_url):
    """Process GitHub URL and return content"""
    github_scraper = AsyncGithubScraper(github_url)
    return await github_scraper.scrape_github()

async def handle_website_url(website_url):
    """Process website URL and return content"""
    web_scraper = AsyncWebScraper(website_url)
    return await web_scraper.scrape()

def handle_pdf_upload(pdf_file):
    """Process uploaded PDF and return content"""
    if pdf_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_file_path = tmp_file.name
        
        pdf_scraper = PDFScraper()
        content = pdf_scraper.process_pdf(tmp_file_path)
        
        os.unlink(tmp_file_path)
        return content
    return None

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