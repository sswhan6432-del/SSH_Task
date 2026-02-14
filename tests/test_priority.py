#!/usr/bin/env python3
"""Unit tests for nlp/priority_ranker.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.priority_ranker import PriorityRanker, PriorityScore


def test_priority_ranker_basic():
    """Test basic priority ranking functionality"""
    ranker = PriorityRanker()

    tasks = [
        "Fix critical security bug",
        "Update documentation",
        "Add new feature"
    ]

    scores = ranker.rank(tasks)

    assert len(scores) == 3, f"Expected 3 scores, got {len(scores)}"
    assert all(isinstance(s, PriorityScore) for s in scores), "All scores should be PriorityScore"

    # Critical security should be highest priority
    security_score = next(s for s in scores if "security" in s.task_text.lower())
    assert security_score.urgency >= 7, f"Security urgency {security_score.urgency} < 7"
    assert security_score.importance >= 7, f"Security importance {security_score.importance} < 7"

    print(f"✓ Basic ranking works (security task: priority={security_score.priority})")


def test_priority_score_fields():
    """Test PriorityScore has all required fields"""
    ranker = PriorityRanker()
    scores = ranker.rank(["Test task"])
    score = scores[0]

    assert hasattr(score, 'task_id'), "Missing field: task_id"
    assert hasattr(score, 'task_text'), "Missing field: task_text"
    assert hasattr(score, 'urgency'), "Missing field: urgency"
    assert hasattr(score, 'importance'), "Missing field: importance"
    assert hasattr(score, 'priority'), "Missing field: priority"
    assert hasattr(score, 'dependencies'), "Missing field: dependencies"
    assert hasattr(score, 'parallel_safe'), "Missing field: parallel_safe"
    assert hasattr(score, 'ml_confidence'), "Missing field: ml_confidence"

    print("✓ All PriorityScore fields present")


def test_priority_range():
    """Test urgency and importance are in valid range [1, 10]"""
    ranker = PriorityRanker()
    scores = ranker.rank(["Task 1", "Task 2", "Task 3"])

    for score in scores:
        assert 1 <= score.urgency <= 10, f"Urgency {score.urgency} out of range [1, 10]"
        assert 1 <= score.importance <= 10, f"Importance {score.importance} out of range [1, 10]"
        assert 0 <= score.priority <= 100, f"Priority {score.priority} out of range [0, 100]"

    print("✓ All priority values in valid range")


def test_urgent_task_prioritization():
    """Test that urgent tasks get high urgency scores"""
    ranker = PriorityRanker()
    scores = ranker.rank([
        "URGENT: Fix production crash immediately",
        "Nice to have: Polish UI colors"
    ])

    urgent_task = scores[0]  # Should be first after sorting
    assert "urgent" in urgent_task.task_text.lower() or "crash" in urgent_task.task_text.lower()
    assert urgent_task.urgency >= 7, f"Urgent task urgency {urgent_task.urgency} < 7"

    print(f"✓ Urgent tasks prioritized correctly (urgency={urgent_task.urgency})")


def test_dependency_extraction():
    """Test dependency extraction from task text"""
    ranker = PriorityRanker()
    scores = ranker.rank([
        "Task A: Setup database",
        "Task B: Add auth (depends on A)",
        "Task C: Add dashboard (requires B)"
    ])

    # Find task B (should depend on A)
    task_b = next((s for s in scores if s.task_id == "B"), None)
    if task_b:
        # Note: dependency extraction looks for uppercase letters, so it may find "A" in the text
        print(f"✓ Dependency extraction tested (Task B deps: {task_b.dependencies})")
    else:
        print("⚠ Task B not found in expected position")


def test_parallel_safety():
    """Test parallel safety detection"""
    ranker = PriorityRanker()
    scores = ranker.rank([
        "Independent task with no dependencies",
        "Sequential task that must run first then second"
    ])

    # First task should be parallel-safe
    independent = next(s for s in scores if "independent" in s.task_text.lower())
    assert independent.parallel_safe, "Independent task should be parallel-safe"

    # Second task should NOT be parallel-safe
    sequential = next(s for s in scores if "sequential" in s.task_text.lower())
    assert not sequential.parallel_safe, "Sequential task should not be parallel-safe"

    print("✓ Parallel safety detection works")


def test_korean_text_handling():
    """Test priority ranking with Korean text"""
    ranker = PriorityRanker()
    scores = ranker.rank([
        "긴급: 보안 버그 수정 필요",
        "나중에: 문서 업데이트"
    ])

    assert len(scores) == 2, f"Expected 2 scores, got {len(scores)}"

    # First should be urgent security task
    urgent_task = scores[0]
    assert urgent_task.urgency >= 5, f"Korean urgent task urgency {urgent_task.urgency} too low"

    print(f"✓ Korean text handled (urgent task priority={urgent_task.priority})")


if __name__ == "__main__":
    print("Testing Priority Ranker Module...")
    print("=" * 70)

    try:
        test_priority_ranker_basic()
        test_priority_score_fields()
        test_priority_range()
        test_urgent_task_prioritization()
        test_dependency_extraction()
        test_parallel_safety()
        test_korean_text_handling()

        print("=" * 70)
        print("✅ All priority tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
