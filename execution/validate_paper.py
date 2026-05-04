import os
import sys
import argparse
import json
from dotenv import load_dotenv
import google.generativeai as genai
import io

# Fix Windows encoding issue - force UTF-8 for stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def validate_paper_relevance(title, abstract):
    """
    Use Gemini to validate if a paper is a core methodology research paper
    relevant to RAG, NLP, LLM, Prompt Engineering, or Context Engineering.

    Returns:
        dict: {
            "is_relevant": bool,
            "confidence": float (0-1),
            "reasoning": str,
            "topics": list of matched topics
        }
    """

    prompt = f"""You are an expert AI researcher evaluating paper relevance for a research database.

Analyze this paper and determine if it is a CORE METHODOLOGY RESEARCH paper in one or more of these topics:
1. RAG (Retrieval-Augmented Generation) - hybrid retrieval, dense retrieval, knowledge integration
2. Fine-tuning - instruction tuning, PEFT (LoRA, adapters), supervised fine-tuning
3. Hallucination - factuality, faithfulness, grounding, attribution verification
4. Prompt Engineering - prompt design, in-context learning, few-shot learning, chain-of-thought
5. Context Engineering - context window optimization, long context handling, context compression

EXCLUDE papers that:
- Only mention these topics as related work or background
- Are simple application/tool papers without novel methodology
- Focus on unrelated topics (computer vision, robotics, etc.) even if they mention LLMs
- Are survey papers without new methods

Paper Title: {title}

Abstract: {abstract}

Return your analysis in this exact JSON format:
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this is/isn't core methodology research",
    "topics": ["topic1", "topic2"]  // Empty list if not relevant
}}

Respond ONLY with valid JSON, no additional text."""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        # Extract JSON from response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        result = json.loads(response_text.strip())

        # Validate result structure
        if not isinstance(result, dict):
            raise ValueError("Response is not a JSON object")

        required_keys = ["is_relevant", "confidence", "reasoning", "topics"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key: {key}")

        return result

    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini response as JSON: {e}", file=sys.stderr)
        print(f"Raw response: {response_text}", file=sys.stderr)
        return {
            "is_relevant": False,
            "confidence": 0.0,
            "reasoning": "Failed to parse validation response",
            "topics": []
        }
    except Exception as e:
        print(f"Error validating paper: {e}", file=sys.stderr)
        return {
            "is_relevant": False,
            "confidence": 0.0,
            "reasoning": f"Validation error: {str(e)}",
            "topics": []
        }

def main(args):
    if args.title and args.abstract:
        result = validate_paper_relevance(args.title, args.abstract)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.json_file:
        # Batch validation from JSON file
        with open(args.json_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        validated_papers = []
        for paper in papers:
            validation = validate_paper_relevance(paper['title'], paper['summary'])
            paper['validation'] = validation
            validated_papers.append(paper)

        # Output validated papers
        print(json.dumps(validated_papers, ensure_ascii=False, indent=2))
    else:
        print("Error: Must provide either --title and --abstract, or --json-file", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate paper relevance using Gemini")
    parser.add_argument("--title", type=str, help="Paper title")
    parser.add_argument("--abstract", type=str, help="Paper abstract")
    parser.add_argument("--json-file", type=str, help="JSON file with papers to validate")

    args = parser.parse_args()
    main(args)
