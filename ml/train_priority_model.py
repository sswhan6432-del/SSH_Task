#!/usr/bin/env python3
"""
ML Model Training Script - LLM Router v5.0
Trains RandomForest models for task priority classification.

Usage:
    python ml/train_priority_model.py

Output:
    ml/priority_model.pkl (trained models + vectorizer)

Author: AI Development Team
Version: 5.0.0
Date: 2026-02-13
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from nlp.priority_ranker import PriorityRanker
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import mean_absolute_error, r2_score
    import numpy as np
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install dependencies:")
    print("  pip install -r requirements-v5.txt")
    sys.exit(1)


def load_training_data(file_path: str = "ml/training_data.json"):
    """
    Load training data from JSON file.

    Returns:
        List of dicts with 'text', 'urgency', 'importance'
    """
    path = Path(file_path)

    if not path.exists():
        print(f"❌ Training data not found: {file_path}")
        print("\nPlease create ml/training_data.json with format:")
        print('[{"text": "...", "urgency": 1-10, "importance": 1-10}, ...]')
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    print(f"✅ Loaded {len(data)} training samples from {file_path}")
    return data


def evaluate_model(ranker: PriorityRanker, data: list) -> dict:
    """
    Evaluate model performance using MAE and R² score.

    Args:
        ranker: Trained PriorityRanker instance
        data: Training data

    Returns:
        Dict with regression metrics (MAE, R²)
    """
    texts = [item["text"] for item in data]
    urgency_labels = [item["urgency"] for item in data]
    importance_labels = [item["importance"] for item in data]

    # Vectorize (sparse matrix for RandomForest)
    features = ranker.vectorizer.transform(texts)

    # Cross-validation scores (MAE - negative because sklearn minimizes)
    urgency_mae_scores = -cross_val_score(
        ranker._urgency_model,
        features,
        urgency_labels,
        cv=5,
        scoring='neg_mean_absolute_error'
    )

    importance_mae_scores = -cross_val_score(
        ranker._importance_model,
        features,
        importance_labels,
        cv=5,
        scoring='neg_mean_absolute_error'
    )

    # R² scores
    urgency_r2_scores = cross_val_score(
        ranker._urgency_model,
        features,
        urgency_labels,
        cv=5,
        scoring='r2'
    )

    importance_r2_scores = cross_val_score(
        ranker._importance_model,
        features,
        importance_labels,
        cv=5,
        scoring='r2'
    )

    return {
        "urgency_mae": float(np.mean(urgency_mae_scores)),
        "urgency_mae_std": float(np.std(urgency_mae_scores)),
        "urgency_r2": float(np.mean(urgency_r2_scores)),
        "urgency_r2_std": float(np.std(urgency_r2_scores)),
        "importance_mae": float(np.mean(importance_mae_scores)),
        "importance_mae_std": float(np.std(importance_mae_scores)),
        "importance_r2": float(np.mean(importance_r2_scores)),
        "importance_r2_std": float(np.std(importance_r2_scores)),
        "overall_mae": float((np.mean(urgency_mae_scores) + np.mean(importance_mae_scores)) / 2),
        "overall_r2": float((np.mean(urgency_r2_scores) + np.mean(importance_r2_scores)) / 2)
    }


def print_sample_predictions(ranker: PriorityRanker, test_cases: list):
    """
    Test the trained model with sample tasks.

    Args:
        ranker: Trained PriorityRanker instance
        test_cases: List of test task strings
    """
    print("\n" + "="*70)
    print("SAMPLE PREDICTIONS")
    print("="*70)

    scores = ranker.rank(test_cases)

    for score in scores:
        print(f"\n[{score.task_id}] {score.task_text[:60]}...")
        print(f"    Priority: {score.priority}/100")
        print(f"    Urgency: {score.urgency}/10 | Importance: {score.importance}/10")
        print(f"    Confidence: {score.ml_confidence:.2f}")


def main():
    """Main training workflow."""
    print("\n" + "="*70)
    print("LLM ROUTER v5.0 - ML MODEL TRAINING")
    print("="*70 + "\n")

    # 1. Load training data
    print("Step 1: Loading training data...")
    data = load_training_data()

    # Show data distribution
    urgencies = [item["urgency"] for item in data]
    importances = [item["importance"] for item in data]

    print(f"\nData Distribution:")
    print(f"  Urgency range: {min(urgencies)}-{max(urgencies)} (avg: {sum(urgencies)/len(urgencies):.1f})")
    print(f"  Importance range: {min(importances)}-{max(importances)} (avg: {sum(importances)/len(importances):.1f})")

    # 2. Create ranker and train
    print("\nStep 2: Training RandomForest models...")
    ranker = PriorityRanker()
    ranker.train(data)

    # 3. Evaluate regression performance
    print("\nStep 3: Evaluating regression model performance...")
    metrics = evaluate_model(ranker, data)

    print("\nCross-Validation Results (5-fold):")
    print(f"  Urgency MAE:       {metrics['urgency_mae']:.2f} (±{metrics['urgency_mae_std']:.2f})")
    print(f"  Urgency R²:        {metrics['urgency_r2']:.3f} (±{metrics['urgency_r2_std']:.3f})")
    print(f"  Importance MAE:    {metrics['importance_mae']:.2f} (±{metrics['importance_mae_std']:.2f})")
    print(f"  Importance R²:     {metrics['importance_r2']:.3f} (±{metrics['importance_r2_std']:.3f})")
    print(f"\n  Overall MAE:       {metrics['overall_mae']:.2f} (±1-2 오차)")
    print(f"  Overall R²:        {metrics['overall_r2']:.3f} ({metrics['overall_r2']*100:.1f}% variance explained)")

    # 4. Save model
    print("\nStep 4: Saving trained models...")
    ranker.save_model()

    # 5. Test with sample cases
    test_cases = [
        "Fix critical security bug in authentication",
        "Add new dashboard feature",
        "Update API documentation",
        "긴급: 결제 시스템 오류",
        "UI 색상 조정"
    ]

    print_sample_predictions(ranker, test_cases)

    # 6. Summary
    print("\n" + "="*70)
    print("✅ REGRESSION MODEL TRAINING COMPLETE")
    print("="*70)
    print(f"\nModel saved to: ml/priority_model.pkl")
    print(f"Training samples: {len(data)}")
    print(f"Overall MAE: {metrics['overall_mae']:.2f} (average ±{metrics['overall_mae']:.1f} error)")
    print(f"Overall R²: {metrics['overall_r2']:.3f} ({metrics['overall_r2']*100:.1f}% variance explained)")
    print("\n📊 Performance Interpretation:")
    print(f"  MAE {metrics['overall_mae']:.2f} = predictions typically off by ±{int(np.round(metrics['overall_mae']))} points")
    if metrics['overall_r2'] >= 0.7:
        print(f"  R² {metrics['overall_r2']:.3f} = Excellent model (explains {metrics['overall_r2']*100:.1f}% of variance)")
    elif metrics['overall_r2'] >= 0.5:
        print(f"  R² {metrics['overall_r2']:.3f} = Good model (explains {metrics['overall_r2']*100:.1f}% of variance)")
    else:
        print(f"  R² {metrics['overall_r2']:.3f} = Fair model (explains {metrics['overall_r2']*100:.1f}% of variance)")
    print("\nYou can now use the trained model in llm_router_v5.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
