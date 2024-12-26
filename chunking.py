from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from pathlib import Path

# Load the document
def load_document(file_path: str) -> str:
    """
    Load text content from a file.
    :param file_path: Path to the text file
    :return: Document content as a string
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Semantic Chunking using RecursiveCharacterTextSplitter
def semantic_chunking(text: str, chunk_size: int = 400, chunk_overlap: int = 50):
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

def save_chunks(chunks, output_dir="chunks"):
    """
    Save each chunk into a separate text file.
    :param chunks: List of text chunks
    :param output_dir: Directory to save chunks
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    for idx, chunk in enumerate(chunks):
        chunk_file = output_path / f"chunk_{idx+1}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as file:
            file.write(chunk)

def chuck_data(filename):
    # Specify the path to the input file
    input_file = f"{filename}.txt"  # Replace with your file path
    text_content = load_document(input_file)
    
    # Perform semantic chunking
    chunks = semantic_chunking(text_content, chunk_size=600, chunk_overlap=50)
    
    # Return the list of chunks
    return chunks

if __name__ == "__main__":
    chunks_list = chuck_data()
    # The chunks are now stored in the `chunks_list` variable
