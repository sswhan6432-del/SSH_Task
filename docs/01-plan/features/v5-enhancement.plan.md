---
template: plan
version: 1.0
description: LLM Router v5.0 Core Enhancement Planning Document
variables:
  - feature: v5-enhancement (LLM Router v5.0)
  - date: 2026-02-13
  - author: AI Development Team
  - project: LLM Router
  - version: 5.0
---

# LLM Router v5.0 Core Enhancement Planning Document

> **Summary**: Token efficiency maximization and UX improvement through NLP/ML enhancements
>
> **Project**: LLM Router v5.0 (Core Enhancement)
> **Version**: 5.0
> **Author**: AI Development Team
> **Date**: 2026-02-13
> **Status**: Draft
> **Base Version**: v4.0 (Match Rate 90.6%)

---

## 1. Overview

### 1.1 Purpose

v5.0은 LLM Router의 핵심 엔진을 AI 기술(NLP/ML)로 고도화하여 **토큰 효율성 극대화** 및 **사용자 경험 개선**을 목표로 합니다.

**핵심 가치:**
- **토큰 50% 절감**: 프롬프트 압축 엔진으로 비전공자의 토큰 낭비 최소화
- **지능형 우선순위**: ML 기반 긴급도/중요도 자동 판단
- **의도 자동 파악**: NLP 기반 사용자 목적 분석
- **문맥 기반 번역**: Groq API 최적화로 다국어 사용자 지원 강화

### 1.2 Background

**v4.0 현황 (2026-02-13 기준):**
- Match Rate: 90.6% (Pass)
- 총 2219 라인 코드 (llm_router.py 596, router_gui.py 1259, web_server.py 367)
- 한계점:
  - 우선순위: 단순 순서 기반 (10, 9, 8, ...)
  - 라우팅: 모두 "claude" 고정 (분류 없음)
  - 압축: 없음 (원문 그대로 전송)
  - 번역: Groq API 사용하지만 최적화 부족

**v5.0 개선 필요성:**
- 비전공자들이 장황한 프롬프트로 토큰 낭비 (평균 2배 이상 과다)
- 다국어 사용자 번역 품질 불안정 (한글 → 영어 직역)
- 작업 우선순위 판단 불가 (사용자 수동 정렬 필요)
- 의도 파악 실패로 잘못된 프롬프트 생성

### 1.3 Related Documents

- Base: `docs/01-plan/features/tools.plan.md` (v4.0 + 로드맵)
- Design: `docs/02-design/features/v5-enhancement.design.md` (생성 예정)
- Analysis: `docs/03-analysis/tools.analysis.md` (v4.0 Gap Analysis)

---

## 2. Scope

### 2.1 In Scope (v5.0 Core Features)

**Phase 1: NLP/ML 엔진 구축** (우선순위 High)
- [ ] FR-11: 사용자 의도 파악 엔진 (NLP 기반)
- [ ] FR-12: 우선순위 자체 판단 알고리즘 (ML 기반)
- [ ] FR-13: 스마트 텍스트 분리 및 재합성
- [ ] FR-14: 프롬프트 압축화 엔진 (토큰 50% 절감)
- [ ] FR-15: 개선된 다국어 번역 (Groq API v2)

**Phase 2: 통합 및 UI** (우선순위 Medium)
- [ ] GUI 개선: 압축 전/후 비교 UI
- [ ] 웹 UI 개선: 토큰 절감률 실시간 표시
- [ ] CLI 플래그 추가: `--compress`, `--intent-detect`, `--smart-priority`
- [ ] 성능 최적화: 응답 시간 3초 이내 유지

**Phase 3: 테스트 및 검증** (우선순위 Medium)
- [ ] 단위 테스트: pytest 도입
- [ ] 성능 벤치마크: 토큰 절감률, 번역 정확도, 응답 시간
- [ ] 사용자 테스트: 비전공자 5명 이상 피드백

### 2.2 Out of Scope (v6.0+ 이후)

- Build Mode (요구사항 자동 파싱, 자동 기획/개발)
- Enterprise Features (유지보수, 프로세스 자동화)
- 데이터베이스 마이그레이션 (JSON → SQLite)
- 웹 UI 완전 재작성 (React 전환)

---

## 3. Requirements

### 3.1 Functional Requirements (v5.0)

