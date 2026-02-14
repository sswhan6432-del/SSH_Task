#!/usr/bin/env python3
"""Unit tests for nlp/compressor.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.compressor import Compressor, CompressionResult


def test_compression_rate_level1():
    """Test compression rate >= 10% for level 1"""
    compressor = Compressor()
    text = """Please implement a new user authentication function for the application.
    The function should validate user credentials and return the authentication status.
    As soon as possible, we need to add this feature to the database configuration.
    For example, the authentication module should check if the user has the proper authorization."""
    result = compressor.compress(text, level=1)

    assert result.reduction_rate >= 0.10, f"Level 1 reduction {result.reduction_rate:.2%} < 10%"
    assert len(result.compressed) > 0, "Compressed text is empty"
    print(f"✓ Level 1 compression: {result.reduction_rate:.2%} reduction")


def test_compression_rate_level2():
    """Test compression rate >= 20% for level 2"""
    compressor = Compressor()
    text = """Please implement a new user authentication function for the application.
    The function should validate user credentials and return the authentication status.
    As soon as possible, we need to add this feature to the database configuration.
    For example, the authentication module should check if the user has the proper authorization."""
    result = compressor.compress(text, level=2)

    assert result.reduction_rate >= 0.20, f"Level 2 reduction {result.reduction_rate:.2%} < 20%"
    print(f"✓ Level 2 compression: {result.reduction_rate:.2%} reduction")


def test_compression_rate_level3():
    """Test compression rate >= 30% for level 3"""
    compressor = Compressor()
    text = """Please implement a new user authentication function for the application.
    The function should validate user credentials and return the authentication status.
    As soon as possible, we need to add this feature to the database configuration.
    For example, the authentication module should check if the user has the proper authorization."""
    result = compressor.compress(text, level=3)

    assert result.reduction_rate >= 0.30, f"Level 3 reduction {result.reduction_rate:.2%} < 30%"
    print(f"✓ Level 3 compression: {result.reduction_rate:.2%} reduction")


def test_compression_result_fields():
    """Test CompressionResult has all required fields"""
    compressor = Compressor()
    result = compressor.compress("Test text")

    assert hasattr(result, 'original'), "Missing field: original"
    assert hasattr(result, 'compressed'), "Missing field: compressed"
    assert hasattr(result, 'original_tokens'), "Missing field: original_tokens"
    assert hasattr(result, 'compressed_tokens'), "Missing field: compressed_tokens"
    assert hasattr(result, 'reduction_rate'), "Missing field: reduction_rate"
    assert hasattr(result, 'compression_level'), "Missing field: compression_level"
    assert hasattr(result, 'lost_info'), "Missing field: lost_info"
    print("✓ All CompressionResult fields present")


def test_empty_text():
    """Test compression of empty text"""
    compressor = Compressor()
    result = compressor.compress("")

    assert result.original_tokens == 0, "Empty text should have 0 tokens"
    assert result.compressed_tokens == 0, "Empty compressed should have 0 tokens"
    assert result.reduction_rate == 0.0, "Empty text reduction should be 0"
    print("✓ Empty text handled correctly")


def test_batch_compression():
    """Test batch compression of multiple texts"""
    compressor = Compressor()
    texts = [
        "First text for compression test",
        "Second text for compression test",
        "Third text for compression test"
    ]
    results = compressor.batch_compress(texts, level=2)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert all(isinstance(r, CompressionResult) for r in results), "All results should be CompressionResult"
    print("✓ Batch compression works correctly")


if __name__ == "__main__":
    print("Testing Compression Module...")
    print("=" * 70)

    try:
        test_compression_rate_level1()
        test_compression_rate_level2()
        test_compression_rate_level3()
        test_compression_result_fields()
        test_empty_text()
        test_batch_compression()

        print("=" * 70)
        print("✅ All compression tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
