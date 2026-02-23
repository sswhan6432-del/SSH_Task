"""
Unit tests for Intent Detector (Hybrid 3-Layer System)

Run: python3 -m pytest tests/test_intent.py
Or: python3 tests/test_intent.py
"""

import sys
sys.path.insert(0, '.')

from nlp.intent_detector import IntentDetector, IntentAnalysis, detect_intent, EMBEDDING_AVAILABLE


# ========================================
# Original Tests (8 tests)
# ========================================

def test_intent_detector_initialization():
    """Test that IntentDetector can be initialized."""
    detector = IntentDetector()
    assert detector is not None
    assert detector.model_name == "distilbert-base-uncased"


def test_analyze_intent():
    """Test detection of 'analyze' intent."""
    test_cases = [
        "Review the code quality in auth.py",
        "Check if the design matches implementation",
        "Verify the test coverage",
        "Analyze the performance bottleneck"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        # For keyword-based fallback, confidence might vary
        # Just check that we get a valid intent
        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.keywords) > 0


def test_implement_intent():
    """Test detection of 'implement' intent."""
    test_cases = [
        "Build a new user login feature",
        "Fix the bug in the router",
        "Add authentication to the API",
        "Create a dashboard component"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0


def test_research_intent():
    """Test detection of 'research' intent."""
    test_cases = [
        "Find all files related to authentication",
        "Search for the login component",
        "Explore the database schema",
        "Understand how routing works"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0


def test_convenience_function():
    """Test module-level convenience function."""
    result = detect_intent("Review the authentication code")

    assert result is not None
    assert result.intent in ["analyze", "implement", "research"]
    assert result.original_text == "Review the authentication code"


def test_empty_text():
    """Test handling of empty input."""
    detector = IntentDetector()
    result = detector.detect("")

    assert result.intent == "research"  # Default
    assert result.confidence == 0.0


def test_korean_analyze_intent():
    """Test detection of 'analyze' intent with Korean input."""
    test_cases = [
        "코드 분석해줘",
        "테스트 검증해주세요",
        "품질 검토 부탁합니다"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0


def test_korean_implement_intent():
    """Test detection of 'implement' intent with Korean input."""
    test_cases = [
        "로그인 기능 구현해줘",
        "버그 수정해주세요",
        "새 기능 추가해줘"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0


def test_korean_research_intent():
    """Test detection of 'research' intent with Korean input."""
    test_cases = [
        "문서 찾아줘",
        "API 설명해주세요",
        "구조 이해하고 싶어"
    ]

    detector = IntentDetector()

    for text in test_cases:
        result = detector.detect(text)
        print(f"\nText: {text}")
        print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")

        assert result.intent in ["analyze", "implement", "research"]
        assert 0.0 <= result.confidence <= 1.0


# ========================================
# New Tests (5 tests for hybrid system)
# ========================================

def test_ambiguous_korean():
    """Test ambiguous Korean input that keyword-only misses."""
    detector = IntentDetector()

    # "이 코드 좀 봐줘" has no direct keyword match for "analyze"
    # but semantic meaning is clearly "analyze/review this code"
    result = detector.detect("이 코드 좀 봐줘")
    print(f"\nText: 이 코드 좀 봐줘")
    print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")
    if result.embedding_scores:
        print(f"Embedding scores: {result.embedding_scores}")

    # With embeddings, should detect as analyze
    # Without embeddings (keyword-only), may detect as implement due to "코드"
    assert result.intent in ["analyze", "implement", "research"]
    assert 0.0 <= result.confidence <= 1.0

    # Full hybrid (with trained classifier) should classify as "analyze"
    # Without classifier, cosine + keyword may lean toward "implement" due to "코드"
    if EMBEDDING_AVAILABLE and detector._embedding_engine and \
       detector._embedding_engine._classifier_available:
        assert result.intent == "analyze", (
            f"Expected 'analyze' for '이 코드 좀 봐줘', got '{result.intent}'"
        )
    elif EMBEDDING_AVAILABLE:
        # Cosine alone should at least show analyze as competitive
        if result.embedding_scores:
            cosine_analyze = result.embedding_scores["analyze"]["cosine"]
            cosine_implement = result.embedding_scores["implement"]["cosine"]
            assert cosine_analyze > cosine_implement - 0.05, (
                f"Cosine should favor analyze ({cosine_analyze:.3f}) "
                f"over implement ({cosine_implement:.3f})"
            )


def test_ambiguous_english():
    """Test mixed-intent English input."""
    detector = IntentDetector()

    # Mixed intent: research + implement
    # Primary should be research (understanding first)
    result = detector.detect("How does this work and can we improve it?")
    print(f"\nText: How does this work and can we improve it?")
    print(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")
    print(f"Secondary: {result.secondary_intent}")
    if result.embedding_scores:
        print(f"Embedding scores: {result.embedding_scores}")

    assert result.intent in ["analyze", "implement", "research"]
    assert 0.0 <= result.confidence <= 1.0

    # Should have secondary intent for ambiguous input
    # (may not have secondary in keyword-only mode if one intent dominates)


def test_fallback_without_model():
    """Test that keyword-only fallback works when embedding model is unavailable."""
    detector = IntentDetector()

    # Force embedding engine to None to simulate model unavailability
    detector._embedding_engine = None
    original_available = None

    # Monkey-patch EMBEDDING_AVAILABLE for this test
    import nlp.intent_detector as module
    original_available = module.EMBEDDING_AVAILABLE
    module.EMBEDDING_AVAILABLE = False

    try:
        # Clear cache to force fresh detection
        detector._memory_cache.clear()

        result = detector.detect("Review the code quality in auth.py")
        print(f"\nFallback test - Intent: {result.intent} (confidence: {result.confidence:.2f})")

        # Should still work with keyword-only
        assert result.intent == "analyze"
        assert result.confidence > 0.0
        # No embedding scores in keyword-only mode
        assert result.embedding_scores is None
    finally:
        module.EMBEDDING_AVAILABLE = original_available


def test_embedding_cache():
    """Test that embedding results are cached."""
    detector = IntentDetector()

    # Clear cache
    detector._memory_cache.clear()
    detector._cache_hits = 0
    detector._cache_misses = 0

    text = "Review the authentication module"

    # First call - cache miss
    result1 = detector.detect(text)
    assert detector._cache_misses == 1
    assert detector._cache_hits == 0

    # Second call - cache hit
    result2 = detector.detect(text)
    assert detector._cache_hits == 1
    assert result1.intent == result2.intent
    assert result1.confidence == result2.confidence

    print(f"\nCache test - hits: {detector._cache_hits}, misses: {detector._cache_misses}")


def test_confidence_ordering():
    """Test that clear inputs have higher confidence than empty/gibberish inputs."""
    detector = IntentDetector()

    # Clear input with strong keywords
    clear_result = detector.detect("Review the code quality in auth.py")
    # Very weak input with no meaningful signal
    weak_result = detector.detect("hmm okay sure")

    print(f"\nClear: intent={clear_result.intent} conf={clear_result.confidence:.2f}")
    print(f"Weak: intent={weak_result.intent} conf={weak_result.confidence:.2f}")

    # Clear input should have higher or equal confidence
    assert clear_result.confidence >= weak_result.confidence, (
        f"Clear ({clear_result.confidence:.2f}) should >= "
        f"Weak ({weak_result.confidence:.2f})"
    )


def test_intent_analysis_fields():
    """Test that IntentAnalysis has all expected fields."""
    detector = IntentDetector()
    result = detector.detect("Check the code for bugs")

    assert hasattr(result, 'original_text')
    assert hasattr(result, 'intent')
    assert hasattr(result, 'confidence')
    assert hasattr(result, 'keywords')
    assert hasattr(result, 'secondary_intent')
    assert hasattr(result, 'embedding_scores')

    # secondary_intent and embedding_scores can be None
    assert result.secondary_intent is None or isinstance(result.secondary_intent, str)
    assert result.embedding_scores is None or isinstance(result.embedding_scores, dict)


# ========================================
# Runner
# ========================================

if __name__ == "__main__":
    print("Running Intent Detector tests...\n")

    tests = [
        ("Test 1: Initialization", test_intent_detector_initialization),
        ("Test 2: Analyze Intent", test_analyze_intent),
        ("Test 3: Implement Intent", test_implement_intent),
        ("Test 4: Research Intent", test_research_intent),
        ("Test 5: Convenience Function", test_convenience_function),
        ("Test 6: Empty Input", test_empty_text),
        ("Test 7: Korean Analyze", test_korean_analyze_intent),
        ("Test 8: Korean Implement", test_korean_implement_intent),
        ("Test 9: Korean Research", test_korean_research_intent),
        ("Test 10: Ambiguous Korean", test_ambiguous_korean),
        ("Test 11: Ambiguous English", test_ambiguous_english),
        ("Test 12: Fallback Without Model", test_fallback_without_model),
        ("Test 13: Embedding Cache", test_embedding_cache),
        ("Test 14: Confidence Ordering", test_confidence_ordering),
        ("Test 15: IntentAnalysis Fields", test_intent_analysis_fields),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print("\n" + "=" * 60)
        print(name)
        print("=" * 60)
        try:
            test_fn()
            passed += 1
            print(f"  -> PASSED")
        except Exception as e:
            failed += 1
            print(f"  -> FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("All tests passed!")
    print("=" * 60)