| ID | Requirement | Priority | Dependencies |
|----|-------------|----------|--------------|
| **FR-11** | **사용자 의도 파악 엔진 (NLP)** | High | spaCy, transformers |
| | - 사용자 요청 텍스트를 분석하여 목적 자동 분류 | | |
| | - 분류: analyze (분석/검토), implement (수정/추가), research (조사/찾기) | | |
| | - 키워드 매칭 → NLP 의미 분석으로 전환 | | |
| | - 컨텍스트 히스토리 추적 (이전 요청 패턴 학습) | | |
| **FR-12** | **우선순위 자체 판단 알고리즘 (ML)** | High | scikit-learn |
| | - 현재: 순서 기반 (10, 9, 8, ...) | | |
| | - 개선: 긴급도/중요도 자동 평가 (1-10 스케일) | | |
| | - 의존성 분석: A 완료 → B 시작 (순서 자동 결정) | | |
| | - 병렬 처리 가능 작업 식별 | | |
| **FR-13** | **스마트 텍스트 분리 및 재합성** | High | spaCy NLP |
| | - 현재: 번호 리스트 OR Groq split | | |
| | - 개선: 의미 기반 청킹 (문장 경계 무시, 의미 단위 분할) | | |
| | - 중복 제거 및 통합 (동일 의미 작업 병합) | | |
| | - 관련 작업 자동 그룹핑 | | |
| **FR-14** | **프롬프트 압축화 엔진 (토큰 50% 절감)** | High | transformers, tiktoken |
| | - 불필요한 단어 제거 (조사, 부사, 접속사 최소화) | | |
| | - 핵심 키워드 추출 (TF-IDF, BERT embeddings) | | |
| | - 문장 압축 (장황한 설명 → 간결한 명령) | | |
| | - 압축 전/후 비교 UI 제공 | | |
| | - 토큰 카운터 통합 (tiktoken 사용) | | |
| **FR-15** | **개선된 다국어 번역** | Medium | Groq API v2 |
| | - Groq API 최적화 (배치 처리로 속도 2배) | | |
| | - 전문 용어 사전 구축 (개발 용어 100+ 단어) | | |
| | - 문맥 기반 번역 (직역 → 의역) | | |
| | - 번역 정확도 95% 이상 목표 | | |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| **Performance** | 응답 시간 < 3초 (v4.0: ~5초) | 벤치마크 테스트 (100회 평균) |
| **Token Efficiency** | 토큰 절감률 >= 50% | tiktoken으로 압축 전/후 비교 |
| **Translation Accuracy** | 번역 정확도 >= 95% | BLEU score, 수동 평가 |
| **ML Model Accuracy** | 의도 분류 정확도 >= 90% | 테스트 데이터 100건 평가 |
| **Backward Compatibility** | v4.0 CLI 플래그 100% 호환 | 회귀 테스트 |
| **Code Quality** | Match Rate >= 90% | Gap Analysis |

---

## 4. Success Criteria

### 4.1 Definition of Done

**Phase 1: NLP/ML 엔진**
- [ ] spaCy, transformers 통합 완료
- [ ] 의도 파악 엔진 정확도 >= 90%
- [ ] 우선순위 판단 알고리즘 작동 확인
- [ ] 압축 엔진 토큰 절감률 >= 50% 달성

**Phase 2: 통합 및 UI**
- [ ] GUI/Web UI 업데이트 완료
- [ ] CLI 새 플래그 추가 및 테스트
- [ ] 전체 시스템 통합 테스트 Pass

**Phase 3: 검증**
- [ ] pytest 단위 테스트 작성 (커버리지 >= 80%)
- [ ] 성능 벤치마크 목표 달성
- [ ] 사용자 테스트 완료 (만족도 >= 4.5/5.0)

### 4.2 Quality Criteria

- [ ] Gap Analysis Match Rate >= 90%
- [ ] 코드 리뷰 완료
- [ ] 문서 완성 (Plan, Design, Analysis, Report)
- [ ] v4.0 대비 성능 개선 입증

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| NLP/ML 라이브러리 성능 부족 | High | Medium | 경량 모델 선택, 캐싱 전략, 백그라운드 처리 |
| 압축 후 의미 손실 | High | Medium | 압축 레벨 조절 옵션, 사용자 확인 UI |
| 응답 시간 증가 (NLP 처리) | Medium | High | 비동기 처리, 모델 로딩 최적화, 캐싱 |
| 의존성 증가 (spaCy, transformers) | Low | High | 옵션 기능화, 미설치 시 v4.0 모드로 폴백 |
| 번역 API 비용 증가 | Medium | Low | 배치 처리, 캐싱, 로컬 모델 대안 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | ☐ |
| **Dynamic** | Feature-based modules | Web apps, MVP | ☑ |
| **Enterprise** | Strict layers, microservices | High-traffic | ☐ |

**Selected: Dynamic** (유지)

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| NLP Library | spaCy / NLTK / Stanza | spaCy | 빠른 속도, 풍부한 기능, Python 친화적 |
| ML Framework | scikit-learn / PyTorch / TensorFlow | scikit-learn | 단순 분류 작업에 적합, 경량 |
| Transformer Model | BERT / GPT / T5 | BERT (lightweight) | 의미 분석에 적합, 경량 버전 사용 가능 |
| Token Counter | tiktoken / transformers tokenizer | tiktoken | OpenAI 공식, 정확한 토큰 카운트 |
| Model Serving | Local / Cloud | Local (v5.0) | 응답 속도, 비용 절감 |

