import asyncio
from crawl4ai import AsyncWebCrawler
import json

async def webscrape(url: str):
    """
    Asynchronously crawls a website using AsyncWebCrawler and returns structured data.
    """
    async with AsyncWebCrawler() as crawler:
        try:
            # Start crawling and get the full result
            result = await crawler.arun(
                url=f"{url}",  # Replace with your target URL
                magic = True
            )
            return result  # Assuming 'result' is the complete structured data
        except Exception as e:
            print(f"Error during web crawling: {e}")
            return None
        
def generate_md(data):
    if data:
        try:
            # Safely convert the result to MD
            structured_data = data.markdown
            with open("output1.txt", "a", encoding="utf-8") as f:
                f.write(structured_data)
            print("Crawling complete. Output saved to 'output.txt'.")
            return None
            
        except (TypeError, ValueError) as e:
            print(f"Error saving data: {e}")
            return None
            
    else:
        print("No data returned from the crawler.")
        return None
    
def wrapper(url : str):
    data = asyncio.run(webscrape(url))
    generate_md(data)
    return data

if __name__ == "__main__":
    scrape_url = "https://react.dev/"
    data = wrapper(url=scrape_url)
    for key in data.links:
        for link in data.links[key]:
            if link['text'].casefold() in ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact', 'sign up', 'sign in', 'expert services']:
                continue 
            print(link['text'])
            wrapper(link["href"])