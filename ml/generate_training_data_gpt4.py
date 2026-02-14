#!/usr/bin/env python3
"""
GPT-4 Training Data Generator
Generates 500 high-quality labeled samples for urgency/importance prediction.

Usage:
    export OPENAI_API_KEY="your-key"
    python ml/generate_training_data_gpt4.py

Output:
    ml/training_data_gpt4.json (500 new samples)
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict

try:
    import openai
except ImportError:
    print("❌ openai package not installed")
    print("Install: pip install openai")
    exit(1)

# Categories for diverse samples
CATEGORIES = [
    ("security", "Security vulnerabilities, authentication, encryption"),
    ("bug", "Bug fixes, crashes, errors"),
    ("feature", "New features, enhancements"),
    ("ui", "UI/UX improvements, styling"),
    ("docs", "Documentation, comments"),
    ("optimization", "Performance, caching, queries"),
    ("testing", "Unit tests, integration tests"),
    ("infrastructure", "CI/CD, monitoring, deployment"),
    ("refactor", "Code refactoring, cleanup"),
    ("maintenance", "Dependency updates, cleanup"),
]

# Urgency/Importance combinations (balanced distribution)
SCORE_DISTRIBUTION = [
    # High urgency, high importance (10%)
    *[(9, 10), (10, 10), (10, 9), (9, 9)] * 13,
    # High urgency, medium/low importance (10%)
    *[(9, 5), (10, 6), (8, 4), (9, 3)] * 13,
    # Medium urgency, high importance (20%)
    *[(5, 10), (6, 9), (5, 8), (6, 10)] * 25,
    # Medium urgency, medium importance (30%)
    *[(5, 5), (6, 6), (5, 6), (6, 5), (4, 5), (5, 4)] * 25,
    # Low urgency, any importance (20%)
    *[(2, 3), (1, 2), (3, 4), (2, 5), (1, 1), (3, 2)] * 17,
    # Any urgency, low importance (10%)
    *[(4, 2), (5, 1), (6, 3), (7, 2)] * 13,
]


def generate_batch_prompt(category: str, description: str, num_samples: int = 10) -> str:
    """Generate GPT-4 prompt for a batch of samples."""
    return f"""You are a project management expert. Generate {num_samples} diverse task descriptions for software development.

Category: {category} ({description})

Requirements:
1. Generate exactly {num_samples} tasks in JSON format
2. Each task should be realistic and specific
3. Include both English and Korean tasks (50/50)
4. Vary the urgency (1-10) and importance (1-10) realistically
5. Urgency = how soon it needs to be done
6. Importance = how critical it is for the project

Output format (JSON array):
[
  {{
    "text": "Task description in English or Korean",
    "urgency": 1-10,
    "importance": 1-10,
    "category": "{category}"
  }},
  ...
]

Examples:
- High urgency (9-10): "Emergency", "ASAP", "Critical", "긴급", "즉시"
- Low urgency (1-3): "Someday", "Eventually", "나중에", "여유시"
- High importance (9-10): "Security", "Authentication", "Payment", "보안", "결제"
- Low importance (1-3): "UI polish", "Typo", "스타일", "오타"

Generate diverse, realistic tasks:"""


def call_gpt4(prompt: str, api_key: str) -> str:
    """Call GPT-4 API."""
    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates training data in JSON format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,  # High creativity
        max_tokens=2000
    )

    return response.choices[0].message.content


def parse_gpt_response(response: str) -> List[Dict]:
    """Parse GPT-4 JSON response."""
    # Extract JSON from response (might be wrapped in markdown)
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]

    response = response.strip()

    try:
        data = json.loads(response)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        print(f"Response: {response[:200]}...")
        return []


def generate_samples(target_count: int = 500) -> List[Dict]:
    """Generate training samples using GPT-4."""
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        print("Set it: export OPENAI_API_KEY='your-key'")
        exit(1)

    all_samples = []
    batches_per_category = target_count // len(CATEGORIES) // 10 + 1

    print(f"\n🚀 Generating {target_count} samples using GPT-4...")
    print(f"Categories: {len(CATEGORIES)}")
    print(f"Batches per category: {batches_per_category}\n")

    for category, description in CATEGORIES:
        print(f"\n📦 Generating {category} tasks...")

        for batch in range(batches_per_category):
            if len(all_samples) >= target_count:
                break

            try:
                # Generate batch
                prompt = generate_batch_prompt(category, description, 10)
                response = call_gpt4(prompt, api_key)
                samples = parse_gpt_response(response)

                # Validate and add
                valid_samples = []
                for sample in samples:
                    if all(k in sample for k in ["text", "urgency", "importance"]):
                        if 1 <= sample["urgency"] <= 10 and 1 <= sample["importance"] <= 10:
                            valid_samples.append(sample)

                all_samples.extend(valid_samples)
                print(f"  Batch {batch+1}: Generated {len(valid_samples)} valid samples (total: {len(all_samples)})")

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"  ⚠️ Batch {batch+1} failed: {e}")
                continue

    return all_samples[:target_count]


def save_samples(samples: List[Dict], output_file: str = "ml/training_data_gpt4.json"):
    """Save generated samples to file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(samples)} samples to {output_file}")


def merge_with_existing(gpt_samples: List[Dict], existing_file: str = "ml/training_data.json") -> List[Dict]:
    """Merge GPT-4 samples with existing data."""
    existing_path = Path(existing_file)

    if existing_path.exists():
        with open(existing_path) as f:
            existing = json.load(f)
        print(f"\n📊 Merging with existing {len(existing)} samples...")
        merged = existing + gpt_samples
        print(f"   Total: {len(merged)} samples")
        return merged
    else:
        return gpt_samples


def main():
    print("="*70)
    print("GPT-4 TRAINING DATA GENERATOR")
    print("="*70)

    # Generate samples
    samples = generate_samples(target_count=500)

    if not samples:
        print("\n❌ No samples generated")
        return

    # Save GPT-4 samples separately
    save_samples(samples, "ml/training_data_gpt4.json")

    # Show distribution
    from collections import Counter
    urgency_dist = Counter(s["urgency"] for s in samples)
    importance_dist = Counter(s["importance"] for s in samples)

    print("\n📊 Generated Data Distribution:")
    print("\nUrgency:")
    for i in range(1, 11):
        count = urgency_dist.get(i, 0)
        bar = "█" * (count // 5)
        print(f"  {i:2d}: {count:3d} {bar}")

    print("\nImportance:")
    for i in range(1, 11):
        count = importance_dist.get(i, 0)
        bar = "█" * (count // 5)
        print(f"  {i:2d}: {count:3d} {bar}")

    # Merge with existing
    print("\n" + "="*70)
    response = input("\n🤔 Merge with existing training_data.json? (y/n): ")

    if response.lower() == 'y':
        merged = merge_with_existing(samples)
        save_samples(merged, "ml/training_data.json")
        print(f"\n✅ Updated training_data.json with {len(merged)} total samples")
    else:
        print("\n✅ GPT-4 samples saved separately")

    print("\n" + "="*70)
    print("✅ DATA GENERATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review: ml/training_data_gpt4.json")
    print("  2. Train: python ml/train_priority_model.py")
    print("  3. Test: python ml/train_priority_model.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
