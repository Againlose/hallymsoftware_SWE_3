# Smart Home Control 상세 설계 및 API 인터페이스 규약 (v0.2)

| 항목 | 내용 |
| :--- | :--- |
| **문서 버전** | v0.2 |
| **작성일** | 2026-11-23 |
| **작성자** | 3번 개발자 (Smart Home Control / BRD / PRD 담당) |
| **상위 및 연계 문서** | `PRD.md` (v0.2), `MODULE_INTEGRATION_GUIDE.md` (v0.1) |
| **기준 코드베이스** | `hallymsoftware_SWE_3` (`Sangin` / `main` `7043a17`) |
| **문서 목적** | 구현 전 패키지 경계·인터페이스·JSON 규약·테스트 기준을 고정하고, AI/인간 개발자가 환각 없이 일관되게 참조할 수 있는 설계 규약 제공 |

> **v0.2 변경 요약**: 다중 외부 스마트홈 플랫폼 논의 생략(가스불 차단기 전용 어댑터 계약으로 단순화), `MODULE_INTEGRATION_GUIDE.md`를 팀 공통 통합 기준으로 명시.

---

## 1. 패키지 구조 및 책임 분리

기존 단일 파일(`companion_robot.py`, 616줄)에 도메인 로직을 누적하지 않고, 객체지향 원칙(SRP, DIP)과 팀 공통 연동 규약(`MODULE_INTEGRATION_GUIDE.md`)을 지키기 위해 `smart_home/` 독립 패키지로 분리한다.

```text
hallymsoftware_SWE_3/
├── companion_robot.py          # 기존 1~4단계 코어 (최소 통합 훅만 추가)
├── test_companion_robot.py     # 기존 8개 회귀 테스트 (무수정 통과 유지)
├── test_smart_home.py          # Smart Home 전용 단위/통합 테스트 스위트 (신규)
└── smart_home/                 # Smart Home Control 독립 패키지 (신규)
    ├── __init__.py             # 공개 심볼 export
    ├── models.py               # 상태 Enum 및 데이터 모델(DeviceStatus, CommandResult, ApiResponse)
    ├── exceptions.py           # 도메인/API 예외 계층
    ├── interfaces.py           # SmartDevice(ABC), SmartHomeApiClient(ABC)
    ├── devices.py              # GasValve(SmartDevice 구현체)
    ├── adapters.py             # MockSmartHomeApiClient (향후 게이트웨이/HTTP 어댑터 확장 지점)
    ├── controller.py           # SmartHomeController (인터페이스에만 의존)
    └── ui.py                   # Tkinter '5단계 · 스마트홈' 탭 빌더
```

### 모듈별 책임 요약

| 파일 | 핵심 책임 | 의존 대상 |
| :--- | :--- | :--- |
| `models.py` | 불변/구조화 데이터 모델(`ValveState`, `DeviceStatus`, `CommandResult`, `ApiResponse`) | Python 표준 라이브러리(`dataclasses`, `enum`) |
| `exceptions.py` | Smart Home 도메인 예외(`SmartHomeError` 하위 계층) | 표준 예외(`Exception`) |
| `interfaces.py` | 추상 포트 정의(`SmartDevice`, `SmartHomeApiClient`) | `models.py`, `abc` |
| `devices.py` | 가스밸브 도메인 상태 전이 및 직렬화(`GasValve`) | `interfaces.py`, `models.py`, `exceptions.py` |
| `adapters.py` | 가스불 차단기 로컬 Mock API 시뮬레이터(`MockSmartHomeApiClient`) | `interfaces.py`, `models.py`, `exceptions.py` |
| `controller.py` | 기기 등록, 상태 조회, 가스 차단 요청, 장시간 개방 점검(`SmartHomeController`) | `interfaces.py`, `models.py`, `exceptions.py` |
| `ui.py` | 키오스크/데스크톱 GUI 스마트홈 탭 UI 구성(`build_smart_home_tab`) | `tkinter`, `Robot`/`SmartHomeController` 공개 메서드 |

---

## 2. UML 다이어그램 v1.0 매핑

`가정 돌봄로봇 모듈 확장 UML 다이어그램.png`의 `3. Smart Home Control` 설계와 구현 심볼을 아래와 같이 1:1 대응시킨다.

