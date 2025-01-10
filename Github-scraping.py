from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup  # For parsing and extracting content
import time
import re  # Add import for regex
import os
from dotenv import load_dotenv

class GitHubScraper:
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

    @staticmethod
    def extract_domain(url):
        match = re.search(r"https?://(?:www\.)?([^./]+)\.([^./]+)\.", url)
        if match:
            return match.group(2)
        return None

    def scrape_github(self):
        self.url = self.replace_hub_with_ingest(self.url)
        html_content = self.webscrape_content()
        return self.extract_main_content(html_content)

def main():
    url = input("Enter the URL to scrape: ")
    scraper = GitHubScraper(url)
    domain = scraper.extract_domain(url)
    if domain:
        print(f"Extracted domain: {domain}")
    main_content = scraper.scrape_github()
    if main_content:
        print("\nExtracted Content")
        directory = main_content[1].text
        file_content = main_content[2].text
    else:
        print("The Github Repo is private")

if __name__ == "__main__":
    main()
