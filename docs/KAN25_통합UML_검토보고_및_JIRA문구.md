# TEAM05 / KAN-25 전체 UML 설계 및 통합 — 통합 프로토타입 현행화본 (v3.0)

> **상태**: 4대 영역 통합 완료 및 단위·통합 테스트 48건 PASS 기준 현행화
> **작성·검증 근거**: `companion_robot.py`, `time_utils.py`, `smart_home/`, `health_monitor/`, `memory_archive/`, `test_*.py` (5개 파일 48건), `docs/BRD.md` (v0.4), `docs/PRD.md` (v0.4), `docs/SMART_HOME_DESIGN.md` (v1.1), `docs/MODULE_INTEGRATION_GUIDE.md` (v0.2), `docs/HEALTH_MONITOR_SRS.md` & `SD.md` (v0.2), `docs/FAMILY_MEMORY_ARCHIVE.md`

> [!NOTE]
> **다이어그램 현행화 완료 (`v3.0`)**: `smart_home/`, `health_monitor/`, `memory_archive/` 통합 완료 및 48개 테스트 통과 기준에 맞춰 **편집 가능한 `.drawio` 원본과 PNG 2종**을 갱신했습니다.
> * [KAN25_Component_통합수정_v2.png](KAN25_Component_통합수정_v2.png) ([.drawio 원본](KAN25_Component_통합수정_v2.drawio))
> * [KAN25_UseCase_통합수정_v2.png](KAN25_UseCase_통합수정_v2.png) ([.drawio 원본](KAN25_UseCase_통합수정_v2.drawio))

---

## 1. 실제 저장소 기준 정리 내용 (`v3.0`)

* **현재 구현 완료 (1~4단계 코어 + 5~7단계 3개 독립 모듈 · 총 7개 GUI 탭)**:
  * **1~4단계 코어 (`companion_robot.py`, `time_utils.py`)**: 한국어 문자 2~3그램 TF-IDF `IntentClassifier`(11종 의도), `VoiceProcessor`, `UserProfile`(SQLite 이름 자동 동기화), `JsonStore`(`demo_data/companion_state.json`), `MedicationManager`(벽시계 `HH:MM` 일정 알림), 키오스크 이용 가이드, `Navigator`(BFS 실내 최단 경로), `DistanceSensor`·`TouchSensor`·`FallSensor`, `AlertService`(`LOCAL_SIMULATION_ONLY`), Tkinter GUI(탭 전환 동기화 포함).
  * **5단계 Smart Home Control (`smart_home/`)**: 가스불 차단기(가스밸브) IoT 상태 조회·차단(멱등성)·장시간 개방 안전 점검·장애 Fail-Safe 시뮬레이션(`5단계 · 스마트홈` 탭 + `smart_home_*` 대화 의도 + 12개 테스트).
  * **6단계 Health Monitoring (`health_monitor/`)**: 심박·SpO₂ 수집(`MockWearable` 이상 징후 시연 UI + `HEALTH_WEARABLE_JSON` 브리지), 120초 연속 이상 시 역할별(`건강/사용자`, `건강/보호자`) 로컬 알림, `DUR` CLI 조회(`6단계 · 건강 모니터링` 탭 + `health_check` 대화 의도 + 10개 테스트).
  * **7단계 Family Memory Archive (`memory_archive/`)**: 개인·가족 보관함, 접근 권한, 기억 CRUD·검색·버전 이력·근거 미리보기(`demo_data/memory_archive.sqlite3`), 손상 DB 격리(`7단계 · 가족 기억` 탭 + `memory_search` 대화 의도 + 12개 테스트).
* **시간 표준**: 저장·도메인 계층은 **RFC 3339 / ISO 8601 UTC (`+00:00`)**로 통일하고, GUI·대화 응답 표시 계층에서만 `time_utils.format_local_time()`으로 로컬 KST 변환.
* **향후 확장 예정 (`Robot.__init__` DI 경계 확보 · 미구현)**:
  * **Family & Visitor Recognition** (`visitor_recognition/` 예약)
  * **복약 리마인더 고도화** (`PRD.md` Section 3.2, `medications` DI 주입 가능)
  * **일상 대화 챗봇** (오픈웨이트 Ollama 모델, `ai_model` DI 주입 가능)
  * **RAG/pgvector & 실기기 BLE/실DUR 키 연동**

---

## 2. 코드 ↔ UML ↔ 요구사항 연결 (실제 저장소 기준)

