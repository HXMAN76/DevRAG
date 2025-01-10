# Import the necessary library
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file.
    
    Args:
        pdf_path (str): The path to the PDF file.
    
    Returns:
        str: The extracted text from the PDF.
    """
    try:
        # Open the PDF file in read-binary mode
        with open(pdf_path, 'rb') as pdf_file:
            # Create a PDF reader object
            reader = PyPDF2.PdfReader(pdf_file)
            
            # Initialize an empty string to store the text
            extracted_text = ""
            
            # Loop through each page in the PDF and extract text
            for page in reader.pages:
                extracted_text += page.extract_text()
            
            return extracted_text
    except FileNotFoundError:
        return "Error: File not found. Please provide a valid PDF file path."
    except Exception as e:
        return f"An error occurred: {e}"

# Example usage
if __name__ == "__main__":
    # Prompt the user for the PDF file path
    pdf_path = "dummy.pdf"
    
    # Extract text from the provided PDF file
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # Print the extracted text
    print("\nExtracted Text from PDF:")
    print(pdf_text)
