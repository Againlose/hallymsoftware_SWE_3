*main 브랜치는 force push 등의 위험한 행동으로부터 보호되고 있습니다. 반드시 자기 이름 branch에서 개발하고 merge 요청하세요.*

# Version 0.2.0
정식_릴리즈_이후_메이저_패치.마이너_패치.버그픽스_사소한_수정

# AI Companion Robot

AI 컴패니언 로봇(이동형 돌봄 로봇 + 충전/종합 설정용 터치스크린 키오스크 콘셉트)의 단계별 기능을 구현한 Python 기반 통합 프로토타입 프로젝트입니다.

---

## 1. 프로젝트 목표 및 현재 구현 상태

본 프로젝트는 고령자의 일상생활(대화, 복약, 실내 이동, 낙상 대응), 주거 안전(가스불 차단), 건강 모니터링, 가족 기억 관리를 지원하는 통합 돌봄 소프트웨어 플랫폼 개발을 목표로 합니다.

* **구현 완료 (1~4단계 코어 · `companion_robot.py`)**: 한국어 TF-IDF 의도 분류 대화, 사용자 프로필(SQLite 자동 동기화), 복약 일정 알림, 키오스크 이용 안내, BFS 실내 경로 안내, 가상 거리·터치·낙상 센서, 로컬 알림 로그(`LOCAL_SIMULATION_ONLY`) 및 JSON 영속화.
* **구현 완료 (5단계 Smart Home Control · `smart_home/`)**: 가스불 차단기(IoT 가스밸브) 상태 조회, 원격/음성 차단(멱등성 지원), 장시간 개방(기본 30분) 안전 점검, 제어 어댑터 장애(오프라인/구동 실패) Fail-Safe 시뮬레이션 및 `5단계 · 스마트홈` 탭.
* **구현 완료 (6단계 Health Monitoring · `health_monitor/`)**: 심박수·산소포화도 수집(GUI 정상/이상 징후 시연 입력 포함), 측정 이력 KST 변환 표시, 연속 이상 징후 시 사용자·보호자 로컬 알림 및 대화 조회 연동.
* **구현 완료 (7단계 Family Memory Archive · `memory_archive/`)**: 개인·가족 보관함, 접근 권한, 기억 CRUD, 키워드·기간·인물·태그 검색, 버전 이력, 근거 미리보기(`demo_data/memory_archive.sqlite3`) 및 대화 검색 연동.
* **시간 표준**: 라이브러리·저장 계층(JSON/SQLite)은 **RFC 3339 / ISO 8601 UTC (`+00:00`)**로 저장하며, GUI·대화 응답 표시 계층에서 `time_utils.py`를 통해 **로컬 KST (`+09:00`)**로 변환해 표시합니다. *(복약 시각 비교는 현지 벽시계 `HH:MM` 기준)*
* **참고**: 코어 센서, 가스불 차단기, 건강 측정 및 알림은 소프트웨어 시뮬레이션입니다. 긴급·건강 알림은 앱 내부에만 기록되며 119나 보호자에게 외부 발송되지 않습니다.

---

## 2. 빠른 실행 및 테스트

Python 표준 라이브러리 기반으로 별도 외부 패키지 설치 없이 바로 실행할 수 있습니다.

```bash
# 1) Tkinter GUI 실행 (7개 탭: 대화/프로필, 복약/키오스크, 실내 이동, 안전/통합, 스마트홈, 건강 모니터링, 가족 기억)
python companion_robot.py

# 2) 전체 단위/통합 테스트 실행 (총 48건)
python -m unittest -v
```

---

## 3. 프로젝트 문서 안내 (`docs/`) — 팀원 및 AI 에이전트 필독

기능을 추가하거나 타 모듈과 연동하기 전에 아래 문서를 먼저 확인하세요.

