---
template: design
version: 1.0
description: LLM Router v5.0 Core Enhancement Design Document
variables:
  - feature: v5-enhancement (LLM Router v5.0)
  - date: 2026-02-13
  - author: AI Development Team
  - project: LLM Router
  - version: 5.0
---

# LLM Router v5.0 Core Enhancement Design Document

> **Summary**: NLP/ML-powered intelligent task routing with 50% token reduction
>
> **Project**: LLM Router v5.0 (Core Enhancement)
> **Version**: 5.0
> **Author**: AI Development Team
> **Date**: 2026-02-13
> **Status**: Draft
> **Planning Doc**: [v5-enhancement.plan.md](../01-plan/features/v5-enhancement.plan.md)
> **Base Version**: v4.0 (tools feature - Match Rate 90.6%)

---

## 1. Overview

### 1.1 Design Goals

v5.0 설계는 다음 기술 목표를 달성합니다:

1. **토큰 효율성**: 프롬프트 압축으로 평균 50% 토큰 절감
2. **지능형 분석**: NLP/ML 기반 의도 파악 및 우선순위 자동 판단
3. **성능 유지**: NLP 처리 추가에도 응답 시간 3초 이내
4. **하위 호환성**: v4.0 CLI 플래그 및 API 100% 호환
5. **모듈성**: v4.0 코드 변경 없이 독립 모듈로 추가

### 1.2 Design Principles

- **Progressive Enhancement**: v4.0 기능 유지, v5.0 기능은 옵션
- **Fail-Safe Fallback**: NLP/ML 실패 시 v4.0 로직으로 자동 전환
- **Lazy Loading**: 모델은 필요 시 로딩 (초기 부하 최소화)
- **Cache-First**: 반복 작업 캐싱으로 성능 최적화
- **Separation of Concerns**: NLP, ML, 압축 각각 독립 모듈

---

## 2. Architecture

### 2.1 Enhanced Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    User Interfaces (v4.0 유지)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────┐         │
│  │   CLI    │   │   GUI    │   │      Web UI          │         │
│  │  (v4.0)  │   │  (v5.0)  │   │     (v5.0)           │         │
│  └────┬─────┘   └────┬─────┘   └──────────┬───────────┘         │
│       │              │                     │                     │
│       └──────────────┼─────────────────────┘                     │
│                      │                                           │
├──────────────────────┼───────────────────────────────────────────┤
│                      ▼                                           │
│          ┌────────────────────────┐                              │
│          │  Router Orchestrator   │  (NEW in v5.0)               │
│          │  - Version detection   │                              │
│          │  - Feature toggling    │                              │
│          │  - Fallback handling   │                              │
│          └────────────┬───────────┘                              │
│                       │                                          │
│          ┌────────────┴────────────┐                             │
│          │                         │                             │
│          ▼                         ▼                             │
│  ┌───────────────┐         ┌──────────────┐                     │
│  │ v4.0 Engine   │         │ v5.0 Engine  │   (NEW)              │
│  │ (llm_router)  │         │ (enhanced)   │                      │
│  └───────────────┘         └──────┬───────┘                     │
│                                    │                             │
│                     ┌──────────────┼──────────────┐              │
│                     │              │              │              │
│                     ▼              ▼              ▼              │
│             ┌────────────┐  ┌───────────┐  ┌──────────┐         │
│             │    NLP     │  │    ML     │  │Compression│         │
│             │  Module    │  │  Module   │  │  Engine   │         │
│             └─────┬──────┘  └─────┬─────┘  └─────┬────┘         │
│                   │               │              │              │
│                   └───────────────┼──────────────┘              │
│                                   │                             │
│                                   ▼                             │
│                        ┌─────────────────────┐                  │
│                        │  Groq API (번역)     │                  │
│                        └─────────────────────┘                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow (v5.0)

```
1. Input Phase
   User Request (Korean/English)
   ↓
   Router Orchestrator (v4 vs v5 선택)
   ↓
   NLP Preprocessing (spaCy tokenization, normalization)
   ↓
   ┌─────────────────────────────────────────┐
   │  Parallel Processing (비동기)           │
   ├─────────────────────────────────────────┤
   │  Thread 1: Intent Detection (BERT)      │
   │  Thread 2: Priority Ranking (ML)        │
   │  Thread 3: Text Chunking (NLP)          │
   └─────────────────────────────────────────┘
   ↓
   Task List + Metadata

2. Optimization Phase
   ↓
   Compression Engine (각 task별 압축)
   ↓
   Token Counter (압축 전/후 비교)
   ↓
   Optimized Tasks (50% 토큰 절감)

3. Output Phase
   ↓
   Translation (Groq API v2, 배치 처리)
   ↓
   Claude Prompt Generation
   ↓
   Clipboard / stdout
```

