import json
import time
import re
import sys
from ollama import Client
from datetime import datetime
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
import fitz  # PyMuPDF
import base64
from pdf2image import convert_from_path
from PIL import Image

start_time = time.time()
# print(datetime.today().strftime("%Y-%m-%d %H:%M"))

ollama = Client()
#PDF transcriber prompts
SYSTEM_PROMPT1 = """Use the following pieces of retrieved context to answer the question. In a list with no bullet points with headings for each item:
1. Provide the Invoice Number, Date, the Customer and the Supplier.
2. List the items in the invoice on one line, the heading in your answer should just be 'Items'.
3. Provide the total price quoted on the invoice,the heading in your answer should just be 'Total Price.
4. If any details requested are not present in the invoice, indicate this with [not found] in your transcription .                Question: {question} 
                Context: {context} 
                Answer:"""

USER_PROMPT = """What is the invoice number?, What is the date of the invoice?, Who is the customer?, 
                Who is the supplier?, What items are listed in the invoice? List them on one line, What is the total price quoted on the invoice?"""

#image transcriber prompt
SYSTEM_PROMPT2 = """Act as an OCR assistant. Analyze the provided invoice and in a list with no bullet points, numbers or asterisks:
1. Provide the Invoice Number, Date, the Customer and the Supplier on separate lines.
2. List the items purchased in the invoice on one line, the heading in your answer should just be 'Items'.
3. Provide the total price quoted on the invoice,the heading in your answer should just be 'Total Price.
4. If any details requested are not present in the invoice, indicate this with [not found] in your transcription ."""


#pdf handling functions
def load_pdf(pdf_bytes):
    """Load PDF document and return its content."""
    if pdf_bytes is None:
        return None, None, None
    loader = PyMuPDFLoader(pdf_bytes)
    data = loader.load()
    return data

