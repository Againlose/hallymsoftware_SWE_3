# SD — 4번 Health Monitoring (v0.1)

## 1. 구조와 클래스 계약

| 파일 | 호출 인터페이스 | 책임 / 의존성 |
|---|---|---|
| `models.py` | `Reading(recorded_at, heart_rate, spo2)` | ISO 8601 시각·시간대, bpm·% 숫자 검증. 입력 허용 범위 1–300 bpm / 1–100% |
| `interfaces.py` | `WearableSource.read()`, `AlertSink.create(category, message)`, `DrugLookup.lookup(product)` | 구현체 교체 포트 |
| `adapters.py` | `MockWearable`, `JsonWearable(path)`, `MockDrugLookup`, `DurLookup` | 모의 데이터, 로컬 JSON, 식약처 품목명 조회 |
| `service.py` | `HealthMonitor(source, alerts)`, `collect()`, `status()`, `snapshot()`, `restore(data)` | 수집·이상 감지·저장·복원 |
| `ui.py` | `build_health_monitor_tab(parent, robot, on_state_change)` | Tkinter에서 수집 요청, 저장 콜백, 최근 기록 갱신 |
| `__main__.py` | `python -m health_monitor` | 코어 없이 데모/독립 DUR 조회 |

## 2. 데이터 및 판정 흐름

`UI/호출자 → collect() → WearableSource.read() → 검증 → 이력 추가 → 연속 이탈 검사 → AlertSink.create()`.
`collect()`는 `Reading`을 반환하며 입력이 중복 또는 역순이면 `ValueError`를 발생시킨다. 이탈 항목이 서로 달라도 연속 두 샘플이 이탈이면 같은 에피소드로 처리한다. 성공적으로 기록된 역할은 `_notified`에 보존하며 정상 샘플에서 초기화한다. 표준 코어 알림 로그 정책 `LOCAL_SIMULATION_ONLY`를 그대로 사용한다.

로컬 입력 JSON 예시(새 수집마다 새로운 시각 필요):

```json
{"recorded_at":"2026-11-23T09:00:00+09:00","heart_rate":75,"spo2":98}
```

저장 형식은 `{"health_monitor":{"history":[…],"notified":["사용자","보호자"]}}`이며 기존 코어 키는 건드리지 않는다. `history`는 오래된 순이다. 복원 시 잘못된 행은 건너뛴다.

## 3. 코어 통합 가이드 — main 원본 확인 후 적용

`companion_robot.py`와 기존 테스트는 첨부되지 않아 이 ZIP에 코어 대체본을 넣지 않았다. 다음 코드 조각은 연동 규약에 따른 적용 지점이며, 코어의 실제 변수명에 맞춰 삽입한다.

1. `Robot.__init__`: 기존 인자 뒤에 `health_monitor: HealthMonitor | None = None` 추가. 기존 알림 서비스와 `saved` 초기화 **후** 아래를 실행한다. `alert_service`는 아래 예시의 자리표시자이며 실제 `AlertService` 인스턴스로 바꾼다.

   ```python
   from health_monitor import HealthMonitor, MockWearable

   self.health_monitor = health_monitor if health_monitor is not None else HealthMonitor(MockWearable(), alert_service)
   self.health_monitor.restore(saved.get("health_monitor"))
   ```

2. `Robot.save`: 기존 저장 dict에 `"health_monitor": self.health_monitor.snapshot()`을 추가한다. 다른 키와 기존 저장 호출은 유지한다.
3. `IntentClassifier.EXAMPLES` / `Robot.generate_reply`: 음성 의도는 선택 통합이다. 추가 시 `health_check` 예시 `심박수와 산소포화도 확인`을 쓰고 기존 dispatch 패턴에서 `self.health_monitor.status()`를 반환한다. 기존 인사·복약·키오스크·응급·배터리 문구 대상으로 분류 회귀 테스트를 먼저 추가한다.
4. `run_gui()`: 기존 Notebook과 저장·갱신 콜백을 사용한다. `notebook`과 `on_state_change`는 실제 코어 변수명에 맞춘다.

   ```python
   from health_monitor.ui import build_health_monitor_tab

   health_tab = ttk.Frame(notebook)
   notebook.add(health_tab, text="건강 모니터링")
   build_health_monitor_tab(health_tab, robot, on_state_change)
   ```

## 4. DUR 외부 계약

첨부에 표시된 서비스 베이스는 `https://apis.data.go.kr/1471000/DURPrdlstInfoService03`이다. 실 어댑터는 하위 작업 `getUsjntTabooInfoList`에 `itemName`, `serviceKey`, `type=json`, `pageNo=1`, `numOfRows=10`을 GET으로 전달한다. 타임아웃은 5초이며 성공 시 첫 페이지 항목 리스트를 반환한다. 응답·네트워크 오류는 키 없는 메시지로 변환한다. 첨부에는 작업별 명세와 응답 원본이 없어 **실 호출 및 응답 계약은 미검증**이며 병합 전 공공데이터포털 작업별 명세 및 승인 계정으로 확인한다. DUR은 코어 GUI나 이상 경보에 연결하지 않는다.

## 5. 검증 추적

- HM-F01/F03/F04: 입력 오류, 중복, 임계 경계, 알림 역할 및 에피소드 리셋 테스트.
- HM-F05: JSON 왕복, 누락 상태 복원, 복원 후 재알림 억제 테스트.
- HM-F06/N01: 가짜 HTTP 응답과 비밀키가 포함된 네트워크 오류의 안전 처리 테스트.
- 코어 전체 회귀, Tkinter 실제 구동, 실제 API/BLE는 이번 단독 검증에 포함되지 않는다.
