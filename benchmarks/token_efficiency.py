#!/usr/bin/env python3
"""
Benchmark: Token Efficiency
Tests average token reduction rate across 100 samples.

Success Criteria:
- Average token reduction >= 40%
- Overall reduction >= 40%

Usage:
    python3 benchmarks/token_efficiency.py
"""

import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_router_v5 import EnhancedRouter


def load_test_samples(count=100):
    """
    Load test samples from ml/training_data.json

    Args:
        count: Number of samples to load (default: 100)

    Returns:
        List of text samples
    """
    training_data_path = Path(__file__).parent.parent / "ml" / "training_data.json"

    if not training_data_path.exists():
        raise FileNotFoundError(f"Training data not found: {training_data_path}")

    with open(training_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract text samples (up to count)
    samples = [item["text"] for item in data[:count]]

    print(f"Loaded {len(samples)} test samples from {training_data_path}")
    return samples


def benchmark_token_reduction():
    """
    Measure average token reduction rate

    Tests compression effectiveness across 100 diverse samples
    """
    print("\n" + "=" * 50)
    print("  Token Efficiency Benchmark")
    print("=" * 50)

    # Load samples
    try:
        samples = load_test_samples(100)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure ml/training_data.json exists with at least 100 samples.")
        sys.exit(1)

    # Initialize router with compression level 2 (balanced)
    print("\nInitializing EnhancedRouter (compression_level=2)...")
    router = EnhancedRouter(
        enable_nlp=True,
        enable_compression=True,
        compression_level=2,
        fallback_to_v4=True
    )

    # Run benchmark
    print(f"\nProcessing {len(samples)} samples...\n")

    results = []
    total_original = 0
    total_compressed = 0
    failures = 0

    benchmark_start = time.time()

    for i, sample in enumerate(samples):
        if i % 10 == 0:
            print(f"  [{i:3d}/{len(samples)}] Processing...")

        try:
            # Route sample (triggers compression)
            output = router.route(sample, v5_enabled=True, economy="balanced")

            # Extract token stats from compression results
            original_tokens = 0
            compressed_tokens = 0

            for task in output.tasks:
                if task.compression_result:
                    original_tokens += task.compression_result.original_tokens
                    compressed_tokens += task.compression_result.compressed_tokens

            # Calculate reduction for this sample
            if original_tokens > 0:
                reduction = 1.0 - (compressed_tokens / original_tokens)
                results.append(reduction)
                total_original += original_tokens
                total_compressed += compressed_tokens
            else:
                # No compression data available
                failures += 1

        except Exception as e:
            print(f"  [ERROR] Sample {i} failed: {e}")
            failures += 1

    benchmark_time = time.time() - benchmark_start

    # Calculate metrics
    avg_reduction = sum(results) / len(results) if results else 0.0
    overall_reduction = 1.0 - (total_compressed / total_original) if total_original > 0 else 0.0

    # Print results
    print("\n" + "=" * 50)
    print("  Results")
    print("=" * 50)
    print(f"  Samples processed:    {len(results)}/{len(samples)}")
    print(f"  Failures:             {failures}")
    print(f"  Benchmark time:       {benchmark_time:.2f}s")
    print(f"\n  Average reduction:    {avg_reduction:.1%}")
    print(f"  Overall reduction:    {overall_reduction:.1%}")
    print(f"  Total tokens:         {total_original:,} -> {total_compressed:,}")
    print(f"  Tokens saved:         {total_original - total_compressed:,}")
    print("=" * 50)

    # Assertion (success criteria)
    if avg_reduction < 0.40:
        print(f"\n❌ Benchmark FAILED: Average reduction {avg_reduction:.1%} < 40%")
        sys.exit(1)

    if overall_reduction < 0.40:
        print(f"\n❌ Benchmark FAILED: Overall reduction {overall_reduction:.1%} < 40%")
        sys.exit(1)

    print(f"\n✅ Benchmark PASSED: Token reduction >= 40% (target achieved)")
    print(f"   Avg: {avg_reduction:.1%}, Overall: {overall_reduction:.1%}")


if __name__ == "__main__":
    try:
        benchmark_token_reduction()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBenchmark failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
