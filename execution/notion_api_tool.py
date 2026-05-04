import os
import sys
import argparse
import requests
import json
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_notion_db():
    """
    Query Notion DB to get all existing Arxiv IDs.
    Handles pagination to retrieve all pages.
    Returns a list of Arxiv IDs (not titles) for accurate duplicate detection.
    """
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

    existing_arxiv_ids = []
    has_more = True
    start_cursor = None

    while has_more:
        payload = {}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            print(f"Error querying Notion: {response.status_code} - {response.text}", file=sys.stderr)
            break

        data = response.json()
        results = data.get("results", [])

        for page in results:
            properties = page.get("properties", {})

            # Extract Arxiv ID (primary duplicate check)
            arxiv_prop = properties.get("Arxiv ID")
            if arxiv_prop and arxiv_prop.get("rich_text"):
                arxiv_texts = arxiv_prop["rich_text"]
                if arxiv_texts and len(arxiv_texts) > 0:
                    arxiv_id = arxiv_texts[0].get("plain_text", "").strip()
                    if arxiv_id:
                        existing_arxiv_ids.append(arxiv_id)

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    print(f"Found {len(existing_arxiv_ids)} existing papers in Notion DB", file=sys.stderr)
    return existing_arxiv_ids

def create_notion_page(data):
    url = "https://api.notion.com/v1/pages"

    analysis = data.get("analysis", {})

    # Build Notion blocks with improved structure
    blocks = []

    # TLDR Callout
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": analysis.get("tldr", "분석 중...")}}],
            "icon": {"emoji": "💡"},
            "color": "blue_background"
        }
    })

    # Key Points
    key_points = analysis.get("key_points", [])
    if key_points and isinstance(key_points, list):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🎯 핵심 포인트"}}], "color": "blue"}
        })
        for point in key_points:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": str(point)}}]}
            })

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # Problem Statement
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "❓ 해결하려는 문제"}}], "color": "red"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("problem", "분석 중...")}}]}
        }
    ])

    # Approach/Methodology
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🛠 제안 방법"}}], "color": "purple"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("approach", "분석 중...")}}]}
        }
    ])

    # Technical Details (Toggle)
    tech_details = analysis.get("technical_details", "분석 중...")
    if isinstance(tech_details, list):
        tech_children = [{
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"text": {"content": str(detail)}}]}
        } for detail in tech_details]
    else:
        tech_children = [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": str(tech_details)}}]}
        }]

    blocks.append({
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": {"content": "🔧 기술적 세부사항 (클릭하여 확장)"}}],
            "color": "gray_background",
            "children": tech_children
        }
    })

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # Experiments
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🧪 실험 설정"}}], "color": "orange"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("experiments", "분석 중...")}}]}
        }
    ])

    # Results
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "📊 주요 결과"}}], "color": "green"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("results", "분석 중...")}}]}
        }
    ])

    # Insights Callout
    insights = analysis.get("insights", [])
    if insights and isinstance(insights, list):
        insights_text = "\n".join([f"• {insight}" for insight in insights])
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": insights_text}}],
                "icon": {"emoji": "💡"},
                "color": "yellow_background"
            }
        })

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # Practical Use
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🚀 실무 적용"}}], "color": "green"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("practical_use", "분석 중...")}}]}
        }
    ])

    # Limitations
    blocks.extend([
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "⚠️ 한계점"}}], "color": "red"}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": analysis.get("limitations", "분석 중...")}}]}
        }
    ])

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # Study Questions
    questions = analysis.get("study_questions", [])
    if questions and isinstance(questions, list):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "❓ 학습 질문"}}], "color": "blue"}
        })
        for q in questions:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": str(q)}}]}
            })

    # Related Concepts
    concepts = analysis.get("related_concepts", [])
    if concepts and isinstance(concepts, list):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🔗 관련 개념"}}], "color": "gray"}
        })
        for concept in concepts:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": str(concept)}}]}
            })

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "icon": {"type": "emoji", "emoji": "📄"},
        "properties": {
            "제목": {
                "title": [{"text": {"content": data["title"]}}]
            },
            "Arxiv ID": {
                "rich_text": [{"text": {"content": data["id"]}}]
            },
            "URL": {
                "url": data["url"]
            },
            "날짜": {
                "date": {"start": data["date"]}
            }
        },
        "children": blocks
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"Error creating Notion page: {response.status_code} - {response.text}")
        return None
    return response.json()

def main(args):
    if args.action == "query":
        titles = query_notion_db()
        print(json.dumps(titles, ensure_ascii=False))
    elif args.action == "create":
        if not args.data:
            print("Error: --data argument required for create action", file=sys.stderr)
            sys.exit(1)

        data_str = args.data
        try:
            # Try to parse as JSON string first
            data = json.loads(data_str)
        except json.JSONDecodeError:
            # If that fails, try to read as file path
            if os.path.exists(data_str):
                with open(data_str, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                print(f"Error: Invalid JSON data: {data_str[:100]}", file=sys.stderr)
                sys.exit(1)

        result = create_notion_page(data)
        if result:
            print(f"Successfully created page: {result.get('id')}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notion API Tool")
    parser.add_argument("action", choices=["query", "create"], help="Action to perform")
    parser.add_argument("--data", type=str, default=None, help="JSON data for creating page (string or file path)")

    args = parser.parse_args()
    main(args)
