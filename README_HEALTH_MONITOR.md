# Health Monitoring — 4번 모듈

심박·산소포화도 수집, 이상 징후 감지, 사용자·보호자 로컬 알림을 구현한 독립 Python 패키지입니다. Python 3.10+ 기준이며 추가 pip 의존성은 없습니다. Tkinter 탭은 팀 코어 GUI에 연결합니다.

```bash
python -m health_monitor
python -m health_monitor --abnormal
python -m health_monitor --drug '시연용 제품명'
python -m unittest -v test_health_monitor
```

- [요구사항 명세서(SRS)](docs/HEALTH_MONITOR_SRS.md)
- [설계서(SD): 함수·변수·의존성·코어 삽입 지점](docs/HEALTH_MONITOR_SD.md)

## DUR 실제 조회

첨부 스크린샷에 보인 키는 이 패키지에 넣지 않았습니다. 이미 공유된 키는 폐기·재발급 후 새 일반 인증키(Decoding)를 쉘 환경 변수 `DUR_SERVICE_KEY`로 설정하세요. Bash에서는 아래 방식으로 입력값을 화면·명령 기록에 남기지 않고 주입할 수 있습니다.

```bash
read -rsp 'DUR 키: ' DUR_SERVICE_KEY; echo
export DUR_SERVICE_KEY
python -m health_monitor --drug '품목명' --live
unset DUR_SERVICE_KEY
```

실 연동 전 포털에서 상세 작업명과 응답 스키마를 확인하세요. 이 검색은 병용 안전 여부를 판단하지 않습니다.

## GitHub 반영

1. 팀 저장소에서 `git fetch origin` 후, 처음 만드는 브랜치라면 `git switch -c <본인이름> origin/main`으로 시작합니다. 기존 본인 브랜치가 있다면 그 브랜치에서 팀 방식으로 최신 `origin/main`을 반영합니다. `main`에서 직접 작업하지 않습니다.
2. ZIP 내부 파일을 저장소 루트에 복사합니다. 기존 `README.md`·팀원 파일은 덮어쓰지 않습니다. [SD](docs/HEALTH_MONITOR_SD.md)에 따라 코어를 통합하고 로컬에서 GUI를 확인합니다.
3. 기존 `.gitignore`에 필요한 경우 `.env`, `.env.*`, `companion_state.json`, `demo_data/`, `__pycache__/`, `.pytest_cache/`를 추가합니다. 이미 추적된 비밀 또는 건강 데이터에는 ignore가 소급 적용되지 않습니다.
4. `python -m unittest -v`로 팀 전체 회귀를 검증한 뒤 전용 파일 및 확인된 코어 변경만 스테이징합니다.

```bash
git add health_monitor/ test_health_monitor.py README_HEALTH_MONITOR.md docs/HEALTH_MONITOR_SRS.md docs/HEALTH_MONITOR_SD.md
git add companion_robot.py
git diff --cached
git commit -m "feat: add health monitoring module and specifications"
git push -u origin HEAD
```

GitHub에서 본인 브랜치 → `main` PR을 만들고 팀 리더 검토 후 병합합니다. ZIP 자체나 실제 건강 데이터는 올리지 않습니다.
