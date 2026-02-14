#!/usr/bin/env python3
"""
Training Data Generator with API Key Prompt
Prompts user for API key instead of reading from environment.
"""

import json
import time
from pathlib import Path
from typing import List, Dict
import getpass

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


def call_gpt4(prompt: str, client) -> str:
    """Call GPT-4 API."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates training data in JSON format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=2000
    )
    return response.choices[0].message.content


def parse_gpt_response(response: str) -> List[Dict]:
    """Parse GPT-4 JSON response."""
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
        return []


def generate_samples(api_key: str, target_count: int = 500) -> List[Dict]:
    """Generate training samples using GPT-4."""
    client = openai.OpenAI(api_key=api_key)
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
                prompt = generate_batch_prompt(category, description, 10)
                response = call_gpt4(prompt, client)
                samples = parse_gpt_response(response)

                valid_samples = []
                for sample in samples:
                    if all(k in sample for k in ["text", "urgency", "importance"]):
                        if 1 <= sample["urgency"] <= 10 and 1 <= sample["importance"] <= 10:
                            valid_samples.append(sample)

                all_samples.extend(valid_samples)
                print(f"  Batch {batch+1}: Generated {len(valid_samples)} samples (total: {len(all_samples)})")

                time.sleep(1)

            except Exception as e:
                print(f"  ⚠️ Batch {batch+1} failed: {e}")
                continue

    return all_samples[:target_count]


def main():
    print("="*70)
    print("GPT-4 TRAINING DATA GENERATOR")
    print("="*70)

    # Get API key from user
    print("\n🔑 Enter your OpenAI API key:")
    print("(Find it at: https://platform.openai.com/api-keys)")
    api_key = getpass.getpass("API Key: ").strip()

    if not api_key:
        print("❌ No API key provided")
        return

    print(f"\n✅ API Key: {api_key[:7]}...{api_key[-4:]}")

    # Test connection
    print("\n🔍 Testing connection...")
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease check:")
        print("  1. API key is correct")
        print("  2. API key has credits")
        print("  3. Network connection is working")
        return

    # Generate samples
    samples = generate_samples(api_key, target_count=500)

    if not samples:
        print("\n❌ No samples generated")
        return

    # Save
    output_file = Path("ml/training_data_gpt4.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(samples)} samples to {output_file}")

    # Show distribution
    from collections import Counter
    urgency_dist = Counter(s["urgency"] for s in samples)
    importance_dist = Counter(s["importance"] for s in samples)

    print("\n📊 Distribution:")
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

    # Merge option
    print("\n" + "="*70)
    response = input("\n🤔 Merge with existing training_data.json? (y/n): ")

    if response.lower() == 'y':
        existing_file = Path("ml/training_data.json")
        if existing_file.exists():
            with open(existing_file) as f:
                existing = json.load(f)
            merged = existing + samples
            with open(existing_file, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Merged! Total: {len(merged)} samples")
        else:
            with open(existing_file, "w", encoding="utf-8") as f:
                json.dump(samples, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Saved as training_data.json")

    print("\n" + "="*70)
    print("✅ GENERATION COMPLETE")
    print("="*70)
    print("\nNext: python ml/train_priority_model.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
