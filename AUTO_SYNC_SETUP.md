# 자동 논문 동기화 설정 가이드

컴퓨터를 켤 때 자동으로 Arxiv 논문을 검색하고 Notion에 저장하는 시스템입니다.

## 기능

- 매일 자동으로 Arxiv에서 최신 논문 검색 (30일 이내)
- RAG, Fine-tuning, Hallucination, Prompt Engineering, Context Engineering 관련 논문 수집
- Arxiv ID 기반 중복 제거
- Gemini API를 통한 관련성 검증
- 새로운 논문 발견 시 윈도우 알림 표시
- 모든 작업 로그 자동 저장

## 설정 방법

### 1단계: 환경 변수 설정

`.env` 파일에 다음 내용을 추가하세요:

```env
# Notion API 설정
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_database_id_here

# Gemini API 설정 (선택사항 - 논문 관련성 검증용)
GEMINI_API_KEY=your_gemini_api_key_here
```

**Notion Token 발급 방법:**
1. https://www.notion.so/my-integrations 접속
2. "New integration" 클릭
3. 이름 입력 후 "Submit" 클릭
4. "Internal Integration Token" 복사

**Notion Database ID 확인 방법:**
1. Notion에서 데이터베이스 페이지 열기
2. URL에서 `/` 다음의 32자리 코드가 Database ID
   - 예: `https://notion.so/myworkspace/a8aec43384f447ed84390e8e42c2e089?v=...`
   - Database ID: `a8aec43384f447ed84390e8e42c2e089`

**Gemini API Key 발급 방법:**
1. https://aistudio.google.com/app/apikey 접속
2. "Create API Key" 클릭

### 2단계: 자동 실행 설정 (2가지 방법 중 선택)

#### 방법 1: 로그인 시 자동 실행 (권장)

컴퓨터를 켤 때마다 자동으로 실행됩니다.

```bash
# 관리자 권한으로 실행
setup_autostart.bat
```

**설정 내용:**
- 윈도우 시작 프로그램에 등록
- 백그라운드에서 조용히 실행 (콘솔 창 없음)
- 새 논문 발견 시 알림 표시

**제거 방법:**
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```
위 폴더에서 "ArxivPaperSync" 바로가기 삭제

#### 방법 2: 매일 정해진 시간에 실행

매일 오전 9시에 자동으로 실행됩니다.

```bash
# 관리자 권한으로 실행
setup_task_scheduler.bat
```

**설정 내용:**
- 작업 스케줄러에 등록
- 매일 오전 9:00에 자동 실행
- 컴퓨터가 꺼져 있어도 다음 부팅 시 실행

**수동 실행:**
```bash
schtasks /Run /TN "ArxivPaperSync"
```

**제거 방법:**
```bash
schtasks /Delete /TN "ArxivPaperSync" /F
```

### 3단계: 수동 테스트

자동 설정 전에 먼저 테스트해보세요:

```bash
python execution/auto_sync_papers.py
```

**로그 확인:**
```
.tmp/sync_log_YYYYMMDD.txt
```

## 작동 흐름

1. **논문 검색** (`fetch_papers.py`)
   - Arxiv API에서 최근 30일 이내 논문 검색
   - 5가지 주제 키워드로 검색 (최대 100개)
   - 날짜 필터링 적용

2. **중복 확인** (`notion_api_tool.py query`)
   - Notion DB에서 기존 Arxiv ID 조회
   - Pagination 처리로 모든 페이지 확인

3. **관련성 검증** (`validate_paper.py`) - 선택사항
   - Gemini API로 논문 관련성 자동 판단
   - 신뢰도 70% 이상만 선별
   - GEMINI_API_KEY가 없으면 이 단계 건너뜀

4. **결과 알림**
   - 새 논문 발견 시 윈도우 알림 표시
   - 로그 파일에 상세 기록

## 알림 예시

새 논문이 발견되면 다음과 같은 윈도우 알림이 표시됩니다:

```
제목: New Papers Found!
내용: Found 5 new papers ready for review
```

알림이 뜨지 않으면 다음을 확인하세요:
- 윈도우 알림 설정이 켜져 있는지 확인
- 방해 금지 모드가 꺼져 있는지 확인

## 트러블슈팅

### Python 경로 문제
```
ERROR: Python not found in PATH
```

**해결 방법:**
1. Python 설치 확인: `python --version`
2. PATH에 Python 추가
3. 또는 setup 스크립트에서 Python 경로 직접 지정

### Notion API 오류
```
ERROR: Failed to query Notion DB
```

**해결 방법:**
1. `.env`의 NOTION_TOKEN, NOTION_DATABASE_ID 확인
2. Integration이 데이터베이스에 연결되어 있는지 확인
   - Notion 데이터베이스 열기 → 우측 상단 "..." → "Connections" → Integration 추가

### Gemini API 오류
```
ERROR: Failed to validate paper
```

**해결 방법:**
1. GEMINI_API_KEY가 .env에 올바르게 설정되었는지 확인
2. API 할당량 확인
3. 또는 GEMINI_API_KEY를 제거하여 검증 단계 건너뛰기

## 로그 분석

로그 파일 위치: `.tmp/sync_log_YYYYMMDD.txt`

**정상 실행 예시:**
```
[2026-01-30 09:00:00] Starting Automatic Paper Sync
[2026-01-30 09:00:05] Found 100 papers from Arxiv
[2026-01-30 09:00:10] Found 2 existing papers in Notion
[2026-01-30 09:00:10] Found 98 new papers (after duplicate filtering)
[2026-01-30 09:00:15] After validation: 5 relevant papers
[2026-01-30 09:00:15] SUCCESS: Found 5 new papers
```

## 개선 내역 (2026-01-30)

### 검색 정확도 향상
- ✅ 날짜 필터링 구현 (30일 이내)
- ✅ 검색 주제 확장 (Prompt/Context Engineering 추가)
- ✅ 키워드 정교화 (주제당 5-8개)
- ✅ 검색 결과 증가 (20개 → 100개)

### 중복 검사 개선
- ✅ Arxiv ID 기반 중복 검사 (제목 → ID)
- ✅ Pagination 처리 (100개 이상 페이지 지원)

### 새 기능
- ✅ Gemini API 관련성 검증
- ✅ 윈도우 알림 시스템
- ✅ 자동 실행 설정 스크립트
- ✅ 상세 로깅 시스템

## 추가 개선 예정 사항

현재 `auto_sync_papers.py`는 논문을 찾고 검증까지만 수행합니다.
Notion 업로드 및 PDF 분석 기능은 추후 추가 예정입니다.

전체 워크플로우 완성을 위해서는 다음이 필요합니다:
1. PDF 다운로드 및 파싱
2. Gemini API를 통한 상세 분석
3. Notion 페이지 생성 및 업로드

## 문의

문제가 발생하면 로그 파일을 확인하고, 필요시 수동으로 각 단계를 실행하여 어디서 문제가 발생하는지 확인하세요:

```bash
# 1. 논문 검색 테스트
python execution/fetch_papers.py --days 30

# 2. Notion 중복 확인 테스트
python execution/notion_api_tool.py query

# 3. 관련성 검증 테스트
python execution/validate_paper.py --title "Test" --abstract "Test abstract"
```
