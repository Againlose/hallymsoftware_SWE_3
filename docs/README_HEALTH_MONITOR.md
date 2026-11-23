# Health Monitoring — 4번 모듈 운영 및 실행 안내

심박·산소포화도 수집, 이상 징후 감지, 사용자·보호자 로컬 알림을 구현한 독립 Python 패키지(`health_monitor/`)입니다. Python 3.10+ 기준이며 추가 pip 의존성은 없습니다. 코어 GUI(`6단계 · 건강 모니터링` 탭)에 통합되어 있습니다.

```bash
python -m health_monitor
python -m health_monitor --abnormal
python -m health_monitor --drug '시연용 제품명'
python -m unittest -v test_health_monitor test_integration
```

* [요구사항 명세서(SRS v0.2)](HEALTH_MONITOR_SRS.md)
* [설계서(SD v0.2): 함수·변수·의존성·상태 전이](HEALTH_MONITOR_SD.md)

## 시간 표준 (UTC 내부 저장 / KST 표시)

* 라이브러리 내부(`Reading.recorded_at`)는 **RFC 3339 / ISO 8601 UTC(`+00:00`)**로 저장·판정합니다.
* 코어 GUI 탭 및 대화 응답(`Robot.get_health_status_summary()`)에서는 `time_utils.format_local_time()`을 통해 **로컬 KST(`+09:00`)**로 변환해 표시합니다.

## DUR 실제 조회 (선택 CLI 기능)

실제 공공데이터포털 인증키는 저장소에 포함하지 않습니다. 조회 테스트 시 일반 인증키(Decoding)를 쉘 환경 변수 `DUR_SERVICE_KEY`로만 설정하세요.

```bash
read -rsp 'DUR 키: ' DUR_SERVICE_KEY; echo
export DUR_SERVICE_KEY
python -m health_monitor --drug '품목명' --live
unset DUR_SERVICE_KEY
```

실 연동 전 포털에서 상세 작업명과 응답 스키마를 확인하세요. 이 검색은 병용 안전 여부를 판단하지 않습니다.

## 로컬 웨어러블 브리지

```bash
python -m health_monitor --sample /path/to/latest_sample.json
```

팀 GUI에서 외부 JSON 샘플을 연동하려면 `HEALTH_WEARABLE_JSON`에 샘플 JSON 파일의 절대 경로를 지정하고 `python companion_robot.py`를 실행하세요. 환경 변수가 비어 있으면 기본 `MockWearable` 시뮬레이션 모드(심박수/SpO₂ Spinbox 및 이상값 시연 프리셋 지원)로 동작합니다.

## 현재 검증 상태

* 오프라인 단위 테스트(`test_health_monitor.py` 10건) 및 코어 통합 테스트(`test_integration.py`) 전부 통과.
* 운영/의료 서비스 투입본이 아닌 팀 통합·시연용 구현이며, 실기기 BLE 연동 및 실제 DUR API 키 검증은 범위 외입니다.