| UML 요소 | UML 멤버 | Python 구현 심볼 | 비고 |
| :--- | :--- | :--- | :--- |
| `<<interface>> 스마트기기` | `+ 상태조회()`<br>`+ 명령처리()` | `SmartDevice(ABC)`<br>`get_status()`<br>`handle_command(command, params)` | 추상 기반 클래스로 향후 기기 확장 기반 제공 |
| `가스밸브` | `- 차단상태: boolean`<br>`+ 가스차단()` | `GasValve(SmartDevice)`<br>`is_shut_off: bool`<br>`shut_off()` | `ValveState`와 연동하여 세부 상태까지 시뮬레이션 |
| `스마트홈제어기` | `+ 기기상태조회()`<br>`+ 가스차단요청()` | `SmartHomeController`<br>`get_device_status(device_id)`<br>`request_gas_shutoff(device_id)` | UML의 "스마트홈 호출" 관계를 `SmartHomeApiClient` 포트로 구체화 |
| *(외부 연동 계층 확장)* | 가스불 차단기 API 호출 | `SmartHomeApiClient(ABC)` / `MockSmartHomeApiClient` | Port-Adapter 패턴으로 차단기 통신 계층 격리 |

---

## 3. 상세 인터페이스 및 메서드 시그니처 규약

### 3.1 데이터 모델 (`smart_home/models.py`)

```python
class ValveState(str, Enum):
    OPEN = "OPEN"                 # 밸브 열림 (가스 공급 중)
    CLOSED = "CLOSED"             # 밸브 잠김 (차단 완료)
    SHUTTING_OFF = "SHUTTING_OFF" # 차단 명령 처리 중 (전이 상태)
    ERROR = "ERROR"               # 기기 오류
    OFFLINE = "OFFLINE"           # 통신 두절

@dataclass
class DeviceStatus:
    device_id: str
    device_type: str              # 예: "gas_valve"
    name: str                     # 예: "주방 가스밸브"
    state: ValveState
    is_shut_off: bool
    opened_minutes: int           # 열림 유지 경과 시간(분, 시뮬레이션 값)
    updated_at: str               # ISO 8601 (timespec="seconds")
    source: str                   # "mock_api" 등 출처 표기

@dataclass
class CommandResult:
    device_id: str
    command: str                  # 예: "SHUT_OFF"
    success: bool
    previous_state: ValveState
    current_state: ValveState
    message: str                  # 사용자/로그용 한국어 안내 문구
    timestamp: str
    simulated: bool = True

@dataclass
class ApiResponse:
    ok: bool
    status_code: int              # 개념적 상태 코드 (200, 503, 504 등)
    payload: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
```

### 3.2 예외 계층 (`smart_home/exceptions.py`)

* `SmartHomeError(Exception)`: 스마트홈 모듈 최상위 예외
* `DeviceNotFoundError(SmartHomeError)`: 등록되지 않은 `device_id` 조회/제어 시 발생
* `ApiConnectionError(SmartHomeError)`: 외부/로컬 차단기 API 연결 실패 또는 타임아웃 시 발생
* `CommandExecutionError(SmartHomeError)`: 지원하지 않는 명령 또는 기기 제어 실패 시 발생

### 3.3 추상 인터페이스 (`smart_home/interfaces.py`)

```python
class SmartDevice(ABC):
    @property
    @abstractmethod
    def device_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_status(self) -> DeviceStatus:
        """현재 기기 상태를 반환한다 (UML: 상태조회)."""

    @abstractmethod
    def handle_command(self, command: str, params: dict[str, Any] | None = None) -> CommandResult:
        """표준 명령 문자열을 처리한다 (UML: 명령처리)."""

class SmartHomeApiClient(ABC):
    @abstractmethod
    def fetch_device_status(self, device_id: str) -> ApiResponse:
        """차단기 제어 어댑터로부터 기기 상태를 조회한다."""

    @abstractmethod
    def send_device_command(
        self, device_id: str, command: str, params: dict[str, Any] | None = None
    ) -> ApiResponse:
        """차단기 제어 어댑터로 기기 제어 명령을 전송한다."""

    @abstractmethod
    def health_check(self) -> bool:
        """차단기 제어 게이트웨이 연결 상태를 점검한다."""
```

### 3.4 도메인 구현체 (`smart_home/devices.py`)

