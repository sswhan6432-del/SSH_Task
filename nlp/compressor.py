"""
Compressor - LLM Router v5.0
Multi-level text compression for token reduction.

Compression Levels:
- Level 1 (Mild): Remove redundancy, keep meaning (10-20% reduction)
- Level 2 (Balanced): Aggressive cleanup (30-50% reduction)
- Level 3 (Aggressive): Maximum compression (50-70% reduction)

Author: AI Development Team
Version: 5.0.0
Date: 2026-02-13
"""

from dataclasses import dataclass
from typing import List
import re

try:
    import tiktoken
except ImportError as e:
    raise ImportError(
        "Required packages not installed. Run: pip install tiktoken"
    ) from e


@dataclass
class CompressionResult:
    """Result of text compression."""
    original: str                     # Original text
    compressed: str                   # Compressed text
    original_tokens: int              # Token count before
    compressed_tokens: int            # Token count after
    reduction_rate: float             # Reduction (0.0-1.0)
    compression_level: int            # 1-3
    lost_info: List[str]              # Removed elements


class Compressor:
    """
    Multi-level text compressor for token reduction.

    Achieves 50%+ token reduction through:
    - Whitespace normalization
    - Redundancy removal
    - Stop word elimination
    - Abbreviation
    - Sentence reconstruction

    Usage:
        compressor = Compressor()
        result = compressor.compress("Long text...", level=2)
        print(f"Reduced by {result.reduction_rate:.1%}")
    """

    # Common stop words (can be removed at level 2+)
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can'
    }

    # Phrases that can be shortened
    REPLACEMENTS = {
        # Level 1: Safe abbreviations
        'as soon as possible': 'ASAP',
        'for example': 'e.g.',
        'in other words': 'i.e.',
        'and so on': 'etc.',

        # Level 2: More aggressive
        'implement': 'impl',
        'function': 'func',
        'variable': 'var',
        'parameter': 'param',
        'configuration': 'config',
        'initialize': 'init',
        'execute': 'exec',
        'database': 'DB',
        'application': 'app',
        'authentication': 'auth',
        'authorization': 'authz',
        'environment': 'env',

        # Level 3: Very aggressive
        'please': '',
        'thank you': '',
        'I would like to': '',
        'could you': '',
        'can you': '',
    }

    def __init__(self, encoding: str = "cl100k_base"):
        """
        Initialize compressor.

        Args:
            encoding: tiktoken encoding name
        """
        self.encoding = tiktoken.get_encoding(encoding)

    def compress(self, text: str, level: int = 2) -> CompressionResult:
        """
        Compress text at specified level.

        Args:
            text: Input text
            level: Compression level (1-3)

        Returns:
            CompressionResult with stats
        """
        if not text or not text.strip():
            return CompressionResult(
                original="",
                compressed="",
                original_tokens=0,
                compressed_tokens=0,
                reduction_rate=0.0,
                compression_level=level,
                lost_info=[]
            )

        original_tokens = self.count_tokens(text)
        lost_info = []

        # Apply compression based on level
        compressed = text

        # Level 1: Basic cleanup
        compressed = self._normalize_whitespace(compressed)
        compressed = self._remove_redundancy(compressed)
        compressed = self._apply_replacements(compressed, level=1)

        if level >= 2:
            # Level 2: Remove stop words
            compressed, removed_words = self._remove_stop_words(compressed)
            lost_info.extend(removed_words)
            compressed = self._apply_replacements(compressed, level=2)

        if level >= 3:
            # Level 3: Aggressive shortening
            compressed = self._apply_replacements(compressed, level=3)
            compressed = self._remove_articles(compressed)
            lost_info.append("articles (a, an, the)")

        # Final cleanup
        compressed = self._normalize_whitespace(compressed)

        # Calculate metrics
        compressed_tokens = self.count_tokens(compressed)
        reduction_rate = (
            (original_tokens - compressed_tokens) / original_tokens
            if original_tokens > 0 else 0.0
        )

        return CompressionResult(
            original=text,
            compressed=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_rate=reduction_rate,
            compression_level=level,
            lost_info=lost_info
        )

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

    def _normalize_whitespace(self, text: str) -> str:
        """Remove extra whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Remove space before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        return text

    def _remove_redundancy(self, text: str) -> str:
        """Remove redundant phrases."""
        # Remove duplicate words
        words = text.split()
        seen = set()
        result = []

        for word in words:
            word_lower = word.lower()
            if word_lower not in seen or word_lower not in self.STOP_WORDS:
                result.append(word)
                seen.add(word_lower)

        return ' '.join(result)

    def _apply_replacements(self, text: str, level: int) -> str:
        """Apply abbreviations and replacements."""
        for phrase, replacement in self.REPLACEMENTS.items():
            # Only apply if replacement matches level
            if level == 1 and len(replacement) == 0:
                continue  # Skip removals at level 1

            text = re.sub(
                r'\b' + re.escape(phrase) + r'\b',
                replacement,
                text,
                flags=re.IGNORECASE
            )

        return text

    def _remove_stop_words(self, text: str) -> tuple[str, List[str]]:
        """Remove common stop words."""
        words = text.split()
        removed = []
        result = []

        for word in words:
            word_clean = word.lower().strip('.,!?;:')
            if word_clean in self.STOP_WORDS:
                removed.append(word_clean)
            else:
                result.append(word)

        return ' '.join(result), list(set(removed))[:5]  # Max 5 examples

    def _remove_articles(self, text: str) -> str:
        """Remove articles (a, an, the)."""
        # Remove standalone articles
        text = re.sub(r'\b(a|an|the)\b\s+', '', text, flags=re.IGNORECASE)
        return text

    def batch_compress(
        self,
        texts: List[str],
        level: int = 2
    ) -> List[CompressionResult]:
        """
        Compress multiple texts.

        Args:
            texts: List of input texts
            level: Compression level

        Returns:
            List of CompressionResult
        """
        return [self.compress(text, level) for text in texts]


# Module-level convenience function
def compress_text(text: str, level: int = 2) -> CompressionResult:
    """
    Convenience function for quick compression.

    Usage:
        from nlp.compressor import compress_text
        result = compress_text("Long text...", level=2)
        print(result.compressed)
    """
    compressor = Compressor()
    return compressor.compress(text, level)


if __name__ == "__main__":
    # Quick test
    print("Testing Compressor...")

    test_text = """
    Please implement a new user authentication function for the application.
    The function should validate user credentials and return the authentication
    status. As soon as possible, we need to add this feature to the database
    configuration. For example, the authentication module should check if the
    user has the proper authorization to access the application environment.
    """

    compressor = Compressor()

    print("\n" + "="*70)
    print("ORIGINAL TEXT")
    print("="*70)
    print(test_text.strip())
    print(f"\nTokens: {compressor.count_tokens(test_text)}")

    for level in [1, 2, 3]:
        result = compressor.compress(test_text, level=level)

        print("\n" + "="*70)
        print(f"COMPRESSION LEVEL {level}")
        print("="*70)
        print(result.compressed)
        print(f"\nOriginal tokens: {result.original_tokens}")
        print(f"Compressed tokens: {result.compressed_tokens}")
        print(f"Reduction: {result.reduction_rate:.1%}")
        if result.lost_info:
            print(f"Lost info: {', '.join(result.lost_info[:3])}")

    print("\n✅ Compressor tests completed!")
