from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import os
from mistralai import Mistral  # type: ignore
import json
import urllib.parse
def scrape(url):

    token = "b1b349ec69b0484db9bd1a37deaab26e02c7488d1fb"

    targetUrl = urllib.parse.quote(url)

    ur = "http://api.scrape.do?token={}&url={}".format(token, targetUrl)

    response = requests.request("GET", ur)

    print(response.text)
        
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