* **`GasValve(SmartDevice)`**
  * 기본 생성 인자: `device_id: str = "gas_valve_main"`, `name: str = "주방 가스밸브"`, `initial_state: ValveState = ValveState.CLOSED`, `opened_minutes: int = 0`
  * 프로퍼티: `is_shut_off -> bool` (`state == ValveState.CLOSED`일 때 `True`)
  * `shut_off() -> CommandResult`:
    * `CLOSED`인 경우에도 오류 없이 `success=True`, `"이미 가스밸브가 잠겨 있습니다."` 반환(멱등성).
    * `OPEN` 또는 `SHUTTING_OFF`인 경우 `CLOSED`로 전이하고 `opened_minutes = 0` 초기화.
    * `ERROR` / `OFFLINE` 상태에서는 로컬 차단 불가를 알리거나(`success=False`) 제어기/API 상태에 따라 처리.
  * `open_valve(opened_minutes: int = 0) -> CommandResult`: 시뮬레이션/테스트에서 가스 열림 및 경과 시간 상황을 재현하는 메서드.
  * `handle_command(command, params)`: 지원 명령 `"SHUT_OFF"`, `"OPEN"`, `"STATUS"`. 미지원 명령은 `CommandExecutionError` 발생.
  * `to_dict() -> dict[str, Any]` / `from_dict(data) -> GasValve`: JSON 직렬화·역직렬화.

### 3.5 제어기 (`smart_home/controller.py`)

* **`SmartHomeController`**
  * 생성자: `SmartHomeController(api_client: SmartHomeApiClient | None = None, long_open_threshold_minutes: int = 30)`
    * `api_client` 미전달 시 기본 `MockSmartHomeApiClient()` 사용.
  * 주요 메서드:
    * `register_device(device: SmartDevice) -> None`
    * `get_device_status(device_id: str = "gas_valve_main") -> DeviceStatus`
      * 등록 기기 확인 후 `api_client.fetch_device_status()` 호출(동기화) → 통신 실패 시 예외 전파 또는 `OFFLINE` 상태 안전 반환 규약에 따라 처리.
    * `request_gas_shutoff(device_id: str = "gas_valve_main") -> CommandResult`
      * 어댑터 `send_device_command(device_id, "SHUT_OFF")` 호출 → 성공 시 로컬 `SmartDevice.handle_command("SHUT_OFF")` 동기화.
      * 통신 실패(`ApiConnectionError`, `ok=False`) 시 예외로 앱을 종료하지 않고 `CommandResult(success=False, ...)`를 반환하여 상위(`Robot`)가 `AlertService` 경고 로그를 생성하도록 보장(Fail-Safe).
    * `simulate_gas_open(device_id: str = "gas_valve_main", opened_minutes: int = 0) -> CommandResult`
      * 테스트·UI 시연용으로 가스 열림 상태와 경과 시간을 주입하고 Mock 어댑터와 동기화.
    * `check_gas_safety(device_id: str = "gas_valve_main") -> tuple[bool, str]`
      * 현재 `OPEN` 상태이고 `opened_minutes >= long_open_threshold_minutes`이면 `(False, 경고 메시지)` 반환, 그 외 안전한 경우 `(True, 정상 메시지)` 반환.
    * `to_dict() -> dict[str, Any]` / `load_from_dict(data: dict[str, Any]) -> None`

---

## 4. 가스불 차단기 제어 어댑터 규약 (`MockSmartHomeApiClient` & 향후 확장)

현 단계에서는 범용 다중 스마트홈 플랫폼(SmartThings, Home Assistant 등) 비교·연동 논의를 생략하고, **가스불 차단기(가스밸브) 제어 전용 어댑터 계약**에 집중한다.

### 4.1 표준 요청/응답 계약 모델 (REST 개념 기준)

| 논리 작업 | 개념 엔드포인트 | 요청 페이로드 예시 | 정규화 응답(`ApiResponse.payload`) 예시 |
| :--- | :--- | :--- | :--- |
| **밸브 상태 조회** | `GET /api/v1/devices/{device_id}/status` | *(Query 없음)* | `{"device_id": "gas_valve_main", "state": "OPEN", "is_shut_off": false, "opened_minutes": 35, "updated_at": "2026-11-23T14:10:00"}` |
| **가스 차단 명령** | `POST /api/v1/devices/{device_id}/commands` | `{"command": "SHUT_OFF", "reason": "user_or_robot_request"}` | `{"device_id": "gas_valve_main", "command": "SHUT_OFF", "accepted": true, "state": "CLOSED", "is_shut_off": true}` |
| **게이트웨이 점검** | `GET /api/v1/health` | *(Query 없음)* | `{"status": "ok", "gateway": "mock"}` |

### 4.2 `MockSmartHomeApiClient` (`smart_home/adapters.py`)
* 외부 네트워크 없이 인메모리 상태 맵으로 동작하는 기본 시뮬레이터.
* 장애 시뮬레이션 지원 메서드:
  * `set_fault_mode(offline: bool = False, fail_commands: bool = False)`
  * `offline=True`일 때 `ApiConnectionError`(HTTP 503/504 개념)를 발생시켜 Fail-Safe 흐름 검증.
  * `fail_commands=True`일 때 `ApiResponse(ok=False, status_code=500, error_code="VALVE_ACTUATION_FAILED", ...)` 반환.