### 6.3 Enhanced Architecture

```
┌──────────────────────────────────────────────────┐
│           User Input (Korean/English)             │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │   NLP Preprocessing         │
    │  - spaCy tokenization       │
    │  - Text normalization       │
    └─────────────┬───────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
┌─────────┐ ┌──────────┐ ┌────────────┐
│ Intent  │ │ Priority │ │ Compression│
│ Detect  │ │ Ranking  │ │ Engine     │
│ (BERT)  │ │ (ML)     │ │ (NLP)      │
└────┬────┘ └────┬─────┘ └─────┬──────┘
     │           │              │
     └───────────┼──────────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │  Task Routing       │
      │  (Intelligent)      │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  Translation        │
      │  (Groq API v2)      │
      └─────────┬───────────┘
                │
                ▼
      ┌─────────────────────┐
      │  Claude Prompt      │
      │  (Optimized)        │
      └─────────────────────┘
```

### 6.4 Folder Structure (v5.0 additions)

```
tools/
├── llm_router.py          # Core engine (v4.0 유지)
├── llm_router_v5.py       # v5.0 enhanced engine (NEW)
├── nlp/                   # NLP module (NEW)
│   ├── __init__.py
│   ├── intent_detector.py   # FR-11
│   ├── priority_ranker.py   # FR-12
│   ├── text_chunker.py      # FR-13
│   └── compressor.py        # FR-14
├── ml/                    # ML models (NEW)
│   ├── __init__.py
│   ├── priority_model.pkl   # Trained classifier
│   └── training_data.json   # Training dataset
├── models/                # Pre-trained models (NEW)
│   ├── spacy_ko/           # Korean spaCy model
│   └── bert_lightweight/   # BERT for intent detection
├── router_gui.py          # GUI (v5.0 업데이트)
├── web_server.py          # Web server (v5.0 업데이트)
├── website/               # Web UI (v5.0 업데이트)
├── tests/                 # Unit tests (NEW)
│   ├── test_intent.py
│   ├── test_priority.py
│   └── test_compression.py
└── benchmarks/            # Performance tests (NEW)
    └── token_efficiency.py
```

---

## 7. Convention Prerequisites

### 7.1 Existing Conventions (v4.0)

- [x] Python PEP8 준수
- [x] snake_case 네이밍
- [x] stdlib → third-party → local import 순서

### 7.2 New Conventions (v5.0)

| Category | Convention | Rationale |
|----------|------------|-----------|
| **Module Naming** | nlp_, ml_ prefix | 명확한 기능 구분 |
| **Model Files** | .pkl, .bin 확장자 | 표준 ML 모델 포맷 |
| **Test Files** | test_*.py | pytest 표준 |
| **Docstrings** | Google style | 가독성, 자동 문서화 |

### 7.3 Environment Variables (v5.0 추가)

| Variable | Purpose | Scope | Required |
|----------|---------|-------|:--------:|
| `GROQ_API_KEY` | Groq API 인증 | Server | ☑ (v4.0 유지) |
| `ENABLE_NLP` | NLP 엔진 활성화 | Server | ☐ (default: true) |
| `ENABLE_COMPRESSION` | 압축 엔진 활성화 | Server | ☐ (default: true) |
| `COMPRESSION_LEVEL` | 압축 강도 (1-3) | Server | ☐ (default: 2) |
| `MODEL_PATH` | ML 모델 경로 | Server | ☐ (default: ./models/) |

---

## 8. Implementation Roadmap

### 8.1 Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| W1-2 | Setup | spaCy, transformers 설치 및 테스트 |
| W3-4 | FR-11 | 의도 파악 엔진 개발 |
| W5-6 | FR-12 | 우선순위 알고리즘 개발 |
| W7-8 | FR-13 | 텍스트 청킹 개발 |
| W9-10 | FR-14 | 압축 엔진 개발 |
| W11-12 | FR-15 | 번역 최적화 |
| W13-14 | Integration | GUI/Web UI 통합 |
| W15-16 | Testing | 단위 테스트, 벤치마크 |

**Total: 16 weeks (2026 Q2)**

### 8.2 Dependencies

```
Week 1-2 (Setup)
   ├─→ Week 3-4 (Intent Detection)
   ├─→ Week 5-6 (Priority Ranking)
   ├─→ Week 7-8 (Text Chunking)
   └─→ Week 9-10 (Compression)
         └─→ Week 11-12 (Translation)
               └─→ Week 13-14 (Integration)
                     └─→ Week 15-16 (Testing)
```

---

## 9. Next Steps

1. [ ] Design 문서 작성 (`v5-enhancement.design.md`)
2. [ ] 기술 스택 환경 구축 (spaCy, transformers, scikit-learn)
3. [ ] FR-11부터 순차 구현
4. [ ] Gap Analysis 및 반복 개선

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-13 | Initial v5.0 enhancement plan | AI Development Team |
