import PyPDF2
import time
import re

def clean_text_thoroughly(text):
    """
    Performs thorough cleaning of the text to remove all types of extra whitespace.
    
    Args:
        text (str): The text to clean.
    
    Returns:
        str: Thoroughly cleaned text.
    """
    # Replace all types of whitespace (including newlines, tabs) with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,!?:;])', r'\1', text)
    
    # Remove spaces at the beginning and end
    text = text.strip()
    
    # Remove multiple newlines
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Remove spaces at the beginning of lines
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    
    # Remove spaces at the end of lines
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    
    return text

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file.
    
    Args:
        pdf_path (str): The path to the PDF file.
    
    Returns:
        tuple: (extracted text, time taken in seconds)
    """ 
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""
            
            for page in reader.pages:
                page_text = page.extract_text()
                extracted_text += page_text + "\n"
            
            # Apply thorough cleaning after all text is extracted
            extracted_text = clean_text_thoroughly(extracted_text)
            
            return extracted_text
    except FileNotFoundError:
        return "Error: File not found. Please provide a valid PDF file path.", 0
    except Exception as e:
        return f"An error occurred: {e}", 0

def save_text_to_file(text, output_path):
    """
    Saves the given text to a file.
    
    Args:
        text (str): The text to save.
        output_path (str): The path to the output text file.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"Text successfully saved to {output_path}")
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")

if __name__ == "__main__":
    pdf_path = "dummy.txt"
    output_txt_path = "output.txt"
    
    # Extract text and get timing
    pdf_text, processing_time = extract_text_from_pdf(pdf_path)
    
    # Save the extracted text to a text file if no errors
    if not pdf_text.startswith("Error"):
        save_text_to_file(pdf_text, output_txt_path)
        print(f"\nPDF Processing Statistics:")
        print(f"Time taken: {processing_time:.2f} seconds")
        print(f"Number of characters in cleaned text: {len(pdf_text)}")
    else:
        print(pdf_text)