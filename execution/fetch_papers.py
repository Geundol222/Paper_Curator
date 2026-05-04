import os
import sys
import argparse
import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import io

# Fix Windows encoding issue - force UTF-8 for stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def fetch_arxiv_papers(keywords, days):
    base_url = "http://export.arxiv.org/api/query?"

    # Calculate date cutoff for filtering
    date_cutoff = datetime.now() - timedelta(days=days)

    # Focus on core AI/NLP categories
    categories = ['cs.CL', 'cs.AI', 'cs.LG']
    cat_query = "(" + " OR ".join([f"cat:{c}" for c in categories]) + ")"

    # Define comprehensive search terms for RAG, NLP, LLM, Prompt Engineering, and Context Engineering
    search_terms = {
        "RAG": [
            "Retrieval-Augmented Generation",
            "Retrieval Augmented",
            "RAG",
            "Knowledge Retrieval",
            "Dense Retrieval",
            "Hybrid Retrieval"
        ],
        "Fine-tuning": [
            "Fine-tuning",
            "Instruction Tuning",
            "Parameter-Efficient",
            "PEFT",
            "LoRA",
            "Adapter",
            "Supervised Fine-Tuning",
            "SFT"
        ],
        "Hallucination": [
            "Hallucination",
            "Factuality",
            "Faithfulness",
            "Grounding",
            "Attribution"
        ],
        "Prompt Engineering": [
            "Prompt Engineering",
            "Prompt Design",
            "In-Context Learning",
            "ICL",
            "Few-Shot Learning",
            "Chain-of-Thought",
            "CoT",
            "Prompt Optimization"
        ],
        "Context Engineering": [
            "Context Engineering",
            "Context Window",
            "Long Context",
            "Context Management",
            "Context Compression",
            "Context Utilization"
        ]
    }

    # Build precise topic queries with title emphasis
    topic_queries = []
    for topic, variations in search_terms.items():
        # Prioritize title matches but also check abstract
        title_queries = " OR ".join([f'ti:"{v}"' for v in variations])
        abs_queries = " OR ".join([f'abs:"{v}"' for v in variations])
        # Title match OR (abstract match with stricter relevance)
        var_query = f"({title_queries}) OR ({abs_queries})"
        topic_queries.append(f"({var_query})")

    # Combine: (Categories) AND (at least one topic)
    query_str = f"{cat_query} AND ({' OR '.join(topic_queries)})"

    params = {
        "search_query": query_str,
        "start": 0,
        "max_results": 100,  # Increased to get more results before date filtering
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"Error fetching data from Arxiv: {response.status_code}")
        return []
    
    root = ET.fromstring(response.content)
    # Namespace for Arxiv API
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
    
    papers = []
    for entry in root.findall('atom:entry', ns):
        id_node = entry.find('atom:id', ns)
        title_node = entry.find('atom:title', ns)
        summary_node = entry.find('atom:summary', ns)
        published_node = entry.find('atom:published', ns)

        if id_node is None or title_node is None or published_node is None:
            continue

        paper_id = id_node.text.split('/abs/')[-1].strip()
        title = title_node.text.strip().replace('\n', ' ')
        summary = summary_node.text.strip().replace('\n', ' ') if summary_node is not None else ""
        published = published_node.text.strip()

        # Apply date filter - only include papers within the specified days
        try:
            published_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            # Convert to naive datetime for comparison
            published_date = published_date.replace(tzinfo=None)
            if published_date < date_cutoff:
                continue  # Skip papers older than the cutoff
        except (ValueError, AttributeError) as e:
            print(f"Warning: Could not parse date for paper {paper_id}: {published}", file=sys.stderr)
            continue

        pdf_url = ""
        for link in entry.findall('atom:link', ns):
            if link.attrib.get('title') == 'pdf':
                pdf_url = link.attrib.get('href')
                break
            elif link.attrib.get('type') == 'application/pdf':
                pdf_url = link.attrib.get('href')

        # If no PDF link found, construct it (standard Arxiv format)
        if not pdf_url:
            # Remove version suffix for URL construction
            base_id = paper_id.split('v')[0] if 'v' in paper_id else paper_id
            pdf_url = f"https://arxiv.org/pdf/{base_id}.pdf"

        papers.append({
            "id": paper_id,
            "title": title,
            "summary": summary,
            "pdf_url": pdf_url,
            "published": published
        })

    return papers

def main(args):
    print(f"--- FETCHING PAPERS START ---")
    papers = fetch_arxiv_papers(args.keywords, args.days)
    
    # Output each paper as a separate identifiable block
    for paper in papers:
        print(f"ID_START:{paper['id']}")
        print(json.dumps(paper, ensure_ascii=False))
        print(f"ID_END:{paper['id']}")
    print(f"--- FETCHING PAPERS END ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch papers from Arxiv")
    parser.add_argument("--keywords", type=str, default="RAG,NLP,LLM", help="Keywords to search in abstract")
    parser.add_argument("--days", type=int, default=30, help="Number of days to look back")
    
    args = parser.parse_args()
    main(args)
