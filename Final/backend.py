# Authentication
# CHATBOT
# WEBSCRAPING
# DATABASE
# Github_Scraper
# Memory

class Github_Scraper:
    def __init__(self):
        pass
    
    def url_changer(self, url):
        pass
    
    def scrape_content(self, url):
        pass
    
    def get_data(self, url):
        url = self.url_changer(url)
        data = self.scrape_content(url)
        return data
        
class Web_Scraper:
    def __init__(self):
        pass
        
    def recursive_scraper(self, links):
        pass
        
    def get_data(self, url):
        pass
    
    def scrape_content(self, url):
        data , struc = self.get_data(url)
        data += self.recursive_scraper(struc.links)
        return data
    
class PDFScraper:
    def __init__(self):
        pass
    def extract_data(pdf_path):
        pass
    
class TextProcessor:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_text(text)

class SnowflakeManager:
    def __init__(self):
        self.uid = None
    
    def get_uid(self):
        # returns data from auth page
        pass
    def set_uid(self, uid):
        self.uid = uid
        
    def connect(self):
        # returns connection object
        pass       
    def disconnect(self):
        # disconnects the connection
        pass
    def insert_data(self,data,source):
        # inserts data into the database
        if source.casefold() == 'Github':
            # insert into github table
            pass
        elif source.casefold() == 'Web':
            # insert into web table
            pass
        elif source.casefold() == 'PDF':
            # insert into pdf table
            pass
    def search(self, query):
        # both common and user data
        pass
    
    def generate(self, query):
        response = self.search(query)
        INSTRUCTION = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
                Document: {response}
                Query: {query}$$
            );
        """
        generation = None # fill up
        return generation

class Memory:
    def __init__(self):
        pass

class LLMcalls:
    def __init__(self):
        pass
    
class Backend:
    def __init__(self):
        pass
        # intisiali