* 추후 실제 IoT 차단기 게이트웨이/HTTP API 연동이 필요해지면, 상업용 허용 라이선스 패키지(예: `requests`, `httpx`) 또는 표준 라이브러리 기반의 `HttpGasValveApiClient(SmartHomeApiClient)`를 `adapters.py`에 추가하고 컨트롤러에 주입하기만 하면 된다.

---

## 5. 기존 `companion_robot.py` 최소 통합 규약

모든 통합 변경은 팀 공통 기준 문서인 **[MODULE_INTEGRATION_GUIDE.md](MODULE_INTEGRATION_GUIDE.md)**를 엄격히 따르며, `companion_robot.py` 수정 지점은 아래 5곳으로 제한한다.

1. **`Robot.__init__`**
   * 시그니처 확장: `def __init__(self, store: JsonStore, smart_home: SmartHomeController | None = None)`
   * `smart_home` 미전달 시 기본 `MockSmartHomeApiClient` + `GasValve("gas_valve_main", "주방 가스밸브")`로 `SmartHomeController` 생성.
   * `saved = store.load()`에서 `saved.get("smart_home")`이 있으면 `self.smart_home.load_from_dict(...)` 호출.
2. **`Robot.save`**
   * 기존 6개 키(`profile`, `battery`, `status`, `history`, `medications`, `alerts`) 구조를 그대로 유지하고 `"smart_home": self.smart_home.to_dict()`만 추가.
3. **`IntentClassifier.EXAMPLES` (TF-IDF 충돌 방지 주의)**
   * 기존 `"status"` 의도(`"로봇 상태 확인"`, `"배터리 잔량 알려줘"`, `"현재 상태 확인"`)와 문자 2~3그램이 겹치지 않도록 `smart_home_*` 접두사와 가스 특화 발화를 사용한다.
   * 추가 의도:
     * `"smart_home_status"`: `["가스불 확인해줘", "가스밸브 상태 알려줘", "가스 켜져 있어", "주방 가스 잠겼는지 확인", "가스 상태 조회"]`
     * `"smart_home_shutoff"`: `["가스불 꺼줘", "가스밸브 잠가줘", "가스 차단해줘", "주방 가스 불 꺼줘", "가스 잠금 실행"]`
   * 구현 후 기존 5개 테스트 발화 + 신규 가스 발화 전체에 대한 의도 분류 비충돌 회귀 테스트를 필수로 실행한다.
4. **`Robot.generate_reply` 및 스마트홈 보조 메서드**
   * `smart_home_status` → `self.smart_home.get_device_status()` 조회 후 상태 요약 응답(통신 오류 시 안전 안내 + `self.alerts.create("스마트홈/가스", ...)`).
   * `smart_home_shutoff` → `self.smart_home.request_gas_shutoff()` 실행 후 결과 응답 + `self.alerts.create("스마트홈/가스", ...)` 기록.
   * `Robot.check_gas_safety()` 헬퍼 메서드를 두어 장시간 개방 시 `self.alerts.create("스마트홈/가스 경고", ...)`와 상태 저장 수행.
5. **`run_gui()` 탭 연결**
   * `tabs`에 `tab5 = ttk.Frame(tabs, style="Panel.TFrame")` (`"5단계 · 스마트홈"`)을 추가하고 `build_smart_home_tab(tab5, robot, on_state_change=...)`를 호출한다.

---

## 6. 영속화 JSON 스키마 (`companion_state.json` 내 `"smart_home"`)

기존 `companion_state.json`의 최상위 키들과 병존하는 `"smart_home"` 네임스페이스 구조:

```json
{
  "smart_home": {
    "long_open_threshold_minutes": 30,
    "fault_mode": {
      "offline": false,
      "fail_commands": false
    },
    "devices": {
      "gas_valve_main": {
        "device_id": "gas_valve_main",
        "device_type": "gas_valve",
        "name": "주방 가스밸브",
        "state": "CLOSED",
        "opened_minutes": 0,
        "updated_at": "2026-11-23T14:15:00"
      }
    }
  }
}
```

* 구버전 `companion_state.json`에 `"smart_home"` 키가 없더라도 예외 없이 기본값(`CLOSED`, `0분`)으로 안전하게 초기화된다.

---

## 7. 테스트 계획 및 요구사항 추적표

### 7.1 단위/통합 테스트 케이스 (`test_smart_home.py`)

