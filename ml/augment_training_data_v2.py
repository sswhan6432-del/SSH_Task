#!/usr/bin/env python3
"""
Training Data Augmentation Script v2
Adds 60+ more samples to reach 200 total.
"""

import json
from pathlib import Path

# Additional 60 samples for better distribution
ADDITIONAL_SAMPLES_V2 = [
    # urgency=1, importance varied
    {"text": "Someday: Update brand colors slightly", "urgency": 1, "importance": 2},
    {"text": "Future idea: Add emoji reactions", "urgency": 1, "importance": 3},
    {"text": "Maybe: Try different font for headings", "urgency": 1, "importance": 1},
    {"text": "나중에: 배경 이미지 교체", "urgency": 1, "importance": 2},

    # urgency=2
    {"text": "Eventually: Add hover tooltips to icons", "urgency": 2, "importance": 3},
    {"text": "Low priority: Improve button spacing", "urgency": 2, "importance": 2},
    {"text": "Later: Add more example data", "urgency": 2, "importance": 3},
    {"text": "여유시: 메뉴 아이콘 변경", "urgency": 2, "importance": 2},

    # urgency=3
    {"text": "Consider: Add breadcrumb trail", "urgency": 3, "importance": 4},
    {"text": "Nice to have: Keyboard shortcuts", "urgency": 3, "importance": 5},
    {"text": "Improve: Help documentation layout", "urgency": 3, "importance": 4},
    {"text": "선택사항: FAQ 페이지 추가", "urgency": 3, "importance": 3},

    # urgency=4
    {"text": "Add user profile avatars", "urgency": 4, "importance": 5},
    {"text": "Implement drag-and-drop sorting", "urgency": 4, "importance": 6},
    {"text": "Create onboarding tutorial", "urgency": 4, "importance": 6},
    {"text": "사용자 설정 페이지 개선", "urgency": 4, "importance": 5},

    # urgency=5
    {"text": "Build notification center", "urgency": 5, "importance": 6},
    {"text": "Add search autocomplete", "urgency": 5, "importance": 7},
    {"text": "Implement data export feature", "urgency": 5, "importance": 6},
    {"text": "알림 시스템 구현", "urgency": 5, "importance": 7},

    # urgency=6
    {"text": "Add two-step verification", "urgency": 6, "importance": 8},
    {"text": "Implement audit logging", "urgency": 6, "importance": 8},
    {"text": "Set up automated backups", "urgency": 6, "importance": 9},
    {"text": "데이터 백업 시스템 구축", "urgency": 6, "importance": 8},

    # urgency=7
    {"text": "Fix security headers configuration", "urgency": 7, "importance": 9},
    {"text": "Implement session management", "urgency": 7, "importance": 8},
    {"text": "Add SQL query optimization", "urgency": 7, "importance": 7},
    {"text": "보안 헤더 설정", "urgency": 7, "importance": 9},

    # urgency=8
    {"text": "Critical: Fix authentication bypass", "urgency": 8, "importance": 10},
    {"text": "Urgent: Resolve data leak issue", "urgency": 8, "importance": 9},
    {"text": "Fix CORS misconfiguration", "urgency": 8, "importance": 8},
    {"text": "긴급: 인증 버그 수정", "urgency": 8, "importance": 9},

    # urgency=9
    {"text": "Emergency: Production outage", "urgency": 9, "importance": 10},
    {"text": "Critical bug: Users locked out", "urgency": 9, "importance": 9},
    {"text": "Urgent: Data inconsistency detected", "urgency": 9, "importance": 9},
    {"text": "긴급 장애: 서비스 중단", "urgency": 9, "importance": 10},

    # urgency=10
    {"text": "CRITICAL: Zero-day exploit patch", "urgency": 10, "importance": 10},
    {"text": "ASAP: Complete system failure", "urgency": 10, "importance": 10},
    {"text": "Immediate: Security breach active", "urgency": 10, "importance": 10},
    {"text": "즉시: 보안 침해 발생", "urgency": 10, "importance": 10},

    # importance=1 varied urgency
    {"text": "Change icon size in sidebar", "urgency": 1, "importance": 1},
    {"text": "Update tooltip text", "urgency": 2, "importance": 1},
    {"text": "Adjust button opacity", "urgency": 1, "importance": 1},
    {"text": "아이콘 색상 조정", "urgency": 2, "importance": 1},

    # importance=2
    {"text": "Add loading animation", "urgency": 3, "importance": 2},
    {"text": "Improve modal transitions", "urgency": 2, "importance": 2},
    {"text": "Update placeholder images", "urgency": 3, "importance": 2},
    {"text": "로딩 애니메이션 개선", "urgency": 2, "importance": 2},

    # importance=3
    {"text": "Add syntax highlighting to docs", "urgency": 3, "importance": 3},
    {"text": "Improve code examples", "urgency": 3, "importance": 3},
    {"text": "Add more FAQ entries", "urgency": 2, "importance": 3},
    {"text": "문서 예제 추가", "urgency": 3, "importance": 3},

    # importance=4
    {"text": "Add changelog page", "urgency": 3, "importance": 4},
    {"text": "Implement version history", "urgency": 4, "importance": 4},
    {"text": "Create release notes template", "urgency": 3, "importance": 4},
    {"text": "버전 히스토리 추가", "urgency": 4, "importance": 4},

    # importance=5
    {"text": "Add user preferences storage", "urgency": 4, "importance": 5},
    {"text": "Implement theme customization", "urgency": 4, "importance": 5},
    {"text": "Add bookmark system", "urgency": 5, "importance": 5},
    {"text": "사용자 환경설정 저장", "urgency": 4, "importance": 5},

    # importance=6
    {"text": "Build reporting dashboard", "urgency": 5, "importance": 6},
    {"text": "Add data visualization", "urgency": 5, "importance": 6},
    {"text": "Implement export formats", "urgency": 4, "importance": 6},
    {"text": "대시보드 차트 추가", "urgency": 5, "importance": 6},

    # importance=7
    {"text": "Set up logging infrastructure", "urgency": 6, "importance": 7},
    {"text": "Implement error tracking", "urgency": 6, "importance": 7},
    {"text": "Add performance monitoring", "urgency": 5, "importance": 7},
    {"text": "모니터링 시스템 구축", "urgency": 6, "importance": 7},

    # importance=8
    {"text": "Implement access control", "urgency": 7, "importance": 8},
    {"text": "Add role-based permissions", "urgency": 6, "importance": 8},
    {"text": "Set up CI/CD pipeline", "urgency": 6, "importance": 8},
    {"text": "권한 관리 시스템 구현", "urgency": 7, "importance": 8},

    # importance=9
    {"text": "Implement data encryption", "urgency": 7, "importance": 9},
    {"text": "Add compliance auditing", "urgency": 6, "importance": 9},
    {"text": "Set up disaster recovery", "urgency": 7, "importance": 9},
    {"text": "데이터 암호화 구현", "urgency": 7, "importance": 9},

    # importance=10
    {"text": "Build authentication system", "urgency": 8, "importance": 10},
    {"text": "Implement payment processing", "urgency": 7, "importance": 10},
    {"text": "Add GDPR compliance", "urgency": 7, "importance": 10},
    {"text": "결제 시스템 구현", "urgency": 7, "importance": 10},
]

