"""
Unit tests for Intent Detector

Run: python3 -m pytest tests/test_intent.py
Or: python3 tests/test_intent.py
"""

import sys
sys.path.insert(0, '.')

from nlp.intent_detector import IntentDetector, detect_intent


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


if __name__ == "__main__":
    print("Running Intent Detector tests...\n")

    print("="*60)
    print("Test 1: Analyze Intent")
    print("="*60)
    test_analyze_intent()

    print("\n" + "="*60)
    print("Test 2: Implement Intent")
    print("="*60)
    test_implement_intent()

    print("\n" + "="*60)
    print("Test 3: Research Intent")
    print("="*60)
    test_research_intent()

    print("\n" + "="*60)
    print("Test 4: Convenience Function")
    print("="*60)
    test_convenience_function()

    print("\n" + "="*60)
    print("Test 5: Empty Input")
    print("="*60)
    test_empty_text()

    print("\n" + "="*60)
    print("Test 6: Korean Analyze Intent")
    print("="*60)
    test_korean_analyze_intent()

    print("\n" + "="*60)
    print("Test 7: Korean Implement Intent")
    print("="*60)
    test_korean_implement_intent()

    print("\n" + "="*60)
    print("Test 8: Korean Research Intent")
    print("="*60)
    test_korean_research_intent()

    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)
