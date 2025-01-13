import asyncio
from crawl4ai import AsyncWebCrawler
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import snowflake.connector
from dotenv import load_dotenv
from snowflake.core import Root
from snowflake.snowpark import Session
load_dotenv()

async def webscrape(url: str):
    async with AsyncWebCrawler() as crawler:
        try:
            result = await crawler.arun(
                url=f"{url}",
                magic=True,
                simulate_user=True,
                override_navigator=True,
                exclude_external_images=True,
                exclude_social_media_links=True,
            )
            return result
        except Exception as e:
            print(f"Error during web crawling: {e}")
            return None
        
def wrapper(url: str):
    scrape_data = ''
    data = asyncio.run(webscrape(url))
    unwanted = ['signup', 'signin', 'register', 'login', 'billing', 'pricing', 'contact', 'sign up', 'sign in', 'expert services']
    social_media = ['youtube', 'twitter', 'facebook', 'linkedin']
    if data and data.markdown:
        scrape_data += data.markdown
    for key in data.links:
        for link in data.links[key]:
            text = link.get('text', '').casefold()
            href = link.get('href', '')
            if text in unwanted or any(platform in href for platform in social_media):
                continue 

            sub_data = asyncio.run(webscrape(link["href"]))
            if sub_data and sub_data.markdown:
                scrape_data += sub_data.markdown
    return scrape_data

def semantic_chunking(text: str, chunk_size: int = 512, chunk_overlap: int = 50):
    """
    Split text into semantic chunks using RecursiveCharacterTextSplitter.
    :param text: The full text to split
    :param chunk_size: Maximum size of each chunk
    :param chunk_overlap: Overlap size between chunks for context
    :return: List of chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    return chunks

def insert_to_table(web_url,content):
    query = "INSERT INTO DEVRAG_SCHEMA.DOCUMENT (WEBSITE_URL, CONTENT) VALUES (%s, %s)"
    cursor.execute(query, (web_url, content))
    conn.commit()

if __name__ == "__main__":

    website_link = input("Enter the website link: ")
    query = input("Enter the query: ")

    conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
    )
    cursor = conn.cursor()

    data = wrapper(website_link)
    chunks = semantic_chunking(data)
    for chunk in chunks:
        insert_to_table(website_link,chunk)
    cursor.close()
    conn.close()

    CONNECTION_PARAMETERS = {
    "account": "pdhifjj-sxb83619",
    "user": 'devrag',
    "password": 'Bsdb@123',
    "role": "ACCOUNTADMIN",
    "database": "DEVRAG_DB",
    "warehouse": "DEVRAG",
    "schema": "DEVRAG_SCHEMA",
    }

    session = Session.builder.configs(CONNECTION_PARAMETERS).create()
    root = Root(session)

    my_service = (
    root
    .databases["DEVRAG_DB"]
    .schemas["DEVRAG_SCHEMA"]
    .cortex_search_services["DEVRAG"]
    )

    resp = my_service.search(
    query=query,
    columns=["CONTENT"],
    limit=5
    )

    response = json.dumps(resp.to_dict())
    generation_query = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
        Document: {response}
        Query: {query}$$
    );
    """
    try:
        generation = session.sql(generation_query).collect()
        print(generation[0][0])
    except Exception as e:
        print("Error:", e)