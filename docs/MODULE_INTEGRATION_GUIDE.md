# AI 컴패니언 로봇 — 팀 공통 확장 모듈 연동 규약 (v0.1)

| 항목 | 내용 |
| :--- | :--- |
| **문서 버전** | v0.2 |
| **작성일** | 2026-11-24 |
| **제정 권한** | 3번 개발자 (팀 리더 위임 규약) |
| **적용 대상** | 4인 개발팀 전체 및 각 팀원이 활용하는 AI 코딩 에이전트 |
| **목적** | 복수의 확장 모듈과 AI 에이전트가 동시 개발할 때 `companion_robot.py` 충돌·의존성 깨짐·회귀 오류를 원천 방지하기 위한 공용 계약 |

> **v0.2 변경 요약**: Section 3.6 시간/타임존 표준(RFC 3339 / ISO 8601 내부 UTC · 표시 계층 KST 변환) 추가, `memory_archive` SQLite 저장소 반영, `ai_model`/`medications` 향후 확장 DI 경계 및 `ui.py` refresh 콜백 반환 규약 반영.

---

## 1. 기준 코드베이스 및 브랜치 원칙

1. **기준 코드베이스**: 모든 PR과 모듈 통합의 기준은 `main` 브랜치의 `companion_robot.py` 및 `test_companion_robot.py`이다.
   * 원격 저장소에 남아 있는 `origin/companionrobot-sub`(`src/eldercare_robot/` 구조)는 참고용 구버전 스켈레톤이므로, 신규 기능은 `main` 기반 구조에 맞춘다.
2. **작업 브랜치**: 각 개발자는 본인 작업 브랜치(예: `Sangin`, `feature/<module-name>`)에서 개발하고, 검증 완료 후 `main`으로 PR 병합한다.
3. **공통 코어 보호 원칙**: `companion_robot.py` 내부 기존 클래스(`UserProfile`, `JsonStore`, `VoiceProcessor`, `Sensor` 계층, `Navigator`, `AlertService`, `MedicationManager`)의 기존 시그니처와 반환 포맷은 임의로 깨지 않는다.

---

## 2. 모듈별 파일 소유권 분리 (File Ownership Matrix)

각 확장 모듈은 루트에 **독립 패키지**와 **독립 테스트 파일**을 두며, 타 팀원의 패키지·테스트 파일을 직접 수정하지 않는다.

| UML 모듈 | 담당 패키지 디렉토리 | 전용 테스트 파일 |
| :--- | :--- | :--- |
| **2. Family Memory Archive** | `memory_archive/` | `test_memory_archive.py` |
| **3. Smart Home Control** | `smart_home/` | `test_smart_home.py` |
| **4. Health Monitoring** | `health_monitor/` | `test_health_monitor.py` |
| **5. Family & Visitor Recognition** | `visitor_recognition/` | `test_visitor_recognition.py` |

* 각 패키지는 최소한 아래 내부 역할 분리를 권장한다.
  * `interfaces.py` (추상 기반 클래스 / 어댑터 포트)
  * `models.py` (데이터 모델 / 상태 Enum)
  * `adapters.py` (외부 API · 로컬 LLM · 센서 Mock 및 실구현 어댑터)
  * `ui.py` (Tkinter 탭 빌더 함수 분리)
* UI나 비즈니스 로직에 직접 외부 API/LLM(Ollama 등)/하드웨어 호출을 박지 말고, 반드시 `interfaces.py` 추상 계층을 거친다.

---

## 3. `companion_robot.py` 최소 통합 5대 규약

`companion_robot.py`는 4개 모듈이 공통으로 만나는 유일한 진입점이므로, 아래 5개 규칙 외의 침습적 수정을 금지한다.

### 3.1 `Robot.__init__` 선택 인자 의존성 주입
* 신규 모듈 컨트롤러/매니저 및 향후 확장 컴포넌트는 **선택 인자(`= None`)**로 주입받는다. 기존 호출부 `Robot(store)`가 인자 없이도 정상 동작해야 한다.
  ```python
  def __init__(
      self,
      store: JsonStore,
      smart_home: SmartHomeController | None = None,
      health_monitor: HealthMonitor | None = None,
      *,
      memory_archive: MemoryArchive | None = None,
      ai_model: Any | None = None,
      medications: MedicationManager | None = None,
  ):
  ```
