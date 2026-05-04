import os
import sys
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta

def get_rag_papers():
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": 'cat:cs.CL AND (abs:"RAG" OR ti:"RAG")',
        "max_results": 10,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    response = requests.get(base_url, params=params)
    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
        id_val = entry.find('atom:id', ns).text.split('/abs/')[-1]
        print(f"ID: {id_val} | Title: {title}")

if __name__ == "__main__":
    get_rag_papers()
