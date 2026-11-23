import argparse
import json
from . import HealthMonitor, MockWearable, DurLookup, MockDrugLookup

class ConsoleAlerts:
    def create(self, category, message):
        print(f'{category} | {message}')

parser = argparse.ArgumentParser(description='건강 모니터링 시연 도구')
parser.add_argument('--abnormal', action='store_true', help='연속 이상 입력 시연')
parser.add_argument('--drug', help='DUR 병용금기 품목명 검색')
parser.add_argument('--live', action='store_true', help='DUR 실제 API 사용')
args = parser.parse_args()
try:
    if args.drug is not None:
        adapter = DurLookup() if args.live else MockDrugLookup()
        print('참고용 검색 결과: 결과 없음은 병용 안전을 의미하지 않습니다.')
        print(json.dumps(adapter.lookup(args.drug), ensure_ascii=False, indent=2))
    else:
        monitor = HealthMonitor(MockWearable(120 if args.abnormal else 75), ConsoleAlerts())
        monitor.collect()
        monitor.collect()
        print(monitor.status())
except (RuntimeError, ValueError) as error:
    parser.exit(1, f'{error}\n')
