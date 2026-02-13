---
template: plan
version: 1.2
description: LLM Router (AI Task Splitter) Planning Document
variables:
  - feature: tools (LLM Router)
  - date: 2026-02-13
  - author: AI Development Team
  - project: LLM Router
  - version: 4.0
---

# LLM Router Planning Document

> **Summary**: AI-powered task routing system that splits user requests into independent tasks and generates Claude-optimized prompts
>
> **Project**: LLM Router (AI Task Splitter)
> **Version**: 4.0
> **Author**: AI Development Team
> **Date**: 2026-02-13
> **Status**: Implemented (Reverse Documentation)

---

## 1. Overview

### 1.1 Purpose

LLM Router는 복잡한 사용자 요청을 독립적인 작업(티켓)으로 분할하고, 각 작업에 대해 Claude에게 최적화된 프롬프트를 자동 생성하는 도구입니다.

**핵심 가치 (v4.0 - 현재):**
- 대규모 작업을 관리 가능한 단위로 분할
- Claude에게 최적화된 프롬프트 자동 생성
- 초보자도 쉽게 사용할 수 있는 GUI/웹 인터페이스 제공
- 다중 프로젝트 지원

**고도화 목적 (v5.0+ - 계획):**
- **비전공자 토큰 낭비 최소화**: 프롬프트 자동 최적화로 불필요한 토큰 소비 방지
- **다국어 지원 강화**: 자동 영어 번역으로 다국어 사용자의 토큰 효율성 향상
- **엔터프라이즈 확장**: 기업 업무 자동화 및 프로세스 최적화 기능 제공

### 1.2 Background

AI 개발 도구를 사용할 때, 복잡한 요청을 한 번에 처리하면 컨텍스트가 손실되거나 일부 작업이 누락될 수 있습니다. 이를 해결하기 위해:
- 작업을 독립적인 티켓으로 분할
- 각 티켓에 우선순위와 컨텍스트 부여
- 티켓별 Claude 프롬프트 자동 생성
- 작업 히스토리 추적 및 관리

### 1.3 Related Documents

- Design: `docs/02-design/features/tools.design.md` (생성 예정)
- Router GUI Design: `router_gui_design.md`
- Change Log: `agent_docs/change_log.md`

---

## 2. Scope

### 2.1 In Scope

- [x] CLI 기반 라우터 엔진 (llm_router.py)
- [x] Tkinter 기반 GUI 인터페이스 (router_gui.py)
- [x] Flask 웹 서버 API (web_server.py)
- [x] 웹 기반 UI (website/router.html)
- [x] 작업 우선순위 및 라우팅 로직
- [x] 티켓 격리 및 추출 (A/B/C 티켓 선택)
- [x] Claude 프롬프트 자동 생성
- [x] 작업 히스토리 로깅
- [x] 한글-영어 자동 번역 (Groq API)
- [x] 다중 라우터 프로젝트 지원

### 2.2 Out of Scope (v4.0)

- 실제 Claude API 호출 (사용자가 복사/붙여넣기)
- 작업 실행 자동화
- 데이터베이스 영구 저장 (현재는 JSON 파일 기반)
- 사용자 인증/권한 관리

### 2.3 Future Scope (v5.0+ 고도화 계획)

**Phase 1: Core Enhancement (v5.0)**
- [ ] 사용자 목적/의도 자동 파악 (NLP 기반)
- [ ] 우선순위 자체 판단 알고리즘 고도화
- [ ] 텍스트 분리 및 재합성 (스마트 청킹)
- [ ] 프롬프트 압축화 (토큰 최소화 엔진)
- [ ] 개선된 다국어 자동 번역

**Phase 2: Build Mode (v6.0 - 수익화 기능)**
- [ ] 요구사항 정의서 기반 자동 기획
- [ ] 자동 개발 실시 (코드 생성 자동화)
- [ ] 프로젝트 구조 자동 생성
- [ ] 클라이언트 요구사항 → 실행 가능 코드 파이프라인

