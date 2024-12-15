from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import os
from mistralai import Mistral  # type: ignore
import json

def scrape(url):
   

    # HEADERS =  {
    #     "Accept" : "*/*",
    #     "Accept-Encoding": "gzip, deflate, br, zstd",
    #     "Accept-Language": "en-US,en;q=0.5",
    #     "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
    # }

    response = requests.get(url)

    html = response.text

    with open("webscrape.html", "w", encoding="utf-8") as f:
        f.write(html)
        
def generate_json(html):
    load_dotenv()
    api_key = os.getenv("MISTRAL_AGENT_KEY")
    client = Mistral(api_key=api_key)
    chat_response = client.agents.complete(
    agent_id="ag:3458fc26:20241215:web-scraper:d9671ce7",
    messages=[
            {
            "role": "user",
            "content": "{html}".format(html=html),
            },
        ],
    )
    return chat_response.choices[0].message.content
    

def main():
    base_url = "https://docs.mistral.ai" 
    scrape(base_url)
    
    with open("webscrape.html", "r") as html_file:
        html_content = html_file.read()
    
    json_response = generate_json(html_content)
    
    with open('data.json', 'w') as json_file:
        json.dump(json.loads(json_response), json_file)
    
    with open('data.json', 'r') as json_file:
        data = json.load(json_file)
        for link_info in data.get('links', []):
            full_link = link_info['url'] if link_info['type'] == "external" else base_url + link_info['url']
            print(full_link)
            
            scrape(full_link)
            
            with open("webscrape.html", "r", encoding="utf-8") as html_file:
                html_content = html_file.read()
            
            json_response = generate_json(html_content)
            json_data = json.loads(json_response)
            json_data['links'] = []
            
            with open('data.json', 'a') as json_file:
                json.dump(json_data, json_file)
main()