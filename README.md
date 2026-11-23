-# main 브랜치는 force push 등의 위험한 행동으로부터 보호되고 있습니다. 반드시 자기 이름 branch에서 개발하고 merge 요청하세요.

# AI Companion Robot

AI 컴패니언 로봇(이동형 돌봄 로봇 + 충전/종합 설정용 터치스크린 키오스크 콘셉트)의 단계별 기능을 구현한 Python 기반 프로토타입 프로젝트입니다.

---

## 1. 프로젝트 목표 및 현재 구현 상태

본 프로젝트는 고령자의 일상생활(대화, 복약, 실내 이동, 낙상 대응)과 주거 안전(가스불 차단)을 지원하는 통합 돌봄 소프트웨어 플랫폼 개발을 목표로 합니다.

* **구현 완료 (1~4단계 코어 · `companion_robot.py`)**: 한국어 TF-IDF 의도 분류 대화, 사용자 프로필, 복약 일정 알림, 키오스크 이용 안내, BFS 실내 경로 안내, 가상 거리·터치·낙상 센서, 로컬 알림 로그(`LOCAL_SIMULATION_ONLY`) 및 JSON 영속화.
* **구현 완료 (5단계 Smart Home Control · `smart_home/`)**: 가스불 차단기(IoT 가스밸브) 상태 조회, 원격/음성 차단(멱등성 지원), 장시간 개방(기본 30분) 안전 점검, 제어 어댑터 장애(오프라인/구동 실패) Fail-Safe 시뮬레이션 및 `5단계 · 스마트홈` GUI 탭.
* **참고**: 모든 센서·차단기 제어·긴급 알림은 소프트웨어 시뮬레이션이며 실제 물리 장치나 외부 기관(119/보호자) 연결은 발생하지 않습니다.

---

## 2. 빠른 실행 및 테스트

Python 표준 라이브러리 기반으로 별도 외부 패키지 설치 없이 바로 실행할 수 있습니다.

```bash
# 1) Tkinter GUI 실행 (5개 탭: 대화/프로필, 복약/키오스크, 실내 이동, 안전/통합, 스마트홈)
python companion_robot.py

# 2) 전체 단위/통합 테스트 실행 (코어 8건 + Smart Home 12건 = 총 20건)
python -m unittest -v
```

---

## 3. 프로젝트 문서 안내 (`docs/`) — 팀원 및 AI 에이전트 필독

기능을 추가하거나 타 모듈과 연동하기 전에 아래 문서를 먼저 확인하세요.

| 문서 | 설명 | 대상 |
| :--- | :--- | :--- |
| [docs/MODULE_INTEGRATION_GUIDE.md](docs/MODULE_INTEGRATION_GUIDE.md) | **팀 공통 확장 모듈 연동 규약** (패키지 소유권 분리, `companion_robot.py` 최소 수정 5대 규칙, JSON 키 예약, AI 에이전트 10원칙) | **전체 팀원 · AI 에이전트 필독** |
| [docs/SMART_HOME_DESIGN.md](docs/SMART_HOME_DESIGN.md) | Smart Home Control v1.0 상세 설계, API 계약 및 **바로 복사해 쓸 수 있는 호출 레퍼런스(Quickstart)** | 3번 모듈 연동/참조용 |
| [docs/BRD.md](docs/BRD.md) | 비즈니스 요구사항 정의서 (`BR-01`~`BR-07`, 렌탈 모델 43,900원, Ollama 비용 절감 방향) | 전체 |
| [docs/PRD.md](docs/PRD.md) | 제품 요구사항 정의서 (`FR-SH-01`~`09` + 타 팀원 구현용 복약 리마인더 고도화 `FR-MED-01`\~`05`) | 전체 |
| [docs/AboutThisProject.md](docs/AboutThisProject.md) | 프로젝트 배경, 하드웨어/소프트웨어 콘셉트 및 저장소 문서 관리 지침 | 전체 |
| [docs/KAN25_통합UML_검토보고_및_JIRA문구.md](docs/KAN25_통합UML_검토보고_및_JIRA문구.md) | 실제 코드베이스 기준 KAN-25 UML/요구사항 대조 및 정정 내역 | UML·JIRA 검토용 |
| [docs/KAN25_Component_통합수정_v2.png](docs/KAN25_Component_통합수정_v2.png) | 실제 저장소 기준 Component Diagram ([.drawio 원본](docs/KAN25_Component_통합수정_v2.drawio)) | 전체 |
| [docs/KAN25_UseCase_통합수정_v2.png](docs/KAN25_UseCase_통합수정_v2.png) | 실제 저장소 기준 Use Case Diagram ([.drawio 원본](docs/KAN25_UseCase_통합수정_v2.drawio)) | 전체 |
| [docs/가정 돌봄로봇 모듈 확장 UML 다이어그램.png](docs/가정%20돌봄로봇%20모듈%20확장%20UML%20다이어그램.png) | 코어 + 4대 확장 모듈 전체 클래스 다이어그램(v1.0) | 전체 |