* `None`이 전달된 경우 내부에서 기본 Mock/로컬 구현으로 생성하고, `saved = store.load()`에서 자기 네임스페이스 키를 읽어 상태를 복원한다.
* 향후 **오픈웨이트(Ollama) 챗봇(`ai_model`)**이나 **복약 리마인더 고도화(`medications`)**를 교체 도입할 때도 기존 `Robot` 코어를 수정하지 않고 해당 선택 인자 DI를 통해 교체할 수 있도록 경계를 유지한다.

### 3.2 `companion_state.json` 및 SQLite 저장소 네임스페이스 규약
* **기존 6개 코어 키 보존**: `profile`, `battery`, `status`, `history`, `medications`, `alerts`의 구조와 의미를 변경하지 않는다.
* **모듈별 저장 위치**:

| 모듈 | 저장 방식 / 최상위 키 | 비고 |
| :--- | :--- | :--- |
| Family Memory Archive | `demo_data/memory_archive.sqlite3` (독립 SQLite) | `profile.user_id`/`name` 동기화(`register_user` upsert) |
| Smart Home Control | `companion_state.json` 내 `"smart_home"` | JSON 직렬화 dict |
| Health Monitoring | `companion_state.json` 내 `"health_monitor"` | JSON 직렬화 dict |
| Family & Visitor Recognition | `companion_state.json` 내 `"visitor_recognition"` (예약) | 미구현 |

* **구버전 하위 호환 필수**: `saved.get("<namespace>")`가 없거나 `None`이더라도 예외를 발생시키지 않고 안전한 기본 상태로 초기화해야 한다.

### 3.3 `IntentClassifier.EXAMPLES` 의도 이름 및 TF-IDF 충돌 방지
* `IntentClassifier`는 문자 2~3그램 TF-IDF + 코사인 유사도를 사용한다.
* **의도 키 접두사 규칙**: 각 모듈은 반드시 고유 접두사를 사용한다.
  * `memory_*` (`memory_search` 구현 완료)
  * `smart_home_*` (`smart_home_status`, `smart_home_shutoff` 구현 완료)
  * `health_*` (`health_check` 구현 완료)
  * `visitor_*` (예약)
* **충돌 방지**: 기존 `"status"`(`로봇 상태 확인`, `현재 상태 확인`) 등 코어 의도와 글자 조합이 겹치지 않도록 도메인 명사(예: `가스불`, `복약`, `심박수`, `가족 기억`, `방문자`)를 예시 문장에 명시적으로 포함한다.
* 의도를 추가한 개발자는 반드시 기존 코어 발화가 원래 의도로 분류되는지 회귀 테스트해야 한다.

### 3.4 `AlertService.create` 카테고리 접두사 및 시뮬레이션 고지
* 알림 로그 생성 시 아래 모듈별 카테고리 접두사를 사용한다.
  * `가족기억/...` | `스마트홈/...` | `건강/...` | `방문자/...`
* 모든 알림은 기존 `AlertService.create(category, message)` 규격을 그대로 따르며, `"delivery": "LOCAL_SIMULATION_ONLY"` 정책(실제 119/보호자 외부 발신 없음)을 준수한다.

### 3.5 `run_gui()` 탭 연결 및 갱신 규약
* GUI 위젯 작성 코드는 `companion_robot.py`에 직접 늘리지 않고 각 모듈의 `ui.py`에 분리한다.
* 표준 탭 빌더 시그니처(탭 전환 시 상태 동기화를 위해 `refresh` 콜백 반환 권장):
  ```python
  def build_<module>_tab(parent, robot, on_state_change) -> Callable[[], None]:
      ...
  ```
* `companion_robot.py`의 `run_gui()`에는 탭 프레임 생성 및 위 빌더 호출(2~3줄)만 추가한다. 기존 색상/폰트 스타일(`PANEL`, `FONT`, `"TLabel"`, `"Heading.TLabel"` 등)을 재사용해 화면 통일성을 유지한다.

### 3.6 시간 및 타임존 표준 (RFC 3339 / ISO 8601)
* **내부 저장·도메인 계층 = UTC (`+00:00`)**:
  * 모든 저장 타임스탬프(`AlertService`, `ConversationEntry`, `GasValve`, `HealthMonitor`, `MemoryArchive`)는 **UTC ISO 8601 (`+00:00`)**으로 저장한다.
  * 공통 헬퍼 [`time_utils.py`](../time_utils.py)의 `utc_now_iso()`, `to_utc_iso()`를 사용한다.
* **표시(UI / 대화 응답) 계층 = 로컬 KST (`+09:00`) 변환**:
  * Tkinter 탭, 알림 로그, 대화 요약 응답 등 사용자에게 보이는 문자열은 `time_utils.format_local_time(iso_str)`을 통해 **로컬 KST(`YYYY-MM-DD HH:MM:SS KST`)**로 변환해 표시한다.
  * 구버전 상태 파일에 타임존 없는 naive 문자열이 남아 있어도 예외 없이 표시한다.
