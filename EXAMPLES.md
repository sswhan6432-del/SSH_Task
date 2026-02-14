# 💡 LLM Router v5.0 실전 예제 모음

> 복사해서 바로 쓸 수 있는 실무 예제

---

## 📑 목차

1. [코드 분석 & 리뷰](#1-코드-분석--리뷰)
2. [버그 수정](#2-버그-수정)
3. [기능 구현](#3-기능-구현)
4. [API 개발](#4-api-개발)
5. [테스트 작성](#5-테스트-작성)
6. [문서 작성](#6-문서-작성)
7. [리팩토링](#7-리팩토링)
8. [데이터베이스](#8-데이터베이스)
9. [성능 최적화](#9-성능-최적화)
10. [보안 강화](#10-보안-강화)

---

## 1. 코드 분석 & 리뷰

### 예제 1-1: 전체 파일 코드 리뷰

```bash
python3 llm_router_v5.py "app.py 파일 코드 리뷰해주세요" --v5 --friendly
```

**결과:**
```
Ticket A: 코드 품질 분석
  Intent: analyze (95%)
  Route: claude

다음을 확인:
- 코드 스타일
- 잠재적 버그
- 성능 이슈
- 베스트 프랙티스
```

### 예제 1-2: 보안 취약점 분석

```bash
python3 llm_router_v5.py \
  "auth.py 파일의 보안 취약점을 찾아주세요. SQL Injection, XSS, CSRF 중점 확인" \
  --v5 --compress --show-stats
```

### 예제 1-3: 성능 병목 찾기

```bash
python3 llm_router_v5.py \
  "data_processor.py의 성능 병목을 찾고 개선 방안을 제시해주세요" \
  --v5 --economy quality
```

---

## 2. 버그 수정

### 예제 2-1: 에러 메시지로 버그 찾기

```bash
python3 llm_router_v5.py \
  "login.py 41번째 줄에서 NullPointerException 발생. 원인 분석 및 수정" \
  --v5 --compress
```

### 예제 2-2: 간헐적 버그 디버깅

```bash
python3 llm_router_v5.py \
  "결제 처리 중 10%의 확률로 실패하는 버그 원인 찾기. payment.py 파일 분석" \
  --v5 --friendly --economy balanced
```

### 예제 2-3: 통합 테스트 실패 수정

```bash
python3 llm_router_v5.py \
  "test_integration.py의 test_user_flow 실패. 로그: 'User not found'. 원인 및 수정" \
  --v5 --show-stats
```

---

## 3. 기능 구현

### 예제 3-1: 사용자 인증 시스템

```bash
python3 llm_router_v5.py \
  "JWT 기반 사용자 인증 시스템 구현
   1. 회원가입 (이메일, 비밀번호)
   2. 로그인 (JWT 토큰 발급)
   3. 로그아웃 (토큰 무효화)
   4. 비밀번호 재설정" \
  --v5 --compress --compression-level 2 --show-stats
```

**결과:**
```
4개 작업으로 분할:
  A: JWT 인증 구조 설계 (우선순위 90)
  B: 회원가입 API (우선순위 81)
  C: 로그인/로그아웃 API (우선순위 81)
  D: 비밀번호 재설정 (우선순위 56)

토큰 절감: 1,200 → 720 (40%)
```

### 예제 3-2: 파일 업로드 기능

```bash
python3 llm_router_v5.py \
  "이미지 업로드 기능 구현
   - 최대 5MB
   - jpg, png만 허용
   - S3 저장
   - 썸네일 자동 생성" \
  --v5 --compress
```

### 예제 3-3: 검색 기능

```bash
python3 llm_router_v5.py \
  "상품 검색 API 구현
   - 키워드 검색 (제목, 설명)
   - 카테고리 필터
   - 가격 범위 필터
   - 정렬 (인기순, 최신순, 가격순)
   - 페이지네이션 (20개씩)" \
  --v5 --friendly
```

---

## 4. API 개발

### 예제 4-1: REST API CRUD

```bash
python3 llm_router_v5.py \
  "게시판 REST API 구현
   GET    /posts          - 목록 조회
   GET    /posts/:id      - 상세 조회
   POST   /posts          - 게시글 작성
   PUT    /posts/:id      - 게시글 수정
   DELETE /posts/:id      - 게시글 삭제

   Express.js + MongoDB 사용" \
  --v5 --compress --economy balanced
```

### 예제 4-2: GraphQL API

```bash
python3 llm_router_v5.py \
  "사용자 관리 GraphQL API 구현
   - Query: users, user(id)
   - Mutation: createUser, updateUser, deleteUser
   - 인증: JWT 토큰
   - Apollo Server 사용" \
  --v5 --show-stats
```

### 예제 4-3: WebSocket 실시간 API

```bash
python3 llm_router_v5.py \
  "실시간 채팅 WebSocket API 구현
   - 메시지 전송/수신
   - 온라인 사용자 목록
   - 타이핑 표시
   - Socket.io 사용" \
  --v5 --compress
```

---

## 5. 테스트 작성

### 예제 5-1: 단위 테스트

```bash
python3 llm_router_v5.py \
  "auth_service.py의 단위 테스트 작성
   - login() 함수 테스트 (성공/실패 케이스)
   - logout() 함수 테스트
   - validateToken() 함수 테스트
   Jest 사용" \
  --v5 --compress
```

### 예제 5-2: 통합 테스트

```bash
python3 llm_router_v5.py \
  "회원가입→로그인→프로필 조회 통합 테스트 작성
   - Supertest 사용
   - 테스트 DB 사용
   - 각 단계별 검증" \
  --v5 --friendly
```

### 예제 5-3: E2E 테스트

```bash
python3 llm_router_v5.py \
  "결제 플로우 E2E 테스트 작성
   1. 상품 선택
   2. 장바구니 담기
   3. 결제 정보 입력
   4. 결제 완료 확인
   Cypress 사용" \
  --v5 --show-stats
```

---

## 6. 문서 작성

### 예제 6-1: API 문서

```bash
python3 llm_router_v5.py \
  "REST API 문서 작성 (Swagger/OpenAPI 3.0)
   - 모든 엔드포인트 스펙
   - 요청/응답 예제
   - 에러 코드 정의
   - 인증 방법" \
  --v5 --compress
```

### 예제 6-2: README 작성

```bash
python3 llm_router_v5.py \
  "프로젝트 README.md 작성
   - 프로젝트 소개
   - 설치 방법
   - 사용법
   - 라이선스
   - 기여 가이드" \
  --v5 --friendly
```

### 예제 6-3: 코드 주석

```bash
python3 llm_router_v5.py \
  "database.py 파일에 JSDoc 주석 추가
   - 각 함수 설명
   - 파라미터 타입
   - 반환값
   - 예외 처리" \
  --v5
```

---

## 7. 리팩토링

### 예제 7-1: 코드 정리

```bash
python3 llm_router_v5.py \
  "legacy_code.js 리팩토링
   - 중복 코드 제거
   - 함수 분리
   - 변수명 개선
   - 에러 처리 추가" \
  --v5 --compress
```

### 예제 7-2: 아키텍처 개선

```bash
python3 llm_router_v5.py \
  "MVC 패턴으로 리팩토링
   현재: 단일 파일 (app.js 500줄)
   목표: Controller, Model, View 분리" \
  --v5 --economy quality
```

### 예제 7-3: 타입스크립트 전환

```bash
python3 llm_router_v5.py \
  "JavaScript → TypeScript 전환
   - 타입 정의
   - 인터페이스 작성
   - strict 모드 적용" \
  --v5 --show-stats
```

---

## 8. 데이터베이스

### 예제 8-1: 스키마 설계

```bash
python3 llm_router_v5.py \
  "전자상거래 DB 스키마 설계
   테이블: users, products, orders, order_items
   - 관계 정의
   - 인덱스 설계
   - 제약조건
   PostgreSQL 사용" \
  --v5 --compress --friendly
```

### 예제 8-2: 마이그레이션

```bash
python3 llm_router_v5.py \
  "users 테이블에 email_verified 컬럼 추가
   - ALTER TABLE 작성
   - Rollback 스크립트
   - 기존 데이터 처리 (default: false)" \
  --v5
```

### 예제 8-3: 쿼리 최적화

```bash
python3 llm_router_v5.py \
  "느린 쿼리 최적화
   SELECT * FROM orders JOIN users ... (3초 소요)
   - 쿼리 분석
   - 인덱스 추천
   - 개선된 쿼리 작성" \
  --v5 --show-stats
```

---

## 9. 성능 최적화

### 예제 9-1: 프론트엔드 최적화

```bash
python3 llm_router_v5.py \
  "React 앱 성능 최적화
   - 번들 크기 줄이기
   - Code splitting
   - Lazy loading
   - 이미지 최적화
   - Lighthouse 점수 80+ 목표" \
  --v5 --compress
```

### 예제 9-2: 백엔드 최적화

```bash
python3 llm_router_v5.py \
  "API 응답 속도 개선
   현재: 평균 2초
   목표: 평균 500ms
   - DB 쿼리 최적화
   - 캐싱 (Redis)
   - N+1 문제 해결" \
  --v5 --economy quality
```

### 예제 9-3: 메모리 최적화

```bash
python3 llm_router_v5.py \
  "메모리 누수 해결
   - 메모리 프로파일링
   - 순환 참조 찾기
   - 이벤트 리스너 정리
   - 타이머 정리" \
  --v5 --show-stats
```

---

## 10. 보안 강화

### 예제 10-1: 인증/인가 강화

```bash
python3 llm_router_v5.py \
  "인증/인가 보안 강화
   - Rate limiting (시간당 100회)
   - CSRF 토큰
   - XSS 방어
   - SQL Injection 방지
   - Helmet.js 적용" \
  --v5 --compress --friendly
```

### 예제 10-2: 데이터 암호화

```bash
python3 llm_router_v5.py \
  "민감 데이터 암호화
   - 비밀번호: bcrypt (10 rounds)
   - 개인정보: AES-256
   - 통신: HTTPS/TLS 1.3
   - 저장: 암호화된 환경변수" \
  --v5 --show-stats
```

### 예제 10-3: 권한 관리

```bash
python3 llm_router_v5.py \
  "RBAC (Role-Based Access Control) 구현
   역할: admin, editor, viewer
   - 역할별 권한 정의
   - 미들웨어 구현
   - 라우트 보호" \
  --v5 --compress
```

---

## 💼 실무 시나리오

### 시나리오 1: 급한 버그 수정

```bash
# 상황: 프로덕션에서 로그인 에러 발생
python3 llm_router_v5.py \
  "긴급: 프로덕션 로그인 500 에러
   에러: 'Cannot read property id of undefined'
   파일: auth_controller.js:45
   즉시 원인 파악 및 핫픽스 필요" \
  --v5 --economy quality --show-stats
```

### 시나리오 2: 신규 기능 개발 (스프린트)

```bash
# 상황: 2주 스프린트로 알림 기능 개발
python3 llm_router_v5.py \
  "알림 기능 전체 구현
   1주차:
     - 알림 DB 스키마 설계
     - 알림 생성 API
     - 알림 목록 API
   2주차:
     - 실시간 알림 (WebSocket)
     - 알림 읽음 처리
     - 알림 설정 (on/off)

   기술 스택: Node.js, PostgreSQL, Socket.io" \
  --v5 --compress --compression-level 2 --show-stats --friendly
```

### 시나리오 3: 레거시 코드 개선

```bash
# 상황: 5년 전 코드 현대화
python3 llm_router_v5.py \
  "레거시 jQuery 코드를 React로 마이그레이션
   - 단계별 마이그레이션 계획
   - 공존 전략 (jQuery + React)
   - 컴포넌트 분리
   - 테스트 작성
   - 점진적 배포" \
  --v5 --economy balanced --show-stats
```

---

## 🎯 사용 팁

### 팁 1: 구체적으로 요청하기

```bash
# ❌ 나쁜 예
python3 llm_router_v5.py "앱 만들어줘"

# ✅ 좋은 예
python3 llm_router_v5.py \
  "할 일 관리 웹앱 구현
   - CRUD 기능
   - 완료 체크
   - 마감일 설정
   - 우선순위 (상/중/하)
   - React + Firebase" \
  --v5 --compress
```

### 팁 2: 컨텍스트 제공하기

```bash
# ✅ 좋은 예 (컨텍스트 포함)
python3 llm_router_v5.py \
  "Next.js 13 App Router 프로젝트에서
   Server Component로 블로그 목록 페이지 구현
   - ISR (10분마다 갱신)
   - 메타데이터 SEO 최적화
   - Markdown 렌더링" \
  --v5 --compress --friendly
```

### 팁 3: 우선순위 명시하기

```bash
# ✅ 우선순위 명시
python3 llm_router_v5.py \
  "다음 작업 중 긴급한 것부터 처리:
   1. [긴급] 결제 버그 수정
   2. [중요] 검색 기능 추가
   3. [일반] 코드 리팩토링" \
  --v5 --smart-priority --show-stats
```

---

## 📊 결과 비교 (v4 vs v5)

### 동일 요청 비교

**요청:**
```
"사용자 인증 시스템 구현 (회원가입, 로그인, 로그아웃)"
```

**v4.0 결과:**
```bash
python3 llm_router.py "사용자 인증 시스템 구현 (회원가입, 로그인, 로그아웃)"

# 결과:
# 작업 1개 (분할 안 됨)
# 토큰: 850
# 시간: 1.8초
# 우선순위: 없음
```

**v5.0 결과:**
```bash
python3 llm_router_v5.py \
  "사용자 인증 시스템 구현 (회원가입, 로그인, 로그아웃)" \
  --v5 --compress --show-stats

# 결과:
# 작업 3개로 분할
#   A: 회원가입 (우선순위 81, 280 토큰)
#   B: 로그인 (우선순위 90, 260 토큰)
#   C: 로그아웃 (우선순위 49, 180 토큰)
# 총 토큰: 720 (v4 대비 15% 절감)
# 시간: 2.3초
# 의도 정확도: 94%
```

**결론:**
- 토큰 절감: 15%
- 작업 분리: 더 명확
- 우선순위: 자동 판단
- 시간: 0.5초 증가 (허용 범위)

---

## 🔗 관련 문서

- [빠른 시작](QUICK_START.md) - 기본 사용법
- [사용 가이드](USER_GUIDE.md) - 상세 가이드
- [문서 인덱스](DOCUMENTATION_INDEX.md) - 전체 문서

---

**예제 추가 요청**: 더 필요한 예제가 있다면 Issue에 남겨주세요!
