# LLM Router System - Technical Pipeline & Feature Documentation

## Overview

LLM Router System은 사용자 요청을 리스크 스코어링과 LURE 방법론을 기반으로 적절한 LLM 프로바이더에 지능적으로 라우팅하는 태스크 라우팅 및 프롬프트 엔지니어링 프레임워크입니다. CLI, Desktop GUI, Web UI 세 가지 인터페이스를 제공하며, 한국어-영어 자동 번역, 멀티 티켓 격리, 펜스 세이프 파싱 등의 핵심 기능을 포함합니다.

---

## 1. System Architecture

### 1.1 Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Router Engine | `llm_router_lure_v3.6.py` (701 lines) | 핵심 라우팅 로직, 태스크 분리, LURE 방법론 |
| Desktop GUI | `router_gui.py` (1268 lines) | Tkinter 기반 데스크톱 애플리케이션 |
| Web Server | `web_server.py` (367 lines) | HTTP API 서버 (stdlib only) |
| Web UI | `website/router.html` + `router.js` + `router.css` | 브라우저 기반 인터페이스 |

### 1.2 Technical Stack

| Layer | Technology |
|-------|------------|
| Core Routing | Python stdlib (regex, dataclasses) |
| Desktop GUI | Tkinter |
| Web Server | http.server (stdlib, no Flask/FastAPI) |
| Web UI | Vanilla JS + CSS (no frameworks) |
| LLM Integration | Groq API (llama-3.1-8b-instant) |
| Translation | Groq API + Dictionary Replacement |
| Styling | Apple-style Design System |

---

## 2. Technical Pipeline

### 2.1 End-to-End Data Flow

```
User Request (Korean/English)
         |
         v
+----------------------------------+
|     Interface Layer              |
|  CLI / Desktop GUI / Web UI     |
+----------------------------------+
         |
         v
+----------------------------------+
|     Text Processing Layer        |
|  1. Normalize input              |
|  2. Strip boilerplate            |
|  3. Split into tasks (Groq API)  |
|  4. Translate (optional)         |
+----------------------------------+
         |
         v
+----------------------------------+
|     LURE Routing Engine          |
|  1. Risk scoring (regex)         |
|  2. Priority assignment          |
|  3. Route decision               |
|     (claude / cheap_llm / split) |
|  4. Ticket generation            |
+----------------------------------+
         |
         v
+----------------------------------+
|     Output Generation            |
|  1. Prompt engineering           |
|  2. Fence-safe block extraction  |
|  3. Translation (Groq API)       |
|  4. Clipboard / File output      |
+----------------------------------+
         |
         v
    Clipboard / File Output
```

### 2.2 Pipeline Phase Details

**Phase 1 - Input Processing**
- 사용자 입력을 정규화하고 불필요한 보일러플레이트를 제거
- 번호 매긴 리스트 감지 (regex) 또는 Groq API를 통한 태스크 분리
- `--force-split` 옵션으로 복합 문장 강제 분리 가능

**Phase 2 - Risk Scoring**
- 고위험/저위험 regex 패턴 매칭으로 각 태스크의 리스크 점수 산출
- 점수 차이에 따라 라우팅 경로와 신뢰도 결정
- 우선순위 기반 정렬 (DB wiring > Auth > Image Gen > UI)

**Phase 3 - Ticket Generation**
- 각 태스크에 대해 `TaskDecision` 데이터 모델 생성
- Claude-ready 프롬프트, 다음 세션 시작 문구, 변경 로그 스텁 포함
- 멀티 티켓 세션 가드 경고 생성

**Phase 4 - Output Delivery**
- 선택된 인터페이스(CLI/GUI/Web)를 통해 결과 출력
- 펜스 세이프 파싱으로 코드 블록 무결성 보장
- 선택적 한-영 번역 적용

---

## 3. LURE Routing Engine

### 3.1 LURE Methodology

**LURE** = **L**ow-risk **U**ser **R**equest **E**ngine

태스크의 리스크 수준을 분류하여 적절한 LLM 티어로 라우팅합니다.

| Route | Model Tier | Use Case | Confidence |
|-------|------------|----------|------------|
| `claude` | High-tier (Opus/Sonnet) | 고위험, 추론 집중 작업 | 62-95% |
| `cheap_llm` | Low-tier (Groq/Llama) | 기계적, 저위험 작업 | 62-95% |
| `split` | Mixed | 양쪽 모두 필요한 작업 | 64-78% |

### 3.2 Risk Scoring System

**High-Risk Patterns** (6 points each):

