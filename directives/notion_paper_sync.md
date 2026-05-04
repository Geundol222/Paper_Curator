# Arxiv 논문 요약 및 Notion 자동화 SOP

본 지시서는 RAG, NLP, LLM, 프롬프트 엔지니어링, 컨텍스트 엔지니어링 분야의 최신 Arxiv 논문을 검색하여 요약하고, 중복을 제외한 후 Notion 데이터베이스에 업로드하는 워크플로우를 정의합니다.

## 1. 운영 파라미터
- **검색 테마**:
    - **RAG**: Retrieval-Augmented Generation, Dense Retrieval, Hybrid Retrieval, Knowledge Retrieval
    - **Fine-tuning**: Instruction Tuning, PEFT (LoRA, Adapter 등), Supervised Fine-Tuning (SFT), 도메인 특화 학습
    - **Hallucination**: Factuality, Faithfulness, Grounding, Attribution, 검증(Verification) 프레임워크
    - **Prompt Engineering**: Prompt Design, In-Context Learning (ICL), Few-Shot Learning, Chain-of-Thought (CoT), Prompt Optimization
    - **Context Engineering**: Context Window Optimization, Long Context Handling, Context Compression, Context Management
- **검색 카테고리**: `cs.CL` (Computation and Language), `cs.AI` (Artificial Intelligence), `cs.LG` (Machine Learning)
- **검색 범위**: 최근 30일 (검색일 기준)
- **중복 기준**: Arxiv ID 기준 (Notion DB에 이미 존재하는 경우 제외)
- **관련성 검증**: Gemini API를 사용하여 핵심 방법론 연구인지 자동 검증

## 2. 세부 단계 (Step-by-Step)

### Step 1: Arxiv 논문 검색 (Improved)
- `execution/fetch_papers.py`를 실행하여 최근 30일 이내의 논문을 검색합니다.
- 파라미터: `--days 30` (기본값)
- **개선 사항**:
  - 날짜 필터링이 자동으로 적용됨 (published_date < 30일 전인 논문 제외)
  - 검색 결과 최대 100개로 증가 (더 많은 후보 확보)
  - 5가지 주제(RAG, Fine-tuning, Hallucination, Prompt Engineering, Context Engineering)에 대한 정교한 키워드 매칭
  - PDF URL 생성 로직 개선 (버전 처리 강화)

### Step 2: 중복 필터링 (Improved)
- `execution/notion_api_tool.py query`를 실행하여 Notion DB의 모든 기존 Arxiv ID를 조회합니다.
- **개선 사항**:
  - 제목 대신 Arxiv ID 기준으로 중복 검사 (정확도 향상)
  - Pagination 처리로 100개 이상의 페이지도 모두 조회
  - 검색된 논문 중 이미 존재하는 Arxiv ID는 자동 제외

### Step 3: 관련성 검증 (New)
- `execution/validate_paper.py`를 사용하여 각 논문의 관련성을 Gemini API로 검증합니다.
- 단순 도구 활용 사례가 아닌 **핵심 방법론 연구**만 선별합니다.
- 검증 결과:
  - `is_relevant: true` - 핵심 방법론 연구
  - `is_relevant: false` - 관련 없는 논문 또는 단순 응용 사례
  - `confidence`: 0.0 ~ 1.0 (신뢰도)
  - `topics`: 매칭된 주제 리스트
- **신뢰도 0.7 이상, is_relevant: true인 논문만 다음 단계로 진행**

### Step 4: 중복 제거된 최종 논문 리스트 확정
- Step 2의 중복 필터링 + Step 3의 관련성 검증을 통과한 논문만 선별
- 최종 리스트 확정

