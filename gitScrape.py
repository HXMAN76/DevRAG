import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
from backend import PDFScraper, SnowflakeManager, TextProcessor
import tempfile
import os
from urllib.parse import urljoin

class SeleniumGithubScraper:
    def __init__(self, url: str):
        self.url = url
        self.setup_driver()

    def setup_driver(self):
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Setup Chrome driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def replace_hub_with_ingest(self, url: str) -> str:
        return url.replace("github.com", "gitingest.com") if "github.com" in url else url

    def scrape_github(self):
        try:
            # Convert URL to gitingest URL
            ingest_url = self.replace_hub_with_ingest(self.url)
            
            # Navigate to the page
            self.driver.get(ingest_url)
            
            # Wait for content to load (5 seconds + waiting for textareas)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "textarea"))
            )
            
            # Extract content from textareas
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            content = [textarea.get_attribute("value") for textarea in textareas if textarea.get_attribute("value")]
            
            # Process the content
            if content:
                text_processor = TextProcessor()
                processed_content = []
                for text in content:
                    processed_content.extend(text_processor.chunk_text(text))
                return processed_content
            
            return None
            
        except Exception as e:
            print(f"Error scraping GitHub: {e}")
            return None
        finally:
            self.driver.quit()

class SimpleWebScraper:
    def __init__(self, url: str):
        self.url = url
        self.visited_urls = set()
        self.unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact']
        self.social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_base_url(self, url):
        return '/'.join(url.split('/')[:3])

    def is_valid_url(self, url):
        return url.startswith('http') and not any(term in url.lower() for term in self.unwanted + self.social_media)

    def scrape_page(self, url):
        if url in self.visited_urls:
            return ""
        
        self.visited_urls.add(url)
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Extract text content
            text = ' '.join([p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])])
            return text
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return ""

    def scrape(self, max_pages=5):
        all_text = []
        base_url = self.get_base_url(self.url)
        
        # Start with the main URL
        main_text = self.scrape_page(self.url)
        if main_text:
            all_text.append(main_text)

        try:
            # Get initial page
            response = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find and process links
            links = soup.find_all('a', href=True)
            pages_scraped = 1

            for link in links:
                if pages_scraped >= max_pages:
                    break

                href = link['href']
                # Convert relative URLs to absolute URLs
                full_url = urljoin(base_url, href)
                
                if (self.is_valid_url(full_url) and 
                    full_url.startswith(base_url) and 
                    full_url not in self.visited_urls):
                    text = self.scrape_page(full_url)
                    if text:
                        all_text.append(text)
                        pages_scraped += 1

            # Process the combined text
            combined_text = ' '.join(all_text)
            text_processor = TextProcessor()
            return text_processor.chunk_text(combined_text)

        except Exception as e:
            print(f"Error in scrape: {e}")
            return []

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'snowflake_manager' not in st.session_state:
        st.session_state.snowflake_manager = SnowflakeManager()
        st.session_state.snowflake_manager.connect()

def handle_pdf_upload(pdf_file):
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
                scraper = SeleniumGithubScraper(github_url)
                content = scraper.scrape_github()
                if content:
                    for chunk in content:
                        st.session_state.snowflake_manager.insert_document(github_url, chunk)
                    st.success("GitHub content processed successfully!")
                else:
                    st.error("Failed to process GitHub content. Please check the URL and try again.")
    
    if st.session_state.get('show_website', False):
        website_url = st.text_input("Enter website URL")
        if website_url:
            with st.spinner("Processing website content..."):
                scraper = SimpleWebScraper(website_url)
                content = scraper.scrape()
                if content:
                    for chunk in content:
                        st.session_state.snowflake_manager.insert_document(website_url, chunk)
                    st.success("Website content processed successfully!")
                else:
                    st.error("Failed to process website content. Please check the URL and try again.")
    
    if st.session_state.get('show_pdf', False):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        if uploaded_file:
            with st.spinner("Processing PDF..."):
                content = handle_pdf_upload(uploaded_file)
                if content:
                    for chunk in content:
                        st.session_state.snowflake_manager.insert_document(uploaded_file.name, chunk)
                    st.success("PDF processed successfully!")
                else:
                    st.error("Failed to process PDF. Please check the file and try again.")

if __name__ == "__main__":
    main()