* **일정 시각 비교 예외**: `MedicationManager.check_due(now)`는 사용자가 입력한 현지 24시간제 벽시계 시각(`"HH:MM"`)과의 비교이므로 로컬 `now` 기준을 유지한다.

---

## 4. 외부 라이브러리 및 AI 모델(Ollama 등) 사용 규약

1. **라이선스 원칙**:
   * 상업적 활용이 가능한 오픈소스 라이선스(**MIT, Apache-2.0, BSD, PSF** 등)만 허용한다.
   * 소스 공개 의무를 유발할 수 있는 강한 카피레프트 라이선스(**GPL, AGPL**) 패키지 도입은 금지한다.
2. **오프라인 단위 테스트 보장**:
   * 외부 API, 하드웨어, 로컬 LLM(**Ollama 오픈웨이트 모델** 등)을 연동하더라도, 반드시 **추상 어댑터 + Mock 구현체**를 함께 제공해야 한다.
   * `python -m unittest -v` 실행 시 외부 네트워크나 Ollama 서버가 꺼져 있는 환경에서도 모든 테스트가 100% 통과해야 한다.
3. **의존성 기록**:
   * 표준 라이브러리 외 패키지를 추가할 경우 저장소 루트에 `requirements.txt`를 두고, 선택 의존성인 경우 `ImportError` 시 안전한 폴백(또는 Mock) 동작을 고려한다.

---

## 5. PR 전 필수 검증 및 Git 위생 규칙

* **필수 테스트**: 커밋/PR 전 아래 명령을 실행해 기존 테스트와 본인 모듈 테스트가 모두 통과하는지 확인한다.
  ```bash
  python -m unittest -v
  ```
* **커밋 금지 파일**: 런타임 생성 데이터(`demo_data/`, `companion_state.json`), 캐시(`__pycache__/`, `.pytest_cache/`), 환경 변수/비밀키(`.env`), 개인용 비공개 초안은 커밋하지 않는다(`.gitignore`로 관리 권장).
* **문서 동기화**: 자신의 모듈에 새 `Robot` 통합 훅, JSON 키, 의존성을 추가했다면 관련 설계 문서 또는 `README.md`를 함께 갱신한다.

---

## 6. AI Agent Quick Rules (팀원용 에이전트 공유 체크리스트)

다른 팀원이 본인의 AI 코딩 에이전트에게 컨텍스트로 바로 넘길 수 있는 핵심 10원칙:

1. `main` 브랜치의 `companion_robot.py`를 기준으로 작업하고, 내 모듈 전용 패키지 디렉토리(`memory_archive/`, `smart_home/`, `health_monitor/`, `visitor_recognition/`) 안에 코드를 작성하라.
2. 타 팀원의 전용 패키지와 전용 테스트 파일은 수정하지 마라.
3. `companion_robot.py` 수정은 `Robot.__init__`(선택 인자 주입), `Robot.save`(예약 키 1개 추가), `IntentClassifier.EXAMPLES`, `Robot.generate_reply`, `run_gui()` 탭 등록 2~3줄로 제한하라.
4. `companion_state.json`에서는 내 모듈에 예약된 최상위 키만 읽고 쓰며, 해당 키가 없는 구버전 JSON도 크래시 없이 복원하라.
5. `IntentClassifier`에 의도를 추가할 때는 `모듈명_*` 접두사를 쓰고, 기존 `"status"`, `"emergency"`, `"medication"`, `"greeting"`, `"kiosk"` 테스트 발화가 깨지지 않는지 확인하라.
6. GUI 코드는 내 패키지 내 `ui.py`의 `build_<module>_tab(parent, robot, on_state_change)` 함수로 분리하라.
7. 외부 API·로컬 LLM(Ollama)·센서 연동은 반드시 추상 인터페이스와 Mock 어댑터를 분리해 네트워크/서버 없이도 동작하게 하라.
8. 외부 라이브러리는 상업용 허용 OSS(MIT/Apache-2.0/BSD)만 사용하고 `requirements.txt`에 명시하라.
9. 알림 생성은 `AlertService.create("모듈접두사/세부분류", ...)`를 사용하고, 시뮬레이션 고지를 누락하지 마라.
10. 작업 완료 후 `python -m unittest -v`로 기존 `test_companion_robot.py` 8개와 신규 모듈 테스트가 모두 PASS하는지 검증하라.