### Step 5: 고도화된 PDF 분석 및 기술 딥다이브 (Extreme Depth)
- 필터링된 각 논문에 대해 `GEMINI_MODEL` (Gemini-2.5-flash)을 사용하여 **전공 서적 수준의 상세한 기술 분석 노트**를 생성합니다.
- **분량 가이드라인**: 각 섹션별로 최소 2~3개 이상의 상세 문단을 작성하며, 단순히 '무엇을 했다'가 아니라 '어떻게 구현했는지'에 집중합니다.
- **분석 필수 요소**:
    1.  **📌 TL;DR**: 핵심 결론 한 문장.
    2.  **🔬 Research Context & Problem Statement**: 기존 SOTA 모델의 한계점과 본 논문이 해결하려는 핵심 수식적/논리적 결함 분석.
    3.  **🛠 Technical Deep-dive (Core Mechanism)**:
        - 아키텍처 다이어그램을 말로 설명하듯 상세히 기술.
        - 핵심 알고리즘의 동작 순서 (Step-by-Step).
        - 사용된 데이터셋, 손실 함수(Loss Function), 파라미터 최적화 방식.
    4.  **📊 Evaluation & Comparative Analysis**: 구체적인 벤치마크 점수와 그래프가 시사하는 바를 전문적으로 분석.
    5.  **🚀 Project Roadmap & Action Plan**: 우리 프로젝트 코드에 직접 삽입할 수 있는 수준의 구체적인 구현 아이디어.
    6.  **❓ Critical Review & Future Study**: 논문의 약점과 이를 극복하기 위해 우리가 더 찾아봐야 할 참고 문헌 및 주제.

### Step 6: Notion 업로드
- `execution/notion_api_tool.py create`를 사용하여 요약된 내용을 Notion DB에 새 페이지로 업로드합니다.
- 데이터베이스 속성: 제목, Arxiv ID, URL, 날짜, 요약 내용(본문)

### Step 7: 정리
- `.tmp/` 폴더의 임시 PDF 파일들을 삭제합니다.

## 3. 예외 처리
- **PDF 다운로드 실패 시**: 초록(Abstract) 정보로만 요약을 시도하고, 요약 내용에 "PDF 분석 실패"라고 명시합니다.
- **Notion API 오류 시**: 로그를 기록하고 다음 논문으로 넘어갑니다.
- **날짜 파싱 실패 시**: 해당 논문을 건너뛰고 경고 메시지를 출력합니다.
- **관련성 검증 실패 시**: 기본값으로 `is_relevant: false` 처리하여 제외합니다.
- **Gemini API 할당량 초과 시**: 에러를 기록하고 나머지 논문은 관련성 검증 없이 진행할지 사용자에게 확인합니다.

## 4. 개선 사항 요약 (2026-01-30)

### 검색 정확도 향상
1. **날짜 필터링 구현**: 검색일 기준 30일 이내의 논문만 선별 (이전에는 미적용)
2. **검색 범위 확장**:
   - Prompt Engineering (In-Context Learning, Few-Shot, CoT 등) 추가
   - Context Engineering (Long Context, Context Compression 등) 추가
3. **키워드 정교화**: 각 주제별로 5~8개의 관련 키워드로 세분화
4. **검색 결과 수 증가**: 20개 → 100개 (날짜 필터링 후 충분한 결과 확보)

### 중복 검사 정확도 향상
1. **Arxiv ID 기반 중복 검사**: 제목 대신 고유 ID로 정확한 중복 검출
2. **Pagination 처리**: 100개 이상의 Notion 페이지도 모두 조회하여 누락 방지

### 관련성 검증 시스템 추가
1. **validate_paper.py 신규 생성**: Gemini API를 사용한 자동 관련성 검증
2. **핵심 방법론 연구 선별**: 단순 도구 활용 사례 자동 필터링
3. **신뢰도 기반 필터링**: confidence >= 0.7인 논문만 선별

### 코드 안정성 향상
1. **에러 처리 강화**: 날짜 파싱, API 오류 등에 대한 예외 처리 추가
2. **PDF URL 생성 개선**: 버전 번호 처리 로직 강화
3. **로깅 개선**: stderr를 통한 진행 상황 추적