**Phase 3: Enterprise Features (v7.0 - 수익화 기능)**
- [ ] 기존 프로그램 자동 유지보수
- [ ] 오류 자동 감지 및 해결
- [ ] 기업 구조 분석 및 점검
- [ ] 자동화 가능 프로세스 도출 및 추천
- [ ] ROI 계산 및 자동화 우선순위 제안

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 사용자 요청을 독립적인 작업(티켓)으로 분할 | High | ✅ Implemented |
| FR-02 | 각 티켓에 우선순위 및 신뢰도 점수 부여 | High | ✅ Implemented |
| FR-03 | Claude에게 최적화된 프롬프트 자동 생성 | High | ✅ Implemented |
| FR-04 | GUI를 통한 초보자 친화적 인터페이스 | High | ✅ Implemented |
| FR-05 | 웹 기반 UI 제공 (브라우저 접근) | Medium | ✅ Implemented |
| FR-06 | 다중 티켓 중 특정 티켓만 선택 복사 | High | ✅ Implemented |
| FR-07 | 한글 티켓을 영어로 자동 번역 | Medium | ✅ Implemented |
| FR-08 | 작업 히스토리 추적 및 JSON 저장 | Medium | ✅ Implemented |
| FR-09 | 다중 프로젝트 라우터 전환 지원 | Low | ✅ Implemented |
| FR-10 | Change Log Stub 자동 생성 | Medium | ✅ Implemented |

**고도화 기능 (v5.0+):**

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-11 | 사용자 목적/의도 자동 파악 (NLP 분석) | High | 📋 Planned (v5.0) |
| FR-12 | 우선순위 자체 판단 알고리즘 (ML 기반) | High | 📋 Planned (v5.0) |
| FR-13 | 텍스트 분리 및 재합성 (스마트 청킹) | High | 📋 Planned (v5.0) |
| FR-14 | 프롬프트 압축화 엔진 (토큰 최소화) | High | 📋 Planned (v5.0) |
| FR-15 | 개선된 자동 영어 번역 (다국어 지원) | Medium | 📋 Planned (v5.0) |
| FR-16 | Build 모드: 요구사항 정의서 자동 파싱 | High | 📋 Planned (v6.0) |
| FR-17 | Build 모드: 자동 기획/개발 실시 | High | 📋 Planned (v6.0) |
| FR-18 | Build 모드: 프로젝트 구조 자동 생성 | Medium | 📋 Planned (v6.0) |
| FR-19 | 기존 프로그램 자동 유지보수 | Medium | 📋 Planned (v7.0) |
| FR-20 | 오류 자동 감지 및 해결 | High | 📋 Planned (v7.0) |
| FR-21 | 기업 프로세스 자동화 도출 | High | 📋 Planned (v7.0) |
| FR-22 | 자동화 가능 프로세스 추천 및 ROI 계산 | Medium | 📋 Planned (v7.0) |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 라우터 응답 시간 < 5초 | 실행 시간 측정 |
| Usability | 초보자도 3단계 이내 사용 가능 | 사용자 테스트 |
| Reliability | 파싱 오류 시 안전한 폴백 | 예외 처리 테스트 |
| Portability | Python 3.8+ 환경에서 동작 | 환경별 테스트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [x] CLI 라우터 정상 동작
- [x] GUI 인터페이스 정상 동작
- [x] 웹 UI 정상 동작
- [x] 티켓 추출 및 복사 기능 정상 동작
- [x] 한글-영어 번역 기능 정상 동작
- [x] 작업 히스토리 저장 정상 동작

### 4.2 Quality Criteria

- [ ] 코드 품질 검증 (Gap Analysis 필요)
- [ ] 설계-구현 일치도 >= 90%
- [ ] 사용자 문서 완성
- [ ] 에러 핸들링 완전성 검증

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Groq API 장애 시 번역 실패 | Medium | Medium | API 에러 시 원본 반환, 사용자에게 경고 표시 |
| 복잡한 요청 파싱 실패 | High | Low | 파싱 오류 시 전체 블록 반환, 로그 기록 |
| 다중 티켓 추출 오류 | High | Low | 정규식 개선, 폴백 로직 구현 |
| 웹 서버 포트 충돌 | Low | Medium | 포트 설정 옵션 제공 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure (`components/`, `lib/`, `types/`) | Static sites, portfolios, landing pages | ☐ |
| **Dynamic** | Feature-based modules, BaaS integration (bkend.ai) | Web apps with backend, SaaS MVPs, fullstack apps | ☑ |
| **Enterprise** | Strict layer separation, DI, microservices | High-traffic systems, complex architectures | ☐ |

