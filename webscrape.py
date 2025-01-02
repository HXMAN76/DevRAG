
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
                magic=True,
                simulate_user=True,
                override_navigator=True,
                exclude_external_images=True,
                exclude_social_media_links=True,
            )
            return result  # Assuming 'result' is the complete structured data
        except Exception as e:
            print(f"Error during web crawling: {e}")
            return None

def generate_md(data, file_name):
    if data:
        try:
            # Safely convert the result to MD
            structured_data = data.markdown
            with open(f"{file_name}", "a", encoding="utf-8") as f:
                f.write(structured_data)
            print("Crawling complete. Output saved to 'output.txt'.")
            return None
        except (TypeError, ValueError) as e:
            print(f"Error saving data: {e}")
            return None
    else:
        print("No data returned from the crawler.")
        return None

def wrapper(url: str, file_name: str = "output.txt"):
    data = asyncio.run(webscrape(url))
    generate_md(data, file_name)
    return data

if __name__ == "__main__":
    isScraped = False
    scrape_url = "https://react.dev/"
    data = wrapper(url=scrape_url)
    unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact', 'sign up', 'sign in', 'expert services']
    social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
    isScraped = True
    for key in data.links:
        for link in data.links[key]:
            text = link.get('text', '').casefold()
            href = link.get('href', '')
            if text in unwanted or any(platform in href for platform in social_media):
                continue
            print(link['text'])
            wrapper(link["href"])