| Pattern | Description |
|---------|-------------|
| `rls`, `row level security`, `policy` | Supabase RLS / Policies |
| `revenuecat`, `subscription`, `iap` | Subscriptions / IAP |
| `comfyui`, `runpod`, `image generation`, `lora` | Image Generation |
| `groq`, `llama`, `rate limit`, `429` | Chat LLM Reliability |
| `codesign`, `xattr`, `entitlements` | iOS Build / Signing |
| `daily_usage`, `quota`, `limit`, `tier`, `vip` | Usage Limits |
| `gate`, `onboarding`, `login flow` | Gate / Onboarding |
| `delete`, `block`, `remove` + `character` | Deletion Semantics |
| `custom character` + `limit` | Per-Account Limit |
| `image` + `db`, `database`, `metadata` | Image DB Wiring |

**Low-Risk Patterns** (4 points each):

| Pattern | Description |
|---------|-------------|
| `scroll`, `overflow`, `clip`, `layout` | UI Layout/Scroll |
| `theme`, `color scheme`, `dark`, `light` | Theme/Prefs |
| `i18n`, `translation`, `strings`, `text` | Copy/i18n |

**Decision Logic**:
```
if should_split:
    return "split", 0.78

if claude_score >= cheap_score + 5:
    return "claude", min(0.95, 0.62 + diff * 0.05)

if cheap_score >= claude_score + 6:
    return "cheap_llm", min(0.95, 0.62 + diff * 0.05)

return "split", 0.64
```

### 3.3 Priority System

| Priority | Value | Use Case |
|----------|-------|----------|
| `PRIORITY_DB_WIRING` | 10 | Database connections (HIGHEST) |
| `PRIORITY_AUTH_GATE` | 20 | Login/Onboarding flows |
| `PRIORITY_IMAGE_GEN` | 30 | Image generation pipelines |
| `PRIORITY_CREATE_CHARACTER` | 35 | Character creation |
| `PRIORITY_UI` | 50 | UI/UX tweaks |
| `PRIORITY_OTHER` | 60 | Everything else (LOWEST) |

DB wiring이 image generation이나 character creation보다 먼저 완료되어야 하므로 가장 높은 우선순위를 가집니다.

---

## 4. Task Splitting

### 4.1 Numbered List Detection (Regex)

```
(^|\n)\s*(\d+[\.\)]|[①-⑳])\s+
```

번호가 매겨진 리스트가 감지되면 각 항목을 개별 태스크로 분리합니다.

### 4.2 Groq API Splitting (LLM-powered)

Groq의 `llama-3.1-8b-instant` 모델을 사용하여 한국어/영어 복합 요청을 독립적 태스크로 분리합니다.

**Control Flags**:

| Flag | Description |
|------|-------------|
| `--force-split` | 복합 문장 강제 분리 |
| `--min-tickets N` | 최소 N개 태스크 보장 (가장 긴 태스크 재분리) |
| `--max-tickets N` | 최대 N개 태스크 제한 (나머지 병합) |
| `--merge "A+B"` | 수동으로 두 티켓 병합 |

---

## 5. Data Models

### 5.1 TaskDecision

```python
@dataclass
class TaskDecision:
    id: str                    # "A", "B", ..., "Z", "T27", etc.
    summary: str               # First 80 chars
    route: str                 # "claude", "cheap_llm", or "split"
    confidence: float          # 0.0 - 1.0
    priority: int              # 10-60 (lower = higher priority)
    reasons: List[str]         # Why this route was chosen
    claude_prompt: str         # Ready-to-paste block
    next_session_starter: str  # "A: Fix login screen"
    change_log_stub: str       # Template for logging
```

### 5.2 RouterOutput

```python
@dataclass
class RouterOutput:
    route: str                 # Overall recommendation
    confidence: float
    reasons: List[str]
    global_notes: List[str]    # Cross-task warnings
    session_guard: List[str]   # Multi-ticket safety warnings
    tasks: List[TaskDecision]
```

---

## 6. Interfaces

### 6.1 CLI (Command Line Interface)

```bash
# Basic usage
python llm_router_lure_v3.6.py --desktop-edit "Fix login bug and update theme"

# Beginner mode (copy/paste blocks)
python llm_router_lure_v3.6.py --friendly "이미지 생성 기능 추가"

# Economy modes
python llm_router_lure_v3.6.py --economy strict --phase implement "Task"

# Ticket control
python llm_router_lure_v3.6.py --one-task B --desktop-edit "Multi-task request"
python llm_router_lure_v3.6.py --max-tickets 3 --merge "A+B" "5 tasks"

# Output formats
python llm_router_lure_v3.6.py --json "Task"
python llm_router_lure_v3.6.py --tickets-md --save-tickets TICKETS.md "Task"
```

**Key Flags**:

| Flag | Description |
|------|-------------|
| `--desktop-edit` | 파일 접근 모드 (Claude Desktop용) |
| `--opus-only` | 모든 태스크를 Claude Opus로 강제 (diff review 모드) |
| `--friendly` | 초보자 친화적 출력 (copy/paste 블록만 표시) |
| `--force-split` | 강제 태스크 분리 |
| `--economy strict\|balanced` | 비용 제어 |
| `--phase analyze\|implement` | 2단계 워크플로우 |
| `--json` | JSON 출력 |

### 6.2 Desktop GUI

**Framework**: Tkinter (1040x820px)

**Key Features**:
- Multi-router auto-discovery (같은 폴더, `routers/`, `tools/` 하위 폴더)
- Git preflight 상태 표시
- Fence-safe Claude 블록 추출
- Multi-ticket 격리 (A/B/C 셀렉터)
- Groq 기반 한-영 번역
- 클립보드 복사 최적화

**Router Discovery Paths**:
```
tools/
├── llm_router_lure_v3*.py      <- Auto-discovered
├── router_gui.py
├── routers/
│   ├── project_a_router.py     <- Auto-discovered
│   └── project_b_router.py     <- Auto-discovered
└── tools/
    └── llm_router_*.py         <- Auto-discovered
```

### 6.3 Web Server & Web UI

**Server**: `http.server` (stdlib, port 8080)

**API Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/routers` | 사용 가능한 라우터 스크립트 목록 |
| GET | `/api/preflight` | Git 상태 + GROQ_API_KEY 체크 |
| POST | `/api/route` | 파라미터로 라우터 실행 |
| POST | `/api/extract-block` | Claude 블록 추출 및 번역 |
| GET | `/` | `router.html` 서빙 |

**Web UI Features**:
- Configuration panel (collapsible): 라우터 선택, 체크박스 7개, Economy/Phase 드롭다운
- Request input: 텍스트 입력 + Cmd/Ctrl+Enter 실행
- Output display: 터미널 스타일 (`#1a1a1a` background)
- Ticket selector: A/B/C 드롭다운
- Toast notifications: 2초 auto-dismiss

---

## 7. Translation System

### 7.1 Three-Layer Architecture

**Layer 1 - Dictionary Replacement** (Zero-cost):
- 84개 하드코딩된 한-영 매핑
- 즉시 치환, API 호출 불필요
- 일반적 UI 문자열에 사용

**Layer 2 - Groq Output Translation** (Low-cost):
- Fence-aware 세그멘테이션
- 코드 블록이 아닌 한국어 세그먼트만 번역
- `llama-3.1-8b-instant` 모델 사용

**Layer 3 - Groq Ticket Translation** (Most accurate):
- 티켓 본문을 구조화된 JSON으로 추출
- 간결한 영어로 정규화
- 원본 한국어를 참조로 보존

### 7.2 Fence-Aware Translation

코드 블록 내부의 내용은 절대 번역하지 않습니다.

```
1. 출력을 fenced(code)와 non-fenced(prose) 세그먼트로 분리
2. 한국어가 포함된 non-fenced 세그먼트만 Groq API로 전송
3. 번역 결과를 원래 위치에 재조합
```

**Guarantees**:
- Code syntax 보존
- File path 미변경
- Technical term 유지

---

## 8. Key Design Patterns

### 8.1 Fence-Safe Parsing

줄의 **시작**이 ` ``` `인 경우만 펜스 경계로 인식합니다. 이는 산문 내의 인라인 백틱(예: "use ` ```python ` to run")으로 인한 잘못된 파싱을 방지합니다.

```python
for line in lines:
    if line.strip().startswith("```"):  # Line-based detection only
        in_fence = not in_fence
```

### 8.2 Multi-Ticket Isolation

한 번의 클립보드 복사에 여러 티켓을 포함하지 않습니다.

**Rationale**:
- 비용 급증 방지 (전체 세션이 최고 모델 비용으로 청구)
- 회귀 방지 (티켓 A의 변경이 티켓 B를 깨뜨림)
- 컨텍스트 손실 방지 (Claude가 이전 티켓을 잊음)

**Enforcement**:
- GUI에서 하나의 티켓 선택 프롬프트
- `--one-task` CLI 플래그로 출력 필터링
- `slice_single_ticket_from_block()` 함수로 다른 티켓 제거

### 8.3 Priority-First Ordering

태스크는 항상 우선순위 기준으로 정렬된 후 라우팅됩니다.

```
Input:  ["Fix theme", "Add DB connection", "Update login flow"]
Sorted: ["Add DB connection"(p10), "Update login flow"(p20), "Fix theme"(p50)]
Output: Ticket A, B, C
```

### 8.4 Session Guard

멀티 티켓 감지 시 경고를 생성합니다:
- "N개 티켓 감지 -> 하나의 세션에서 모두 구현하지 마세요"
- "권장: 세션당 하나의 티켓만 실행"
- "Economy strict: 멀티 티켓 세션은 비용 급증 + 회귀 유발"

---

## 9. Integration Points

### 9.1 Supported LLM Providers

| Provider | Model | Usage |
|----------|-------|-------|
| Anthropic | Claude Opus 4.6 | 고위험 태스크 (`route: "claude"`) |
| Anthropic | Claude Sonnet 4.5 | 혼합/균형 태스크 |
| Groq | llama-3.1-8b-instant | 태스크 분리, 번역 |
| Cheap LLM | (Generic) | 저위험 UI/copy 태스크 (`route: "cheap_llm"`) |

### 9.2 Groq API Integration

**Endpoint**: `https://api.groq.com/openai/v1/chat/completions`