def main():
    # Load existing data
    data_file = Path("ml/training_data.json")
    with open(data_file) as f:
        existing_data = json.load(f)

    print(f"Current samples: {len(existing_data)}")

    # Add new samples
    augmented_data = existing_data + ADDITIONAL_SAMPLES_V2

    print(f"Adding: {len(ADDITIONAL_SAMPLES_V2)} new samples")
    print(f"Total samples: {len(augmented_data)}")

    # Save augmented data
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(augmented_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Training data augmented to {len(augmented_data)} samples")

    # Show distribution
    from collections import Counter
    urgency_dist = Counter(item["urgency"] for item in augmented_data)
    importance_dist = Counter(item["importance"] for item in augmented_data)

    print("\n📊 Urgency distribution:")
    for i in range(1, 11):
        count = urgency_dist.get(i, 0)
        bar = "█" * (count // 2)
        print(f"  {i:2d}: {count:3d} {bar}")

    print("\n📊 Importance distribution:")
    for i in range(1, 11):
        count = importance_dist.get(i, 0)
        bar = "█" * (count // 2)
        print(f"  {i:2d}: {count:3d} {bar}")

    # Calculate balance
    min_urgency = min(urgency_dist.values())
    max_urgency = max(urgency_dist.values())
    min_importance = min(importance_dist.values())
    max_importance = max(importance_dist.values())

    print(f"\n📈 Balance:")
    print(f"  Urgency: {min_urgency}-{max_urgency} samples per class")
    print(f"  Importance: {min_importance}-{max_importance} samples per class")

if __name__ == "__main__":
    main()
