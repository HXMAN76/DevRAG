import snowflake.connector
from dotenv import load_dotenv
load_dotenv()
import os
from chunking import chuck_data
conn = snowflake.connector.connect(
    user='devrag',
    password='Bsdb@123',
    account="pdhifjj-sxb83619",
    database="DEVRAG_DB",
    schema="DEVRAG_SCHEMA",
    warehouse="DEVRAG"
)
cursor = conn.cursor()
chunks_list = chuck_data('output')
web_url = 'https://react.dev/'
def insert_to_table(web_url,content):
    query = "INSERT INTO DEVRAG_SCHEMA.DOCUMENT (WEBSITE_URL, CONTENT) VALUES (%s, %s)"
    cursor.execute(query, (web_url, content))
    conn.commit()
for chunk in chunks_list:
    insert_to_table(web_url,chunk)
cursor.close()
conn.close()