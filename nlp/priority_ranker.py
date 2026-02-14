"""
Priority Ranker - LLM Router v5.0
ML-based priority ranking for task scheduling.

Uses RandomForest to classify urgency and importance:
- Urgency: 1-10 (how soon it needs to be done)
- Importance: 1-10 (how critical it is)
- Priority: urgency * importance / 10

Author: AI Development Team
Version: 5.0.0
Date: 2026-02-13
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import json
from pathlib import Path
import re

try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    import pickle
except ImportError as e:
    raise ImportError(
        "Required packages not installed. Run: pip install scikit-learn numpy"
    ) from e


@dataclass
class PriorityScore:
    """Result of priority ranking."""
    task_id: str                      # "A", "B", "C", ...
    task_text: str                    # Original task description
    urgency: int                      # 1-10 (긴급도)
    importance: int                   # 1-10 (중요도)
    priority: int                     # urgency * importance / 10
    dependencies: List[str]           # 의존 task IDs ["B", "C"]
    parallel_safe: bool               # 병렬 처리 가능 여부
    ml_confidence: float              # ML 모델 신뢰도


class PriorityRanker:
    """
    ML-based priority classifier for task scheduling.

    Analyzes tasks and assigns:
    - Urgency: How soon it needs to be done (1-10)
    - Importance: How critical it is (1-10)
    - Dependencies: What tasks it depends on
    - Parallel safety: Can it run in parallel?

    Usage:
        ranker = PriorityRanker()
        tasks = ["Fix login bug", "Add new feature", "Update docs"]
        scores = ranker.rank(tasks)

        for score in scores:
            print(f"{score.task_id}: Priority {score.priority}")
    """

    # Urgency keywords (높은 긴급도 = 빠르게 처리 필요)
    URGENCY_HIGH = [
        "urgent", "asap", "immediately", "critical", "emergency", "bug", "fix",
        "broken", "crash", "down", "error", "failing", "blocker",
        "긴급", "즉시", "버그", "오류", "고장", "에러", "크리티컬"
    ]

    URGENCY_LOW = [
        "later", "eventually", "nice to have", "optional", "consider",
        "future", "someday", "maybe",
        "나중에", "여유", "선택", "고려", "미래"
    ]

    # Importance keywords (높은 중요도 = 비즈니스 가치 큼)
    IMPORTANCE_HIGH = [
        "security", "authentication", "payment", "data", "database",
        "critical", "core", "essential", "must", "required",
        "보안", "인증", "결제", "데이터", "핵심", "필수"
    ]

    IMPORTANCE_LOW = [
        "ui", "style", "cosmetic", "polish", "tweak", "minor",
        "documentation", "comment", "typo",
        "스타일", "문서", "주석", "오타", "사소"
    ]

    # Dependency patterns
    DEPENDENCY_PATTERNS = [
        r"after\s+([A-Z])",
        r"depends\s+on\s+([A-Z])",
        r"requires\s+([A-Z])",
        r"blocked\s+by\s+([A-Z])",
        r"다음에\s+([A-Z])",
        r"의존\s+([A-Z])"
    ]

    def __init__(self, model_path: str = "ml/priority_model.pkl"):
        """
        Initialize priority ranker.

        Args:
            model_path: Path to saved ML model (if exists)
        """
        self.model_path = Path(model_path)
        # Simple but effective: keep it minimal for small dataset
        self.vectorizer = TfidfVectorizer(max_features=100)

        # Try to load existing model
        self._urgency_model = None
        self._importance_model = None

        if self.model_path.exists():
            self._load_model()

    def rank(self, tasks: List[str]) -> List[PriorityScore]:
        """
        Rank multiple tasks by priority.

        Args:
            tasks: List of task descriptions

        Returns:
            List of PriorityScore sorted by priority (high to low)
        """
        scores = []

        for i, task in enumerate(tasks):
            task_id = chr(65 + i)  # A, B, C, ...

            # Analyze task
            urgency, urgency_conf = self._classify_urgency(task)
            importance, importance_conf = self._classify_importance(task)
            dependencies = self._extract_dependencies(task)
            parallel_safe = self._check_parallel_safety(task, dependencies)

            # Calculate priority
            priority = int(urgency * importance / 10)

            # Average confidence
            confidence = (urgency_conf + importance_conf) / 2

            scores.append(PriorityScore(
                task_id=task_id,
                task_text=task,
                urgency=urgency,
                importance=importance,
                priority=priority,
                dependencies=dependencies,
                parallel_safe=parallel_safe,
                ml_confidence=confidence
            ))

        # Sort by priority (high to low)
        scores.sort(key=lambda x: x.priority, reverse=True)

        return scores

    def _classify_urgency(self, text: str) -> Tuple[int, float]:
        """
        Classify urgency level (1-10).

        Args:
            text: Task description

        Returns:
            (urgency_score, confidence)
        """
        # Try ML model first
        if self._urgency_model is not None:
            try:
                features = self.vectorizer.transform([text])
                urgency_raw = self._urgency_model.predict(features)[0]

                # Clip to valid range [1, 10] and round
                urgency = int(np.clip(np.round(urgency_raw), 1, 10))

                # Calculate confidence based on how well prediction fits in range
                # Raw prediction closer to valid range = higher confidence
                if 1 <= urgency_raw <= 10:
                    confidence = 0.8  # Good prediction within range
                else:
                    # Penalize out-of-range predictions
                    distance = min(abs(urgency_raw - 1), abs(urgency_raw - 10))
                    confidence = max(0.3, 0.8 - distance * 0.1)

                return urgency, confidence
            except Exception as e:
                print(f"⚠️ ML urgency classification failed: {e}")

        # Fallback to keyword-based
        return self._classify_urgency_keywords(text)

    def _classify_urgency_keywords(self, text: str) -> Tuple[int, float]:
        """Keyword-based urgency classification."""
        text_lower = text.lower()

        high_matches = sum(1 for kw in self.URGENCY_HIGH if kw in text_lower)
        low_matches = sum(1 for kw in self.URGENCY_LOW if kw in text_lower)

        if high_matches > 0:
            urgency = min(10, 7 + high_matches)
            confidence = min(1.0, 0.6 + high_matches * 0.2)
        elif low_matches > 0:
            urgency = max(1, 4 - low_matches)
            confidence = min(1.0, 0.6 + low_matches * 0.2)
        else:
            # Default: medium urgency
            urgency = 5
            confidence = 0.4

        return urgency, confidence

    def _classify_importance(self, text: str) -> Tuple[int, float]:
        """
        Classify importance level (1-10).

        Args:
            text: Task description

        Returns:
            (importance_score, confidence)
        """
        # Try ML model first
        if self._importance_model is not None:
            try:
                features = self.vectorizer.transform([text])
                importance_raw = self._importance_model.predict(features)[0]

                # Clip to valid range [1, 10] and round
                importance = int(np.clip(np.round(importance_raw), 1, 10))

                # Calculate confidence based on how well prediction fits in range
                if 1 <= importance_raw <= 10:
                    confidence = 0.8  # Good prediction within range
                else:
                    # Penalize out-of-range predictions
                    distance = min(abs(importance_raw - 1), abs(importance_raw - 10))
                    confidence = max(0.3, 0.8 - distance * 0.1)

                return importance, confidence
            except Exception as e:
                print(f"⚠️ ML importance classification failed: {e}")

        # Fallback to keyword-based
        return self._classify_importance_keywords(text)

    def _classify_importance_keywords(self, text: str) -> Tuple[int, float]:
        """Keyword-based importance classification."""
        text_lower = text.lower()

        high_matches = sum(1 for kw in self.IMPORTANCE_HIGH if kw in text_lower)
        low_matches = sum(1 for kw in self.IMPORTANCE_LOW if kw in text_lower)

        if high_matches > 0:
            importance = min(10, 7 + high_matches)
            confidence = min(1.0, 0.6 + high_matches * 0.2)
        elif low_matches > 0:
            importance = max(1, 4 - low_matches)
            confidence = min(1.0, 0.6 + low_matches * 0.2)
        else:
            # Default: medium importance
            importance = 5
            confidence = 0.4

        return importance, confidence

    def _extract_dependencies(self, text: str) -> List[str]:
        """
        Extract task dependencies from text.

        Args:
            text: Task description

        Returns:
            List of task IDs this depends on
        """
        dependencies = []

        for pattern in self.DEPENDENCY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dependencies.extend(matches)

        return list(set(dependencies))  # Remove duplicates

    def _check_parallel_safety(self, text: str, dependencies: List[str]) -> bool:
        """
        Check if task can run in parallel.

        Args:
            text: Task description
            dependencies: List of dependency task IDs

        Returns:
            True if parallel-safe
        """
        # Not safe if has dependencies
        if dependencies:
            return False

        # Check for sequential keywords
        sequential_keywords = [
            "sequential", "order", "first", "then", "after",
            "순차", "순서", "먼저", "다음"
        ]

        text_lower = text.lower()
        has_sequential = any(kw in text_lower for kw in sequential_keywords)

        return not has_sequential

    def train(self, training_data: List[Dict]) -> None:
        """
        Train ML models on labeled data.

        Args:
            training_data: List of dicts with keys:
                - "text": task description
                - "urgency": 1-10
                - "importance": 1-10
        """
        if not training_data:
            print("⚠️ No training data provided")
            return

        texts = [item["text"] for item in training_data]
        urgency_labels = [item["urgency"] for item in training_data]
        importance_labels = [item["importance"] for item in training_data]

        # Vectorize texts
        features = self.vectorizer.fit_transform(texts)

        # Train urgency model (REGRESSION) - Simple works best for small datasets
        self._urgency_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self._urgency_model.fit(features, urgency_labels)

        # Train importance model (REGRESSION) - Simple works best for small datasets
        self._importance_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self._importance_model.fit(features, importance_labels)

        print(f"✅ Regression models trained on {len(training_data)} samples")

    def save_model(self) -> None:
        """Save trained models to disk."""
        if self._urgency_model is None or self._importance_model is None:
            print("⚠️ No models to save (train first)")
            return

        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "urgency_model": self._urgency_model,
            "importance_model": self._importance_model,
            "vectorizer": self.vectorizer
        }

        with open(self.model_path, "wb") as f:
            pickle.dump(model_data, f)

        print(f"✅ Models saved to {self.model_path}")

    def _load_model(self) -> None:
        """Load trained models from disk."""
        try:
            with open(self.model_path, "rb") as f:
                model_data = pickle.load(f)

            self._urgency_model = model_data["urgency_model"]
            self._importance_model = model_data["importance_model"]
            self.vectorizer = model_data["vectorizer"]

            print(f"✅ Models loaded from {self.model_path}")
        except Exception as e:
            print(f"⚠️ Failed to load models: {e}")


# Module-level convenience function
def rank_tasks(tasks: List[str]) -> List[PriorityScore]:
    """
    Convenience function for quick priority ranking.

    Usage:
        from nlp.priority_ranker import rank_tasks
        scores = rank_tasks(["Fix bug", "Add feature", "Update docs"])
        for score in scores:
            print(f"{score.task_id}: Priority {score.priority}")
    """
    ranker = PriorityRanker()
    return ranker.rank(tasks)


if __name__ == "__main__":
    # Quick test
    print("Testing Priority Ranker...")

    test_tasks = [
        "Fix critical security bug in authentication",
        "Add new dashboard feature",
        "Update documentation for API",
        "Polish UI styles",
        "Urgent: Payment processing is broken"
    ]

    ranker = PriorityRanker()
    scores = ranker.rank(test_tasks)

    print("\n" + "="*70)
    print("PRIORITY RANKING RESULTS")
    print("="*70)

    for score in scores:
        print(f"\n[{score.task_id}] Priority: {score.priority}/100")
        print(f"    Urgency: {score.urgency}/10 | Importance: {score.importance}/10")
        print(f"    Confidence: {score.ml_confidence:.2f}")
        print(f"    Parallel Safe: {score.parallel_safe}")
        print(f"    Task: {score.task_text}")
