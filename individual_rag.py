def insert_into_github_rag(self,user_id,content):
    if(content):
        insert_query = f"""INSERT INTO {user_id}_github (content) VALUES {content}"""
        self.cursor.execute(insert_query)
        self.conn.commit()
def insert_into_personal_rag(self,user_id,content):
    if(content):
        insert_query = f"""INSERT INTO {user_id}_rag (content) VALUES {content}"""
        self.cursor.execute(insert_query)
        self.conn.commit()
def insert_into_pdf_rag(self,user_id,content):
    if(content):
        insert_query = f"""INSERT INTO {user_id}_pdf (content) VALUES {content}"""
        self.cursor.execute(insert_query)
        self.conn.commit()

def presonal_rag_search(self,user_id,query):
    root = Root(self.session)
    search_service_common = (
        root
        .databases["DEVRAG_DB"]
        .schemas["DEVRAG_SCHEMA"]
        .cortex_search_services[f"{user_id}_ragsearch"]
    )
    search_results = search_service_common.search(
        query=query,
        columns=["CONTENT"],
        limit=5
    )
    response = json.dumps(search_results.to_dict())
    return response
def common_rag_search(self,query):
    root = Root(self.session)
    search_service_common = (
        root
        .databases["DEVRAG_DB"]
        .schemas["DEVRAG_SCHEMA"]
        .cortex_search_services["DEVRAG"]
    )
    search_results = search_service_common.search(
        query=query,
        columns=["CONTENT"],
        limit=5
    )
    
    response = json.dumps(search_results.to_dict())
    return response
def github_rag_search(self,user_id,query):
    root = Root(self.session)
    search_service_common = (
        root
        .databases["DEVRAG_DB"]
        .schemas["DEVRAG_SCHEMA"]
        .cortex_search_services[f"{user_id}_githubsearch"]
    )
    search_results = search_service_common.search(
        query=query,
        columns=["CONTENT"],
        limit=5
    )
    response = json.dumps(search_results.to_dict())
    return response
def pdf_rag_search(self,user_id,query):
    root = Root(self.session)
    search_service_common = (
        root
        .databases["DEVRAG_DB"]
        .schemas["DEVRAG_SCHEMA"]
        .cortex_search_services[f"{user_id}_pdfsearch"]
    )
    search_results = search_service_common.search(
        query=query,
        columns=["CONTENT"],
        limit=5
    )
    response = json.dumps(search_results.to_dict())
    return response