### 2.3 Module Dependencies

| Module | Depends On | External Libs |
|--------|-----------|---------------|
| `nlp/intent_detector.py` | spaCy, transformers | spacy, transformers, torch |
| `nlp/priority_ranker.py` | scikit-learn | sklearn, numpy |
| `nlp/text_chunker.py` | spaCy | spacy |
| `nlp/compressor.py` | transformers, tiktoken | transformers, tiktoken |
| `llm_router_v5.py` | All NLP modules | All above + v4.0 |
| `router_gui.py` (v5) | llm_router_v5.py | tkinter (unchanged) |
| `web_server.py` (v5) | router_gui.py | http.server (unchanged) |

---

## 3. Data Model

### 3.1 Enhanced Entities (v5.0)

#### IntentAnalysis (NEW)

```python
@dataclass
class IntentAnalysis:
    original_text: str                # 원문
    intent: str                       # "analyze" | "implement" | "research"
    confidence: float                 # 0.0-1.0
    keywords: List[str]               # 추출된 핵심 키워드
    embeddings: Optional[np.ndarray]  # BERT embeddings (캐싱용)
```

#### PriorityScore (NEW)

```python
@dataclass
class PriorityScore:
    task_id: str                      # "A", "B", "C", ...
    urgency: int                      # 1-10 (긴급도)
    importance: int                   # 1-10 (중요도)
    priority: int                     # urgency * importance / 10
    dependencies: List[str]           # 의존 task IDs ["B", "C"]
    parallel_safe: bool               # 병렬 처리 가능 여부
    ml_confidence: float              # ML 모델 신뢰도
```

#### CompressionResult (NEW)

```python
@dataclass
class CompressionResult:
    original: str                     # 압축 전 텍스트
    compressed: str                   # 압축 후 텍스트
    original_tokens: int              # 압축 전 토큰 수
    compressed_tokens: int            # 압축 후 토큰 수
    reduction_rate: float             # 절감률 (0.0-1.0)
    compression_level: int            # 1-3 (압축 강도)
    lost_info: List[str]              # 제거된 정보 목록
```

#### EnhancedTaskDecision (v5.0 확장)

```python
@dataclass
class EnhancedTaskDecision(TaskDecision):  # v4.0 TaskDecision 상속
    # v4.0 필드 유지
    id: str
    summary: str
    route: str                        # v5.0: "analyze" | "implement" | "research"
    confidence: float                 # v5.0: ML-based (not fixed 0.95)
    priority: int                     # v5.0: ML-based (not order-based)
    reasons: List[str]
    claude_prompt: str
    next_session_starter: str
    change_log_stub: str

    # v5.0 추가 필드
    intent_analysis: IntentAnalysis   # NEW
    priority_score: PriorityScore     # NEW
    compression_result: CompressionResult  # NEW
    processing_time_ms: float         # 처리 시간 (성능 모니터링)
```

### 3.2 Model Files (Serialization)

```python
# ml/priority_model.pkl
{
    "model": sklearn.RandomForestClassifier,
    "feature_names": ["urgency_keywords", "importance_keywords", "length", "complexity"],
    "version": "1.0",
    "trained_on": "2026-02-13",
    "accuracy": 0.92
}

# nlp/term_dictionary.json
{
    "en_to_ko": {
        "implement": "구현",
        "refactor": "리팩토링",
        ...
    },
    "ko_to_en": {
        "구현": "implement",
        "리팩토링": "refactor",
        ...
    }
}

# nlp/cache.json (런타임 캐시)
{
    "embeddings": {
        "hash_of_text": np.array(...),  # BERT embeddings
        ...
    },
    "intents": {
        "hash_of_text": "implement",
        ...
    }
}
```

---

## 4. API Specification

### 4.1 CLI Interface (v5.0 확장)

```bash
# v4.0 플래그 (100% 호환)
python3 llm_router.py "요청" --friendly --economy balanced

# v5.0 새 플래그
python3 llm_router.py "요청" \
  --v5                        # v5.0 엔진 활성화 (default: auto-detect)
  --compress                  # 압축 엔진 활성화 (default: true if v5)
  --compression-level 2       # 압축 강도 1-3 (default: 2)
  --intent-detect             # 의도 파악 활성화 (default: true if v5)
  --smart-priority            # ML 우선순위 활성화 (default: true if v5)
  --show-stats                # 토큰 절감률, 처리 시간 표시
  --fallback-v4               # 에러 시 v4.0으로 폴백 (default: true)
  --no-cache                  # 캐싱 비활성화 (default: false)
```

