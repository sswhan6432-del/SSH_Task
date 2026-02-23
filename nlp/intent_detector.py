"""
Intent Detector - LLM Router v5.0
Uses keyword-based classification (primary) with optional BERT fallback.

Intent Categories:
- analyze: Code review, gap analysis, verification
- implement: Build features, write code, develop
- research: Search, explore, understand codebase

Author: AI Development Team
Version: 5.1.0
Date: 2026-02-23
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional ML dependencies
NLP_AVAILABLE = False
try:
    from transformers import pipeline
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    logger.info("transformers not available, using keyword-only mode")
    np = None


@dataclass
class IntentAnalysis:
    """Result of intent detection."""
    original_text: str                # Original user request
    intent: str                       # "analyze" | "implement" | "research"
    confidence: float                 # 0.0-1.0
    keywords: List[str]               # Extracted key terms
    embeddings: Optional[object] = None  # For caching (future use)


class IntentDetector:
    """
    Keyword-primary intent classifier for LLM Router.

    Detection order: cache -> keywords -> (optional) BERT fallback
    Keywords are weighted with exact match (1.0) and partial match (0.5).
    BERT is only used when keyword confidence < 0.5.

    Detects whether user wants to:
    - analyze: Review, verify, check code/design
    - implement: Build, develop, create features
    - research: Search, explore, understand

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
            ("테스트", 0.8), ("품질", 1.0),
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

        logger.info("IntentDetector initialized (keyword-primary mode)")

    def _load_model(self):
        """Lazy load the BERT model (only when keyword confidence is low)."""
        if self._classifier is None and NLP_AVAILABLE:
            logger.info("Loading BERT fallback model: %s", self.model_name)
            try:
                self._classifier = pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    device=-1
                )
                logger.info("BERT model loaded successfully")
            except Exception as e:
                logger.warning("Failed to load BERT model: %s", e)

    def detect(self, text: str) -> IntentAnalysis:
        """
        Detect intent from user text.

        Order: cache -> keywords -> (if confidence < 0.5) BERT fallback

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

        # Primary: keyword-based detection
        intent, confidence = self._classify_with_keywords(text)
        logger.debug("Keyword result: intent=%s confidence=%.2f text=%s",
                      intent, confidence, text[:50])

        # Secondary: BERT fallback only when keyword confidence is low
        if confidence < 0.5 and NLP_AVAILABLE:
            try:
                self._load_model()
                if self._classifier is not None:
                    bert_intent, bert_confidence = self._classify_with_bert(text)
                    logger.debug("BERT result: intent=%s confidence=%.2f",
                                  bert_intent, bert_confidence)
                    # Use BERT result only if it's meaningfully better
                    if bert_confidence > confidence + 0.1:
                        intent, confidence = bert_intent, bert_confidence
            except Exception as e:
                logger.warning("BERT classification failed: %s", e)

        # Extract keywords
        keywords = self._extract_keywords(text)

        result = IntentAnalysis(
            original_text=text,
            intent=intent,
            confidence=confidence,
            keywords=keywords
        )

        # Cache the result
        self._memory_cache[cache_key] = result
        self._save_disk_cache()

        logger.info("Detected intent=%s confidence=%.2f for: %s",
                     intent, confidence, text[:80])

        return result

    def _classify_with_keywords(self, text: str) -> Tuple[str, float]:
        """
        Primary keyword-based classification with weighted scoring.

        Scores are calculated from:
        1. Bigram phrase matches (highest weight)
        2. Exact keyword matches (full weight)
        3. Partial keyword matches (half weight)

        Confidence is calibrated to 0.5-1.0 range.

        Args:
            text: Input text

        Returns:
            (intent, confidence) tuple
        """
        text_lower = text.lower()

        scores: Dict[str, float] = {"analyze": 0.0, "implement": 0.0, "research": 0.0}

        # 1. Bigram phrase matching (strongest signal)
        for intent, phrases in self.BIGRAM_PHRASES.items():
            for phrase, weight in phrases:
                if phrase in text_lower:
                    scores[intent] += weight

        # 2. Keyword matching with weights
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword, weight in keywords:
                if keyword in text_lower:
                    # Check for exact word boundary match
                    # For Korean, substring match is fine
                    if any(ord(c) > 127 for c in keyword):
                        # Korean keyword - substring match
                        scores[intent] += weight
                    else:
                        # English keyword - check word boundaries
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, text_lower):
                            scores[intent] += weight
                        elif keyword in text_lower:
                            scores[intent] += weight * 0.5  # Partial match

        # Find best match
        total_score = sum(scores.values())
        if total_score == 0:
            return "implement", 0.3  # Default

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Calibrate confidence: 0.5 + (best_score / total_score) * 0.5
        # This maps to 0.5-1.0 range
        confidence = 0.5 + (best_score / total_score) * 0.5

        return best_intent, round(confidence, 4)

    def _classify_with_bert(self, text: str) -> Tuple[str, float]:
        """
        BERT zero-shot classification (secondary fallback).

        Args:
            text: Input text

        Returns:
            (intent, confidence) tuple
        """
        candidate_labels = ["analyze code", "implement feature", "research information"]
        result = self._classifier(text, candidate_labels)

        label_map = {
            "analyze code": "analyze",
            "implement feature": "implement",
            "research information": "research"
        }

        top_label = result["labels"][0]
        top_score = result["scores"][0]

        return label_map[top_label], float(top_score)

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

    print("Testing Intent Detector...")

    test_cases = [
        "Review the code quality in auth.py",
        "Build a new user login feature",
        "Find all files related to authentication",
        "Fix the bug in the router",
        "Check if the design matches implementation"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")
        print(f"Keywords: {', '.join(result.keywords[:5])}")
