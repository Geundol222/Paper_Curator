import os
import sys
import argparse
import json
import requests
import tempfile
from dotenv import load_dotenv

# Fix Windows console encoding for Korean output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import google.genai as genai

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables", file=sys.stderr)
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def download_pdf(pdf_url, max_size_mb=10):
    """Download PDF file and return content"""
    try:
        print(f"Downloading PDF from {pdf_url}...", file=sys.stderr)
        response = requests.get(pdf_url, timeout=60, stream=True)
        response.raise_for_status()

        # Check file size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size_mb * 1024 * 1024:
            print(f"Warning: PDF too large ({int(content_length)/1024/1024:.1f}MB), using abstract only", file=sys.stderr)
            return None

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name

        print(f"PDF downloaded successfully", file=sys.stderr)
        return tmp_path
    except Exception as e:
        print(f"Failed to download PDF: {e}", file=sys.stderr)
        return None

def analyze_paper_with_pdf(title, abstract, pdf_path):
    """Analyze paper using PDF content with Gemini"""

    prompt = f"""당신은 AI/NLP 연구 논문을 깊이 있게 분석하는 전문 연구원입니다.
첨부된 PDF 논문을 **정독**하고, 아래 논문을 **매우 상세하게** 분석하여 **한글로** 구조화된 요약을 제공하세요.

논문 제목: {title}

초록: {abstract}

**분석 지침:**
1. PDF 전체를 읽고 논문의 핵심 내용을 완전히 이해하세요
2. 단순 요약이 아닌, **학습자가 논문을 이해할 수 있는 수준**의 상세한 설명
3. 수식, 알고리즘, 실험 세팅 등 구체적인 내용 포함
4. 모든 내용은 **한글**로 작성하되, 중요 기술 용어는 영어 병기

다음 형식으로 JSON을 반환하세요:

{{
    "tldr": "논문의 핵심 기여를 2-3문장으로 명확하게 요약 (한글)",

    "key_points": [
        "핵심 포인트 1 (구체적으로)",
        "핵심 포인트 2 (구체적으로)",
        "핵심 포인트 3 (구체적으로)",
        "핵심 포인트 4 (구체적으로)"
    ],

    "problem": "이 논문이 해결하려는 문제와 기존 방법의 한계를 5-7문장으로 상세히 설명 (한글)",

    "approach": "제안하는 방법의 핵심 아이디어를 8-10문장으로 상세히 설명. 아키텍처 구성 요소, 학습 방법, 주요 알고리즘 포함 (한글)",

    "technical_details": "구현의 핵심 기술적 세부사항 5-7가지를 불릿 포인트로 작성. 수식, 하이퍼파라미터, 데이터셋 정보 포함 (한글)",

    "experiments": "실험 설정, 비교 대상(baseline), 사용한 데이터셋, 평가 지표를 5-6문장으로 설명 (한글)",

    "results": "주요 실험 결과를 구체적인 숫자와 함께 5-6문장으로 설명. 성능 개선폭, 통계적 유의성 포함 (한글)",

    "insights": [
        "이 논문에서 배울 수 있는 인사이트 1",
        "이 논문에서 배울 수 있는 인사이트 2",
        "이 논문에서 배울 수 있는 인사이트 3"
    ],

    "limitations": "논문의 한계점이나 향후 연구 방향 3-4문장으로 설명 (한글)",

    "practical_use": "실무 적용 시나리오와 활용 방안을 4-5문장으로 구체적으로 설명 (한글)",

    "study_questions": [
        "깊이 있게 공부하기 위한 질문 1",
        "깊이 있게 공부하기 위한 질문 2",
        "깊이 있게 공부하기 위한 질문 3",
        "깊이 있게 공부하기 위한 질문 4",
        "깊이 있게 공부하기 위한 질문 5"
    ],

    "related_concepts": [
        "관련 개념/기술 1: 간단한 설명",
        "관련 개념/기술 2: 간단한 설명",
        "관련 개념/기술 3: 간단한 설명"
    ]
}}

**절대 지켜야 할 규칙:**
1. 모든 문장은 **한글**로 작성
2. 기술 용어: "검색 증강 생성(Retrieval-Augmented Generation, RAG)" 형식
3. 추상적 표현 금지 - 구체적인 내용과 숫자 필수
4. 각 섹션은 최소 길이를 반드시 지켜야 함
5. 논문을 읽지 않고는 쓸 수 없는 구체적인 내용 포함

JSON만 반환하세요."""

    try:
        # Upload PDF to Gemini
        print("Uploading PDF to Gemini...", file=sys.stderr)
        uploaded_file = client.files.upload(file=pdf_path)

        print("Analyzing with Gemini...", file=sys.stderr)
        import time
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[uploaded_file, prompt]
                )
                break
            except Exception as e:
                if '429' in str(e) and attempt < 2:
                    wait = 30 * (attempt + 1)
                    print(f"Rate limit hit, waiting {wait}s before retry ({attempt+1}/3)...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    raise

        # Clean up temp file
        os.unlink(pdf_path)

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
        return result

    except Exception as e:
        print(f"Error analyzing with PDF: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Cleanup
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
        return None

def analyze_paper_abstract_only(title, abstract):
    """Fallback: Analyze using abstract only"""

    prompt = f"""당신은 AI/NLP 연구 논문을 분석하는 전문가입니다.
초록만으로 논문을 **최대한 상세하게** 분석하여 **한글로** 구조화된 요약을 제공하세요.

논문 제목: {title}

초록: {abstract}

다음 형식으로 JSON을 반환하세요 (각 필드는 충분히 길고 구체적으로):

{{
    "tldr": "핵심 기여 2-3문장 요약 (한글)",
    "key_points": ["핵심 1", "핵심 2", "핵심 3", "핵심 4"],
    "problem": "문제 정의 및 기존 방법의 한계 5-6문장 (한글)",
    "approach": "제안 방법 7-8문장 상세 설명 (한글)",
    "technical_details": "기술적 세부사항 5가지 (불릿)",
    "experiments": "실험 설정 추론 4-5문장 (한글)",
    "results": "예상 결과 및 성능 3-4문장 (한글)",
    "insights": ["인사이트 1", "인사이트 2", "인사이트 3"],
    "limitations": "한계점 3문장 (한글)",
    "practical_use": "실무 적용 방안 4문장 (한글)",
    "study_questions": ["질문1", "질문2", "질문3", "질문4", "질문5"],
    "related_concepts": ["개념1: 설명", "개념2: 설명", "개념3: 설명"]
}}

**규칙: 모든 내용 한글, 기술 용어는 "한글(영어)" 형식, 구체적으로 작성**

JSON만 반환하세요."""

    try:
        import time
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                break
            except Exception as e:
                if '429' in str(e) and attempt < 2:
                    wait = 30 * (attempt + 1)
                    print(f"Rate limit hit, waiting {wait}s before retry ({attempt+1}/3)...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    raise

        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        result = json.loads(response_text.strip())
        return result

    except Exception as e:
        print(f"Error analyzing abstract: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None

def main(args):
    # Try PDF first, fallback to abstract
    pdf_path = download_pdf(args.pdf_url)

    if pdf_path:
        result = analyze_paper_with_pdf(args.title, args.abstract, pdf_path)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    # Fallback to abstract only
    print("Falling back to abstract-only analysis...", file=sys.stderr)
    result = analyze_paper_abstract_only(args.title, args.abstract)

    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "tldr": "분석 실패",
            "key_points": ["분석 실패"],
            "problem": "분석 실패",
            "approach": "분석 실패",
            "technical_details": "분석 실패",
            "experiments": "분석 실패",
            "results": "분석 실패",
            "insights": ["분석 실패"],
            "limitations": "분석 실패",
            "practical_use": "분석 실패",
            "study_questions": ["분석 실패"],
            "related_concepts": ["분석 실패"]
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze paper with Gemini")
    parser.add_argument("--title", type=str, required=True, help="Paper title")
    parser.add_argument("--abstract", type=str, required=True, help="Paper abstract")
    parser.add_argument("--pdf-url", type=str, required=True, help="PDF URL")

    args = parser.parse_args()
    main(args)