**Selected: Dynamic**
- 웹 앱 + 백엔드 API 구조
- Flask 서버 포함
- 다중 기능 모듈 (CLI, GUI, Web)

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Backend Framework | Flask / FastAPI / Django | Flask | 경량, 빠른 프로토타이핑 |
| Frontend | HTML/CSS/JS / React / Vue | HTML/CSS/JS | 단순성, 의존성 최소화 |
| GUI Framework | Tkinter / PyQt / Kivy | Tkinter | Python 기본 라이브러리 |
| Translation API | Groq / OpenAI / Google | Groq | 빠른 속도, 저비용 |
| Storage | JSON / SQLite / PostgreSQL | JSON | 단순성, 파일 기반 추적 |
| Deployment | Local / Docker / Cloud | Local | 개발 도구, 로컬 실행 우선 |

### 6.3 Clean Architecture Approach

```
Selected Level: Dynamic

Folder Structure:
tools/
├── llm_router.py          # Core router engine (CLI)
├── router_gui.py          # GUI interface (Tkinter)
├── web_server.py          # Web API server (Flask)
├── website/               # Web UI
│   ├── router.html        # Main interface
│   ├── router.js          # Client-side logic
│   ├── router.css         # Styling
│   ├── index.html         # Portfolio page
│   ├── style.css          # Main styles
│   └── script.js          # Main scripts
├── docs/                  # PDCA documents
│   ├── 01-plan/
│   ├── 02-design/
│   ├── 03-analysis/
│   └── 04-report/
├── agent_docs/            # Change logs
│   └── change_log.md
└── task_history.json      # Task history log
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

Check which conventions already exist in the project:

- [x] `CLAUDE.md` has coding conventions section (Global security guidelines)
- [ ] `docs/01-plan/conventions.md` exists (To be created)
- [ ] `CONVENTIONS.md` exists at project root (Not needed)
- [ ] ESLint configuration (`.eslintrc.*`) (N/A - Python project)
- [ ] Prettier configuration (`.prettierrc`) (N/A - Python project)
- [ ] TypeScript configuration (`tsconfig.json`) (N/A - Python project)

### 7.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | Implicit | Python PEP8 준수, snake_case | High |
| **Folder structure** | Exists | 문서화 필요 | Medium |
| **Import order** | Implicit | stdlib → third-party → local | Medium |
| **Environment variables** | Missing | GROQ_API_KEY | High |
| **Error handling** | Partial | try-except 표준화 | Medium |

### 7.3 Environment Variables Needed

| Variable | Purpose | Scope | To Be Created |
|----------|---------|-------|:-------------:|
| `GROQ_API_KEY` | Groq API 인증 | Server | ☑ Required |
| `ROUTER_PORT` | 웹 서버 포트 | Server | ☐ Optional (default: 8000) |
| `ROUTER_HOST` | 웹 서버 호스트 | Server | ☐ Optional (default: localhost) |

### 7.4 Pipeline Integration

Not using 9-phase Development Pipeline (standalone tool project).

---

## 8. Next Steps

1. [x] Write design document (`tools.design.md`)
2. [ ] Gap analysis (설계-구현 비교)
3. [ ] Code quality review
4. [ ] Documentation completion

---

## 9. Future Roadmap & Monetization Strategy

### 9.1 Development Roadmap

```
Timeline:
2026 Q2 (v5.0) → 2026 Q3 (v6.0) → 2026 Q4 (v7.0) → 2027+ (Enterprise Scale)
```

#### Phase 1: Core Enhancement (v5.0) - 2026 Q2

**목표**: 토큰 효율성 극대화 및 사용자 경험 개선

**주요 기능:**

1. **사용자 의도 파악 엔진**
   - NLP 기반 목적 분석 (분석/구현/연구 자동 분류)
   - 사용자 패턴 학습 및 개인화
   - 컨텍스트 히스토리 추적

2. **우선순위 자체 판단 알고리즘**
   - 긴급도/중요도 자동 평가
   - 의존성 분석 (A → B → C 순서 자동 결정)
   - 병렬 처리 가능 작업 식별

3. **스마트 텍스트 분리 및 재합성**
   - 의미 기반 청킹 (문장 경계가 아닌 의미 단위)
   - 중복 제거 및 통합
   - 관련 작업 자동 그룹핑

4. **프롬프트 압축화 엔진**
   - 불필요한 단어 제거 (조사, 부사 최소화)
   - 핵심 키워드 추출
   - 토큰 수 50% 절감 목표
   - 압축 전/후 비교 UI 제공

5. **개선된 다국어 번역**
   - Groq API 최적화 (현재 대비 속도 2배)
   - 전문 용어 사전 구축
   - 문맥 기반 번역 (직역 → 의역)

**기술 스택:**
- NLP: spaCy, transformers (BERT 계열)
- ML: scikit-learn (우선순위 분류)
- API: Groq API v2 (고속 번역)

**성공 지표:**
- 토큰 절감률: 평균 50% 이상
- 번역 정확도: 95% 이상
- 응답 시간: 3초 이내

---

#### Phase 2: Build Mode (v6.0) - 2026 Q3

**목표**: 수익화 - 클라이언트 프로젝트 자동화

**핵심 기능:**

1. **요구사항 정의서 자동 파싱**
   - PDF/Word/Excel 문서 자동 읽기
   - 표, 리스트, 다이어그램 인식
   - 요구사항 추출 및 구조화

2. **자동 기획 (Plan 문서 생성)**
   - 요구사항 → PDCA Plan 문서 자동 작성
   - 범위, 우선순위, 일정 자동 산출
   - 기술 스택 추천 (프로젝트 성격 분석)

3. **자동 개발 실시**
   - Plan → Design → 코드 생성 자동화
   - 프로젝트 구조 자동 생성 (폴더, 파일)
   - 보일러플레이트 코드 자동 작성
   - Claude API 연동 (자동 프롬프트 전송)

4. **진행 상황 추적**
   - 실시간 진행률 표시
   - 생성된 파일 목록 및 미리보기
   - 오류 발생 시 자동 재시도

**사용 시나리오:**
```
클라이언트 요구사항 정의서 (PDF)
  ↓
