"""
Automatic Paper Sync Script
Runs daily to fetch new papers, validate them, and upload to Notion.
Shows Windows notification when new papers are added.
"""
import os
import sys
import io
import json
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows encoding issue - force UTF-8 for stdout/stderr
# Needed when run via VBScript/Task Scheduler where stdout may be a pipe or NUL device
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # stdout may not have .buffer in some environments

# Load environment variables
load_dotenv()

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TMP_DIR = os.path.join(PROJECT_ROOT, ".tmp")
LOG_FILE = os.path.join(TMP_DIR, f"sync_log_{datetime.now().strftime('%Y%m%d')}.txt")

# Ensure .tmp directory exists
os.makedirs(TMP_DIR, exist_ok=True)

def log(message):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"

    # Print to console - suppress all errors (VBScript/Task Scheduler may have no stdout)
    try:
        print(log_message)
    except (UnicodeEncodeError, OSError):
        pass

    # Always write to file with UTF-8
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')

def show_notification(title, message):
    """Show Windows notification using PowerShell"""
    try:
        # Escape special characters for PowerShell
        title_escaped = title.replace('"', '`"')
        message_escaped = message.replace('"', '`"')

        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title_escaped}</text>
                    <text id="2">{message_escaped}</text>
                </binding>
            </visual>
        </toast>
