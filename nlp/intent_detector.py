"""
Intent Detector - LLM Router v5.0
Uses BERT-based classification to detect user intent.

Intent Categories:
- analyze: Code review, gap analysis, verification
- implement: Build features, write code, develop
- research: Search, explore, understand codebase

Author: AI Development Team
Version: 5.0.0
Date: 2026-02-13
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import json
from pathlib import Path

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import numpy as np
except ImportError as e:
    raise ImportError(
        "Required packages not installed. Run: pip install transformers numpy"
    ) from e


@dataclass
class IntentAnalysis:
    """Result of intent detection."""
    original_text: str                # Original user request
    intent: str                       # "analyze" | "implement" | "research"
    confidence: float                 # 0.0-1.0
    keywords: List[str]               # Extracted key terms
    embeddings: Optional[np.ndarray] = None  # For caching (future use)


class IntentDetector:
    """
    BERT-based intent classifier for LLM Router.

    Detects whether user wants to:
    - analyze: Review, verify, check code/design
    - implement: Build, develop, create features
    - research: Search, explore, understand

    Usage:
        detector = IntentDetector()
        result = detector.detect("Fix the login bug in auth.py")
        print(result.intent)  # "implement"
        print(result.confidence)  # 0.92
    """

    # Intent keywords for fallback classification
    INTENT_KEYWORDS = {
        "analyze": [
            "review", "check", "verify", "validate", "analyze", "gap",
            "compare", "audit", "inspect", "test", "quality",
            "검토", "확인", "검증", "분석", "테스트", "품질"
        ],
        "implement": [
            "build", "create", "implement", "develop", "write", "add",
            "fix", "update", "modify", "refactor", "code", "feature",
            "구현", "개발", "작성", "추가", "수정", "코드", "기능"
        ],
        "research": [
            "search", "find", "explore", "understand", "learn", "discover",
            "investigate", "study", "read", "documentation", "explain",
            "검색", "찾기", "이해", "학습", "조사", "문서", "설명"
        ]
    }

    def __init__(self, model_name: str = "distilbert-base-uncased", cache_dir: str = "models/"):
        """
        Initialize intent detector.

        Args:
            model_name: HuggingFace model name (default: distilbert for speed)
            cache_dir: Directory to cache downloaded models
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Lazy loading - models loaded on first use
        self._classifier = None
        self._tokenizer = None

        # Result cache (memory + disk)
        self._memory_cache = {}  # {text_hash: IntentAnalysis}
        self._cache_file = Path("nlp/cache.json")
        self._load_disk_cache()
        self._cache_hits = 0
        self._cache_misses = 0

    def _load_model(self):
        """Lazy load the BERT model (on first detect call)."""
        if self._classifier is None:
            print(f"Loading intent detection model: {self.model_name}...")
            # For now, use zero-shot classification as we don't have trained model yet
            # In production, this would be a fine-tuned model
            self._classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1  # CPU (-1), use 0 for GPU
            )
            print("✅ Model loaded successfully")

    def detect(self, text: str) -> IntentAnalysis:
        """
        Detect intent from user text.

        Args:
            text: User request text

        Returns:
            IntentAnalysis with detected intent and confidence
        """
        if not text or not text.strip():
            return IntentAnalysis(
                original_text=text,
                intent="research",  # Default to safest option
                confidence=0.0,
                keywords=[]
            )

        # Check cache first
        import hashlib
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            return self._memory_cache[cache_key]

        self._cache_misses += 1

        # Try ML-based detection
        try:
            self._load_model()
            intent, confidence = self._classify_with_bert(text)
        except Exception as e:
            print(f"⚠️ BERT classification failed: {e}")
            print("Falling back to keyword-based detection...")
            intent, confidence = self._classify_with_keywords(text)

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

        return result

    def _classify_with_bert(self, text: str) -> Tuple[str, float]:
        """
        Classify using BERT zero-shot classification.

        Args:
            text: Input text

        Returns:
            (intent, confidence) tuple
        """
        candidate_labels = ["analyze code", "implement feature", "research information"]

        result = self._classifier(text, candidate_labels)

        # Map back to our intent categories
        label_map = {
            "analyze code": "analyze",
            "implement feature": "implement",
            "research information": "research"
        }

        top_label = result["labels"][0]
        top_score = result["scores"][0]

        intent = label_map[top_label]

        return intent, float(top_score)

    def _classify_with_keywords(self, text: str) -> Tuple[str, float]:
        """
        Fallback keyword-based classification.

        Args:
            text: Input text

        Returns:
            (intent, confidence) tuple
        """
        text_lower = text.lower()

        # Count keyword matches for each intent
        scores = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[intent] = score

        # Find best match
        if max(scores.values()) == 0:
            # No keywords found - default to "implement" (most common)
            return "implement", 0.3

        best_intent = max(scores, key=scores.get)

        # Confidence based on keyword count (max 1.0)
        total_matches = sum(scores.values())
        confidence = min(scores[best_intent] / max(total_matches, 1), 1.0)

        return best_intent, confidence

    def _load_disk_cache(self):
        """Load cached results from disk."""
        if not self._cache_file.exists():
            return

        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Convert JSON to IntentAnalysis objects
            for key, data in cache_data.items():
                self._memory_cache[key] = IntentAnalysis(
                    original_text=data.get("original_text", ""),
                    intent=data.get("intent", "research"),
                    confidence=data.get("confidence", 0.0),
                    keywords=data.get("keywords", [])
                )
        except Exception as e:
            print(f"⚠️ Failed to load cache: {e}")

    def _save_disk_cache(self):
        """Save cached results to disk."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert IntentAnalysis to JSON-serializable dict
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
            print(f"⚠️ Failed to save cache: {e}")

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
        # Simple keyword extraction (words longer than 3 chars, not common words)
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

        # Return unique keywords (max 10)
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
    # Quick test
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