def split_text(documents):
    """Split text into manageable chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    return text_splitter.split_documents(documents)

def index_docs(vector_store, documents):
    """Index documents into the vector store."""
    vector_store.add_documents(documents)

def retrieve_docs(vector_store, query):
    """Retrieve documents from the vector store based on a query."""
    return vector_store.similarity_search(query)

def answer_question(documents, question, model_name):
    """Answer a question based on the retrieved documents."""
    model = OllamaLLM(model=model_name)
    context = "\n\n".join([doc.page_content for doc in documents])
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT1)
    chain = prompt | model
    return chain.invoke({"question": question, "context": context})

def invoice_parser(invoice_results):
    """Parse the invoice results to extract structured data."""
    invoice_data = {}
    invoice_data['Invoice Number'] = re.search(r'Invoice Number:\**\s*(.*)', invoice_results).group(1) if re.search(r'Invoice Number:\**\s*(.*)', invoice_results) else '[not found]'
    invoice_data['Date'] = re.search(r'Date:\**\s*(.*)', invoice_results).group(1) if re.search(r'Date:\**\s*(.*)', invoice_results) else '[not found]'   
    invoice_data['Customer'] = re.search(r'Customer:\**\s*(.*)', invoice_results).group(1) if re.search(r'Customer:\**\s*(.*)', invoice_results) else '[not found]'
    invoice_data['Supplier'] = re.search(r'Supplier:\**\s*(.*)', invoice_results).group(1) if re.search(r'Supplier:\**\s*(.*)', invoice_results) else '[not found]'
    invoice_data['Item/s'] = re.search(r'Items:\**\s*(.*)', invoice_results).group(1) if re.search(r'Items:\**\s*(.*)', invoice_results) else '[not found]'
    invoice_data['Total Price'] = re.search(r'Total Price:\**\s*(.*)', invoice_results).group(1) if re.search(r'Total Price:\**\s*(.*)', invoice_results) else '[not found]'
   
    return invoice_data

def pdf_contains_images(pdf_path):
    """Check if the PDF contains images."""
    try:
        pdf_document = fitz.open(pdf_path)
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            if page.get_images(full=True):  # Check if the page contains images
                return True
        return False
    except Exception as e:
        # print(f"Error while checking for images: {e}")
        return False


def pdf_contains_text(pdf_path):
    """Check if the PDF contains text."""
    try:
        pdf_document = fitz.open(pdf_path)
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            if page.get_text():  # Check if the page contains text
                return True
        return False
    except Exception as e:
        # print(f"Error while checking for text: {e}")
        return False

#Handles transcription of PDF documents
def pdf_transcribe(file_path):
    model_name = "deepseek-r1"
    embeddings = OllamaEmbeddings(model=model_name)
    vector_store = InMemoryVectorStore(embeddings)

    #print(f"Using model: {model_name}")

    documents = load_pdf(file_path)
    chunked_documents = split_text(documents)
    index_docs(vector_store, chunked_documents)  # Pass vector_store here

    related_documents = retrieve_docs(vector_store, USER_PROMPT)  # Pass vector_store here
    answer = answer_question(related_documents, USER_PROMPT, model_name)
    # print(f"Question: {USER_PROMPT}")
    # print(f"Answer: {answer}")

    invoice_data = invoice_parser(answer)
    return invoice_data  # Return the results for further processing if needed

#Handles transcription of image documents
def image_transcribe(image_url):
    model_name = 'llama3.2-vision:11b'
    #print(f"Using model: {model_name}")

    with open(image_url, 'rb') as img_file:
        image_bytes = img_file.read()

    invoice_results = None  # Initialize the variable

    try:
        # Get description without a timeout mechanism
        # result = ollama.generate(model='llama3.2-vision', prompt=SYSTEM_PROMPT, images=[image_bytes])
        result = ollama.generate(model=model_name, prompt=SYSTEM_PROMPT2, images=[image_bytes])
        # print(result['response'])
        invoice_results = result['response']  # Assign value if no exception occurs

    except Exception as e:
        exit()
        # print(f"Error occurred: {e}")

    invoice_data = invoice_parser(invoice_results)
    return invoice_data  # Return the results for further processing if needed

# Main execution starts here

# Get the document name from command line arguments
document_name = sys.argv[1]

#identify whether a file is a PDF or an image
if document_name.lower().endswith('.pdf'):
    # Check if the PDF contains text or images
    # If it contains text, extract text; if it contains images, transcribe images
    # considering the PDF might contain both text and images. combine the results from both functions into a single dictionary.
    if pdf_contains_text(document_name):
        # print("The PDF contains text. Extracting text...")
        # Add logic to extract text from the PDF
        invoice_data = pdf_transcribe(document_name)
    # check if the pdf transcribe got all fields, if not check if the fields can be captured from the images. the function should stll run if there was no text in the pdf.
    if pdf_contains_images(document_name) and (not invoice_data or any(value == '[not found]' for value in invoice_data.values())):
        # print("Some fields were not found in the text extraction. Checking images...")
        # Add logic to transcribe images from the PDF
        # screenshot the pages of the pdf and transcribe them using pdf2image library
        images = convert_from_path(document_name)
        for i, image in enumerate(images):
            image_path = f"page_{i + 1}.png"
            image.save(image_path, 'PNG')
            result = image_transcribe(image_path)
            if not isinstance(invoice_data, dict):
                invoice_data = result
            else:
                # Update invoice_data with new results, ensuring no overwriting of existing data
                # This assumes that the keys in result match those in invoice_data
                # If a key is not present in invoice_data, it will be added
                # If a key is present but has a value of '[not found]', it will be updated with the new value
                # If a key is present and has a value other than '[not found]', it will remain unchanged
                # This way, we ensure that we capture all available data without losing any existing information
                for key, value in result.items():
                    if key not in invoice_data or re.search(r'\[not found\]', invoice_data[key]):
                        invoice_data[key] = value
    # else:
    #     print("No images found in the PDF or all fields were captured from text extraction.")

elif document_name.lower().endswith(('.png', '.jpg', '.jpeg')):
    invoice_data = image_transcribe(document_name)

else:
    # print("Unsupported file type. Please provide a PDF or an image file.")
    sys.exit(1)


# print the invoice data as a JSON object
# print("\nFinal Parsed Invoice Data:")
print(json.dumps(invoice_data, indent=4))  # Print the invoice data in JSON format

# print("Final Parsed Invoice Data:")
# for key, value in invoice_data.items():
#     print(f"{key}: {value}")

end_time = time.time()
# print(f"Execution time: {end_time - start_time} seconds")
# print(datetime.today().strftime("%Y-%m-%d %H:%M"))
