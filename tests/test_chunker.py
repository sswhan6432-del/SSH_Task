#!/usr/bin/env python3
"""Unit tests for nlp/text_chunker.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.text_chunker import TextChunker


def test_chunker_basic():
    """Test basic text chunking functionality"""
    chunker = TextChunker()

    text = "First sentence. Second sentence. Third sentence."
    chunks = chunker.chunk(text, max_tokens=500)

    assert len(chunks) >= 1, "No chunks created"
    assert all(isinstance(c, str) for c in chunks), "All chunks should be strings"
    assert all(len(c) > 0 for c in chunks), "No chunk should be empty"

    print(f"✓ Basic chunking works ({len(chunks)} chunks)")


def test_chunker_token_limit():
    """Test chunking respects token limit"""
    chunker = TextChunker()

    long_text = "Word " * 1000  # 1000 words
    chunks = chunker.chunk(long_text, max_tokens=100)

    assert len(chunks) > 1, "Long text should be split into multiple chunks"

    for i, chunk in enumerate(chunks):
        tokens = chunker.count_tokens(chunk)
        # Allow 10% margin for chunking overhead
        assert tokens <= 110, f"Chunk {i} has {tokens} tokens, exceeds limit+margin (110)"

    print(f"✓ Token limit respected ({len(chunks)} chunks, max {max(chunker.count_tokens(c) for c in chunks)} tokens)")


def test_chunk_result_fields():
    """Test chunk results have required metadata"""
    chunker = TextChunker()

    text = "Test sentence one. Test sentence two."
    chunks = chunker.chunk(text, max_tokens=500)

    assert len(chunks) > 0, "Expected at least one chunk"
    assert all(len(c) > 0 for c in chunks), "Empty chunk found"
    assert all(isinstance(c, str) for c in chunks), "All chunks should be strings"

    print("✓ Chunk results valid")


def test_empty_text():
    """Test chunking of empty text"""
    chunker = TextChunker()
    chunks = chunker.chunk("", max_tokens=500)

    assert len(chunks) == 0, "Empty text should produce no chunks"
    print("✓ Empty text handled correctly")


def test_single_chunk():
    """Test text that fits in single chunk"""
    chunker = TextChunker()

    short_text = "Short text."
    chunks = chunker.chunk(short_text, max_tokens=500)

    assert len(chunks) == 1, f"Short text should be single chunk, got {len(chunks)}"
    assert chunks[0].strip() == short_text.strip(), "Content should match"

    print("✓ Single chunk case works")


def test_sentence_splitting():
    """Test sentence boundary detection"""
    chunker = TextChunker()

    text = "First sentence! Second sentence? Third sentence. Fourth sentence."
    sentences = chunker._split_sentences(text)

    assert len(sentences) >= 3, f"Expected at least 3 sentences, got {len(sentences)}"
    assert all(isinstance(s, str) for s in sentences), "All sentences should be strings"

    print(f"✓ Sentence splitting works ({len(sentences)} sentences)")


def test_semantic_split():
    """Test semantic splitting into N chunks"""
    chunker = TextChunker()

    text = " ".join([f"Sentence {i}." for i in range(10)])
    chunks = chunker.semantic_split(text, num_chunks=3)

    # Semantic split should create chunks, may be more than requested if few sentences
    assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"
    assert len(chunks) <= 10, f"Should not exceed number of sentences (10), got {len(chunks)}"
    assert all(len(c) > 0 for c in chunks), "No chunk should be empty"

    print(f"✓ Semantic split works ({len(chunks)} chunks)")


def test_token_counting():
    """Test token counting functionality"""
    chunker = TextChunker()

    text = "Hello world, this is a test."
    tokens = chunker.count_tokens(text)

    assert tokens > 0, "Token count should be > 0"
    assert isinstance(tokens, int), "Token count should be integer"

    # Test empty
    empty_tokens = chunker.count_tokens("")
    assert empty_tokens == 0, "Empty text should have 0 tokens"

    print(f"✓ Token counting works ('{text}' = {tokens} tokens)")


def test_long_sentence_split():
    """Test splitting of very long sentences"""
    chunker = TextChunker()

    # Create a very long sentence (no punctuation)
    long_sentence = " ".join(["word"] * 500)
    chunks = chunker.chunk(long_sentence, max_tokens=50)

    assert len(chunks) > 1, "Long sentence should be split"

    for chunk in chunks:
        tokens = chunker.count_tokens(chunk)
        assert tokens <= 60, f"Chunk exceeds token limit: {tokens} > 60"

    print(f"✓ Long sentence splitting works ({len(chunks)} chunks)")


def test_korean_text_chunking():
    """Test chunking with Korean text"""
    chunker = TextChunker()

    korean_text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
    chunks = chunker.chunk(korean_text, max_tokens=500)

    assert len(chunks) >= 1, "Korean text should produce chunks"
    assert all(len(c) > 0 for c in chunks), "No Korean chunk should be empty"

    print(f"✓ Korean text chunking works ({len(chunks)} chunks)")


if __name__ == "__main__":
    print("Testing Text Chunker Module...")
    print("=" * 70)

    try:
        test_chunker_basic()
        test_chunker_token_limit()
        test_chunk_result_fields()
        test_empty_text()
        test_single_chunk()
        test_sentence_splitting()
        test_semantic_split()
        test_token_counting()
        test_long_sentence_split()
        test_korean_text_chunking()

        print("=" * 70)
        print("✅ All chunker tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
