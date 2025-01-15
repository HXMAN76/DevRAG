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

