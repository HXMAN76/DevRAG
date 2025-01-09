import os
import json
import snowflake.connector
from snowflake.core import Root
from snowflake.snowpark import Session

class RAG:
    def __init__(self):
        self.CONNECTION_PARAMETERS = {
            "account": "pdhifjj-sxb83619",
            "user": 'devrag',
            "password": 'Bsdb@123',
            "role": "ACCOUNTADMIN",
            "database": "DEVRAG_DB",
            "warehouse": "DEVRAG",
            "schema": "DEVRAG_SCHEMA",
        }
        self.session = Session.builder.configs(self.CONNECTION_PARAMETERS).create()
        self.root = Root(self.session)

    def insert_to_table(self, web_url, content):
        conn = snowflake.connector.connect(
            user='devrag',
            password='Bsdb@123',
            account="pdhifjj-sxb83619",
            database="DEVRAG_DB",
            schema="DEVRAG_SCHEMA",
            warehouse="DEVRAG"
        )
        cursor = conn.cursor()
        query = "INSERT INTO DEVRAG_SCHEMA.DOCUMENT (WEBSITE_URL, CONTENT) VALUES (%s, %s)"
        cursor.execute(query, (web_url, content))
        conn.commit()
        cursor.close()
        conn.close()

    def search_and_generate(self, query):
        my_service = (
            self.root
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
            generation = self.session.sql(generation_query).collect()
            return generation[0][0]
        except Exception as e:
            print("Error:", e)
            return None