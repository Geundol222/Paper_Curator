# Arxiv Paper Auto-Sync

매일 Arxiv 최신 논문을 자동 수집하고, Gemini로 분석한 뒤 Notion 데이터베이스에 저장하는 자동화 파이프라인.

RAG / Fine-tuning / Hallucination / Prompt Engineering / Context Engineering 분야 논문을 추적하는 개인 연구 워크플로우로, 3개월 이상 매일 운영 중.

![Notion에 자동으로 쌓이는 논문 목록](assets/스크린샷%202026-05-04%20170648.png)

---

## 목적

논문을 Arxiv에서 직접 찾고 → 읽을 가치를 판단하고 → Notion에 정리하는 과정 전체를 자동화함. 단순 크롤링이 아니라, **읽을 가치가 있는 논문만 선별해 심층 분석**하는 것이 목표.

---

## 아키텍처

LLM은 확률적이고 비즈니스 로직은 결정론적이어야 함. 둘을 같은 레이어에 두면 오류가 복합적으로 누적됨 (90% 정확도 × 5단계 = 59% 성공률).

이를 분리하기 위해 역할을 **3개 레이어(3-Layer Architecture)**로 나눔.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Directive (무엇을 할지)                         │
│  directives/*.md — SOP 문서, 목표·입력·예외처리 정의        │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Orchestration (어떻게 판단할지)                  │
│  AI Agent — 디렉티브를 읽고, 스크립트를 순서대로 호출,       │
│  에러 처리, 디렉티브 개선                                   │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Execution (실제 수행)                           │
│  execution/*.py — 결정론적 Python 스크립트,                │
│  API 호출·데이터 처리·파일 조작                             │
└─────────────────────────────────────────────────────────┘
```

**핵심 원칙:** AI는 의사결정만 담당하고, 실제 작업은 테스트 가능한 코드가 처리함.

---

## 파이프라인

```
Arxiv API
    │
    ▼
[1] fetch_papers.py          ← 최근 30일 논문 최대 100개 수집
    │  cs.CL / cs.AI / cs.LG 카테고리
    │  5개 주제 × 다중 키워드 검색
    │
    ▼
[2] notion_api_tool.py query ← Notion DB의 기존 Arxiv ID 전체 조회
    │  Pagination 처리 (100개 이상도 누락 없이)
    │  제목 아닌 Arxiv ID 기준 → 정확한 중복 제거
    │
    ▼
[3] 키워드 스코어링           ← 무료, 즉시 실행
    │  고가치 키워드(+3), 중간(+1), 저가치(-2) 가중치
    │  상위 15개만 다음 단계로
    │
    ▼
[4] validate_paper.py        ← Gemini API로 관련성 검증
    │  "핵심 방법론 연구"인지 판단 (단순 응용 사례 제외)
    │  confidence >= 0.7인 논문만 통과
    │  RPM 한도 맞춰 13초 간격 요청
    │
    ▼
[5] paper_analyzer.py        ← Gemini로 논문 심층 분석
    │  PDF 전문 다운로드 → Gemini에 업로드 → 정독 분석
    │  PDF 실패 시 Abstract 기반 분석으로 자동 폴백
    │  한글 구조화 리포트 생성 (12개 섹션)
    │
    ▼
[6] notion_api_tool.py create ← Notion 페이지 생성
    │  구조화된 블록 레이아웃 (Callout, Toggle, Heading)
    │  TL;DR / 핵심 포인트 / 기술 세부사항 / 실험 결과 등
    │
    ▼
Windows 알림                 ← 업로드 완료 시 Toast 알림
```

---

## Notion 출력 구조

각 논문은 다음 섹션으로 구성된 Notion 페이지로 저장됨.

| 섹션 | 내용 |
|------|------|
| 💡 TL;DR | 핵심 기여 2-3문장 요약 |
| 🎯 핵심 포인트 | 불릿 리스트 |
| ❓ 해결하려는 문제 | 기존 방법의 한계 분석 |
| 🛠 제안 방법 | 아키텍처·알고리즘 상세 설명 |
| 🔧 기술적 세부사항 | 수식·하이퍼파라미터·데이터셋 (Toggle) |
| 🧪 실험 설정 | Baseline·평가 지표 |
| 📊 주요 결과 | 구체적인 수치와 성능 개선폭 |
| 🚀 실무 적용 | 실제 프로젝트 적용 시나리오 |
| ⚠️ 한계점 | 논문의 약점과 향후 연구 방향 |
| ❓ 학습 질문 | 깊이 공부하기 위한 질문 5개 |
| 🔗 관련 개념 | 연결된 기술·논문 |

---

## 파일 구조

```
.
├── Agent.md                    # AI 에이전트 운영 원칙 (3-Layer 아키텍처 정의)
├── directives/
│   └── notion_paper_sync.md   # 워크플로우 SOP (단계별 지침, 예외처리, 개선 이력)
├── execution/
│   ├── fetch_papers.py         # Arxiv API 논문 수집
│   ├── validate_paper.py       # Gemini API 관련성 검증
│   ├── paper_analyzer.py       # Gemini API PDF 심층 분석
│   ├── notion_api_tool.py      # Notion API CRUD (query / create)
│   └── auto_sync_papers.py     # 전체 파이프라인 오케스트레이터
├── setup_autostart.bat         # 윈도우 시작프로그램 등록
├── setup_task_scheduler.bat    # 작업 스케줄러 등록 (매일 09:00)
├── run_paper_sync_silent.vbs   # 백그라운드 실행용 VBScript
├── .env.example                # 환경변수 템플릿
└── .tmp/                       # 임시 파일 및 실행 로그 (gitignore)
```

---

## 설치

### 1. 의존성 설치

```bash
pip install requests python-dotenv google-generativeai google-genai
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 값 입력.

```env
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id
GEMINI_API_KEY=your_gemini_api_key
```

**Notion 설정**

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration 생성
2. 논문을 저장할 데이터베이스에 Integration 연결 (DB 우측 상단 `...` → Connections)
3. DB URL에서 32자리 ID 추출: `notion.so/workspace/[DATABASE_ID]?v=...`

**Notion 데이터베이스 필수 속성**

| 속성명 | 타입 |
|--------|------|
| 제목 | Title |
| Arxiv ID | Text |
| URL | URL |
| 날짜 | Date |

**Gemini API Key**

[aistudio.google.com](https://aistudio.google.com/app/apikey) → Create API Key

### 3. 수동 실행 테스트

```bash
python execution/auto_sync_papers.py
```

로그 확인: `.tmp/sync_log_YYYYMMDD.txt`

### 4. 자동 실행 설정

**방법 A — 로그인 시 자동 실행 (권장)**

```bash
# 관리자 권한으로 실행
setup_autostart.bat
```

**방법 B — 매일 09:00 실행**

```bash
# 관리자 권한으로 실행
setup_task_scheduler.bat
```

---

## 개별 스크립트 직접 실행

```bash
# 논문 수집만
python execution/fetch_papers.py --days 30

# Notion 중복 확인만
python execution/notion_api_tool.py query

# 관련성 검증만
python execution/validate_paper.py \
  --title "Your Paper Title" \
  --abstract "Your abstract text"

# 논문 분석만
python execution/paper_analyzer.py \
  --title "Your Paper Title" \
  --abstract "Your abstract text" \
  --pdf-url "https://arxiv.org/pdf/xxxx.xxxxx.pdf"
```

---

## Self-Annealing

시스템은 실패 시 단순 재시도가 아니라 **스스로 개선**함.

1. 에러 메시지와 스택 트레이스 분석
2. 스크립트 수정 및 재테스트
3. `directives/notion_paper_sync.md`에 학습 내용 기록
4. 다음 실행부터 개선된 로직 적용

예시: Gemini API rate limit(RPD 20) 발견 → 배치 검증 횟수를 15회로 제한, 요청 간 13초 간격 추가 → 디렉티브에 제약 조건 명시.

---

## 트러블슈팅

**Notion API 오류**
- `.env`의 토큰과 DB ID 확인
- Notion DB에 Integration이 연결되어 있는지 확인

**Gemini 할당량 초과**
- `GEMINI_API_KEY`를 제거하면 키워드 스코어링만으로 동작 (검증 단계 스킵)

**PDF 다운로드 실패**
- Abstract 기반 분석으로 자동 폴백, Notion에 "PDF 분석 실패" 표시

**로그 위치**
```
.tmp/sync_log_YYYYMMDD.txt
```