| 문서 | 설명 | 대상 |
| :--- | :--- | :--- |
| [docs/MODULE_INTEGRATION_GUIDE.md](docs/MODULE_INTEGRATION_GUIDE.md) | **팀 공통 확장 모듈 연동 규약 v0.2** (패키지 소유권 분리, DI 경계, UTC/KST 시간 표준, JSON/SQLite 규약, AI 에이전트 10원칙) | **전체 팀원 · AI 에이전트 필독** |
| [docs/SMART_HOME_DESIGN.md](docs/SMART_HOME_DESIGN.md) | Smart Home Control v1.1 상세 설계, API 계약 및 **바로 복사해 쓸 수 있는 호출 레퍼런스(Quickstart)** | 3번 모듈 연동/참조용 |
| [docs/HEALTH_MONITOR_SRS.md](docs/HEALTH_MONITOR_SRS.md) | Health Monitoring 요구사항 명세서 (`v0.2`, 검증 추적표 포함) | 4번 모듈 참조용 |
| [docs/HEALTH_MONITOR_SD.md](docs/HEALTH_MONITOR_SD.md) | Health Monitoring 설계서 (`v0.2`, 상태 전이·예외·웨어러블 브리지 규약 포함) | 4번 모듈 참조용 |
| [docs/README_HEALTH_MONITOR.md](docs/README_HEALTH_MONITOR.md) | Health Monitoring CLI, 로컬 JSON 브리지(`HEALTH_WEARABLE_JSON`) 및 DUR 조회 안내 | 4번 모듈 실행 안내 |
| [docs/FAMILY_MEMORY_ARCHIVE.md](docs/FAMILY_MEMORY_ARCHIVE.md) | Family Memory Archive 구현 문서, SQLite 스키마 및 Python 호출 예시 | 2번 모듈 참조용 |
| [docs/BRD.md](docs/BRD.md) | 비즈니스 요구사항 정의서 (`v0.4`, `BR-01`~`BR-07`, 렌탈 모델 43,900원, Ollama 비용 절감 방향) | 전체 |
| [docs/PRD.md](docs/PRD.md) | 제품 요구사항 정의서 (`v0.4`, `FR-SH-01`~`09` + 향후 확장 복약 리마인더 고도화 `FR-MED-01`~`05`) | 전체 |
| [docs/AboutThisProject.md](docs/AboutThisProject.md) | 프로젝트 배경, 하드웨어/소프트웨어 콘셉트 및 저장소 문서 관리 지침 | 전체 |
| [docs/TODO.md](docs/TODO.md) | 통합 프로토타입 점검 결과 및 보완 체크리스트 | 전체 |
| [docs/KAN25_통합UML_검토보고_및_JIRA문구.md](docs/KAN25_통합UML_검토보고_및_JIRA문구.md) | 실제 코드베이스 기준 KAN-25 UML/요구사항 대조 및 정정 내역 | UML·JIRA 검토용 |
| [docs/KAN25_Component_통합수정_v2.png](docs/KAN25_Component_통합수정_v2.png) | 실제 저장소 기준 Component Diagram ([.drawio 원본](docs/KAN25_Component_통합수정_v2.drawio)) | 전체 |
| [docs/KAN25_UseCase_통합수정_v2.png](docs/KAN25_UseCase_통합수정_v2.png) | 실제 저장소 기준 Use Case Diagram ([.drawio 원본](docs/KAN25_UseCase_통합수정_v2.drawio)) | 전체 |
| [docs/가정 돌봄로봇 모듈 확장 UML 다이어그램.png](docs/가정%20돌봄로봇%20모듈%20확장%20UML%20다이어그램.png) | 코어 + 4대 확장 모듈 전체 클래스 다이어그램(v1.0) | 전체 |

---

## 4. 주요 파일 및 패키지 구조

