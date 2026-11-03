# 노인 생활보조 AI 로봇 (Eldercare AI Robot)

아파트·주거 공간에서 고령자의 생활을 보조하는 **소형 실내 로봇 소프트웨어 프로젝트**입니다. UML 설계의 주요 기능을 Python 모듈로 나눈 **실행 가능한 시뮬레이션 프로토타입**입니다.

> ⚠️ **안전 고지:** 현재 코드는 학습·시연용입니다. 실제 낙상 진단, 응급 신고, 복약 처방, 모터 구동 또는 자율주행을 수행하지 않습니다. 사람의 안전이 관련된 실제 환경에 그대로 배포하지 마세요.

## 주요 기능 및 구현 상태

| 기능 | 구현된 시뮬레이션 | 실제 제품화를 위한 추가 작업 |
|---|---|---|
| 낙상 감지 | 자세·급격한 움직임·무동작 시간 기반 의심 판별 | 카메라/IMU 연동, AI 모델 검증, 사용자 응답 확인 |
| 복약 관리 | 일정 시각 알림 및 중복 방지 | 스케줄러, 영속 저장, 보호자 설정, 복약 확인 |
| 실내 이동 보조 | 장애물 거리 기반 이동 허용·비상 정지 상태 | ROS 2/Nav2, 센서 융합, 모터·안전 회로 |
| 편의시설 안내 | 승강기·인터폰 안내 문구 | 음성 입출력, 기기별 UI/접근성 검증 |
| 키오스크 안내 | 주문 단계별 안내 문구 | OCR, 화면 인식, 음성 안내, 실제 화면별 시나리오 |
| 보호자 알림 | 로컬 이벤트 기록 | 인증된 서버/API, 동의 및 보안 정책 |

## 빠른 시작

Python 3.10 이상을 준비합니다.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
eldercare-demo
python -m pytest
```

선택적 기능 패키지 설치:

```bash
python -m pip install -e ".[vision,medication,speech,kiosk,api,dev]"
```

`rclpy` 및 Nav2는 ROS 2 배포판에 맞춰 별도 설치해야 하며, `pytesseract`는 시스템 Tesseract 엔진도 필요합니다. 선택 패키지는 현재 시뮬레이션 실행에 필요하지 않습니다.

## 프로젝트 구조

```text
eldercare-ai-robot/
├── src/eldercare_robot/
│   ├── main.py             # 시연 실행
│   ├── controller.py       # 통합 안전 이벤트 처리
│   ├── fall_detection.py   # 낙상 의심 판별
│   ├── medication.py       # 복약 일정
│   ├── mobility.py         # 이동 안전 게이트
│   ├── guidance.py         # 시설·키오스크 안내
│   └── notifications.py    # 보호자 알림 기록
├── tests/test_robot.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_PLAN.md
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

## 개발 로드맵

1. **프로토타입:** 시뮬레이션과 단위 테스트 (현재 저장소)
2. **알파:** ROS 2/센서 연동, 모듈 통합, 안전 정지 검증
3. **베타:** 동의 기반 주거 환경 시험, 오탐 분석, 접근성 개선
4. **릴리즈:** 보안·안전 검증, 배포, 업데이트·롤백
5. **운영:** 모니터링, 오류 수정, 회귀 테스트

단계별 제안 일정과 검증 항목은 [개발 계획](docs/DEVELOPMENT_PLAN.md), 구성 요소는 [아키텍처](docs/ARCHITECTURE.md)를 참고하세요.

## GitHub 업로드

```bash
git init
git add .
git commit -m "Initial simulated eldercare robot prototype"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

GitHub에서 빈 저장소를 먼저 만들고 `USERNAME/REPOSITORY`를 실제 값으로 변경하세요. `.env`에 넣은 토큰·개인정보·영상 기록은 업로드하지 마세요.

## 라이선스

MIT — [LICENSE](LICENSE) 참고.