"@

        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ArxivPaperSync").Show($toast)
        '''

        subprocess.run(['powershell', '-Command', ps_script],
                      capture_output=True, timeout=10)
        log("Windows notification sent")
    except Exception as e:
        log(f"Failed to show notification: {e}")

def run_script(script_name, *args):
    """Run a Python script and return output"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + list(args)

    log(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=300)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        log(f"ERROR: {script_name} timed out after 5 minutes")
        return None, "Timeout", 1
    except Exception as e:
        log(f"ERROR running {script_name}: {e}")
        return None, str(e), 1

def main():
    log("="*60)
    log("Starting Automatic Paper Sync")
    log("="*60)

    # Step 1: Fetch papers from Arxiv
    log("Step 1: Fetching papers from Arxiv (last 30 days)")
    stdout, stderr, code = run_script("fetch_papers.py", "--days", "30")

    if code != 0 or not stdout:
        log(f"ERROR: Failed to fetch papers")
        log(f"Error: {stderr}")
        show_notification("Paper Sync Failed", "Failed to fetch papers from Arxiv")
        return

    # Parse fetched papers
    papers = []
    for line in stdout.split('\n'):
        if line.startswith('{') and line.endswith('}'):
            try:
                paper = json.loads(line)
                papers.append(paper)
            except json.JSONDecodeError:
                continue

    log(f"Found {len(papers)} papers from Arxiv")

    if len(papers) == 0:
        log("No papers found. Exiting.")
        return

    # Step 2: Query Notion for existing papers
    log("Step 2: Querying Notion DB for existing papers")
    stdout, stderr, code = run_script("notion_api_tool.py", "query")

    if code != 0:
        log(f"ERROR: Failed to query Notion DB")
        log(f"Error: {stderr}")
        show_notification("Paper Sync Failed", "Failed to query Notion database")
        return

    # Parse existing IDs from stderr (progress messages) and stdout (JSON result)
    existing_ids = []
    try:
        # Find the JSON array in output
        for line in stdout.split('\n'):
            if line.strip().startswith('['):
                existing_ids = json.loads(line.strip())
                break
    except json.JSONDecodeError:
        log("Warning: Could not parse existing IDs, assuming empty")

    log(f"Found {len(existing_ids)} existing papers in Notion")

    # Step 3: Filter out duplicates
    new_papers = [p for p in papers if p['id'] not in existing_ids]
    log(f"Found {len(new_papers)} new papers (after duplicate filtering)")

    if len(new_papers) == 0:
        log("No new papers to add. Exiting.")
        show_notification(
            "Paper Sync - 중복 없음",
            f"Arxiv에서 {len(papers)}개 논문을 확인했지만 Notion에 이미 모두 저장되어 있습니다."
        )
        return

    # Step 4: Smart filtering - keyword scoring first
    log("Step 3: Smart filtering papers")

    # Phase 1: Quick keyword scoring (free, instant)
    def score_paper(paper):
        """Score paper based on title/abstract keywords"""
        title = paper['title'].lower()
        abstract = paper['summary'].lower()

        # High-value keywords
        high_value = ['retrieval', 'rag', 'prompt', 'context', 'hallucination',
                      'fine-tuning', 'lora', 'peft', 'in-context', 'few-shot',
                      'chain-of-thought', 'reasoning', 'grounding', 'attribution']

        # Medium-value keywords
        medium_value = ['llm', 'language model', 'transformer', 'attention',
                       'generation', 'inference', 'alignment']

        # Low-value signals (subtract points)
        low_value = ['vision', 'image', 'video', 'robot', 'survey', 'benchmark only']

        score = 0
        for kw in high_value:
            if kw in title:
                score += 3
            if kw in abstract:
                score += 1

        for kw in medium_value:
            if kw in title:
                score += 1
            if kw in abstract:
                score += 0.5

        for kw in low_value:
            if kw in title or kw in abstract:
                score -= 2

        return max(0, score)

    # Score all papers
    scored_papers = [(paper, score_paper(paper)) for paper in new_papers]
    scored_papers.sort(key=lambda x: x[1], reverse=True)

    log(f"Scored {len(scored_papers)} papers")
    log(f"Top score: {scored_papers[0][1]:.1f}, Bottom score: {scored_papers[-1][1]:.1f}")

    # Phase 2: Validate top 30 with Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    validated_papers = []

    if gemini_key:
        import time
        # RPD=20 한도: validation 최대 15회 + 분석 1회 = 16회 (여유 4회)
        # RPM=5 한도: 요청 간 13초 간격 유지
        VALIDATE_LIMIT = 15
        top_papers = [p for p, s in scored_papers[:VALIDATE_LIMIT]]
        log(f"Step 4: Validating top {VALIDATE_LIMIT} papers with Gemini API (RPD limit)")

        for i, paper in enumerate(top_papers, 1):
            if i > 1:
                time.sleep(13)  # RPM 5 = 분당 5회 = 12초 간격, 여유 1초 추가
            log(f"Validating {i}/{VALIDATE_LIMIT}: {paper['title'][:50]}...")
            stdout, stderr, code = run_script(
                "validate_paper.py",
                "--title", paper['title'],
                "--abstract", paper['summary']
            )

            if code == 0 and stdout:
                try:
                    validation = json.loads(stdout.strip())
                    paper['validation'] = validation

                    if validation.get('is_relevant') and validation.get('confidence', 0) >= 0.7:
                        validated_papers.append(paper)
                        log(f"  ✓ Relevant (confidence: {validation['confidence']:.2f})")
                    else:
                        log(f"  ✗ Not relevant (confidence: {validation.get('confidence', 0):.2f})")
                except Exception as e:
                    log(f"  ! Validation parsing failed: {e}")
            else:
                log(f"  ! Validation error: {stderr[:100] if stderr else 'Unknown error'}")

        log(f"After validation: {len(validated_papers)} relevant papers (from {VALIDATE_LIMIT} checked)")

        # Select only the top 1 paper per day
        if len(validated_papers) > 1:
            validated_papers = validated_papers[:1]
            log(f"Selected top 1 paper for daily upload")
    else:
        log("Step 3: Skipping validation (GEMINI_API_KEY not set)")
        log("Using top 1 paper by keyword score instead")
        validated_papers = [p for p, s in scored_papers[:1]]

    if len(validated_papers) == 0:
        log("No relevant papers after validation. Exiting.")
        show_notification(
            "Paper Sync - 관련 논문 없음",
            f"새 논문 {len(new_papers)}개를 검토했지만 RAG/NLP/프롬프트 엔지니어링 관련 논문이 없습니다."
        )
        return

    # Step 5: Upload to Notion
    log(f"\nStep 5: Uploading {len(validated_papers)} papers to Notion")

    uploaded_count = 0
    failed_count = 0

    for i, paper in enumerate(validated_papers, 1):
        log(f"\nProcessing {i}/{len(validated_papers)}: {paper['title'][:60]}...")

        try:
            # Extract date from published field (format: 2024-01-30T12:00:00Z)
            published_date = paper.get('published', '').split('T')[0] if paper.get('published') else ''

            # Step 5.1: Analyze paper with Gemini
            log(f"  Analyzing paper with Gemini...")
            stdout, stderr, code = run_script(
                "paper_analyzer.py",
                "--title", paper['title'],
                "--abstract", paper['summary'],
                "--pdf-url", paper['pdf_url']
            )

            if stderr:
                log(f"  [analyzer stderr]: {stderr[:500]}")

            if code == 0 and stdout:
                try:
                    # Extract JSON from output (skip any stderr messages mixed in)
                    # Find the first '{' and last '}' to extract the JSON object
                    json_start = stdout.find('{')
                    json_end = stdout.rfind('}')

                    if json_start != -1 and json_end != -1:
                        json_str = stdout[json_start:json_end+1]
                        analysis = json.loads(json_str)
                        # Check if analysis actually succeeded (not the fallback "분석 실패")
                        if analysis.get('tldr') == '분석 실패':
                            raise ValueError("Analyzer returned fallback failure JSON")
                        # Pack full analysis data for Notion
                        notion_data = {
                            "title": paper['title'],
                            "id": paper['id'],
                            "url": paper['pdf_url'],
                            "date": published_date,
                            "analysis": analysis  # Pass entire analysis object
                        }
                        log(f"  ✓ Analysis complete")
                    else:
                        raise ValueError("No JSON found in output")
                except Exception as e:
                    log(f"  ! Analysis parsing failed: {e}")
                    log(f"  ! Output preview: {stdout[:200] if stdout else 'empty'}")
                    # Fallback to basic data
                    notion_data = {
                        "title": paper['title'],
                        "id": paper['id'],
                        "url": paper['pdf_url'],
                        "date": published_date,
                        "analysis": {
                            "tldr": paper['summary'][:200],
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
                        }
                    }
            else:
                log(f"  ! Analysis failed with code {code}")
                if stderr:
                    log(f"  ! Error: {stderr[:200]}")
                if stdout:
                    log(f"  ! Output preview: {stdout[:200]}")
                # Fallback to basic data
                notion_data = {
                    "title": paper['title'],
                    "id": paper['id'],
                    "url": paper['pdf_url'],
                    "date": published_date,
                    "analysis": {
                        "tldr": paper['summary'][:200],
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
                    }
                }

            # Call notion_api_tool.py to create the page
            stdout, stderr, code = run_script(
                "notion_api_tool.py",
                "create",
                "--data",
                json.dumps(notion_data)
            )

            if code == 0:
                uploaded_count += 1
                log(f"  ✓ Successfully uploaded")
            else:
                failed_count += 1
                log(f"  ✗ Upload failed: {stderr[:100] if stderr else 'Unknown error'}")

        except Exception as e:
            failed_count += 1
            log(f"  ✗ Upload error: {str(e)[:100]}")

    # Show summary
    log("\n" + "="*60)
    log(f"UPLOAD COMPLETE")
    log(f"  Successfully uploaded: {uploaded_count}")
    log(f"  Failed: {failed_count}")
    log("="*60)

    # Show papers that were uploaded
    if uploaded_count > 0:
        log("\nUploaded papers:")
        for i, paper in enumerate(validated_papers[:min(5, uploaded_count)], 1):
            log(f"  {i}. {paper['title'][:70]}")
            log(f"     ID: {paper['id']}")

        if uploaded_count > 5:
            log(f"  ... and {uploaded_count - 5} more")

    # Show success notification
    notification_msg = f"Uploaded {uploaded_count} new papers to Notion"
    if failed_count > 0:
        notification_msg += f" ({failed_count} failed)"
    show_notification("Paper Sync Complete!", notification_msg)

    log(f"Log saved to: {LOG_FILE}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        show_notification("Paper Sync Error", f"Script failed: {str(e)[:100]}")
        sys.exit(1)
