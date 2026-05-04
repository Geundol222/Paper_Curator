import requests
import xml.etree.ElementTree as ET

def verify():
    url = "http://export.arxiv.org/api/query?search_query=id:2601.20674"
    r = requests.get(url)
    root = ET.fromstring(r.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entry = root.find('atom:entry', ns)
    if entry is not None:
        title = entry.find('atom:title', ns).text.strip()
        paper_id = entry.find('atom:id', ns).text
        print(f"ID: {paper_id}")
        print(f"Title: {title}")
    else:
        print("Not found")

if __name__ == "__main__":
    verify()
