#!/bin/bash
# SSH_WEB 야간 자율 작업 스크립트
# 실행: chmod +x overnight_tasks.sh && ./overnight_tasks.sh
# 예상 소요: 30-60분 (모델 응답 속도에 따라 다름)

set -e
cd "$(dirname "$0")"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="overnight_results/${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "=== SSH_WEB 야간 자율 작업 시작: $(date) ==="
echo "결과 저장 위치: $LOG_DIR"
echo ""

# ─────────────────────────────────────────────────
# 작업 1: 테스트 보강
# ─────────────────────────────────────────────────
echo "[1/5] 테스트 보강 시작..."
claude --dangerously-skip-permissions \
  -p "SSH_WEB 프로젝트의 테스트를 보강해줘.

현재 테스트 파일:
- tests/test_intent.py
- tests/test_priority.py
- tests/test_compression.py
- tests/test_chunker.py
- tests/test_router_v5.py
- tests/test_environment.py

작업:
1. 각 테스트 파일을 읽고 현재 커버리지 확인
2. 테스트가 부족한 모듈 파악 (특히 nlp/cache_manager.py, web_server.py API 엔드포인트)
3. 누락된 엣지 케이스 테스트 추가
4. 에러 핸들링 테스트 추가
5. 모든 테스트가 통과하는지 pytest로 확인
6. 결과를 ${LOG_DIR}/01_test_report.md 에 저장

중요: 기존 테스트를 깨뜨리지 마. 새 테스트만 추가." \
  --output-file "$LOG_DIR/01_test_log.txt" 2>&1 || true

echo "[1/5] 테스트 보강 완료"
echo ""

# ─────────────────────────────────────────────────
# 작업 2: 코드 품질 개선
# ─────────────────────────────────────────────────
echo "[2/5] 코드 품질 개선 시작..."
claude --dangerously-skip-permissions \
  -p "SSH_WEB 프로젝트의 Python 코드 품질을 개선해줘.

주요 파일:
- llm_router_v5.py (메인 라우터)
- nlp/compressor.py (텍스트 압축)
- nlp/text_chunker.py (텍스트 청킹)
- nlp/intent_detector.py (의도 감지)
- nlp/priority_ranker.py (우선순위)
- nlp/cache_manager.py (캐시)
- web_server.py (웹 서버)

작업:
1. 각 파일을 읽고 코드 품질 이슈 파악
2. 버그 수정 (논리 오류, 예외 처리 누락 등)
3. 타입 힌트가 누락된 함수에 추가
4. 중복 코드 제거
5. 변수명/함수명 개선 (영문)
6. 수정 후 pytest 실행해서 기존 테스트 통과 확인
7. 결과를 ${LOG_DIR}/02_quality_report.md 에 저장

중요: 동작을 변경하지 마. 리팩토링만 해. 수정 전후 테스트 통과 확인 필수." \
  --output-file "$LOG_DIR/02_quality_log.txt" 2>&1 || true

echo "[2/5] 코드 품질 개선 완료"
echo ""

# ─────────────────────────────────────────────────
# 작업 3: 보안 점검
# ─────────────────────────────────────────────────
echo "[3/5] 보안 점검 시작..."
claude --dangerously-skip-permissions \
  -p "SSH_WEB 프로젝트의 보안 취약점을 점검해줘.

점검 대상:
- 모든 Python 파일 (*.py)
- 모든 JavaScript 파일 (website/*.js)
- 모든 HTML 파일 (website/*.html)
- web_server.py의 API 엔드포인트

점검 항목:
1. XSS 취약점 (HTML/JS에서 사용자 입력 이스케이프 확인)
2. Command Injection (subprocess, os.system 사용 여부)
3. Path Traversal (파일 경로 검증)
4. SQL Injection (해당 시)
5. CORS 설정 확인
6. 입력 검증 누락
7. 에러 메시지에 민감 정보 노출
8. 하드코딩된 시크릿 확인

작업:
1. 전체 코드 스캔
2. 발견된 취약점 즉시 수정
3. 수정 후 테스트 통과 확인
4. 결과를 ${LOG_DIR}/03_security_report.md 에 저장 (심각도별 분류)

중요: .env 파일 내용은 절대 읽거나 출력하지 마." \
  --output-file "$LOG_DIR/03_security_log.txt" 2>&1 || true

echo "[3/5] 보안 점검 완료"
echo ""

# ─────────────────────────────────────────────────
# 작업 4: API 문서화
# ─────────────────────────────────────────────────
echo "[4/5] API 문서화 시작..."
claude --dangerously-skip-permissions \
  -p "SSH_WEB 프로젝트의 API 문서를 자동 생성해줘.

대상 파일:
- web_server.py (모든 API 엔드포인트)
- llm_router_v5.py (라우터 기능)

작업:
1. web_server.py를 읽고 모든 API 엔드포인트 추출
2. 각 엔드포인트의 HTTP 메서드, 경로, 파라미터, 응답 형식 파악
3. llm_router_v5.py의 주요 클래스/함수 문서화
4. API 문서를 ${LOG_DIR}/04_api_docs.md 에 저장

문서 형식:
- 각 엔드포인트별 설명, 요청/응답 예시
- 에러 코드 목록
- 사용 가능한 파라미터 설명" \
  --output-file "$LOG_DIR/04_docs_log.txt" 2>&1 || true

echo "[4/5] API 문서화 완료"
echo ""

# ─────────────────────────────────────────────────
# 작업 5: 리팩토링
# ─────────────────────────────────────────────────
echo "[5/5] 리팩토링 시작..."
claude --dangerously-skip-permissions \
  -p "SSH_WEB 프로젝트의 nlp 모듈을 리팩토링해줘.

대상:
- nlp/compressor.py
- nlp/text_chunker.py
- nlp/cache_manager.py
- nlp/__init__.py

작업:
1. 각 파일의 코드 구조 분석
2. 함수가 너무 길면 분리 (50줄 이상)
3. 매직 넘버를 상수로 추출
4. 에러 핸들링 개선
5. docstring 추가 (영문)
6. 불필요한 import 정리
7. 수정 후 pytest 실행해서 모든 테스트 통과 확인
8. 결과를 ${LOG_DIR}/05_refactor_report.md 에 저장

중요:
- 외부 인터페이스(함수 시그니처, 반환값)는 변경하지 마
- 기존 테스트 전부 통과해야 함
- 수정 전에 git diff로 변경사항 확인" \
  --output-file "$LOG_DIR/05_refactor_log.txt" 2>&1 || true

echo "[5/5] 리팩토링 완료"
echo ""

# ─────────────────────────────────────────────────
# 최종 요약
# ─────────────────────────────────────────────────
echo "=== 전체 작업 완료: $(date) ==="
echo ""
echo "결과 파일 목록:"
ls -la "$LOG_DIR/"
echo ""
echo "리포트 확인: cat $LOG_DIR/*.md"
echo "로그 확인: cat $LOG_DIR/*_log.txt"
