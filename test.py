import os
import json
from dotenv import load_dotenv
import snowflake.connector
from concurrent.futures import ThreadPoolExecutor, as_completed

class SnowflakeManager:
    def __init__(self):
        load_dotenv()
        self.connection_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "role": "ACCOUNTADMIN",
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        }
        self.session = None
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = snowflake.connector.connect(**self.connection_params)
        self.cursor = self.conn.cursor()
        self.session = Session.builder.configs(self.connection_params).create()

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        if self.session:
            self.session.close()

    def _insert(self, table_name, contents):
        if contents:
            insert_queries = [f"INSERT INTO {table_name} (content) VALUES ('{content}')" for content in contents]
            for query in insert_queries:
                self.cursor.execute(query)
            self.conn.commit()

    def insert_into_github_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_github", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise an exception if the insert failed
                except Exception as e:
                    print(f"Error inserting into {user_id}_github: {e}")

    def insert_into_personal_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_rag", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_rag: {e}")

    def insert_into_pdf_rag(self, user_id, contents):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._insert, f"{user_id}_pdf", contents): user_id}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error inserting into {user_id}_pdf: {e}")

    def _search_service(self, user_id, service_name, query):
        root = Root(self.session)
        search_service = (
            root.databases[os.getenv("SNOWFLAKE_DATABASE")]
                .schemas[os.getenv("SNOWFLAKE_SCHEMA")]
                .cortex_search_services[service_name]
        )
        search_results = search_service.search(query=query, columns=["CONTENT"], limit=5)
        return json.dumps(search_results.to_dict())

    def search(self, user_id, query: str) -> list:
        services = {
            "common": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "personal": f"{user_id}_ragsearch",
            "github": f"{user_id}_githubsearch",
            "pdf": f"{user_id}_pdfsearch"
        }

        results = []
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self._search_service, user_id, service_name, query): name for name, service_name in services.items()}
            
            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error searching in {service_name}: {e}")

        return results

    def generation(self, query, response):
        generation_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
                Document: {response}
                Query: {query}$$
            );
        """
        generation = self.session.sql(generation_query).collect()
        return generation[0][0]
