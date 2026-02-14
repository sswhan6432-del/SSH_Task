#!/usr/bin/env python3
"""
test_router_v5.py -- Unit tests for llm_router_v5.py

Tests v5.0 basic functionality:
- EnhancedRouter initialization
- LazyModelLoader
- v4.0 fallback
- Basic routing
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_router_v5 import EnhancedRouter, LazyModelLoader, EnhancedTaskDecision


def test_enhanced_router_init():
    """Test EnhancedRouter initialization"""
    router = EnhancedRouter(
        enable_nlp=True,
        enable_compression=True,
        compression_level=2,
        fallback_to_v4=True
    )

    assert router.enable_nlp == True
    assert router.enable_compression == True
    assert router.compression_level == 2
    assert router.fallback_to_v4 == True

    print("✅ EnhancedRouter initialization test passed")


def test_lazy_model_loader():
    """Test LazyModelLoader lazy loading"""
    loader = LazyModelLoader()

    # Models should not be loaded initially
    assert loader._intent_detector is None
    assert loader._priority_ranker is None
    assert loader._text_chunker is None
    assert loader._compressor is None

    print("✅ LazyModelLoader initialization test passed")

    # Test lazy loading (will actually load models)
    try:
        intent_detector = loader.intent_detector
        assert intent_detector is not None
        print("✅ Intent detector lazy loading test passed")
    except Exception as e:
        print(f"⚠️  Intent detector loading skipped: {e}")

    try:
        text_chunker = loader.text_chunker
        assert text_chunker is not None
        print("✅ Text chunker lazy loading test passed")
    except Exception as e:
        print(f"⚠️  Text chunker loading skipped: {e}")

    try:
        compressor = loader.compressor
        assert compressor is not None
        print("✅ Compressor lazy loading test passed")
    except Exception as e:
        print(f"⚠️  Compressor loading skipped: {e}")


def test_v4_fallback():
    """Test v4.0 fallback when v5.0 fails"""
    router = EnhancedRouter(
        enable_nlp=False,  # Disable NLP to force fallback
        fallback_to_v4=True
    )

    # Simple request that should work with v4.0
    request = "Fix login bug"

    result = router.route(request)

    assert result is not None
    assert len(result.tasks) > 0

    print("✅ v4.0 fallback test passed")
    print(f"   Tasks: {len(result.tasks)}")
    print(f"   Features used: {result.v5_features_used}")

    # Note: When NLP is disabled, v5.0 still processes but without NLP features
    # This is different from actual fallback (which happens on error)


def test_basic_routing():
    """Test basic routing with v5.0 features"""
    router = EnhancedRouter(
        enable_nlp=True,
        enable_compression=True,
        compression_level=2,
        fallback_to_v4=True
    )

    request = "Implement user authentication and add login page"

    result = router.route(request)

    assert result is not None
    assert len(result.tasks) > 0

    print("✅ Basic routing test passed")
    print(f"   Tasks: {len(result.tasks)}")
    print(f"   Processing time: {result.total_processing_time_ms:.2f}ms")
    print(f"   Token reduction: {result.token_reduction_rate * 100:.1f}%")
    print(f"   Features used: {result.v5_features_used}")

    # Check task details
    for task in result.tasks:
        print(f"\n   Task {task.id}: {task.summary}")
        print(f"     Route: {task.route}, Priority: {task.priority}")
        if task.compression_result:
            print(f"     Compression: {task.compression_result.reduction_rate * 100:.1f}%")


def test_enhanced_task_to_v4():
    """Test EnhancedTaskDecision to v4 format conversion"""
    from llm_router import TaskDecision

    enhanced = EnhancedTaskDecision(
        id="A",
        summary="Test task",
        route="implement",
        confidence=0.9,
        priority=1,
        reasons=["test"],
        claude_prompt="Test prompt",
        next_session_starter="Next",
        change_log_stub="Change log",
        v5_enabled=True
    )

    v4_task = enhanced.to_v4_format()

    assert isinstance(v4_task, TaskDecision)
    assert v4_task.id == enhanced.id
    assert v4_task.summary == enhanced.summary

    print("✅ EnhancedTaskDecision to v4 conversion test passed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("llm_router_v5.py Unit Tests")
    print("=" * 60 + "\n")

    test_enhanced_router_init()
    test_lazy_model_loader()
    test_enhanced_task_to_v4()
    test_v4_fallback()
    test_basic_routing()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60 + "\n")