---

## 4. 주요 파일 및 패키지 구조

### `companion_robot.py`
AI 컴패니언 로봇 코어 및 Tkinter GUI 실행 진입점입니다.
프로그램 실행 시 `demo_data/companion_state.json`에 아래 정보를 로컬 저장하며 재실행 시 복원합니다. (현재 프로토타입은 로그인/DB 없이 로컬 JSON 원자적 저장 방식 사용)
* `profile`: 사용자 프로필(ID, 이름, 선호사항)
* `history`: 대화 기록 및 의도 분류 결과
* `medications`: 등록된 복약 일정 및 일일 알림 기록
* `alerts`: 로컬 시뮬레이션 알림 로그
* `battery`, `status`: 로봇 배터리 잔량 및 상태
* `smart_home`: 가스불 차단기 및 시뮬레이션 장애 설정 상태

### `smart_home/` (독립 패키지 — 가스불 차단기 제어)
객체지향 분리와 어댑터 교체를 위해 코어와 분리된 Smart Home Control 패키지입니다.
* `models.py`: `ValveState`, `DeviceStatus`, `CommandResult`, `ApiResponse`
* `exceptions.py`: `SmartHomeError`, `DeviceNotFoundError`, `ApiConnectionError`, `CommandExecutionError`
* `interfaces.py`: `SmartDevice`(ABC), `SmartHomeApiClient`(ABC)
* `devices.py`: `GasValve` (IoT 가스밸브 도메인 모델)
* `adapters.py`: `MockSmartHomeApiClient` (로컬 시뮬레이터 및 오프라인/실패 장애 주입)
* `controller.py`: `SmartHomeController`, `create_default_controller()`
* `ui.py`: `build_smart_home_tab()` (`5단계 · 스마트홈` 탭 UI)

**간단 호출 예시** (상세 레퍼런스는 [docs/SMART_HOME_DESIGN.md](docs/SMART_HOME_DESIGN.md) 8절 참고):
```python
from companion_robot import JsonStore, Robot

robot = Robot(JsonStore("demo_data"))
reply, intent, _ = robot.start_conversation("가스불 꺼줘")
is_safe, msg = robot.check_gas_safety()
```

### 테스트 코드
* **`test_companion_robot.py`**: 코어 기능(의도 분류, 실내 경로, 거리센서, 복약 검증, 낙상 로컬 알림, 대화 영속화, 키오스크 가이드) 8개 테스트
* **`test_smart_home.py`**: Smart Home Control(`TC-SH-01`~`TC-SH-12` — 가스 상태 조회/차단/멱등성, 장시간 개방 경고, API 오프라인·명령 실패 Fail-Safe, 커스텀 어댑터 DIP, 대화 의도 비충돌, JSON 영속화) 12개 테스트

---

## 5. 향후 개발 방향

신규 모듈은 [docs/MODULE_INTEGRATION_GUIDE.md](docs/MODULE_INTEGRATION_GUIDE.md) 규약에 따라 루트 아래 독립 패키지로 구현합니다.

* **Family Memory Archive (`memory_archive/`)**: 가족 기억 저장·키워드/DB 검색 및 대화 활용
* **Health Monitoring (`health_monitor/`)**: 웨어러블 기기 연동 및 이상 징후 알림
* **Family & Visitor Recognition (`visitor_recognition/`)**: 가족/방문자 인식 및 보호자 알림 *(필수/선택 범위 팀 최종 확인)*
* **복약 리마인더 고도화 & 일상 대화 챗봇**: 복용 완료 확인·스누즈 재알림·미복용 경고([docs/PRD.md](docs/PRD.md) 3.2절) 및 일상 대화용 오픈웨이트(Ollama) 모델 연동 검토