### 4.2 Python API (v5.0)

```python
from llm_router_v5 import EnhancedRouter

router = EnhancedRouter(
    enable_nlp=True,
    enable_compression=True,
    compression_level=2,
    fallback_to_v4=True,
    model_path="./models/"
)

# 라우팅 실행
result = router.route(
    request="사용자 요청 텍스트",
    economy="balanced",
    friendly=True
)

# result: EnhancedRouterOutput
print(f"Token reduction: {result.token_reduction_rate:.1%}")
print(f"Processing time: {result.processing_time_ms}ms")

for task in result.tasks:
    print(f"{task.id}: {task.intent_analysis.intent} (priority: {task.priority})")
    print(f"  Original: {task.compression_result.original_tokens} tokens")
    print(f"  Compressed: {task.compression_result.compressed_tokens} tokens")
```

### 4.3 Web API (v5.0 확장)

**POST /api/route** (v4.0과 동일, v5 파라미터 추가)

```json
{
  "router": "/path/to/llm_router_v5.py",
  "request": "사용자 요청",
  "v5_enabled": true,
  "compress": true,
  "compression_level": 2,
  "intent_detect": true,
  "smart_priority": true,
  "show_stats": true
}
```

**Response (v5.0 확장):**

```json
{
  "output": "Full router output",
  "tickets": ["A", "B", "C"],
  "translate_status": "ok",
  "error": null,
  "v5_stats": {
    "enabled": true,
    "token_reduction_rate": 0.52,
    "original_tokens": 1000,
    "compressed_tokens": 480,
    "processing_time_ms": 2800,
    "intent_accuracy": 0.95,
    "priority_confidence": 0.92
  }
}
```

---

## 5. Module Design

### 5.1 NLP Module (`nlp/`)

#### intent_detector.py

```python
class IntentDetector:
    """BERT 기반 사용자 의도 파악 엔진"""

    def __init__(self, model_path: str = "./models/bert_lightweight/"):
        self.model = BertForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.cache = {}

    def detect(self, text: str) -> IntentAnalysis:
        """
        텍스트에서 의도 추출

        Returns:
            IntentAnalysis(
                intent="analyze"|"implement"|"research",
                confidence=0.0-1.0,
                keywords=["keyword1", ...]
            )
        """
        # 1. 캐시 확인
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 2. BERT inference
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        logits = outputs.logits
        predicted_class = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1).max().item()

        # 3. 의도 매핑
        intent_map = {0: "analyze", 1: "implement", 2: "research"}
        intent = intent_map[predicted_class]

        # 4. 키워드 추출 (TF-IDF)
        keywords = self._extract_keywords(text)

        result = IntentAnalysis(
            original_text=text,
            intent=intent,
            confidence=confidence,
            keywords=keywords,
            embeddings=outputs.last_hidden_state.mean(dim=1).detach().numpy()
        )

        # 5. 캐싱
        self.cache[cache_key] = result
        return result
```

#### priority_ranker.py

```python
class PriorityRanker:
    """ML 기반 우선순위 판단"""

    def __init__(self, model_path: str = "./ml/priority_model.pkl"):
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

    def rank(self, tasks: List[str], intent_analyses: List[IntentAnalysis]) -> List[PriorityScore]:
        """
        작업 목록의 우선순위 계산

        Returns:
            List[PriorityScore] (우선순위 높은 순 정렬)
        """
        scores = []

        for i, (task, intent) in enumerate(zip(tasks, intent_analyses)):
            # 1. 특징 추출
            features = self._extract_features(task, intent)

            # 2. ML 예측
            urgency = int(self.model.predict([features["urgency_features"]])[0])
            importance = int(self.model.predict([features["importance_features"]])[0])
            priority = urgency * importance // 10

            # 3. 의존성 분석
            dependencies = self._analyze_dependencies(task, tasks)

            # 4. 병렬 처리 가능 여부
            parallel_safe = len(dependencies) == 0

            scores.append(PriorityScore(
                task_id=chr(65 + i),  # A, B, C, ...
                urgency=urgency,
                importance=importance,
                priority=priority,
                dependencies=dependencies,
                parallel_safe=parallel_safe,
                ml_confidence=self.model.predict_proba([features])[0].max()
            ))

        # 의존성 기반 재정렬
        return self._topological_sort(scores)
```

