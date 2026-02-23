"""
Intent Detector - LLM Router v5.0
Hybrid 3-layer classification: Sentence Embeddings + Classifier + Keywords.

Intent Categories:
- analyze: Code review, gap analysis, verification
- implement: Build features, write code, develop
- research: Search, explore, understand codebase

Architecture:
  Input -> [Cache] -> [Sentence Transformer] -> Score Fusion -> Result
                          |           |              |
                     Cosine(0.3) Classifier(0.5) Keyword(0.2)

Fallback chain:
  - No classifier: cosine(0.6) + keyword(0.4)
  - No model:      keyword-only (v5.0 behavior)

Author: AI Development Team
Version: 5.2.0
Date: 2026-02-23
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import json
import hashlib
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional ML dependencies
NLP_AVAILABLE = False
try:
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    logger.info("numpy not available, using keyword-only mode")
    np = None

# Sentence Transformer availability (separate from NLP_AVAILABLE)
EMBEDDING_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    logger.info("sentence-transformers not available, embedding features disabled")
    SentenceTransformer = None


@dataclass
class IntentAnalysis:
    """Result of intent detection."""
    original_text: str                # Original user request
    intent: str                       # "analyze" | "implement" | "research"
    confidence: float                 # 0.0-1.0
    keywords: List[str]               # Extracted key terms
    embeddings: Optional[object] = None  # For caching (future use)
    secondary_intent: Optional[str] = None  # Top-2 intent if gap < 0.1
    embedding_scores: Optional[Dict[str, float]] = None  # Debug scores


class EmbeddingIntentEngine:
    """
    Sentence embedding-based intent classification engine.

    Uses paraphrase-multilingual-MiniLM-L12-v2 for multilingual embeddings,
    cosine similarity against intent centroids, and optional LogisticRegression
    classifier for refined predictions.
    """

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(
        self,
        exemplar_path: str = "ml/intent_exemplars.json",
        classifier_path: str = "ml/intent_classifier.pkl",
        cache_manager=None
    ):
        self._model = None
        self._centroids: Optional[Dict[str, object]] = None
        self._classifier = None
        self._classifier_available = False
        self._cache_manager = cache_manager

        self._exemplar_path = Path(exemplar_path)
        self._classifier_path = Path(classifier_path)

        # Try to load classifier
        self._load_classifier()

    def _load_model(self):
        """Lazy load SentenceTransformer model with MPS support."""
        if self._model is not None:
            return

        if not EMBEDDING_AVAILABLE:
            raise RuntimeError("sentence-transformers not installed")

        logger.info("Loading SentenceTransformer: %s", self.MODEL_NAME)
        device = "mps" if self._check_mps() else "cpu"
        self._model = SentenceTransformer(self.MODEL_NAME, device=device)
        logger.info("Model loaded on device: %s", device)

        # Build centroids after model is loaded
        self._build_centroids()

    def _check_mps(self) -> bool:
        """Check if Apple MPS (Metal) is available."""
        try:
            import torch
            return torch.backends.mps.is_available()
        except (ImportError, AttributeError):
            return False

    def _load_classifier(self):
        """Load trained LogisticRegression classifier if available."""
        if not self._classifier_path.exists():
            logger.info("No trained classifier at %s", self._classifier_path)
            return

        try:
            with open(self._classifier_path, 'rb') as f:
                self._classifier = pickle.load(f)
            self._classifier_available = True
            logger.info("Loaded intent classifier from %s", self._classifier_path)
        except Exception as e:
            logger.warning("Failed to load classifier: %s", e)

    def _build_centroids(self):
        """Build intent centroid vectors from exemplar embeddings."""
        if not self._exemplar_path.exists():
            logger.warning("Exemplar file not found: %s", self._exemplar_path)
            return

        try:
            with open(self._exemplar_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._centroids = {}
            for intent, info in data["intents"].items():
                exemplars = info["exemplars"]
                embeddings = self._model.encode(exemplars, normalize_embeddings=True)
                centroid = np.mean(embeddings, axis=0)
                # L2 normalize the centroid
                centroid = centroid / np.linalg.norm(centroid)
                self._centroids[intent] = centroid

            logger.info("Built centroids for %d intents", len(self._centroids))
        except Exception as e:
            logger.warning("Failed to build centroids: %s", e)
            self._centroids = None

    def encode(self, text: str) -> Optional[object]:
        """
        Encode text to embedding vector with caching.

        Args:
            text: Input text

        Returns:
            Embedding numpy array or None
        """
        self._load_model()

        # Check cache first
        cache_key = f"emb:{self.MODEL_NAME}:{text}"
        if self._cache_manager:
            cached = self._cache_manager.get_embedding(cache_key)
            if cached is not None:
                return cached

        embedding = self._model.encode(text, normalize_embeddings=True)

        # Cache the embedding
        if self._cache_manager:
            self._cache_manager.set_embedding(cache_key, embedding)

        return embedding

    def cosine_similarity_scores(self, text: str) -> Dict[str, float]:
        """
        Compute cosine similarity between text and each intent centroid.

        Args:
            text: Input text

        Returns:
            Dict mapping intent name to similarity score (0.0-1.0)
        """
        if self._centroids is None:
            self._load_model()
            if self._centroids is None:
                return {}

        embedding = self.encode(text)
        if embedding is None:
            return {}

        scores = {}
        for intent, centroid in self._centroids.items():
            # Cosine similarity (both vectors are L2-normalized, so dot product = cosine)
            similarity = float(np.dot(embedding, centroid))
            # Clamp to [0, 1] range
            scores[intent] = max(0.0, min(1.0, similarity))

        return scores

    def classify(self, text: str) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Classify text using cosine similarity and optional classifier.

        Args:
            text: Input text

        Returns:
            Tuple of (cosine_scores, classifier_scores).
            classifier_scores is empty if no classifier is available.
        """
        cosine_scores = self.cosine_similarity_scores(text)

        classifier_scores = {}
        if self._classifier_available and self._classifier is not None:
            try:
                embedding = self.encode(text)
                if embedding is not None:
                    proba = self._classifier.predict_proba([embedding])[0]
                    classes = self._classifier.classes_
                    classifier_scores = {
                        cls: float(prob) for cls, prob in zip(classes, proba)
                    }
            except Exception as e:
                logger.warning("Classifier prediction failed: %s", e)

        return cosine_scores, classifier_scores

    @property
    def is_available(self) -> bool:
        """Check if embedding engine can be used."""
        return EMBEDDING_AVAILABLE


