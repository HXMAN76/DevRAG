import os
from snowflake.core import Root
from snowflake.snowpark import Session
import json
from dotenv import load_dotenv
load_dotenv()

q = "what is RAG, and how does it work?"

CONNECTION_PARAMETERS = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "role": "ACCOUNTADMIN",
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
}

# Initialize the Snowflake session
session = Session.builder.configs(CONNECTION_PARAMETERS).create()
root = Root(session)

# Access the Cortex Search service
my_service = (
    root
    .databases["DEVRAG_DB"]
    .schemas["DEVRAG_SCHEMA"]
    .cortex_search_services["DEVRAG"]
)

# Perform the search query
resp = my_service.search(
    query=q,
    columns=["CONTENT"],
    limit=5
)

# Convert the response to JSON and escape it properly
response = json.dumps(resp.to_dict())  # Ensures proper formatting for SQL

# Format the SQL query string
generation_query = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
        Document: {response}
        Query: {q}$$
    );
"""

# Execute the query
try:
    generation = session.sql(generation_query).collect()
    print(generation[0][0])
except Exception as e:
    print("Error:", e)