#### text_chunker.py

```python
class TextChunker:
    """의미 기반 텍스트 분리 및 재합성"""

    def __init__(self):
        self.nlp = spacy.load("ko_core_news_sm")  # 또는 en_core_web_sm

    def chunk(self, text: str) -> List[str]:
        """
        의미 단위로 텍스트 분리

        Returns:
            List[chunk1, chunk2, ...]
        """
        # 1. spaCy 문장 분리
        doc = self.nlp(text)
        sentences = [sent.text for sent in doc.sents]

        # 2. 의미 유사도 계산 (sentence embeddings)
        embeddings = [sent.vector for sent in doc.sents]

        # 3. 유사한 문장 그룹핑
        chunks = self._cluster_by_similarity(sentences, embeddings)

        # 4. 중복 제거
        chunks = self._deduplicate(chunks)

        return chunks

    def merge(self, chunks: List[str]) -> List[str]:
        """
        관련 청크 병합
        """
        merged = []
        i = 0
        while i < len(chunks):
            if i + 1 < len(chunks) and self._should_merge(chunks[i], chunks[i+1]):
                merged.append(chunks[i] + " " + chunks[i+1])
                i += 2
            else:
                merged.append(chunks[i])
                i += 1
        return merged
```

#### compressor.py

```python
class PromptCompressor:
    """프롬프트 압축 엔진 (토큰 50% 절감)"""

    def __init__(self, compression_level: int = 2):
        self.level = compression_level  # 1: mild, 2: balanced, 3: aggressive
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer

    def compress(self, text: str) -> CompressionResult:
        """
        텍스트 압축

        Compression strategies:
        - Level 1: 조사 제거, 중복 제거
        - Level 2: 부사/접속사 제거, 문장 단순화
        - Level 3: 핵심 키워드만 추출, 명령형 변환
        """
        original_tokens = len(self.tokenizer.encode(text))

        # 1. 기본 정규화
        compressed = self._normalize(text)

        # 2. 레벨별 압축
        if self.level >= 1:
            compressed = self._remove_particles(compressed)  # 조사 제거
            compressed = self._deduplicate_words(compressed)  # 중복 제거

        if self.level >= 2:
            compressed = self._remove_adverbs(compressed)  # 부사 제거
            compressed = self._simplify_sentences(compressed)  # 문장 단순화

        if self.level >= 3:
            compressed = self._extract_keywords_only(compressed)  # 키워드만
            compressed = self._to_imperative(compressed)  # 명령형 변환

        compressed_tokens = len(self.tokenizer.encode(compressed))
        reduction_rate = 1.0 - (compressed_tokens / original_tokens)

        return CompressionResult(
            original=text,
            compressed=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_rate=reduction_rate,
            compression_level=self.level,
            lost_info=self._track_removed_info(text, compressed)
        )

    def _remove_particles(self, text: str) -> str:
        """한국어 조사 제거 (은/는/이/가/을/를/...)"""
        # spaCy POS tagging
        doc = self.nlp(text)
        return " ".join([token.text for token in doc if token.pos_ not in ["ADP", "PART"]])
```

### 5.2 ML Module (`ml/`)

#### training_script.py (모델 훈련)

```python
def train_priority_model():
    """우선순위 판단 모델 훈련"""

    # 1. 훈련 데이터 로드
    with open("training_data.json") as f:
        data = json.load(f)

    # 2. 특징 추출
    X = extract_features(data["tasks"])
    y_urgency = data["urgency_labels"]
    y_importance = data["importance_labels"]

    # 3. 모델 훈련 (RandomForest)
    model_urgency = RandomForestClassifier(n_estimators=100)
    model_urgency.fit(X, y_urgency)

    model_importance = RandomForestClassifier(n_estimators=100)
    model_importance.fit(X, y_importance)

    # 4. 모델 저장
    with open("priority_model.pkl", "wb") as f:
        pickle.dump({
            "urgency": model_urgency,
            "importance": model_importance,
            "feature_names": FEATURE_NAMES,
            "version": "1.0",
            "accuracy": calculate_accuracy(model_urgency, X, y_urgency)
        }, f)
```

---

## 6. Integration Strategy

### 6.1 v4.0과의 통합

