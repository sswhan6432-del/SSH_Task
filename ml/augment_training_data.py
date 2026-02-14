#!/usr/bin/env python3
"""
Training Data Augmentation Script
Adds samples to balance urgency/importance distribution.
"""

import json
from pathlib import Path

# Additional samples to balance distribution
ADDITIONAL_SAMPLES = [
    # urgency=1 (극히 낮은 긴급도) - 6개 추가
    {"text": "Someday: Consider adding tooltip animations", "urgency": 1, "importance": 2},
    {"text": "Maybe later: Improve button hover effects", "urgency": 1, "importance": 3},
    {"text": "Future: Add sound effects to UI", "urgency": 1, "importance": 1},
    {"text": "Low priority: Update placeholder text", "urgency": 1, "importance": 2},
    {"text": "Eventually: Add more color themes", "urgency": 1, "importance": 3},
    {"text": "Sometime: Refine shadow effects", "urgency": 1, "importance": 2},

    # urgency=2 (매우 낮은 긴급도) - importance 1-3
    {"text": "Later: Adjust padding in footer", "urgency": 2, "importance": 1},
    {"text": "Eventually: Update icon set", "urgency": 2, "importance": 2},
    {"text": "Low: Improve tooltip positioning", "urgency": 2, "importance": 1},

    # urgency=9 (매우 높은 긴급도) - 4개 추가
    {"text": "Critical: Server down, users cannot access app", "urgency": 9, "importance": 10},
    {"text": "Urgent bug: Data corruption in recent update", "urgency": 9, "importance": 9},
    {"text": "Emergency: SQL injection vulnerability discovered", "urgency": 9, "importance": 10},
    {"text": "Critical issue: Password reset not working", "urgency": 9, "importance": 9},

    # urgency=10 (극히 높은 긴급도) - 4개 추가
    {"text": "URGENT: Production server crashed, immediate fix required", "urgency": 10, "importance": 10},
    {"text": "ASAP: Data breach detected, security patch needed now", "urgency": 10, "importance": 10},
    {"text": "Emergency fix: Payment gateway down, losing revenue", "urgency": 10, "importance": 10},
    {"text": "Critical hotfix: User data exposed, patch immediately", "urgency": 10, "importance": 10},

    # importance=1 (극히 낮은 중요도) - 7개 추가
    {"text": "Update sidebar background color", "urgency": 2, "importance": 1},
    {"text": "Change button border radius", "urgency": 1, "importance": 1},
    {"text": "Adjust font weight in footer", "urgency": 2, "importance": 1},
    {"text": "Tweak hover animation speed", "urgency": 1, "importance": 1},
    {"text": "Update placeholder image", "urgency": 2, "importance": 1},
    {"text": "Change icon color slightly", "urgency": 1, "importance": 1},
    {"text": "Adjust spacing in sidebar", "urgency": 2, "importance": 1},

    # importance=2 (매우 낮은 중요도) - 6개 추가
    {"text": "Update about page text", "urgency": 3, "importance": 2},
    {"text": "Improve FAQ formatting", "urgency": 2, "importance": 2},
    {"text": "Add team member photos", "urgency": 3, "importance": 2},
    {"text": "Update company logo on footer", "urgency": 2, "importance": 2},
    {"text": "Refine carousel transition", "urgency": 3, "importance": 2},
    {"text": "Add social media icons", "urgency": 2, "importance": 2},

    # importance=3 (낮은 중요도) - 3개 추가
    {"text": "Improve help section layout", "urgency": 3, "importance": 3},
    {"text": "Add search icon to header", "urgency": 2, "importance": 3},
    {"text": "Update contact form styling", "urgency": 3, "importance": 3},

    # importance=4 (중간-낮은 중요도) - 3개 추가
    {"text": "Add breadcrumb navigation", "urgency": 4, "importance": 4},
    {"text": "Implement tab navigation", "urgency": 3, "importance": 4},
    {"text": "Add print stylesheet", "urgency": 3, "importance": 4},

    # 균형 잡힌 샘플 추가 (다양한 조합)
    {"text": "긴급하지 않음: 로고 크기 조정", "urgency": 2, "importance": 2},
    {"text": "여유롭게: 메뉴 순서 변경", "urgency": 1, "importance": 2},
    {"text": "필수 아님: 배너 이미지 교체", "urgency": 2, "importance": 3},
    {"text": "선택: 애니메이션 효과 추가", "urgency": 3, "importance": 3},

    # urgency=8 추가 (보안/버그)
    {"text": "Fix SQL injection in user input", "urgency": 8, "importance": 10},
    {"text": "Patch XSS vulnerability in comments", "urgency": 8, "importance": 9},
    {"text": "긴급 버그: 파일 업로드 실패", "urgency": 8, "importance": 7},

    # importance=10 추가 (핵심 보안/기능)
    {"text": "Implement two-factor authentication", "urgency": 7, "importance": 10},
    {"text": "Add data encryption at rest", "urgency": 6, "importance": 10},
    {"text": "Set up automated backups", "urgency": 6, "importance": 10},

    # 중간 범위 균형 (urgency=4-6, importance=4-7)
    {"text": "Add user feedback form", "urgency": 4, "importance": 5},
    {"text": "Implement bookmark feature", "urgency": 5, "importance": 5},
    {"text": "Add tags to posts", "urgency": 4, "importance": 4},
    {"text": "Create admin activity log", "urgency": 5, "importance": 6},
    {"text": "Add bulk edit functionality", "urgency": 5, "importance": 6},
    {"text": "Implement user preferences", "urgency": 4, "importance": 5},

    # 한국어 샘플 추가
    {"text": "나중에: 글꼴 변경 고려", "urgency": 1, "importance": 2},
    {"text": "선택사항: 애니메이션 개선", "urgency": 2, "importance": 3},
    {"text": "여유시: 레이아웃 조정", "urgency": 2, "importance": 2},
    {"text": "긴급: 로그인 시스템 오류", "urgency": 9, "importance": 9},
    {"text": "즉시 수정: 보안 결함 발견", "urgency": 10, "importance": 10},
    {"text": "필수 구현: 데이터 암호화", "urgency": 7, "importance": 10},
    {"text": "핵심 기능: 검색 기능 추가", "urgency": 6, "importance": 8},
    {"text": "중요: 알림 시스템 구축", "urgency": 6, "importance": 7},
]

def main():
    # Load existing data
    data_file = Path("ml/training_data.json")
    with open(data_file) as f:
        existing_data = json.load(f)

    print(f"Existing samples: {len(existing_data)}")

    # Add new samples
    augmented_data = existing_data + ADDITIONAL_SAMPLES

    print(f"New samples: {len(ADDITIONAL_SAMPLES)}")
    print(f"Total samples: {len(augmented_data)}")

    # Save augmented data
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(augmented_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Training data augmented and saved to {data_file}")

    # Show new distribution
    from collections import Counter
    urgency_dist = Counter(item["urgency"] for item in augmented_data)
    importance_dist = Counter(item["importance"] for item in augmented_data)

    print("\nNew Urgency distribution:")
    for i in range(1, 11):
        count = urgency_dist.get(i, 0)
        print(f"  {i}: {count:2d} samples")

    print("\nNew Importance distribution:")
    for i in range(1, 11):
        count = importance_dist.get(i, 0)
        print(f"  {i}: {count:2d} samples")

if __name__ == "__main__":
    main()
