from web_scraper import WebScraper
from rag import RAG

class Main:
    def __init__(self):
        self.web_scraper = WebScraper()
        self.rag = RAG()

    def run(self):
        website_link = input("Enter the website link: ")
        query = input("Enter the query: ")

        data = self.web_scraper.wrapper(website_link)
        chunks = self.web_scraper.semantic_chunking(data)
        for chunk in chunks:
            self.rag.insert_to_table(website_link, chunk)

        response = self.rag.search_and_generate(query)
        if response:
            print(response)

if __name__ == "__main__":
    main = Main()
    main.run()