Build Mode 실행
  ↓
자동 분석 → Plan 생성 → Design 생성 → 코드 생성
  ↓
검토 및 수정 → 완성된 프로젝트 전달
```

**수익 모델:**
- 프로젝트당 라이선스: $500-$2000
- 월 구독 (무제한): $299/월
- 엔터프라이즈 라이선스: $5000/년

**목표 고객:**
- 소규모 개발 대행사
- 프리랜서 개발자
- 스타트업 (빠른 MVP 제작)

---

#### Phase 3: Enterprise Features (v7.0) - 2026 Q4

**목표**: 대기업 자동화 컨설팅 서비스

**핵심 기능:**

1. **기존 프로그램 자동 유지보수**
   - 코드베이스 자동 스캔
   - 버그 패턴 감지
   - 의존성 업데이트 자동 제안
   - 레거시 코드 리팩토링 추천

2. **오류 자동 감지 및 해결**
   - 로그 파일 실시간 모니터링
   - 에러 패턴 분석 및 분류
   - 자동 수정 스크립트 생성
   - 테스트 자동 실행 및 검증

3. **기업 프로세스 분석**
   - 업무 플로우 자동 매핑
   - 병목 구간 식별
   - 수작업 구간 자동 탐지
   - 자동화 가능 프로세스 도출

4. **자동화 추천 및 ROI 계산**
   - 자동화 우선순위 평가
   - 예상 비용 절감 계산
   - 구현 난이도 평가
   - ROI 보고서 자동 생성

**사용 시나리오:**
```
기업 컨설팅 요청
  ↓