class IntentDetector:
    """
    Hybrid 3-layer intent classifier for LLM Router.

    Detection pipeline:
      1. Cache check (MD5 hash)
      2. Keyword scoring (existing logic)
      3. Embedding scoring (cosine + classifier)
      4. Score fusion with weighted combination

    Fusion weights:
      - Full hybrid: 0.1 * cosine + 0.5 * classifier + 0.4 * keyword
      - No classifier: 0.3 * cosine + 0.7 * keyword
      - No model: keyword-only (100%)

    Usage:
        detector = IntentDetector()
        result = detector.detect("Fix the login bug in auth.py")
        print(result.intent)  # "implement"
        print(result.confidence)  # 0.85
    """

    # Weighted intent keywords: (keyword, weight)
    INTENT_KEYWORDS: Dict[str, List[Tuple[str, float]]] = {
        "analyze": [
            ("review", 1.0), ("check", 1.0), ("verify", 1.0), ("validate", 1.0),
            ("analyze", 1.0), ("gap", 1.0), ("compare", 1.0), ("audit", 1.0),
            ("inspect", 1.0), ("test", 0.8), ("quality", 1.0),
            # Korean
            ("검토", 1.0), ("확인", 1.0), ("검증", 1.0), ("분석", 1.0),
            ("테스트", 0.8), ("품질", 1.0), ("봐줘", 1.0), ("봐봐", 1.0),
            ("살펴", 1.0), ("이상해", 1.0), ("문제", 0.8),
        ],
        "implement": [
            ("build", 1.0), ("create", 1.0), ("implement", 1.0), ("develop", 1.0),
            ("write", 0.8), ("add", 1.0), ("fix", 1.0), ("update", 1.0),
            ("modify", 1.0), ("refactor", 1.0), ("code", 0.5), ("feature", 0.8),
            # Korean
            ("구현", 1.0), ("개발", 1.0), ("작성", 1.0), ("추가", 1.0),
            ("수정", 1.0), ("코드", 0.5), ("기능", 0.8),
        ],
        "research": [
            ("search", 1.0), ("find", 1.0), ("explore", 1.0), ("understand", 1.0),
            ("learn", 1.0), ("discover", 1.0), ("investigate", 1.0), ("study", 1.0),
            ("read", 0.8), ("documentation", 1.0), ("explain", 1.0),
            # Korean
            ("검색", 1.0), ("찾기", 1.0), ("찾아", 1.0), ("이해", 1.0),
            ("학습", 1.0), ("조사", 1.0), ("문서", 1.0), ("설명", 1.0),
            ("알려", 1.0), ("뭐하는", 1.0), ("어떻게", 0.8), ("동작", 0.8),
        ]
    }

    # Bigram phrases for stronger signal
    BIGRAM_PHRASES: Dict[str, List[Tuple[str, float]]] = {
        "analyze": [
            ("code review", 2.0), ("gap analysis", 2.0), ("quality check", 2.0),
            ("test coverage", 1.5), ("design matches", 1.5),
            ("코드 리뷰", 2.0), ("품질 검사", 2.0), ("갭 분석", 2.0),
        ],
        "implement": [
            ("fix bug", 2.0), ("add feature", 2.0), ("write code", 2.0),
            ("build feature", 2.0), ("new feature", 1.5),
            ("버그 수정", 2.0), ("기능 추가", 2.0), ("기능 구현", 2.0),
        ],
        "research": [
            ("find files", 2.0), ("search for", 1.5), ("understand how", 1.5),
            ("explore the", 1.5), ("look for", 1.5),
            ("파일 찾기", 2.0), ("문서 찾", 2.0), ("구조 이해", 2.0),
        ]
    }

    def __init__(self, model_name: str = "distilbert-base-uncased", cache_dir: str = "models/"):
        """
        Initialize intent detector.

        Args:
            model_name: HuggingFace model name (for optional BERT fallback)
            cache_dir: Directory to cache downloaded models
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Lazy loading - BERT model loaded only when needed
        self._classifier = None

        # Result cache (memory + disk)
        self._memory_cache: Dict[str, IntentAnalysis] = {}
        self._cache_file = Path(__file__).parent / "cache.json"
        self._load_disk_cache()
        self._cache_hits = 0
        self._cache_misses = 0

        # Embedding engine (lazy init)
        self._embedding_engine: Optional[EmbeddingIntentEngine] = None

        logger.info("IntentDetector initialized (hybrid mode)")

    def _get_embedding_engine(self) -> Optional[EmbeddingIntentEngine]:
        """Lazy initialize embedding engine."""
        if self._embedding_engine is None and EMBEDDING_AVAILABLE:
            try:
                # Try to get cache_manager for embedding caching
                cache_mgr = None
                try:
                    from nlp.cache_manager import get_global_cache
                    cache_mgr = get_global_cache()
                except ImportError:
                    pass

                self._embedding_engine = EmbeddingIntentEngine(
                    cache_manager=cache_mgr
                )
            except Exception as e:
                logger.warning("Failed to initialize embedding engine: %s", e)
        return self._embedding_engine

    def detect(self, text: str) -> IntentAnalysis:
        """
        Detect intent from user text using hybrid 3-layer system.

        Pipeline: cache -> keyword scores -> embedding scores -> fusion -> result

        Args:
            text: User request text

        Returns:
            IntentAnalysis with detected intent and confidence
        """
        if not text or not text.strip():
            return IntentAnalysis(
                original_text=text,
                intent="research",
                confidence=0.0,
                keywords=[]
            )

        # Check cache first
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            logger.debug("Cache hit for: %s", text[:50])
            return self._memory_cache[cache_key]

        self._cache_misses += 1

        # Step 1: Keyword scoring (always available)
        keyword_scores = self._get_keyword_scores(text)
        keyword_intent, keyword_confidence = self._best_from_scores(keyword_scores)

        # Step 2: Embedding scoring (if available)
        cosine_scores: Dict[str, float] = {}
        classifier_scores: Dict[str, float] = {}
        embedding_engine = self._get_embedding_engine()

        if embedding_engine and embedding_engine.is_available:
            try:
                cosine_scores, classifier_scores = embedding_engine.classify(text)
            except Exception as e:
                logger.warning("Embedding classification failed: %s", e)

        # Step 3: Score fusion
        fused_scores = self._fuse_scores(keyword_scores, cosine_scores, classifier_scores)
        intent, confidence = self._best_from_scores(fused_scores)

        # Determine secondary intent
        secondary_intent = None
        sorted_intents = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_intents) >= 2:
            top_score = sorted_intents[0][1]
            second_score = sorted_intents[1][1]
            if top_score - second_score < 0.1:
                secondary_intent = sorted_intents[1][0]

        # Extract keywords
        keywords = self._extract_keywords(text)

        # Build combined embedding scores for debug
        debug_scores = None
        if cosine_scores or classifier_scores:
            debug_scores = {}
            for intent_name in ["analyze", "implement", "research"]:
                debug_scores[intent_name] = {
                    "cosine": round(cosine_scores.get(intent_name, 0.0), 4),
                    "classifier": round(classifier_scores.get(intent_name, 0.0), 4),
                    "keyword": round(keyword_scores.get(intent_name, 0.0), 4),
                    "fused": round(fused_scores.get(intent_name, 0.0), 4),
                }

        result = IntentAnalysis(
            original_text=text,
            intent=intent,
            confidence=confidence,
            keywords=keywords,
            secondary_intent=secondary_intent,
            embedding_scores=debug_scores
        )

        # Cache the result
        self._memory_cache[cache_key] = result
        self._save_disk_cache()

        logger.info("Detected intent=%s confidence=%.2f secondary=%s for: %s",
                     intent, confidence, secondary_intent, text[:80])

        return result

    def _get_keyword_scores(self, text: str) -> Dict[str, float]:
        """
        Compute normalized keyword scores for all intents.

        Returns:
            Dict mapping intent to normalized score (0.0-1.0)
        """
        text_lower = text.lower()
        raw_scores: Dict[str, float] = {"analyze": 0.0, "implement": 0.0, "research": 0.0}

        # Bigram phrase matching (strongest signal)
        for intent, phrases in self.BIGRAM_PHRASES.items():
            for phrase, weight in phrases:
                if phrase in text_lower:
                    raw_scores[intent] += weight

        # Keyword matching with weights
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword, weight in keywords:
                if keyword in text_lower:
                    if any(ord(c) > 127 for c in keyword):
                        # Korean keyword - substring match
                        raw_scores[intent] += weight
                    else:
                        # English keyword - check word boundaries
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, text_lower):
                            raw_scores[intent] += weight
                        elif keyword in text_lower:
                            raw_scores[intent] += weight * 0.5

        # Normalize with Laplace smoothing to prevent single-match dominance
        # Prior prevents a lone weak keyword (e.g., "코드" = 0.5) from scoring 1.0
        total = sum(raw_scores.values())
        if total == 0:
            return {"analyze": 0.33, "implement": 0.34, "research": 0.33}

        prior = 0.5
        denom = total + prior * len(raw_scores)
        return {
            intent: round((score + prior) / denom, 4)
            for intent, score in raw_scores.items()
        }

    def _fuse_scores(
        self,
        keyword_scores: Dict[str, float],
        cosine_scores: Dict[str, float],
        classifier_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Fuse scores from all three layers with weighted combination.

        Weights:
          - Full hybrid: 0.1 * cosine + 0.5 * classifier + 0.4 * keyword
          - No classifier: 0.3 * cosine + 0.7 * keyword
          - No model: keyword-only with calibration
        """
        intents = ["analyze", "implement", "research"]

        if cosine_scores and classifier_scores:
            # Full hybrid: cosine(0.1) + classifier(0.5) + keyword(0.4)
            fused = {}
            for intent in intents:
                score = (
                    0.1 * cosine_scores.get(intent, 0.0) +
                    0.5 * classifier_scores.get(intent, 0.0) +
                    0.4 * keyword_scores.get(intent, 0.0)
                )
                fused[intent] = score
            return fused

        elif cosine_scores:
            # Cosine + keyword: cosine(0.3) + keyword(0.7)
            fused = {}
            for intent in intents:
                score = (
                    0.3 * cosine_scores.get(intent, 0.0) +
                    0.7 * keyword_scores.get(intent, 0.0)
                )
                fused[intent] = score
            return fused

        else:
            # Keyword-only: calibrate to 0.5-1.0 range
            best_intent = max(keyword_scores, key=keyword_scores.get)
            best_raw = keyword_scores[best_intent]
            calibrated = {}
            for intent in intents:
                raw = keyword_scores.get(intent, 0.0)
                # Scale: highest keyword score maps to 0.5 + raw * 0.5
                calibrated[intent] = 0.5 * raw + (0.3 if intent == best_intent and best_raw > 0.4 else 0.0)
            return calibrated

    def _best_from_scores(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """Extract best intent and confidence from score dict."""
        if not scores:
            return "implement", 0.3

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Calibrate confidence to 0.0-1.0
        confidence = min(1.0, max(0.0, best_score))

        # For keyword-only mode, ensure minimum confidence
        if confidence < 0.3:
            confidence = 0.3

        return best_intent, round(confidence, 4)

    def _classify_with_keywords(self, text: str) -> Tuple[str, float]:
        """
        Primary keyword-based classification with weighted scoring.
        Kept for backward compatibility.

        Args:
            text: Input text

        Returns:
            (intent, confidence) tuple
        """
        scores = self._get_keyword_scores(text)
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Calibrate: map normalized score to 0.5-1.0 range
        # best_score is already Laplace-smoothed (range ~0.25-0.6+)
        confidence = 0.3 + best_score

        return best_intent, round(min(1.0, confidence), 4)

    def _load_disk_cache(self):
        """Load cached results from disk."""
        if not self._cache_file.exists():
            return

        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            for key, data in cache_data.items():
                self._memory_cache[key] = IntentAnalysis(
                    original_text=data.get("original_text", ""),
                    intent=data.get("intent", "research"),
                    confidence=data.get("confidence", 0.0),
                    keywords=data.get("keywords", [])
                )
            logger.info("Loaded %d entries from disk cache", len(cache_data))
        except Exception as e:
            logger.warning("Failed to load cache: %s", e)

    def _save_disk_cache(self):
        """Save cached results to disk."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {}
            for key, result in self._memory_cache.items():
                cache_data[key] = {
                    "original_text": result.original_text,
                    "intent": result.intent,
                    "confidence": result.confidence,
                    "keywords": result.keywords
                }

            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save cache: %s", e)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0.0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate": round(hit_rate, 1),
            "cache_size": len(self._memory_cache)
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from text.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        common_words = {
            "the", "and", "for", "with", "this", "that", "from", "have",
            "what", "when", "where", "which", "who", "how", "can", "will"
        }

        words = text.lower().split()
        keywords = [
            word.strip(".,!?;:")
            for word in words
            if len(word) > 3 and word.lower() not in common_words
        ]

        return list(dict.fromkeys(keywords))[:10]

    def batch_detect(self, texts: List[str]) -> List[IntentAnalysis]:
        """
        Detect intent for multiple texts.

        Args:
            texts: List of user requests

        Returns:
            List of IntentAnalysis results
        """
        return [self.detect(text) for text in texts]


# Module-level convenience function
def detect_intent(text: str) -> IntentAnalysis:
    """
    Convenience function for quick intent detection.

    Usage:
        from nlp.intent_detector import detect_intent
        result = detect_intent("Review the authentication code")
        print(result.intent)  # "analyze"
    """
    detector = IntentDetector()
    return detector.detect(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("Testing Intent Detector (Hybrid Mode)...")

    test_cases = [
        "Review the code quality in auth.py",
        "Build a new user login feature",
        "Find all files related to authentication",
        "Fix the bug in the router",
        "Check if the design matches implementation",
        "이 코드 좀 봐줘",
        "로그인 기능 만들어줘",
        "이 모듈이 뭐하는 건지 알려줘",
        "How does this work and can we improve it?",
        "auth.py 에서 뭔가 이상해",
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        secondary = f" (secondary: {result.secondary_intent})" if result.secondary_intent else ""
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f}){secondary}")
        print(f"Keywords: {', '.join(result.keywords[:5])}")
        if result.embedding_scores:
            for intent, scores in result.embedding_scores.items():
                print(f"  {intent}: cosine={scores['cosine']:.3f} "
                      f"classifier={scores['classifier']:.3f} "
                      f"keyword={scores['keyword']:.3f} "
                      f"fused={scores['fused']:.3f}")
