"""
Compressor - LLM Router v5.0
Multi-level text compression for token reduction.

Compression Levels:
- Level 1 (Mild): Remove redundancy, keep meaning (10-20% reduction)
- Level 2 (Balanced): Aggressive cleanup (30-50% reduction)
- Level 3 (Aggressive): Maximum compression (50-70% reduction)

Code blocks (fenced ``` and indented 4-space) are protected from compression.

Author: AI Development Team
Version: 5.1.0
Date: 2026-02-23
"""

from dataclasses import dataclass
from typing import List, Tuple
import logging
import re

logger = logging.getLogger(__name__)

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

    Code blocks (fenced and indented) are extracted before compression
    and restored after, preventing stop-word removal inside code.

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

        Code blocks are protected from compression at all levels.

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

        # Extract code blocks before compression
        text_without_code, code_blocks = self._extract_code_blocks(text)
        if code_blocks:
            logger.debug("Protected %d code blocks from compression", len(code_blocks))

        # Apply compression to prose only
        compressed = text_without_code

        # Level 1: Basic cleanup
        compressed = self._normalize_whitespace(compressed)
        compressed, removed_particles = self._remove_particles(compressed)
        if removed_particles:
            lost_info.append(f"Korean particles: {', '.join(removed_particles[:3])}")
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
            compressed = self._extract_keywords_only(compressed)
            compressed = self._to_imperative(compressed)

        # Final cleanup
        compressed = self._normalize_whitespace(compressed)

        # Restore code blocks
        compressed = self._restore_code_blocks(compressed, code_blocks)

        # Calculate metrics
        compressed_tokens = self.count_tokens(compressed)
        reduction_rate = (
            (original_tokens - compressed_tokens) / original_tokens
            if original_tokens > 0 else 0.0
        )

        logger.info("Compressed level=%d: %d -> %d tokens (%.1f%% reduction)",
                     level, original_tokens, compressed_tokens, reduction_rate * 100)

        return CompressionResult(
            original=text,
            compressed=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_rate=reduction_rate,
            compression_level=level,
            lost_info=lost_info
        )

    def _extract_code_blocks(self, text: str) -> Tuple[str, List[str]]:
        """
        Extract code blocks from text and replace with placeholders.

        Detects:
        1. Fenced code blocks (``` ... ```)
        2. Indented code blocks (4+ spaces at line start)

        Args:
            text: Input text

        Returns:
            (text_with_placeholders, list_of_code_blocks)
        """
        code_blocks = []

        # 1. Extract fenced code blocks (```...```)
        def replace_fenced(match):
            idx = len(code_blocks)
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{idx}__"

        text = re.sub(r'```[\s\S]*?```', replace_fenced, text)

        # 2. Extract indented code blocks (lines starting with 4+ spaces)
        lines = text.split('\n')
        result_lines = []
        indent_block = []

        for line in lines:
            if re.match(r'^(    |\t)', line) and line.strip():
                indent_block.append(line)
            else:
                if indent_block:
                    idx = len(code_blocks)
                    code_blocks.append('\n'.join(indent_block))
                    result_lines.append(f"__CODE_BLOCK_{idx}__")
                    indent_block = []
                result_lines.append(line)

        # Handle trailing indented block
        if indent_block:
            idx = len(code_blocks)
            code_blocks.append('\n'.join(indent_block))
            result_lines.append(f"__CODE_BLOCK_{idx}__")

        text = '\n'.join(result_lines)

        return text, code_blocks

    def _restore_code_blocks(self, text: str, code_blocks: List[str]) -> str:
        """
        Restore code blocks from placeholders.

        Args:
            text: Text with __CODE_BLOCK_N__ placeholders
            code_blocks: List of original code blocks

        Returns:
            Text with code blocks restored
        """
        for i, block in enumerate(code_blocks):
            text = text.replace(f"__CODE_BLOCK_{i}__", block)
        return text

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
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        return text

    def _remove_redundancy(self, text: str) -> str:
        """Remove redundant phrases."""
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
            if level == 1 and len(replacement) == 0:
                continue

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

        return ' '.join(result), list(set(removed))[:5]

    def _remove_articles(self, text: str) -> str:
        """Remove articles (a, an, the)."""
        text = re.sub(r'\b(a|an|the)\b\s+', '', text, flags=re.IGNORECASE)
        return text

    def _remove_particles(self, text: str) -> tuple[str, list[str]]:
        """
        Remove Korean particles (regex-based).

        Args:
            text: Input text

        Returns:
            Tuple of (processed text, list of removed particles)
        """
        removed = []

        pattern = r'(에서|으로|까지|부터|은|는|이|가|을|를|의|에|로|와|과|도|만)(?=\s|$|[.,!?])'
        matches = re.findall(pattern, text)
        if matches:
            removed = list(set(matches))
            text = re.sub(pattern, '', text)
            text = re.sub(r'\s+', ' ', text).strip()

        return text, removed

    def _extract_keywords_only(self, text: str) -> str:
        """
        Extract nouns/verbs/key terms only, drop filler.

        Args:
            text: Input text

        Returns:
            Text with only keywords
        """
        words = text.split()
        seen = set()
        keywords = []

        for word in words:
            word_clean = word.lower().strip('.,!?;:')
            if len(word_clean) > 2 and word_clean not in self.STOP_WORDS:
                if word_clean not in seen:
                    keywords.append(word)
                    seen.add(word_clean)

        return ' '.join(keywords) if keywords else text

    def _to_imperative(self, text: str) -> str:
        """
        Convert to imperative form.

        Args:
            text: Input text

        Returns:
            Text in imperative form
        """
        hedges = [
            r'\bi think\b\s*',
            r'\bmaybe\b\s*',
            r'\bperhaps\b\s*',
            r'\bprobably\b\s*',
            r'\bit seems like\b\s*',
            r'\bin my opinion\b\s*',
        ]
        for hedge in hedges:
            text = re.sub(hedge, '', text, flags=re.IGNORECASE)

        conversions = [
            (r'\byou should\b\s*', ''),
            (r'\bwe need to\b\s*', ''),
            (r'\bwe should\b\s*', ''),
            (r'\byou need to\b\s*', ''),
            (r'\bit is necessary to\b\s*', ''),
            (r'\byou have to\b\s*', ''),
            (r'\bwe have to\b\s*', ''),
        ]
        for pattern, replacement in conversions:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        text = re.sub(r'\s+', ' ', text).strip()
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
    logging.basicConfig(level=logging.DEBUG)

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

    # Test code block protection
    print("\n" + "="*70)
    print("CODE BLOCK PROTECTION TEST")
    print("="*70)

    code_test = """Please review this function for errors:

```python
for item in items:
    if item.is_valid:
        result = process(item)
```

The function should handle all edge cases."""

    result = compressor.compress(code_test, level=3)
    print(f"Original:\n{code_test}")
    print(f"\nCompressed:\n{result.compressed}")

    # Verify code is preserved
    assert "for item in items:" in result.compressed, "Code block was corrupted!"
    assert "if item.is_valid:" in result.compressed, "Code block was corrupted!"
    print("\nCode block preserved successfully!")
