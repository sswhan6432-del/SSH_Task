#!/usr/bin/env python3
"""
Intent Classifier Training Script - LLM Router v5.0
Trains LogisticRegression on sentence embeddings for intent classification.

Usage:
    python ml/train_intent_model.py

Input:
    ml/intent_training_data.json (labeled text-intent pairs)

Output:
    ml/intent_classifier.pkl (trained LogisticRegression model)

Author: AI Development Team
Version: 5.2.0
Date: 2026-02-23
"""

import json
import sys
import pickle
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import classification_report, accuracy_score
except ImportError as e:
    print(f"Import error: {e}")
    print("\nPlease install dependencies:")
    print("  pip install sentence-transformers scikit-learn")
    sys.exit(1)


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TRAINING_DATA_PATH = "ml/intent_training_data.json"
OUTPUT_PATH = "ml/intent_classifier.pkl"


def load_training_data(file_path: str = TRAINING_DATA_PATH) -> list:
    """Load labeled training data from JSON file."""
    path = Path(file_path)

    if not path.exists():
        print(f"Training data not found: {file_path}")
        print("\nPlease create ml/intent_training_data.json with format:")
        print('[{"text": "...", "intent": "analyze|implement|research"}, ...]')
        sys.exit(1)

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} training samples from {file_path}")
    return data


def check_distribution(data: list):
    """Print label distribution."""
    from collections import Counter
    labels = [item["intent"] for item in data]
    dist = Counter(labels)

    print("\nLabel Distribution:")
    for intent, count in sorted(dist.items()):
        pct = count / len(labels) * 100
        print(f"  {intent}: {count} ({pct:.1f}%)")

    # Warn if imbalanced
    min_count = min(dist.values())
    max_count = max(dist.values())
    if max_count > min_count * 2:
        print(f"\n  Warning: Imbalanced data (min={min_count}, max={max_count})")
        print("  LogisticRegression(class_weight='balanced') will compensate.")


def encode_texts(texts: list, model_name: str = MODEL_NAME) -> np.ndarray:
    """Encode all texts using SentenceTransformer."""
    print(f"\nLoading model: {model_name}")

    # Use MPS if available
    device = "cpu"
    try:
        import torch
        if torch.backends.mps.is_available():
            device = "mps"
    except (ImportError, AttributeError):
        pass

    model = SentenceTransformer(model_name, device=device)
    print(f"Model loaded on device: {device}")

    print(f"Encoding {len(texts)} texts...")
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    print(f"Embeddings shape: {embeddings.shape}")

    return embeddings


def train_and_evaluate(embeddings: np.ndarray, labels: list) -> LogisticRegression:
    """Train LogisticRegression with stratified 5-fold cross-validation."""
    print("\nTraining LogisticRegression...")

    clf = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight='balanced',
        solver='lbfgs',
        random_state=42
    )

    # Stratified 5-fold cross-validation
    labels_array = np.array(labels)
    n_splits = min(5, min(np.bincount(np.unique(labels_array, return_inverse=True)[1])))
    if n_splits < 2:
        print(f"  Warning: Too few samples for CV (min class size < 2). Training without CV.")
        clf.fit(embeddings, labels)
        return clf

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_pred = cross_val_predict(clf, embeddings, labels_array, cv=skf)

    # Metrics
    accuracy = accuracy_score(labels_array, y_pred)
    print(f"\n{n_splits}-Fold Cross-Validation Results:")
    print(f"  Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"\nClassification Report:")
    print(classification_report(labels_array, y_pred, digits=3))

    # Train final model on all data
    clf.fit(embeddings, labels_array)
    print("Final model trained on all data.")

    return clf


def test_predictions(clf: LogisticRegression, model_name: str = MODEL_NAME):
    """Test with sample inputs to verify model behavior."""
    test_cases = [
        ("Review the code quality in auth.py", "analyze"),
        ("Build a new user login feature", "implement"),
        ("Find all files related to authentication", "research"),
        ("이 코드 좀 봐줘", "analyze"),
        ("로그인 기능 만들어줘", "implement"),
        ("이 모듈이 뭐하는 건지 알려줘", "research"),
        ("How does this work and can we improve it?", "research"),
        ("auth.py 에서 뭔가 이상해", "analyze"),
    ]

    print("\nSample Predictions:")
    print("-" * 70)

    # Use MPS if available
    device = "cpu"
    try:
        import torch
        if torch.backends.mps.is_available():
            device = "mps"
    except (ImportError, AttributeError):
        pass

    model = SentenceTransformer(model_name, device=device)

    correct = 0
    for text, expected in test_cases:
        embedding = model.encode(text, normalize_embeddings=True)
        proba = clf.predict_proba([embedding])[0]
        classes = clf.classes_
        pred_idx = np.argmax(proba)
        predicted = classes[pred_idx]
        conf = proba[pred_idx]

        match = "OK" if predicted == expected else "MISS"
        if predicted == expected:
            correct += 1

        scores = " | ".join(f"{c}={p:.3f}" for c, p in zip(classes, proba))
        print(f"  [{match}] {text[:50]:<50} -> {predicted} ({conf:.3f})")
        print(f"        Expected: {expected} | Scores: {scores}")

    print(f"\nSample accuracy: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.0f}%)")


def main():
    """Main training workflow."""
    print("\n" + "=" * 70)
    print("LLM ROUTER v5.0 - INTENT CLASSIFIER TRAINING")
    print("=" * 70)

    # 1. Load data
    print("\nStep 1: Loading training data...")
    data = load_training_data()
    check_distribution(data)

    texts = [item["text"] for item in data]
    labels = [item["intent"] for item in data]

    # 2. Encode
    print("\nStep 2: Encoding texts with SentenceTransformer...")
    embeddings = encode_texts(texts)

    # 3. Train + evaluate
    print("\nStep 3: Training and evaluating...")
    clf = train_and_evaluate(embeddings, labels)

    # 4. Save
    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        pickle.dump(clf, f)
    print(f"\nStep 4: Model saved to {OUTPUT_PATH}")

    # 5. Test predictions
    print("\nStep 5: Testing sample predictions...")
    test_predictions(clf)

    # Summary
    print("\n" + "=" * 70)
    print("INTENT CLASSIFIER TRAINING COMPLETE")
    print("=" * 70)
    print(f"\n  Model: {MODEL_NAME}")
    print(f"  Training samples: {len(data)}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"\nNext steps:")
    print(f"  1. Run: python3 tests/test_intent.py")
    print(f"  2. The intent_detector.py will auto-load the classifier")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTraining failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
