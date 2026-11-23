# 통합 프로토타입 점검 및 보완 TODO (`hallymsoftware_SWE_3`)

| 항목 | 내용 |
| :--- | :--- |
| **점검 및 안정화 완료일** | 2026-11-24 |
| **기준 브랜치** | `Sangin` |
| **현재 테스트 상태** | `python -m unittest -v` **48건 전부 PASS** (`test_companion_robot` 8 / `test_smart_home` 12 / `test_health_monitor` 10 / `test_memory_archive` 12 / `test_integration` 6) |
| **실행 환경 / 의존성** | Python 표준 라이브러리 기반(외부 pip 의존성 없음, `pyttsx3`만 선택 의존성) |

---

## 확정된 통합 기준 (`D-01` ~ `D-04`)

| ID | 안건 | 확정 내용 |
| :--- | :--- | :--- |
| **D-01** | 프로토타입 범위 및 확장성 | 현 4대 영역(코어 + 스마트홈 + 건강 + 가족기억) 안정화로 프로토타입을 마감하며, 복약 리마인더 고도화(`medications` DI)·Ollama 챗봇(`ai_model` DI)·`visitor_recognition/`은 코어 종속성 없이 교체 확장 가능하도록 DI 경계만 확보 |
| **D-02** | 대화창 연동 & 건강 시연 UI | `IntentClassifier`에 `health_check`·`memory_search` 의도 연결 및 `건강 모니터링` 탭(`MockWearable`)에 심박수/SpO₂ 이상 징후 시연 입력 UI 추가 |
| **D-03** | Health Monitoring 문서 단일화 | `v0.2` PDF의 검증 추적표·상태 전이표를 `.md`로 통합하고 중복 PDF 2종 삭제, `README_HEALTH_MONITOR.md`를 `docs/`로 통합 이동 |
| **D-04** | 전체 모듈 타임존 표준 | **RFC 3339 / ISO 8601 기준 라이브러리·저장소 내부 UTC (`+00:00`) + UI/응답 표시 계층 로컬 KST (`+09:00`) 변환** (`time_utils.py`, 복약 시각 `HH:MM` 비교만 현지 벽시계 기준 유지) |

---

## 1. 상태 동기화 · 의존성 · 통합 보완 (Code & State Sync)

- [x] **[P0] `profile.name` ↔ `memory_archive` SQLite(`app_user.display_name`) 동기화**
  * `MemoryArchive.register_user()`를 `ON CONFLICT(user_id) DO UPDATE SET display_name = excluded.display_name`으로 변경(가족 별칭은 유지)하고, `Robot.update_profile()` 및 `save_profile()`에서 즉시 동기화.
- [x] **[P0] 탭 간 UI 상태 비동기화 해결**
  * `build_smart_home_tab`, `build_health_monitor_tab`, `build_memory_archive_tab`이 refresh 콜백을 반환하도록 통일하고, `send_chat()`·`save_profile()`·`<<NotebookTabChanged>>` 이벤트에서 `refresh_tabs()` 호출.
- [x] **[P1] `health_monitor` GUI 이상 징후(`UC-02`) 시연 입력 추가**
  * `health_monitor/ui.py`에 `MockWearable`용 심박수/SpO₂ Spinbox 및 `정상값 (75 / 98)` · `이상값 시연 (125 / 89)` 프리셋 버튼 추가(`JsonWearable` 모드에서는 숨김).
- [x] **[P1] 대화(`IntentClassifier` / `Robot.generate_reply`) ↔ `health_monitor` · `memory_archive` 연동**
  * `health_check`, `memory_search` 의도 추가 및 `Robot.get_health_status_summary()`, `Robot.search_memory_summary()` 구현, 전체 11종 의도 TF-IDF 비충돌 회귀 테스트 통과.
- [x] **[P1] 모듈 간 타임스탬프 / 타임존 표준화 (`D-04`)**
  * `time_utils.py`(`utc_now_iso`, `to_utc_iso`, `format_local_time`) 추가 및 `AlertService`, `ConversationEntry`, `smart_home/` 내부 저장을 UTC로 전환, 모든 UI·대화 요약 표시를 KST 변환으로 통일.