### `companion_robot.py` & `time_utils.py`
AI 컴패니언 로봇 코어, 공통 UTC/KST 시간 유틸리티(`time_utils.py`) 및 Tkinter GUI 실행 진입점입니다.
프로그램 실행 시 `demo_data/companion_state.json`에 아래 정보를 로컬 저장하며 재실행 시 복원합니다.
* `profile`: 사용자 프로필(ID, 이름, 선호사항 — 변경 시 `memory_archive`와 자동 동기화)
* `history`: 대화 기록 및 의도 분류 결과 (UTC 저장)
* `medications`: 등록된 복약 일정 및 일일 알림 기록
* `alerts`: 로컬 시뮬레이션 알림 로그 (UTC 저장 / KST 표시)
* `battery`, `status`: 로봇 배터리 잔량 및 상태
* `smart_home`: 가스불 차단기 및 시뮬레이션 장애 설정 상태
* `health_monitor`: 건강 측정 이력 및 이상 징후 감지 상태

### `smart_home/` (5단계 · 가스불 차단기 제어)
객체지향 분리와 어댑터 교체를 위해 코어와 분리된 Smart Home Control 패키지입니다.
* `models.py`, `exceptions.py`, `interfaces.py` (`SmartDevice`, `SmartHomeApiClient`), `devices.py` (`GasValve`), `adapters.py` (`MockSmartHomeApiClient`), `controller.py` (`SmartHomeController`), `ui.py` (`build_smart_home_tab`)
* 상세 호출 예제는 [docs/SMART_HOME_DESIGN.md](docs/SMART_HOME_DESIGN.md) 8절 참고.

### `health_monitor/` (6단계 · 건강 모니터링)
심박수·산소포화도 수집(`MockWearable` 이상 징후 시연 UI 및 `HEALTH_WEARABLE_JSON` 로컬 브리지 지원)과 연속 이상 경고를 제공합니다. [운영 및 실행 안내](docs/README_HEALTH_MONITOR.md)

### `memory_archive/` (7단계 · 가족 기억 보관함)
개인·가족 보관함, 접근 권한, 기억 검색·편집·버전 이력과 근거 미리보기를 제공합니다. 데이터는 `demo_data/memory_archive.sqlite3`에 저장합니다. [구현 문서 및 Python 호출 예시](docs/FAMILY_MEMORY_ARCHIVE.md)

### 테스트 코드 (총 48건)
* **`test_companion_robot.py`** (8건): 코어 기능(의도 분류, 실내 경로, 거리센서, 복약 검증, 낙상 로컬 알림, 대화 영속화, 키오스크 가이드)
* **`test_smart_home.py`** (12건): Smart Home Control(`TC-SH-01`~`TC-SH-12`)
* **`test_health_monitor.py`** (10건): 건강 측정 유효성·이탈 규칙·역할별 알림·DUR 오프라인 계약
* **`test_memory_archive.py`** (12건): 재실행, 검색 필터, 권한 회수, 버전 충돌, 손상 DB 안전 복구
* **`test_integration.py`** (6건): 4개 영역 동시 영속화, `Robot`↔`health_monitor` 통합, 프로필 이름 동기화, 전체 의도 TF-IDF 비충돌, UTC/KST 변환, 향후 확장 DI 검증

---

## 5. 향후 개발 방향 (DI 확장 경계 확보 완료)

신규 모듈 및 고도화 기능은 [docs/MODULE_INTEGRATION_GUIDE.md](docs/MODULE_INTEGRATION_GUIDE.md) 규약과 `Robot.__init__` 선택 인자 DI를 통해 기존 코어에 종속성을 주지 않고 확장할 수 있습니다.

* **Family & Visitor Recognition (`visitor_recognition/`)**: 가족/방문자 인식 및 보호자 알림
* **복약 리마인더 고도화 (`medications` DI)**: 복용 완료 확인·스누즈 재알림·미복용 경고([docs/PRD.md](docs/PRD.md) 3.2절)
* **일상 대화 챗봇 (`ai_model` DI)**: 오픈웨이트(Ollama) 모델 연동 및 Mock 어댑터
* **Family Memory Archive 확장**: 파일 첨부, 의미 검색(pgvector) 및 RAG 대화 연동
