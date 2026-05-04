---
description: Arxiv 논문 검색부터 Notion 업로드까지 전체 자동화 프로세스 실행
---

이 워크플로우는 Arxiv에서 최신 논문을 검색하고, 요약하여 Notion에 업로드합니다.

// turbo-all

1. 최근 한 달간의 관련 논문을 검색합니다.
```powershell
python execution/fetch_papers.py --days 30 --keywords "RAG,NLP,LLM"
```

2. Notion에 이미 등록된 논문 목록을 가져와 중복을 확인합니다.
```powershell
python execution/notion_api_tool.py query
```

3. 새 논문들에 대해 PDF를 파싱하고 요약을 생성합니다. (에이전트가 수행)
   - 각 논문의 PDF URL을 사용하여 `execution/pdf_parser.py`를 실행합니다.
   - 추출된 텍스트와 초록을 바탕으로 `GEMINI_MODEL`을 사용하여 요약, 인사이트, 학습 포인트를 요약합니다.

4. 요약된 내용을 Notion에 업로드합니다.
```powershell
python execution/notion_api_tool.py create --data "업로드용_JSON_데이터"
```

5. 임시 파일을 정리합니다.
