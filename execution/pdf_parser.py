import os
import sys
import argparse
import requests
import io

def download_pdf(url):
    print(f"Downloading PDF from {url}...")
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        print(f"Failed to download PDF: {response.status_code}")
        return None

def extract_text_from_pdf(pdf_content):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = ""
        # Limit to more pages for deeper analysis
        for i in range(min(len(reader.pages), 10)):
            text += reader.pages[i].extract_text()
        return text
    except ImportError:
        print("PyPDF2 not installed. Please install it with 'pip install PyPDF2'")
        return ""
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def main(args):
    pdf_content = download_pdf(args.url)
    if pdf_content:
        text = extract_text_from_pdf(pdf_content)
        # Handle unicode output safely for Windows
        sys.stdout.reconfigure(encoding='utf-8')
        print(text[:10000])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Parser")
    parser.add_argument("--url", type=str, required=True, help="URL of the PDF to download and parse")
    
    args = parser.parse_args()
    main(args)