```python
# llm_router_v5.py
class RouterOrchestrator:
    """v4.0 vs v5.0 선택 및 폴백"""

    def route(self, request: str, **kwargs) -> RouterOutput:
        v5_enabled = kwargs.get("v5_enabled", True)
        fallback_to_v4 = kwargs.get("fallback_to_v4", True)

        # 1. v5.0 시도
        if v5_enabled:
            try:
                return self._route_v5(request, **kwargs)
            except Exception as e:
                if fallback_to_v4:
                    logger.warning(f"v5.0 failed, falling back to v4.0: {e}")
                    return self._route_v4(request, **kwargs)
                else:
                    raise

        # 2. v4.0 모드
        return self._route_v4(request, **kwargs)

    def _route_v5(self, request: str, **kwargs) -> EnhancedRouterOutput:
        """v5.0 엔진 (NLP/ML 활성화)"""
        # NLP preprocessing
        preprocessed = self.nlp_preprocessor.process(request)

        # Parallel processing
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_intent = executor.submit(self.intent_detector.detect, preprocessed)
            future_priority = executor.submit(self.priority_ranker.rank, preprocessed)
            future_chunks = executor.submit(self.text_chunker.chunk, preprocessed)

        intent = future_intent.result()
        priority = future_priority.result()
        chunks = future_chunks.result()

        # Compression
        compressed_chunks = [self.compressor.compress(chunk) for chunk in chunks]

        # ...

    def _route_v4(self, request: str, **kwargs) -> RouterOutput:
        """v4.0 엔진 (기존 로직)"""
        import llm_router as v4
        return v4.route_request(request, **kwargs)
```

### 6.2 모델 로딩 전략 (Lazy Loading)

```python
class LazyModelLoader:
    """모델을 필요할 때만 로딩"""

    def __init__(self):
        self._intent_model = None
        self._priority_model = None
        self._spacy_model = None

    @property
    def intent_model(self):
        if self._intent_model is None:
            logger.info("Loading intent detection model...")
            self._intent_model = load_intent_model()
        return self._intent_model

    # 동일하게 다른 모델들도...
```

---

## 7. Error Handling

### 7.1 Fallback Strategy

| Error Type | v5.0 Behavior | Fallback |
|------------|---------------|----------|
| Model not found | Warning + v4.0 mode | v4.0 engine |
| BERT inference failure | Skip intent detection | Use keyword-based (v4.0) |
| ML prediction error | Skip priority ranking | Use order-based (v4.0) |
| Compression error | Skip compression | Use original text |
| spaCy error | Skip NLP preprocessing | Simple split |

### 7.2 Error Response

```json
{
  "output": "...",
  "tickets": ["A", "B"],
  "error": null,
  "v5_stats": {
    "enabled": true,
    "fallback_occurred": true,
    "fallback_reason": "BERT model load failed",
    "modules_active": {
      "intent_detection": false,
      "priority_ranking": true,
      "compression": true
    }
  }
}
```

---

## 8. Testing

### 8.1 Unit Tests

```python
# tests/test_intent.py
def test_intent_detector_accuracy():
    detector = IntentDetector()

    test_cases = [
        ("코드 분석해줘", "analyze"),
        ("버그 수정해", "implement"),
        ("문서 찾아줘", "research"),
    ]

    correct = 0
    for text, expected in test_cases:
        result = detector.detect(text)
        if result.intent == expected:
            correct += 1

    accuracy = correct / len(test_cases)
    assert accuracy >= 0.90, f"Accuracy {accuracy} < 0.90"

# tests/test_compression.py
def test_compression_rate():
    compressor = PromptCompressor(level=2)

    text = "이 코드를 자세히 분석해주시고, 문제점을 찾아서 알려주세요. 그리고 개선 방안도 제시해주세요."
    result = compressor.compress(text)

    assert result.reduction_rate >= 0.40, f"Reduction {result.reduction_rate} < 0.40"
    assert len(result.compressed) > 0, "Compressed text is empty"
```

### 8.2 Benchmark Tests

```python
# benchmarks/token_efficiency.py
def benchmark_token_reduction():
    """100개 샘플로 평균 토큰 절감률 측정"""

    samples = load_test_samples(100)
    results = []

    for sample in samples:
        router = EnhancedRouter(compression_level=2)
        output = router.route(sample)
        results.append(output.v5_stats["token_reduction_rate"])

    avg_reduction = sum(results) / len(results)
    assert avg_reduction >= 0.50, f"Average reduction {avg_reduction} < 0.50"

    print(f"✅ Token reduction: {avg_reduction:.1%} (target: 50%+)")
```

---

## 9. Performance Optimization

### 9.1 Caching Strategy

