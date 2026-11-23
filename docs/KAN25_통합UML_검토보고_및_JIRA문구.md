# TEAM05 / KAN-25 전체 UML 설계 및 통합 — 형상관리 정정본 (v2.1)

> **상태**: 형상관리 정정 반영 / 팀 교차 검토 필요
> **작성·검증 근거**: `companion_robot.py`, `test_companion_robot.py`, `smart_home/` 패키지, `test_smart_home.py`, `docs/BRD.md` (v0.3), `docs/PRD.md` (v0.3), `docs/SMART_HOME_DESIGN.md` (v1.0), `docs/MODULE_INTEGRATION_GUIDE.md` (v0.1), `docs/가정 돌봄로봇 모듈 확장 UML 다이어그램.png`

> [!NOTE]
> **형상관리 정비 완료**: 기존 PR(#2)에 첨부되었던 `KAN25_Component_통합수정_v2.png`, `KAN25_UseCase_통합수정_v2.png`는 본 저장소에 존재하지 않는 프로토타입(`app.py`, `robot_core.py`) 기준이어서 삭제한 뒤, 실제 저장소(`companion_robot.py` + `smart_home/`) 기준으로 **편집 가능한 `.drawio` 원본과 함께 새 PNG 2종을 재작성**하여 `docs/`에 반영했습니다.
> * [KAN25_Component_통합수정_v2.png](KAN25_Component_통합수정_v2.png) ([.drawio 원본](KAN25_Component_통합수정_v2.drawio))
> * [KAN25_UseCase_통합수정_v2.png](KAN25_UseCase_통합수정_v2.png) ([.drawio 원본](KAN25_UseCase_통합수정_v2.drawio))

---

## 1. 실제 저장소 기준 정리 내용

* **현재 구현 완료 (1~4단계 코어 + 5단계 Smart Home Control)**:
  * **1~4단계 코어 (`companion_robot.py`)**: 한국어 문자 2~3그램 TF-IDF `IntentClassifier`, `VoiceProcessor`, `UserProfile`, `JsonStore`(`demo_data/companion_state.json`), `MedicationManager`(단순 복약 일정 알림), 키오스크 이용 가이드, `Navigator`(BFS 실내 최단 경로), `DistanceSensor`·`TouchSensor`·`FallSensor`, `AlertService`(로컬 시뮬레이션 로그), Tkinter GUI.
  * **5단계 Smart Home Control (`smart_home/` 독립 패키지)**: 현 단계 범위인 **가스불 차단기(가스밸브)** IoT 시뮬레이션 구현 완료(`SmartDevice`, `GasValve`, `SmartHomeController`, `SmartHomeApiClient`, `MockSmartHomeApiClient`, `build_smart_home_tab`, `test_smart_home.py` 12개 테스트). 다중 상용 스마트홈 플랫폼 비교·연동은 현 단계 범위에서 제외함.
* **문서화 완료 · 미구현 (타 팀원 구현 대상)**:
  * **Family Memory Archive** (`memory_archive/` 예약): 로컬 저장·검색 등 미구현.
  * **Health Monitoring** (`health_monitor/` 예약): 웨어러블/심박수 모니터링 미구현.
  * **복약 리마인더 고도화** (`PRD.md` Section 3.2, `BR-07`): 재알림(스누즈)·복용 확인·미복용 경고는 문서화 완료, 구현은 타 팀원 담당.
  * **일상 대화 챗봇(오픈웨이트 Ollama 모델)**: 추후 연동 검토 방향만 문서화.
* **선택 검토 기능**:
  * **Family & Visitor Recognition** (`visitor_recognition/` 예약): UML v1.0에는 확장 모듈 5로 포함되어 있으나, 필수 포함 여부는 팀 최종 확인 대상.
* **공통 협업 규칙 확정**: `docs/MODULE_INTEGRATION_GUIDE.md`에 패키지 소유권, `companion_state.json` 네임스페이스 키, `IntentClassifier` 접두사, `AlertService` 카테고리, `ui.py` 탭 연결 규약을 정의함.

---

## 2. 코드 ↔ UML ↔ 요구사항 연결 (실제 저장소 기준)

| UML / 기능 영역 | 실제 구현 파일 · 클래스 · 메서드 | 요구사항 / 문서 | 현재 상태 |
| :--- | :--- | :--- | :--- |
| GUI / 사용자 상호작용 | `companion_robot.py`: `run_gui()` (5개 탭) | 코어 1~4단계 | 로컬 구현 완료 |
| 대화 / 의도 분류 | `Robot.start_conversation()`, `IntentClassifier` (TF-IDF) | 코어 1단계 | 로컬 구현 완료 (외부 LLM 미연동, Ollama 검토 중) |
| 사용자 프로필 | `UserProfile`, `JsonStore` | 코어 1단계 | 로컬 JSON 영속화 완료 |
| 복약 일정 / 키오스크 | `MedicationManager`, `Robot.check_medication()`, 키오스크 가이드 | 코어 2단계 | 기본 일정 알림 구현 완료 (리마인더 고도화 `PRD` 3.2절은 미구현) |
| 실내 이동 / 장애물 | `Navigator.route()`, `DistanceSensor`, `Robot.check_distance()` | 코어 3단계 | BFS 경로 및 가상 센서 구현 완료 |
| 낙상 감지 / 알림 로그 | `FallSensor`, `TouchSensor`, `Robot.trigger_fall()`, `AlertService` | 코어 4단계 | 버튼 시연 및 `LOCAL_SIMULATION_ONLY` 로그 완료 |
| **Smart Home (가스불 차단기)** | `smart_home/`: `SmartDevice`, `GasValve`, `SmartHomeController`, `SmartHomeApiClient`, `MockSmartHomeApiClient`, `build_smart_home_tab()` | `BR-02~04`, `FR-SH-01~09` | **독립 패키지 구현 및 `Robot`/GUI 통합 완료 (`test_smart_home.py` 12개 PASS)** |
| 가족 기억 보관소 | *(미구현 — `memory_archive/` 예약)* | `MODULE_INTEGRATION_GUIDE.md` | 미구현 (타 팀원 담당) |
| 건강 모니터링 | *(미구현 — `health_monitor/` 예약)* | `MODULE_INTEGRATION_GUIDE.md` | 미구현 (타 팀원 담당) |
| 가족/방문자 인식 | *(미구현 — `visitor_recognition/` 예약)* | UML v1.0 모듈 5 | 선택 기능 (팀 최종 확인 필요) |
| 로컬 저장 / 복구 | `JsonStore.load()`, `JsonStore.save()` (`companion_state.json`) | `FR-SH-09`, 코어 | 원자적 임시 파일 치환(`.tmp`) 저장 완료 |

### 이전 UML 설계와 실제 Python 클래스의 관계

* 기존 UML 다이어그램(`docs/가정 돌봄로봇 모듈 확장 UML 다이어그램.png`) 코어부의 `동반자로봇`, `대화관리자`, `AI모델`, `음성처리기`, `센서`, `사용자프로필`, `대화기록`은 실제 `companion_robot.py`에 **`Robot`**, **`IntentClassifier`**, **`VoiceProcessor`**, **`Sensor`/`TouchSensor`/`DistanceSensor`/`FallSensor`**, **`UserProfile`**, **`ConversationEntry`** 등으로 구현되어 있다(대화관리자 역할은 `Robot` + `IntentClassifier`에 통합).
* `3. Smart Home Control`의 `<<interface>> 스마트기기`, `가스밸브`, `스마트홈제어기`는 `smart_home/` 패키지에서 **`SmartDevice`**, **`GasValve`**, **`SmartHomeController`**로 1:1 대응 구현되었으며, 제어 어댑터 경계(`SmartHomeApiClient` / `MockSmartHomeApiClient`)가 추가되었다.
* `companion_state.json`은 프로토타입용 로컬 JSON 영속화 파일(현재 키: `profile`, `battery`, `status`, `history`, `medications`, `alerts`, `smart_home`)이며, 아직 RDB/SQLite는 도입되지 않았다.

---

## 3. 모듈 인터페이스 계약 안내

* **현행 확정 팀 규약**: 모든 확장 모듈 연동은 **[MODULE_INTEGRATION_GUIDE.md](MODULE_INTEGRATION_GUIDE.md)** (패키지 분리, `Robot.__init__` 선택 인자 주입, JSON 최상위 키 예약, `IntentClassifier` 접두사, `AlertService` 접두사, `ui.py` 탭 빌더)를 따른다.
* **Smart Home 호출 레퍼런스**: 실제 Python 호출 계약 및 예제는 **[SMART_HOME_DESIGN.md](SMART_HOME_DESIGN.md)**를 참조한다.

### (참고) 향후 Command Router 도입 시 JSON Envelope 확장 예시

현재 `Robot.start_conversation()`은 `(reply: str, intent: str, confidence: float)`를 반환하며, `smart_home`은 `DeviceStatus`/`CommandResult`/`ApiResponse` 데이터클래스를 반환한다. 추후 팀이 공통 `Command Router` 계층을 추가하기로 합의할 경우 아래 Envelope 형식을 참고할 수 있다.

```json
{
  "request_id": "REQ-001",
  "user_id": "U001",
  "action": "smart_home.gas_shutoff",
  "payload": {"device_id": "gas_valve_main"}
}
```

```json
{
  "success": true,
  "data": {"device_id": "gas_valve_main", "state": "CLOSED", "is_shut_off": true},
  "error_code": null,
  "source": "mock_api",
  "timestamp": "2026-11-23T15:30:00"
}
```

---

## 4. 검토 체크리스트

- [x] `Smart Home Control`(가스불 차단기) 독립 패키지 구현 및 테스트(`test_smart_home.py`) 완료
- [x] 팀 공통 모듈 연동 규약(`docs/MODULE_INTEGRATION_GUIDE.md`) 및 `BRD`/`PRD` v0.3 문서화 완료
- [x] 삭제된 `KAN25_Component_통합수정_v2.png`, `KAN25_UseCase_통합수정_v2.png`를 실제 코드(`companion_robot.py`, `smart_home/`) 기준으로 재작성 (`.drawio` 원본 포함)
- [ ] `Family & Visitor Recognition`의 필수/선택 여부를 JIRA에 최종 명시
- [ ] 타 팀원 담당 모듈(`memory_archive/`, `health_monitor/`, 복약 리마인더 고도화) 구현 및 KAN-24 Class Diagram / ERD / SD 용어 일치 확인
- [ ] 리뷰 의견과 승인자를 JIRA에 기록한 뒤 KAN-25 최종 완료 처리

---

## 5. JIRA KAN-25 댓글용 문구 (정정본)

> 실제 저장소(`companion_robot.py`, `smart_home/`, `docs/BRD.md`, `docs/PRD.md`, `docs/SMART_HOME_DESIGN.md`, `docs/MODULE_INTEGRATION_GUIDE.md`) 기준으로 KAN-25 검토 문서를 현행화하고, 불일치하던 기존 PNG 2종(`KAN25_Component_통합수정_v2.png`, `KAN25_UseCase_통합수정_v2.png`)을 실제 코드베이스 기준으로 재작성(`.drawio` + `.png`)하여 반영했습니다.
> 현재 1~4단계 코어(`companion_robot.py`)와 5단계 Smart Home Control(`smart_home/`, 가스불 차단기 IoT 시뮬레이션)은 구현 및 단위 테스트(총 20건 PASS)까지 완료되었으며, Family Memory Archive·Health Monitoring·복약 리마인더 고도화는 `MODULE_INTEGRATION_GUIDE.md` 규약에 맞춰 후속 개발 예정입니다.