| TC ID | 테스트 항목 | 입력 / 조건 | 기대 결과 |
| :--- | :--- | :--- | :--- |
| **TC-SH-01** | 가스밸브 초기 상태 및 `SmartDevice` 구현 확인 | 기본 `GasValve` 생성 | `isinstance(valve, SmartDevice)` 참, `state == CLOSED`, `is_shut_off == True` |
| **TC-SH-02** | 가스밸브 열림 시뮬레이션 및 상태 조회 | `simulate_gas_open(opened_minutes=10)` 후 `get_device_status()` | `state == OPEN`, `is_shut_off == False`, `opened_minutes == 10` |
| **TC-SH-03** | 가스밸브 정상 차단 | `OPEN` 상태에서 `request_gas_shutoff()` | `success == True`, `current_state == CLOSED`, `opened_minutes == 0` |
| **TC-SH-04** | 이미 차단된 밸브 중복 차단 (멱등성) | `CLOSED` 상태에서 `request_gas_shutoff()` | `success == True`, `previous_state == CLOSED`, `current_state == CLOSED` |
| **TC-SH-05** | 미등록 기기 및 미지원 명령 예외 처리 | 존재하지 않는 `device_id` / `"INVALID_CMD"` | `DeviceNotFoundError` / `CommandExecutionError` 발생 |
| **TC-SH-06** | 장시간 개방 안전 경고 | `OPEN`, `opened_minutes=35` (임계치 30분) | `check_gas_safety()`가 `(False, 경고문구)` 반환; 10분일 때는 `(True, 정상문구)` |
| **TC-SH-07** | 차단기 어댑터 오프라인 장애 Fail-Safe | `set_fault_mode(offline=True)` 후 차단 요청 | 예외 크래시 없이 `CommandResult(success=False, ...)` 반환 |
| **TC-SH-08** | 차단기 어댑터 명령 실패 응답 Fail-Safe | `set_fault_mode(fail_commands=True)` 후 차단 요청 | `CommandResult(success=False, ...)` 반환 및 밸브 상태 무단 변경 안 됨 |
| **TC-SH-09** | 커스텀 `SmartHomeApiClient` 주입 가능성 | 테스트용 Fake 어댑터 주입 | `MockSmartHomeApiClient` 없이도 컨트롤러 정상 동작 (DIP 입증) |
| **TC-SH-10** | 대화 의도 분류 및 비충돌 검증 | `"가스불 꺼줘"`, `"가스불 확인해줘"` + 기존 5개 의도 | 각각 `smart_home_shutoff`, `smart_home_status` 및 기존 5개 의도 정확히 분류 |
| **TC-SH-11** | `Robot` 통합 흐름 및 `AlertService` 기록 | `Robot.start_conversation("가스불 꺼줘")` | 응답 생성, `"스마트홈/가스"` 로컬 알림(`LOCAL_SIMULATION_ONLY`) 기록 |
| **TC-SH-12** | JSON 영속화 및 재시작 복원 | 가스 열림(40분) 상태 저장 후 새 `Robot` 인스턴스 로드 | 재로딩된 `Robot`에서 `OPEN`, `40분` 상태 동일 복원 |

### 7.2 요구사항 추적표 (Traceability Matrix)

| BR | PRD 요구사항 / 유스케이스 | 설계 심볼 | 테스트 케이스 |
| :--- | :--- | :--- | :--- |
| **BR-01, BR-05** | `FR-SH-09`, `NFR-SH-01`, `NFR-SH-02` | `smart_home/` 패키지, `Robot.__init__`/`save`, `load_from_dict` | `TC-SH-12` + 기존 8개 회귀 테스트 |
| **BR-02** | `FR-SH-01`, `FR-SH-02`, `FR-SH-03`, `UC-SH-01~03` | `SmartDevice`, `GasValve`, `SmartHomeController` | `TC-SH-01` ~ `TC-SH-05` |
| **BR-02** | `FR-SH-04`, `UC-SH-04` | `SmartHomeController.check_gas_safety`, `Robot.check_gas_safety` | `TC-SH-06` |
| **BR-04** | `FR-SH-05`, `NFR-SH-03`, `UC-SH-05` | `SmartHomeApiClient`, `MockSmartHomeApiClient` | `TC-SH-07`, `TC-SH-08`, `TC-SH-09` |
| **BR-01, BR-02, BR-06** | `FR-SH-06`, `FR-SH-07`, `FR-SH-08`, `NFR-SH-05` | `IntentClassifier`, `Robot.generate_reply`, `build_smart_home_tab`, `AlertService` | `TC-SH-10`, `TC-SH-11` |