- [x] **[P1] `Robot.__init__` 향후 확장 DI 경계 확보 및 `actor_id` 동적 조회**
  * `Robot.__init__`에 선택 인자 `ai_model=None`, `medications=None` 추가(`D-01`), `memory_archive/ui.py`가 `current_actor_id()`로 현재 프로필 ID를 동적 조회하도록 수정.
- [ ] **[P2 · 향후 운영 전환 시] `health_monitor` 수집 후 `robot.save()` 실패 시 원자성 보완**
  * 현재는 로컬 시뮬레이션 프로토타입이므로 `SD` 6절에 알려진 한계로 유지하며, 향후 운영 DB 전환 시 알림 outbox 트랜잭션 통합 검토.

---

## 2. GUI / UX 일관성 보완

- [x] **[P1] 창 제목 · docstring · 탭 명칭 통일(`1~7단계`) 및 창 크기 조정** (`1240x760`, 탭 패딩 `(14, 10)`)
- [x] **[P2] `health_monitor` (`tk.Listbox`) / `memory_archive` (`ScrolledText`) 테마(`#EAF4FB`, `#15283C`, `맑은 고딕`) 통일**
- [x] **[P2] 1단계 대화 탭 초기 안내문 및 `사용 예시` 현행화**
- [ ] **[P2 · 수동 확인] Tkinter GUI 실창(`python companion_robot.py`) 7개 탭 전환 및 시각 레이아웃 최종 수동 점검**

---

## 3. 통합 테스트 보완

- [x] **[P1] `test_integration.py` 신설 (6건 추가 · 전체 48건 PASS)**
  * `Robot` ↔ `health_monitor` 수집·알림·재시작 복원·중복 억제 테스트
  * 코어 + `smart_home` + `health_monitor` + `memory_archive` 4대 영역 동시 영속화 End-to-End 테스트
  * `Robot.update_profile()` → `memory_archive` 이름 동기화 테스트
  * 전체 11종 의도 TF-IDF 비충돌 및 `health_check`/`memory_search` 대화 테스트
  * UTC 저장 + `format_local_time()` KST 변환(구버전 naive 호환 포함) 테스트
  * `ai_model` / `medications` DI 확장성 검증 스텁 테스트

---

## 4. 문서 (`README.md`, `docs/`, UML) 정리 및 현행화

- [x] **[P0] `README.md` 깨진 링크(`docs/README_HEALTH_MONITOR.md`)·오타(`FR-MED-01~05`)·누락된 `docs/` 및 테스트 목록 수정**
- [x] **[P0] Health Monitoring 문서 단일화 (`D-03`)**: `v0.2` PDF 내용을 `docs/HEALTH_MONITOR_SRS.md`·`SD.md`에 통합하고 중복 PDF 2종 및 `health_monitor/README_HEALTH_MONITOR.md` 삭제(`docs/README_HEALTH_MONITOR.md`로 이동)
- [x] **[P1] `BRD.md` (`v0.4`), `PRD.md` (`v0.4`), `SMART_HOME_DESIGN.md` (`v1.1`), `MODULE_INTEGRATION_GUIDE.md` (`v0.2`) 현행화 및 `resource/` 사본 동기화**
- [x] **[P1] KAN-25 UML 다이어그램 2종(`.drawio` + `.png`) 및 검토 보고서 `v3.0` 현행화** (`memory_archive/`, `health_monitor/` 구현 완료 승격, 48건 테스트 반영)

---

## 5. 향후 확장 백로그 (프로토타입 범위 외)

- [ ] **Family & Visitor Recognition (`visitor_recognition/`)** 구현 및 보호자 외부 알림 연계
- [ ] **복약 리마인더 고도화** (`PRD.md` Section 3.2, `medications` DI 주입 구현)
- [ ] **일상 대화용 오픈웨이트(Ollama) 챗봇** (`ai_model` DI 주입 및 Mock 어댑터 구현)
- [ ] **Family Memory Archive 확장** (파일 첨부, pgvector 의미 검색, RAG 대화 연동)
- [ ] **실기기 BLE 웨어러블 / 공공데이터포털 `DUR_SERVICE_KEY` 실환경 검증**