**Functions**:
1. **Task Splitting**: 한국어/영어 산문을 번호 매긴 태스크로 변환
2. **Translation**: 한국어 -> 영어 (UI 출력, 티켓 본문)
3. **Ticket Normalization**: 티켓을 간결한 영어로 재작성

### 9.3 Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional | 태스크 분리 + 번역 |

**Fallback** (GROQ_API_KEY 미설정 시):
- Task splitting: 입력을 단일 태스크로 반환
- Translation: 건너뜀 (한국어 출력 유지)

---

## 10. Logging & Audit

### 10.1 Task History

모든 라우팅 실행은 `task_history.json`에 기록됩니다:

```json
{
  "timestamp": "2026-02-13T10:07:32.123456",
  "id": "A",
  "summary": "Fix image DB wiring for custom character uploads",
  "priority": 10,
  "route": "claude",
  "confidence": 0.92,
  "reasons": ["Image DB wiring", "High-risk impl"]
}
```

### 10.2 Change Log

`agent_docs/change_log.md`에 수동 기록:

```
[YYYYMMDD] [type] [scope]
> Changes
- Impact
- Issues
```

---

## 11. Deployment

### 11.1 Web Server

```bash
# Default port (8080)
python3 web_server.py

# Custom port
python3 web_server.py --port 3000
```

Access:
- Router UI: `http://localhost:8080/router.html`
- Portfolio: `http://localhost:8080/index.html`

### 11.2 Desktop GUI

```bash
python3 router_gui.py
```

### 11.3 Dependencies

- **Router Engine**: 외부 의존성 없음 (stdlib only), optional: `certifi`
- **Desktop GUI**: `tkinter` (stdlib), router script (auto-discovered)
- **Web Server**: `http.server` (stdlib), `router_gui.py` (helper imports), `website/` directory

---

## 12. Known Issues & Limitations

### Critical

| Issue | Description |
|-------|-------------|
| Fence detection fragility | `line.strip().startswith("```")`가 인라인 백틱과 매칭될 수 있음 |
| Bare except clauses | `KeyboardInterrupt`와 `SystemExit`를 catch함 |
| Subprocess CWD | GUI 실행 디렉토리를 프로젝트 디렉토리 대신 사용 |
| ARG_MAX overflow | 긴 요청이 macOS ARG_MAX (262KB) 초과 가능 |
| Groq API blocking | 번역 중 UI 프리징 (background threading 없음) |

### Translation

| Issue | Description |
|-------|-------------|
| 2000 token cap | 긴 출력이 번역 중 잘릴 수 있음 |
| Segment parsing | `---SEGMENT N---` 마커 누락 시 출력 깨짐 |
| Korean dialog messages | `messagebox` 다이얼로그 미번역 |
| Translation map gaps | 많은 한국어 문자열이 `TRANSLATE_MAP`에 없음 |

### Ticket

| Issue | Description |
|-------|-------------|
| Single-letter IDs only | GUI는 `[A-Za-z]` ID만 감지 |
| T27+ invisible | Z 이후 티켓(T27, T28...)이 GUI 셀렉터에 표시되지 않음 |
| Nested fences | 중첩 펜스 미지원 (flat 구조 가정) |

---

## 13. Future Enhancements

### High Priority
- Background threading: 비동기 Groq API 호출 (GUI 프리징 방지)
- Stdin for requests: CLI 인자 대신 `subprocess.run(input=)` 사용
- Stricter fence regex: 더 정확한 펜스 감지
- Fence utility module: 중복된 펜스 추적 로직을 공유 헬퍼로 추출

### Medium Priority
- Per-ticket copy buttons: 드롭다운 대신 `[Copy A] [Copy B] [Copy C]` 버튼
- Syntax highlighting: 티켓 헤더, 펜스, 한국어 텍스트 색상 코딩
- Read-only output: 실수로 인한 편집 방지

### Low Priority
- Project root selector: 서브프로세스 실행을 위한 CWD 오버라이드
- JSON output mode: 라우팅 결정을 구조화된 JSON으로 내보내기
- Task history UI: `task_history.json`을 GUI/Web에서 열람
