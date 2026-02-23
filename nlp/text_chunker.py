"""
Text Chunker - LLM Router v5.0
Semantic text chunking without spaCy (simplified version).

Splits text into meaningful chunks based on:
- Sentence boundaries
- Token limits
- Semantic similarity (simple approach)

Author: AI Development Team
Version: 5.0.0
Date: 2026-02-13
"""

from typing import List, Dict
import re
from collections import Counter

try:
    import tiktoken
except ImportError as e:
    raise ImportError(
        "Required packages not installed. Run: pip install tiktoken"
    ) from e


class TextChunker:
    """
    Simple text chunker without spaCy dependency.

    Uses sentence splitting and token counting for chunking.
    Less sophisticated than spaCy but works without Python 3.14 issues.

    Usage:
        chunker = TextChunker()
        chunks = chunker.chunk("Long text here...", max_tokens=500)
    """

    # Sentence boundary patterns
    SENTENCE_ENDINGS = r'[.!?]+\s+'

    # Keep these together (don't split)
    KEEP_TOGETHER = [
        r'Mr\.',
        r'Mrs\.',
        r'Dr\.',
        r'e\.g\.',
        r'i\.e\.',
        r'etc\.',
    ]

    def __init__(self, encoding: str = "cl100k_base"):
        """
        Initialize text chunker.

        Args:
            encoding: tiktoken encoding name
        """
        self.encoding = tiktoken.get_encoding(encoding)

    def chunk(self, text: str, max_tokens: int = 500) -> List[str]:
        """
        Split text into chunks under token limit.

        Args:
            text: Input text to chunk
            max_tokens: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # Count total tokens
        total_tokens = self.count_tokens(text)

        # If under limit, return as single chunk
        if total_tokens <= max_tokens:
            return [text.strip()]

        # Split into sentences
        sentences = self._split_sentences(text)

        # Group sentences into chunks
        chunks = self._group_sentences(sentences, max_tokens)

        # Post-process: deduplicate and merge small chunks
        chunks = self._deduplicate(chunks)
        chunks = self.merge(chunks, max_tokens)

        return chunks

    def semantic_split(self, text: str, num_chunks: int = 3) -> List[str]:
        """
        Split text into approximately equal semantic chunks.

        Args:
            text: Input text
            num_chunks: Target number of chunks

        Returns:
            List of chunks
        """
        sentences = self._split_sentences(text)

        if len(sentences) <= num_chunks:
            return sentences

        # Calculate chunk size
        chunk_size = len(sentences) // num_chunks

        chunks = []
        current_chunk = []

        for i, sentence in enumerate(sentences):
            current_chunk.append(sentence)

            # Create chunk at boundaries
            if (i + 1) % chunk_size == 0 or i == len(sentences) - 1:
                chunks.append(' '.join(current_chunk))
                current_chunk = []

        return [c for c in chunks if c]  # Remove empty

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Input text

        Returns:
            Token count
        """
        if not text:
            return 0

        tokens = self.encoding.encode(text)
        return len(tokens)

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Protect abbreviations
        protected = text
        for pattern in self.KEEP_TOGETHER:
            protected = re.sub(pattern, pattern.replace('.', '<DOT>'), protected)

        # Split on sentence boundaries
        sentences = re.split(self.SENTENCE_ENDINGS, protected)

        # Restore dots and clean
        sentences = [
            s.replace('<DOT>', '.').strip()
            for s in sentences
            if s.strip()
        ]

        return sentences

    def _group_sentences(self, sentences: List[str], max_tokens: int) -> List[str]:
        """
        Group sentences into chunks under token limit.

        Args:
            sentences: List of sentences
            max_tokens: Maximum tokens per chunk

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds limit, split it
            if sentence_tokens > max_tokens:
                # Save current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by words
                chunks.extend(self._split_long_sentence(sentence, max_tokens))
                continue

            # Check if adding sentence exceeds limit
            if current_tokens + sentence_tokens > max_tokens:
                # Save current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                # Start new chunk
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _split_long_sentence(self, sentence: str, max_tokens: int) -> List[str]:
        """
        Split a very long sentence by words.

        Args:
            sentence: Long sentence
            max_tokens: Token limit

        Returns:
            List of chunks
        """
        words = sentence.split()
        chunks = []
        current_chunk = []
        current_tokens = 0

        for word in words:
            word_tokens = self.count_tokens(word)

            if current_tokens + word_tokens > max_tokens:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_tokens = word_tokens
            else:
                current_chunk.append(word)
                current_tokens += word_tokens

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _cluster_by_similarity(
        self, sentences: List[str], embeddings: List[List[float]] = None
    ) -> List[List[str]]:
        """
        Cluster sentences by similarity using token overlap.

        Groups sentences with high word overlap into the same cluster.
        Uses simple cosine similarity via word sets (no spaCy/embeddings needed).

        Args:
            sentences: List of sentences
            embeddings: Optional pre-computed embeddings (unused, for API compat)

        Returns:
            List of sentence clusters
        """
        if not sentences:
            return []

        threshold = 0.3  # Minimum word overlap ratio to cluster together
        clusters: List[List[str]] = []
        assigned = [False] * len(sentences)

        # Build word sets for each sentence
        word_sets = [
            set(s.lower().split()) for s in sentences
        ]

        for i, sentence in enumerate(sentences):
            if assigned[i]:
                continue

            cluster = [sentence]
            assigned[i] = True

            for j in range(i + 1, len(sentences)):
                if assigned[j]:
                    continue

                # Compute Jaccard similarity (token overlap)
                intersection = word_sets[i] & word_sets[j]
                union = word_sets[i] | word_sets[j]
                similarity = len(intersection) / len(union) if union else 0.0

                if similarity >= threshold:
                    cluster.append(sentences[j])
                    assigned[j] = True

            clusters.append(cluster)

        return clusters

    def _deduplicate(self, chunks: List[str]) -> List[str]:
        """
        Remove near-duplicate chunks.

        Compares normalized text; removes if >90% word overlap.

        Args:
            chunks: List of text chunks

        Returns:
            Deduplicated list of chunks
        """
        if len(chunks) <= 1:
            return chunks

        result = []
        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            is_duplicate = False

            for existing in result:
                existing_words = set(existing.lower().split())
                if not chunk_words or not existing_words:
                    continue

                intersection = chunk_words & existing_words
                smaller = min(len(chunk_words), len(existing_words))
                overlap = len(intersection) / smaller if smaller > 0 else 0.0

                if overlap > 0.9:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(chunk)

        return result

    def merge(self, chunks: List[str], max_tokens: int = 500) -> List[str]:
        """
        Merge small adjacent chunks when possible.

        Iterates chunks pairwise; merges when _should_merge() returns True.

        Args:
            chunks: List of text chunks
            max_tokens: Maximum tokens per merged chunk

        Returns:
            Merged list of chunks
        """
        if len(chunks) <= 1:
            return chunks

        merged = [chunks[0]]

        for i in range(1, len(chunks)):
            if self._should_merge(merged[-1], chunks[i], max_tokens):
                merged[-1] = merged[-1] + ' ' + chunks[i]
            else:
                merged.append(chunks[i])

        return merged

    def _should_merge(self, chunk_a: str, chunk_b: str, max_tokens: int = 500) -> bool:
        """
        Determine if two chunks should be merged.

        Returns True if combined tokens < max_tokens and chunks share words.

        Args:
            chunk_a: First chunk
            chunk_b: Second chunk
            max_tokens: Maximum token limit

        Returns:
            True if chunks should be merged
        """
        combined_tokens = self.count_tokens(chunk_a + ' ' + chunk_b)
        if combined_tokens > max_tokens:
            return False

        # Check if chunks share any content words (related)
        words_a = set(chunk_a.lower().split())
        words_b = set(chunk_b.lower().split())
        shared = words_a & words_b

        # Merge if they share words or either chunk is very small
        small_chunk = (
            self.count_tokens(chunk_a) < max_tokens * 0.2
            or self.count_tokens(chunk_b) < max_tokens * 0.2
        )

        return len(shared) > 0 or small_chunk


# Module-level convenience function
def chunk_text(text: str, max_tokens: int = 500) -> List[str]:
    """
    Convenience function for quick text chunking.

    Usage:
        from nlp.text_chunker import chunk_text
        chunks = chunk_text("Long text...", max_tokens=500)
    """
    chunker = TextChunker()
    return chunker.chunk(text, max_tokens)


if __name__ == "__main__":
    # Quick test
    print("Testing Text Chunker...")

    test_text = """
    This is the first sentence. This is the second sentence with more content.
    This is a third sentence that adds even more information to the text.

    Here's a new paragraph. It contains multiple sentences as well. Some are longer
    than others. Some are quite short. But they all contribute to the overall meaning.

    The final paragraph wraps up the test. It ensures we have enough content to test
    chunking properly. This should create multiple chunks when limited.
    """

    chunker = TextChunker()

    print("\n" + "="*70)
    print("TEST 1: Token Counting")
    print("="*70)
    tokens = chunker.count_tokens(test_text)
    print(f"Total tokens: {tokens}")

    print("\n" + "="*70)
    print("TEST 2: Chunking with max_tokens=100")
    print("="*70)
    chunks = chunker.chunk(test_text, max_tokens=100)
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks, 1):
        chunk_tokens = chunker.count_tokens(chunk)
        print(f"\nChunk {i} ({chunk_tokens} tokens):")
        print(f"  {chunk[:80]}...")

    print("\n" + "="*70)
    print("TEST 3: Semantic Splitting")
    print("="*70)
    semantic_chunks = chunker.semantic_split(test_text, num_chunks=3)
    print(f"Number of semantic chunks: {len(semantic_chunks)}")
    for i, chunk in enumerate(semantic_chunks, 1):
        print(f"\nSemantic Chunk {i}:")
        print(f"  {chunk[:80]}...")

    print("\n✅ Text Chunker tests completed!")
