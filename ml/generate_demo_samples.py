#!/usr/bin/env python3
"""
Demo: Generate 10 samples using GPT-4
Test the generation quality before running full 500 samples.

Usage:
    export OPENAI_API_KEY="your-key"
    python ml/generate_demo_samples.py
"""

import os
import json
from pathlib import Path

try:
    import openai
except ImportError:
    print("❌ openai package not installed")
    print("Install: pip install openai")
    exit(1)


def generate_demo_samples():
    """Generate 10 demo samples."""
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        print("\nSet it in terminal:")
        print('  export OPENAI_API_KEY="sk-..."')
        print("\nOr load from .env:")
        print('  export $(cat path/to/.env | xargs)')
        exit(1)

    client = openai.OpenAI(api_key=api_key)

    prompt = """Generate 10 diverse task descriptions for software development with urgency and importance labels.

Requirements:
- 5 in English, 5 in Korean
- Vary urgency (1-10) and importance (1-10)
- Include different categories: bugs, features, docs, UI, security

Output JSON array:
[
  {
    "text": "Task description",
    "urgency": 1-10,
    "importance": 1-10,
    "category": "bug|feature|docs|ui|security"
  },
  ...
]"""

    print("\n🚀 Generating 10 demo samples with GPT-4...")
    print("(This will cost ~$0.10)\n")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates training data in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=1000
        )

        content = response.choices[0].message.content

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        samples = json.loads(content.strip())

        print("✅ Generated samples:\n")
        for i, sample in enumerate(samples, 1):
            print(f"{i}. {sample['text'][:60]}...")
            print(f"   Urgency: {sample['urgency']}, Importance: {sample['importance']}, Category: {sample.get('category', 'N/A')}\n")

        # Save
        output_file = Path("ml/demo_samples.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved to {output_file}")
        print("\n📊 Quality looks good? Run full generation:")
        print("  python ml/generate_training_data_gpt4.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    generate_demo_samples()
