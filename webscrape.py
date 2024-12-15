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

    with open("webscrape.html", "w") as f:
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
    chat_response.choices[0].message.content
    

def main():
    url = "https://docs.mistral.ai/"
    scrape(url)
    html = open("webscrape.html", "r").read()
    json_data = generate_json(html)
    print(json_data)
    # with open('sample.json', 'r') as f:
    #     data = json.load(f) 
    #     for i in data['links']:
    #         if i['type'] == "external":
    #             print(i['url'])
    #             scrape(i['url'])
    #             html = open("webscrape.html", "r").read()
    #             json_data = generate_json(html)
                
    
main()