| UML / 기능 영역 | 실제 구현 파일 · 클래스 · 메서드 | 요구사항 / 문서 | 현재 상태 |
| :--- | :--- | :--- | :--- |
| GUI / 탭 동기화 | `companion_robot.py`: `run_gui()` (7개 탭, `<<NotebookTabChanged>>`) | 코어 + `MODULE_INTEGRATION_GUIDE.md` | 구현 완료 |
| 대화 / 의도 분류 | `Robot.start_conversation()`, `IntentClassifier` (11종 의도 TF-IDF) | 코어 + `health_check` / `memory_search` | 로컬 구현 완료 (Ollama `ai_model` DI 준비) |
| 사용자 프로필 / DB 동기화 | `UserProfile`, `Robot.update_profile()`, `MemoryArchive.register_user()` | 코어 + `FAMILY_MEMORY_ARCHIVE.md` | JSON+SQLite 동기화 완료 |
| 복약 일정 / 키오스크 | `MedicationManager`, `Robot.check_medication()`, 키오스크 가이드 | 코어 2단계 (`medications` DI 준비) | 기본 일정 구현 완료 (리마인더 고도화는 향후 확장) |
| 실내 이동 / 낙상·알림 | `Navigator.route()`, `DistanceSensor`, `FallSensor`, `AlertService` | 코어 3~4단계 | 로컬 시뮬레이션 완료 |
| **Smart Home (가스불 차단기)** | `smart_home/`: `SmartDevice`, `GasValve`, `SmartHomeController`, `MockSmartHomeApiClient`, `build_smart_home_tab()` | `BR-02~04`, `FR-SH-01~09` | **구현 및 통합 완료 (12 tests PASS)** |
| **Health Monitoring** | `health_monitor/`: `HealthMonitor`, `Reading`, `MockWearable`, `JsonWearable`, `DurLookup`, `build_health_monitor_tab()` | `HEALTH_MONITOR_SRS.md` / `SD.md` (`v0.2`) | **구현 및 통합 완료 (10 tests PASS)** |
| **Family Memory Archive** | `memory_archive/`: `MemoryArchive`, `schema.sql`, `build_memory_archive_tab()` | `FAMILY_MEMORY_ARCHIVE.md` | **구현 및 통합 완료 (12 tests PASS)** |
| 가족/방문자 인식 | *(미구현 — `visitor_recognition/` 예약)* | UML v1.0 모듈 5 | 향후 확장 (팀 범위 외 마감) |
| 영속화 / 시간 표준 | `JsonStore`(`companion_state.json`), `memory_archive.sqlite3`, `time_utils.py` | `MODULE_INTEGRATION_GUIDE.md` 3.6절 | UTC 저장 / KST 표시 적용 완료 |

---

## 3. 모듈 인터페이스 계약 안내

* **현행 확정 팀 규약**: **[MODULE_INTEGRATION_GUIDE.md](MODULE_INTEGRATION_GUIDE.md)** (`v0.2`: 패키지 분리, `Robot.__init__` 선택 인자 DI, JSON/SQLite 네임스페이스, `IntentClassifier` 접두사, `AlertService` 접두사, `ui.py` refresh 콜백, UTC/KST 시간 표준).
* **모듈별 상세 설계**: [SMART_HOME_DESIGN.md](SMART_HOME_DESIGN.md) (`v1.1`), [HEALTH_MONITOR_SD.md](HEALTH_MONITOR_SD.md) (`v0.2`), [FAMILY_MEMORY_ARCHIVE.md](FAMILY_MEMORY_ARCHIVE.md).

---

## 4. 검토 체크리스트

- [x] `Smart Home Control`, `Health Monitoring`, `Family Memory Archive` 독립 패키지 구현 및 통합 완료
- [x] `KAN25_Component_통합수정_v2.png`, `KAN25_UseCase_통합수정_v2.png`를 통합 4대 영역 완료 기준으로 재작성 (`.drawio` 원본 포함)
- [x] 전체 단위·통합 테스트 48건 PASS (`test_companion_robot` 8 / `test_smart_home` 12 / `test_health_monitor` 10 / `test_memory_archive` 12 / `test_integration` 6)
- [ ] `Family & Visitor Recognition`의 향후 확장 일정 JIRA 정리
- [ ] 리뷰 의견과 승인자를 JIRA에 기록한 뒤 KAN-25 최종 완료 처리

---

## 5. JIRA KAN-25 댓글용 문구 (v3.0)

> 통합된 4대 영역(1~4단계 코어 `companion_robot.py`, 5단계 `smart_home/`, 6단계 `health_monitor/`, 7단계 `memory_archive/`) 기준으로 KAN-25 Component/Use Case 다이어그램(`.drawio` + `.png`)과 검토 문서를 v3.0으로 현행화했습니다.
> 프로필 DB 동기화, 탭 간 UI 갱신, 건강 이상 징후 시연 UI, 대화 의도 2종(`health_check`, `memory_search`), RFC 3339 / ISO 8601 UTC 내부 저장·KST 표시 변환 표준을 반영했으며, 전체 단위·통합 테스트 48건(기존 42건 + 통합 6건)이 모두 통과했습니다.
> `visitor_recognition/`, 복약 리마인더 고도화, Ollama 챗봇은 코어 종속성 없이 확장 가능하도록 `Robot.__init__` DI 경계를 확보한 상태로 향후 확장 범위에 남겼습니다.