```python
class CacheManager:
    """다단계 캐싱"""

    def __init__(self):
        self.memory_cache = {}  # 메모리 캐시 (세션 내)
        self.disk_cache_path = "./nlp/cache.json"  # 디스크 캐시 (영구)

    def get_embedding(self, text_hash: str) -> Optional[np.ndarray]:
        # 1. 메모리 캐시 확인
        if text_hash in self.memory_cache:
            return self.memory_cache[text_hash]

        # 2. 디스크 캐시 확인
        disk_cache = self._load_disk_cache()
        if text_hash in disk_cache.get("embeddings", {}):
            emb = np.array(disk_cache["embeddings"][text_hash])
            self.memory_cache[text_hash] = emb  # 메모리에도 로드
            return emb

        return None

    def set_embedding(self, text_hash: str, embedding: np.ndarray):
        self.memory_cache[text_hash] = embedding
        self._append_to_disk_cache("embeddings", text_hash, embedding.tolist())
```

### 9.2 Async Processing

```python
async def route_async(request: str) -> EnhancedRouterOutput:
    """비동기 라우팅 (GUI/Web에서 사용)"""

    loop = asyncio.get_event_loop()

    # 병렬 작업
    intent_task = loop.run_in_executor(None, intent_detector.detect, request)
    priority_task = loop.run_in_executor(None, priority_ranker.rank, request)
    chunk_task = loop.run_in_executor(None, text_chunker.chunk, request)

    intent, priority, chunks = await asyncio.gather(intent_task, priority_task, chunk_task)

    # ...
```

---

## 10. Implementation Order

### 10.1 Phase 1: Core NLP/ML (Week 1-10)

```
Week 1-2: Environment Setup
  ├─ Install spaCy, transformers, scikit-learn, tiktoken
  ├─ Download Korean spaCy model (ko_core_news_sm)
  └─ Setup project structure (nlp/, ml/, models/)

Week 3-4: Intent Detection (FR-11)
  ├─ intent_detector.py implementation
  ├─ BERT model fine-tuning (100 samples)
  └─ Unit tests (>= 90% accuracy)

Week 5-6: Priority Ranking (FR-12)
  ├─ priority_ranker.py implementation
  ├─ Training data collection (50 samples)
  ├─ ML model training (RandomForest)
  └─ Unit tests

Week 7-8: Text Chunking (FR-13)
  ├─ text_chunker.py implementation
  ├─ Similarity clustering algorithm
  └─ Unit tests

Week 9-10: Compression Engine (FR-14)
  ├─ compressor.py implementation
  ├─ Multi-level compression (1-3)
  ├─ Token counter integration
  └─ Unit tests (>= 50% reduction)
```

### 10.2 Phase 2: Integration (Week 11-14)

```
Week 11-12: Router Integration
  ├─ llm_router_v5.py main engine
  ├─ RouterOrchestrator (v4/v5 switching)
  ├─ Fallback logic
  └─ Integration tests

Week 13-14: UI Updates
  ├─ router_gui.py v5.0 features
  ├─ web_server.py API extensions
  ├─ website/ stats display
  └─ E2E tests
```

### 10.3 Phase 3: Testing (Week 15-16)

```
Week 15: Benchmark & Optimization
  ├─ Token efficiency benchmark (100 samples)
  ├─ Performance profiling (응답 시간 < 3초)
  ├─ Caching optimization
  └─ Memory usage optimization

Week 16: User Testing & Documentation
  ├─ User testing (5 non-developers)
  ├─ Documentation update
  ├─ Gap Analysis
  └─ Final release
```

---

## 11. Known Limitations

### 11.1 v5.0 Limitations

1. **Korean-only NLP**: 현재 한국어 모델만 지원 (영어는 v4.0 폴백)
2. **Local Models**: 클라우드 배포 시 모델 크기 문제 (향후 개선)
3. **Training Data**: 초기 훈련 데이터 100건으로 한정 (지속 학습 필요)
4. **Compression Loss**: 압축 레벨 3에서 의미 손실 가능성
5. **Dependency Size**: transformers 설치 시 ~2GB 추가

### 11.2 Future Improvements (v6.0+)

- [ ] 다국어 지원 (영어, 일본어, 중국어)
- [ ] 클라우드 모델 서빙 (API 기반)
- [ ] 지속 학습 (사용자 피드백 반영)
- [ ] GPU 가속 (CUDA 지원)
- [ ] 압축 품질 자동 조절

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-13 | Initial v5.0 design document | AI Development Team |
