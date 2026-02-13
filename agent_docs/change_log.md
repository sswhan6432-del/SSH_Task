# Change Log

## 2026-02-13

[20260213] [bugfix] [web_server.py]
> 포트 8080 "Address already in use" 에러 해결
- ReusableHTTPServer 클래스 추가 (SO_REUSEADDR 설정)
- RouterHandler에 allow_reuse_address = True 추가
- server_bind() 메서드 오버라이드로 socket 옵션 강제 설정
- 구형 web_server.py 프로세스(PID 51879, 52395) 강제 종료
- 웹 서버 정상 시작 확인 완료 (http://localhost:8080)

## 2026-02-12

[20260212] [feat] [CLAUDE.md]
> 로그 템플릿 형식을 압축된 형태로 변경
- CLAUDE.md 파일의 Log Template 섹션 수정
- 토큰 효율성 향상 및 가독성 개선

[20260212] [setup] [agent_docs/]
> agent_docs 디렉토리 및 change_log.md 파일 생성
- 로그 시스템 초기 구축
- 새로운 로그 형식 테스트

[20260212] [cleanup] [tools/]
> 사용되지 않는 시스템 파일 및 캐시 삭제
- .DS_Store (6KB) 제거
- __pycache__/ (116KB) 제거
- 총 122KB 공간 확보

[20260212] [setup] [.gitignore]
> .gitignore 파일 생성 및 표준 패턴 추가
- macOS 시스템 파일 (.DS_Store 등)
- Python 캐시 및 빌드 파일
- 가상환경, IDE 설정, 환경 변수 파일

