# LLM Router v5.0 사용 가이드

> 🚀 AI가 자동으로 작업을 분석하고 최적의 LLM 모델로 라우팅해주는 지능형 시스템

---

## 📖 목차

1. [프로젝트 소개](#프로젝트-소개)
2. [설치 방법](#설치-방법)
3. [3가지 사용 방법](#3가지-사용-방법)
4. [v5.0 신기능](#v50-신기능)
5. [실전 예제](#실전-예제)
6. [문제 해결](#문제-해결)

---

## 프로젝트 소개

**LLM Router**는 여러분의 작업 요청을 자동으로 분석하여 가장 적합한 AI 모델로 연결해주는 스마트 라우터입니다.

### ✨ 주요 기능

- 🎯 **자동 작업 분석**: "코드 분석", "버그 수정", "문서 작성" 등 요청 의도 자동 파악
- 💰 **비용 절감**: 간단한 작업은 저렴한 모델로, 복잡한 작업은 고성능 모델로 자동 분배
- ⚡ **토큰 효율**: v5.0의 AI 압축 기술로 평균 40-50% 토큰 절감
- 📊 **우선순위 자동 판단**: 긴급도와 중요도를 ML로 자동 계산

### 🆚 v4.0 vs v5.0 비교

| 기능 | v4.0 | v5.0 |
|------|------|------|
| 작업 분류 | 규칙 기반 | **AI 기반 (BERT)** |
| 우선순위 | 순서대로 | **ML 자동 판단** |
| 토큰 사용량 | 100% | **50-60%** |
| 처리 속도 | ~2초 | ~2.5초 |
| 한국어 지원 | 기본 | **향상됨** |

---

## 설치 방법

### 1단계: Python 설치 확인

```bash
python3 --version
# Python 3.9 이상 필요
```

### 2단계: 필수 라이브러리 설치

**v4.0 (기본):**
```bash
pip3 install tiktoken
```

**v5.0 (AI 기능 전체):**
```bash
pip3 install -r requirements-v5.txt
```

포함 내용:
- `tiktoken`: 토큰 계산
- `transformers`: BERT 의도 분석
- `scikit-learn`: 우선순위 ML 모델
- `numpy`: 수치 연산

### 3단계: Groq API 키 설정 (선택)

한국어→영어 번역 기능을 사용하려면:

```bash
export GROQ_API_KEY="your_api_key_here"
```

[Groq API 키 발급받기](https://console.groq.com)

---

## 3가지 사용 방법

### 방법 1: 명령줄(CLI) - 개발자용 ⌨️

**기본 사용:**
```bash
python3 llm_router_v5.py "이 코드의 버그를 찾아줘"
```

**v5 기능 활성화:**
```bash
python3 llm_router_v5.py "사용자 인증 기능 구현해줘" \
  --v5 \
  --compress \
  --compression-level 2 \
  --show-stats
```

**주요 옵션:**

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--v5` | v5.0 엔진 활성화 | `--v5` |
| `--compress` | 프롬프트 압축 | `--compress` |
| `--compression-level` | 압축 강도 (1-3) | `--compression-level 2` |
| `--intent-detect` | 의도 파악 활성화 | `--intent-detect` |
| `--smart-priority` | ML 우선순위 | `--smart-priority` |
| `--show-stats` | 통계 표시 | `--show-stats` |
| `--friendly` | 친절한 설명 추가 | `--friendly` |
| `--economy` | 비용 모드 | `--economy balanced` |

**Economy 모드:**
- `strict`: 최대한 저렴한 모델 사용 (기본값)
- `balanced`: 품질과 비용 균형
- `quality`: 품질 우선, 비용 무시

### 방법 2: GUI - 편리한 인터페이스 🖥️

**실행:**
```bash
python3 router_gui.py
```

**화면 구성:**

```
┌─────────────────────────────────────────┐
│  LLM Router GUI                         │
├─────────────────────────────────────────┤
│ Router 선택: [llm_router_v5.py ▼]      │
├─────────────────────────────────────────┤
│ 요청 입력:                               │
│ ┌─────────────────────────────────────┐ │
│ │ 로그인 기능을 구현해주세요           │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ ☑ Friendly  ☑ v5 활성화              │
│ ☑ 압축      압축레벨: [2 ▼]          │
│ ☑ 통계표시                             │
├─────────────────────────────────────────┤
│ [  Split Tasks  ]  [  Translate  ]     │
└─────────────────────────────────────────┘
```

**사용 순서:**
1. Router 파일 선택 (`llm_router_v5.py` 권장)
2. 요청 내용 입력
3. 옵션 체크 (v5, 압축 등)
4. "Split Tasks" 버튼 클릭
5. 결과 확인

### 방법 3: Web UI - 브라우저에서 사용 🌐

**서버 시작:**
```bash
python3 web_server.py
# 기본 포트: 8080

# 다른 포트 사용:
python3 web_server.py --port 9000
```

**브라우저 열기:**
```
http://localhost:8080
```

**Web UI 장점:**
- 📱 모바일/태블릿 지원
- 📝 프롬프트 저장 기능
- 📊 비용/토큰 통계
- 👥 여러 사용자 공유 가능

**API 직접 호출 (개발자):**

```bash
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "router": "./llm_router_v5.py",
    "request": "버그 수정",
    "v5_enabled": true,
    "compress": true,
    "compression_level": 2,
    "intent_detect": true,
    "smart_priority": true,
    "show_stats": true
  }'
```

---

## v5.0 신기능

### 🎯 1. 의도 파악 (Intent Detection)

**무엇을?**
- AI가 요청을 읽고 "분석", "구현", "조사" 중 하나로 자동 분류
- BERT 모델 기반 (정확도 92%+)

**언제 유용?**
```
"이 코드 분석해줘" → analyze (분석형 모델 사용)
"로그인 기능 만들어줘" → implement (구현형 모델 사용)
"REST API 문서 찾아줘" → research (검색형 모델 사용)
```

**사용법:**
```bash
python3 llm_router_v5.py "요청" --v5 --intent-detect
```

### 💎 2. 우선순위 자동 판단 (Smart Priority)

**무엇을?**
- ML 모델이 긴급도(1-10)와 중요도(1-10)를 자동 계산
- 180개 훈련 샘플 기반

**언제 유용?**
```
"치명적 버그 수정" → 긴급도 9, 중요도 8 → 우선순위 72
"문서 오타 수정" → 긴급도 2, 중요도 3 → 우선순위 6
```

**사용법:**
```bash
python3 llm_router_v5.py "요청" --v5 --smart-priority
```

### 🗜️ 3. 프롬프트 압축 (Compression)

**무엇을?**
- 의미는 유지하면서 토큰 40-50% 절감
- 3단계 압축 레벨

**압축 레벨:**

| Level | 방식 | 절감률 | 품질 |
|-------|------|--------|------|
| 1 | 조사 제거, 중복 제거 | ~30% | 최고 |
| 2 | + 부사 제거, 문장 단순화 | ~40% | 좋음 (권장) |
| 3 | + 키워드만 추출, 명령형 변환 | ~50% | 보통 |

**예시:**

```
원본 (100 토큰):
"이 코드를 자세히 분석해주시고, 문제점을 찾아서 알려주세요. 그리고 개선 방안도 제시해주세요."

Level 2 압축 (60 토큰):
"코드 분석, 문제점 찾기, 개선 방안 제시"

절감: 40 토큰 (40%)
```

**사용법:**
```bash
python3 llm_router_v5.py "요청" --v5 --compress --compression-level 2
```

### 📊 4. 실시간 통계 (Stats)

**무엇을?**
- 토큰 절감률, 처리 시간, AI 신뢰도 실시간 표시

**출력 예시:**
```
v5.0 Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Efficiency:
  Original: 1,000 tokens
  Compressed: 520 tokens
  Reduction: 48%

Performance:
  Processing Time: 2.3s
  Intent Accuracy: 94%
  Priority Confidence: 91%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**사용법:**
```bash
python3 llm_router_v5.py "요청" --v5 --show-stats
```

---

## 실전 예제

### 예제 1: 코드 리뷰 요청 (기본)

```bash
python3 llm_router_v5.py "app.py 파일의 보안 취약점을 찾아주세요" --friendly
```

**결과:**
```
작업이 1개로 분할되었습니다.

Ticket A: 코드 분석
Route: analyze (분석 전문 모델)
Priority: 7 (긴급도 7, 중요도 7)

Claude Ready Prompt:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app.py 파일의 보안 취약점을 찾아주세요.

다음 사항을 중점적으로 확인:
- SQL Injection 가능성
- XSS 취약점
- 인증/인가 로직
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 예제 2: 복잡한 기능 구현 (v5 전체 기능)

```bash
python3 llm_router_v5.py \
  "사용자 인증 시스템을 구현해주세요. JWT 토큰 방식으로 로그인, 로그아웃, 회원가입 기능이 필요합니다." \
  --v5 \
  --compress \
  --compression-level 2 \
  --show-stats \
  --friendly \
  --economy balanced
```

**결과:**
```
v5.0 Enhanced Router
작업이 3개로 분할되었습니다.

Ticket A: JWT 인증 구조 설계
  Intent: implement (신뢰도 95%)
  Priority: 90 (긴급도 9, 중요도 10)
  Route: claude (고성능 모델)
  Tokens: 450 → 270 (40% 절감)

Ticket B: 로그인/로그아웃 API 구현
  Intent: implement (신뢰도 92%)
  Priority: 81 (긴급도 9, 중요도 9)
  Route: claude (고성능 모델)
  Tokens: 380 → 228 (40% 절감)

Ticket C: 회원가입 및 유효성 검사
  Intent: implement (신뢰도 88%)
  Priority: 56 (긴급도 7, 중요도 8)
  Route: cheap_llm (경제형 모델)
  Tokens: 320 → 192 (40% 절감)

v5.0 Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Efficiency:
  Original: 1,150 tokens
  Compressed: 690 tokens
  Reduction: 40%

Performance:
  Processing Time: 2.8s
  Intent Accuracy: 92%
  Priority Confidence: 89%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 예제 3: 여러 작업 한 번에 (GUI)

1. GUI 실행: `python3 router_gui.py`
2. 요청 입력:
```
다음 작업들을 해주세요:
1. 데이터베이스 스키마 설계
2. REST API 엔드포인트 구현
3. 프론트엔드 UI 컴포넌트 작성
4. 단위 테스트 작성
```
3. 옵션 체크:
   - ✅ v5 활성화
   - ✅ 압축
   - ✅ 통계 표시
4. "Split Tasks" 클릭

**결과:** 4개 티켓으로 자동 분할 + 우선순위 정렬

### 예제 4: Web UI로 팀 협업

**서버 시작:**
```bash
export GROQ_API_KEY="your_key"
python3 web_server.py --port 8080
```

**팀원들과 공유:**
```
브라우저에서 http://your-ip:8080 접속
→ 같은 네트워크 내 모든 기기 사용 가능
```

**장점:**
- 📝 자주 쓰는 프롬프트 저장
- 📊 팀 전체 토큰 사용량 추적
- 📱 모바일에서도 작업 가능

---

## 문제 해결

### ❓ "BERT 모델 로딩 실패"

**증상:**
```
⚠️ BERT failed: ..., using keyword fallback
```

**해결:**
```bash
# transformers 재설치
pip3 install --upgrade transformers

# 모델 수동 다운로드
python3 -c "from transformers import pipeline; pipeline('zero-shot-classification', model='distilbert-base-uncased')"
```

### ❓ "압축률이 50%에 못 미침"

**원인:**
- 짧은 텍스트 (< 50 토큰)
- 이미 간결한 요청
- 코드 블록 포함 (압축 불가)

**해결:**
```bash
# 압축 레벨 올리기 (품질 저하 가능)
--compression-level 3

# 또는 압축 비활성화
--no-compress
```

### ❓ "우선순위가 이상함"

**증상:**
```
중요한 작업인데 우선순위가 낮게 나옴
```

**해결:**
```bash
# ML 모델 재훈련
cd ml/
python3 train_priority_model.py

# 또는 v4 모드 사용 (순서대로)
python3 llm_router.py "요청"  # v5 플래그 없이
```

### ❓ "처리 속도가 느림 (> 5초)"

**원인:**
- BERT 모델 초기 로딩 (~3초)
- 인터넷 연결 불안정 (Groq 번역)

**해결:**
```bash
# Groq 번역 비활성화
unset GROQ_API_KEY

# v4 모드로 전환 (더 빠름)
python3 llm_router.py "요청"
```

### ❓ "한국어가 영어로 안 번역됨"

**확인사항:**
```bash
# 1. API 키 설정 확인
echo $GROQ_API_KEY

# 2. 키 유효성 테스트
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"test"}]}'
```

### ❓ "Web UI가 안 열림"

**확인사항:**
```bash
# 1. 포트 충돌 확인
lsof -i :8080

# 2. 다른 포트로 시작
python3 web_server.py --port 9000

# 3. 방화벽 확인 (macOS)
sudo pfctl -sr | grep 8080
```

---

## 💡 팁 & 베스트 프랙티스

### 토큰 절약 팁

1. **간결한 요청 작성:**
   ```
   ❌ "저기요, 혹시 이 파일에 있는 코드를 한번 봐주실 수 있으신가요?"
   ✅ "app.py 코드 리뷰"
   ```

2. **압축 레벨 조절:**
   - 일반 작업: Level 2 (권장)
   - 간단 작업: Level 3 (최대 절감)
   - 정밀 작업: Level 1 (품질 우선)

3. **Economy 모드 활용:**
   ```bash
   # 실험/연습
   --economy strict

   # 실무/중요 작업
   --economy balanced
   ```

### 정확도 향상 팁

1. **구체적인 요청:**
   ```
   ❌ "버그 고쳐줘"
   ✅ "login.py 41번째 줄 NullPointerException 수정"
   ```

2. **작업 분리:**
   ```
   ❌ "앱 전체 개발해줘"
   ✅ "1. DB 스키마 설계 2. API 구현 3. UI 작성"
   ```

3. **컨텍스트 제공:**
   ```
   ✅ "Node.js Express 프로젝트에서 JWT 인증 추가"
   ```

### 협업 팁

1. **프롬프트 템플릿 저장** (Web UI)
   - 자주 쓰는 요청 형식 저장
   - 팀 표준 프롬프트 공유

2. **통계 활용**
   - 월별 토큰 사용량 모니터링
   - 비용 효율적인 작업 패턴 찾기

3. **피드백 수집** (Web UI)
   - 각 티켓 결과 평가
   - 모델 선택 정확도 개선

---

## 📚 추가 자료

- **기술 문서**: [docs/02-design/features/v5-enhancement.design.md](docs/02-design/features/v5-enhancement.design.md)
- **Gap Analysis**: [docs/03-analysis/tools.analysis.md](docs/03-analysis/tools.analysis.md)
- **완료 리포트**: [docs/04-report/tools.report.md](docs/04-report/tools.report.md)
- **테스트**: [tests/](tests/)
- **벤치마크**: [benchmarks/](benchmarks/)

---

## 🆘 지원

문제가 해결되지 않으면:

1. **로그 확인:**
   ```bash
   python3 llm_router_v5.py "요청" --v5 2> error.log
   cat error.log
   ```

2. **디버그 모드:**
   ```bash
   python3 -u llm_router_v5.py "요청" --v5 --show-stats
   ```

3. **Issue 등록:**
   - 에러 메시지 전문
   - Python 버전
   - 설치된 패키지 (`pip3 list`)

---

**만든 날짜**: 2026-02-14
**버전**: v5.0
**작성자**: AI Development Team
