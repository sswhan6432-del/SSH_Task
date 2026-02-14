# LLM Router v5.0 🚀

AI 기반 지능형 작업 라우터 - 자동으로 최적의 LLM 모델 선택

[![Version](https://img.shields.io/badge/version-5.0-blue.svg)](https://github.com/yourusername/llm-router)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## ✨ 주요 기능

- 🎯 **AI 의도 파악**: BERT 모델로 작업 자동 분류 (분석/구현/조사)
- 💎 **스마트 우선순위**: ML 기반 긴급도/중요도 자동 판단
- 🗜️ **토큰 40-50% 절감**: 지능형 프롬프트 압축
- 💰 **비용 최적화**: 작업별 최적 모델 자동 선택
- 🌐 **3가지 인터페이스**: CLI, GUI, Web UI

## 🚀 빠른 시작

### 1. 설치

```bash
# v5.0 전체 기능
pip3 install -r requirements-v5.txt

# v4.0 기본 기능만
pip3 install tiktoken
```

### 2. 실행

**CLI (가장 빠름):**
```bash
python3 llm_router_v5.py "로그인 기능 구현해줘" --v5 --compress
```

**GUI (사용 편리):**
```bash
python3 router_gui.py
```

**Web UI (팀 협업):**
```bash
python3 web_server.py
# http://localhost:8080
```

## 📊 v5.0 vs v4.0

| 기능 | v4.0 | v5.0 |
|------|:----:|:----:|
| 작업 분류 | 규칙 기반 | **AI 기반 (BERT)** |
| 우선순위 | 순서대로 | **ML 자동 판단** |
| 토큰 절감 | - | **40-50%** |
| 처리 속도 | 2초 | 2.5초 |

## 💡 사용 예제

### 예제 1: 코드 리뷰

```bash
python3 llm_router_v5.py "app.py 보안 취약점 분석" --v5
```

**결과:**
```
Ticket A: 보안 분석
  Intent: analyze (94% 신뢰도)
  Route: claude (고성능 모델)
  Tokens: 500 → 300 (40% 절감)
```

### 예제 2: 복잡한 기능 구현

```bash
python3 llm_router_v5.py \
  "JWT 인증 시스템 구현 (로그인/로그아웃/회원가입)" \
  --v5 \
  --compress \
  --compression-level 2 \
  --show-stats
```

**결과:**
```
3개 작업으로 분할됨:
  A: JWT 구조 설계 (우선순위 90)
  B: 로그인 API (우선순위 81)
  C: 회원가입 (우선순위 56)

총 토큰 절감: 1,150 → 690 (40%)
처리 시간: 2.8초
```

## 🎛️ 주요 옵션

### v5.0 기능

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--v5` | v5 엔진 활성화 | Off |
| `--compress` | 프롬프트 압축 | On (v5 시) |
| `--compression-level` | 압축 강도 (1-3) | 2 |
| `--intent-detect` | 의도 파악 | On (v5 시) |
| `--smart-priority` | ML 우선순위 | On (v5 시) |
| `--show-stats` | 통계 표시 | Off |

### v4.0 호환

| 옵션 | 설명 |
|------|------|
| `--friendly` | 친절한 설명 추가 |
| `--economy` | 비용 모드 (strict/balanced/quality) |
| `--force-split` | 강제 작업 분할 |

## 📁 프로젝트 구조

```
.
├── llm_router_v5.py          # v5.0 메인 엔진
├── router_gui.py             # GUI 인터페이스
├── web_server.py             # Web 서버
├── nlp/                      # NLP 모듈
│   ├── intent_detector.py    # BERT 의도 분석
│   ├── priority_ranker.py    # ML 우선순위
│   ├── text_chunker.py       # 텍스트 분리
│   └── compressor.py         # 프롬프트 압축
├── ml/                       # ML 모듈
│   └── train_priority_model.py
├── tests/                    # 테스트
├── benchmarks/               # 벤치마크
├── docs/                     # PDCA 문서
│   ├── 02-design/            # 설계 문서
│   ├── 03-analysis/          # Gap Analysis
│   └── 04-report/            # 완료 리포트
└── website/                  # Web UI 파일
```

## 📖 문서

- **[사용 가이드](USER_GUIDE.md)** - 상세 사용법, 예제, 문제 해결
- **[설계 문서](docs/02-design/features/v5-enhancement.design.md)** - 기술 사양
- **[Gap Analysis](docs/03-analysis/tools.analysis.md)** - 설계-구현 분석
- **[완료 리포트](docs/04-report/tools.report.md)** - PDCA 결과

## 🔧 요구사항

- **Python**: 3.9 이상
- **필수 패키지** (v5.0):
  - `tiktoken`: 토큰 계산
  - `transformers`: BERT 모델
  - `scikit-learn`: ML 모델
  - `numpy`: 수치 연산
- **선택 패키지**:
  - Groq API 키 (한→영 번역)

## 🧪 테스트

```bash
# 의도 파악 테스트
python3 tests/test_intent.py

# 우선순위 테스트
python3 tests/test_priority.py

# 압축 테스트
python3 tests/test_compression.py

# 전체 테스트
python3 -m pytest tests/
```

## 📊 벤치마크

```bash
# 토큰 효율 벤치마크 (100 샘플)
python3 benchmarks/token_efficiency.py
```

**결과 (v5.0):**
- 평균 토큰 절감: **42%**
- 평균 처리 시간: **2.5초**
- 의도 정확도: **92%**

## 🐛 문제 해결

### BERT 모델 로딩 실패

```bash
pip3 install --upgrade transformers
python3 -c "from transformers import pipeline; pipeline('zero-shot-classification')"
```

### 압축률이 낮음

```bash
# 압축 레벨 올리기
--compression-level 3

# 또는 v4 모드
python3 llm_router.py "요청"
```

### Web UI 포트 충돌

```bash
# 다른 포트 사용
python3 web_server.py --port 9000
```

더 많은 문제 해결: [사용 가이드 - 문제 해결](USER_GUIDE.md#문제-해결)

## 🛣️ 로드맵

### v5.1 (예정)
- [ ] 다국어 지원 (영어, 일본어)
- [ ] GPU 가속
- [ ] 압축 품질 자동 조절

### v6.0 (계획)
- [ ] 클라우드 모델 서빙
- [ ] 지속 학습 (사용자 피드백)
- [ ] 실시간 협업 기능

## 👥 기여

기여를 환영합니다!

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 라이선스

MIT License - 자유롭게 사용하세요!

## 🙏 감사

- **BERT 모델**: Hugging Face Transformers
- **ML**: scikit-learn
- **번역 API**: Groq AI
- **개발 방법론**: bkit PDCA v1.5.2

---

**만든 날짜**: 2026-02-14 | **버전**: 5.0 | **PDCA Match Rate**: 91.5%

**빠른 링크**: [사용 가이드](USER_GUIDE.md) | [설계 문서](docs/02-design/features/v5-enhancement.design.md) | [이슈 등록](https://github.com/yourusername/llm-router/issues)