1. 현재 시스템 분석 (코드, 로그, 프로세스)
  ↓
2. 문제점 및 개선점 도출
  ↓
3. 자동화 방안 제시 (우선순위별)
  ↓
4. ROI 보고서 + 구현 플랜 제공
  ↓
5. 자동화 스크립트 생성 및 배포
```

**수익 모델:**
- 컨설팅 서비스: $10,000-$100,000/프로젝트
- 연간 유지보수: $20,000-$50,000/년
- 성과 기반 수수료: 비용 절감액의 10-20%

**목표 고객:**
- 중견/대기업 (50인 이상)
- 제조업, 물류, 금융권
- 레거시 시스템 운영 기업

---

### 9.2 Monetization Strategy

#### 9.2.1 Price Tiers

| Tier | Target | Price | Features |
|------|--------|-------|----------|
| **Free** | 개인 개발자 | $0 | v4.0 기능 (현재) |
| **Pro** | 프리랜서 | $29/월 | v5.0 기능 (압축, 우선순위) |
| **Build** | 개발 대행사 | $299/월 | v6.0 Build Mode |
| **Enterprise** | 대기업 | Custom | v7.0 + 컨설팅 |

#### 9.2.2 Revenue Projection

| Year | Tier | Users | Revenue |
|------|------|-------|---------|
| 2026 Q2 | Pro | 100 | $2,900/월 |
| 2026 Q3 | Build | 20 | $5,980/월 |
| 2026 Q4 | Enterprise | 5 | $50,000/월 (평균) |
| **2027** | **Total** | **500+** | **$150,000+/월** |

#### 9.2.3 Go-to-Market Strategy

**Phase 1 (v5.0):**
- GitHub 오픈소스 공개 (Free tier)
- Product Hunt 런칭
- 개발자 커뮤니티 마케팅

**Phase 2 (v6.0):**
- 프리랜서 플랫폼 파트너십 (Upwork, Fiverr)
- 케이스 스터디 발행 (토큰 절감 사례)
- 웨비나 개최 (Build Mode 시연)

**Phase 3 (v7.0):**
- 엔터프라이즈 영업팀 구성
- 컨설팅 서비스 론칭
- 업계별 맞춤 솔루션 개발

---

### 9.3 Technical Debt & Risks

#### 9.3.1 기술 부채

| Item | Impact | Plan |
|------|--------|------|
| JSON 기반 저장소 | High | v5.0에서 SQLite로 마이그레이션 |
| 단일 언어 UI | Medium | v5.0에서 i18n 적용 |
| 수동 테스트 | High | v5.0에서 pytest 도입 |
| 로컬 전용 | Medium | v6.0에서 클라우드 배포 옵션 추가 |

#### 9.3.2 리스크

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Claude API 정책 변경 | High | Medium | 다중 LLM 지원 (GPT-4, Gemini) |
| Groq API 가격 인상 | Medium | Low | 자체 번역 엔진 개발 (fallback) |
| 경쟁 제품 출현 | Medium | High | 차별화 (Build Mode, Enterprise) |
| 수익화 지연 | Medium | Medium | 단계별 출시로 리스크 분산 |

---

### 9.4 Success Metrics

#### 9.4.1 v5.0 (Core Enhancement)

- [ ] 토큰 절감률: 50% 이상
- [ ] 사용자 만족도: 4.5/5.0 이상
- [ ] 일일 활성 사용자: 100명 이상

#### 9.4.2 v6.0 (Build Mode)

- [ ] 프로젝트 자동 생성 성공률: 80% 이상
- [ ] 평균 생성 시간: 10분 이내
- [ ] 유료 전환율: 5% 이상

#### 9.4.3 v7.0 (Enterprise)

- [ ] 엔터프라이즈 계약: 5개 이상
- [ ] 평균 ROI: 300% 이상
- [ ] 고객 유지율: 90% 이상

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-13 | Initial draft (reverse documentation) | AI Development Team |
| 0.2 | 2026-02-13 | Added SSH 프로젝트 고도화 roadmap (v5.0-v7.0), monetization strategy, 12 new FRs | AI Development Team |
