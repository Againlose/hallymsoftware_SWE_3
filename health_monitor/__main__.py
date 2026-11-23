import argparse
import json
from . import HealthMonitor, MockWearable, JsonWearable, DurLookup, MockDrugLookup

class ConsoleAlerts:
    def create(self, category, message):
        print(f'{category} | {message}')

parser = argparse.ArgumentParser(description='건강 모니터링 시연 도구')
parser.add_argument('--abnormal', action='store_true', help='연속 이상 입력 시연')
parser.add_argument('--drug', help='DUR 병용금기 품목명 검색')
parser.add_argument('--live', action='store_true', help='DUR 실제 API 사용')
parser.add_argument('--sample', help='로컬 웨어러블 JSON 파일')
args = parser.parse_args()
if args.live and args.drug is None:
    parser.error('--live에는 --drug가 필요합니다.')
if args.sample and (args.drug is not None or args.abnormal):
    parser.error('--sample은 --drug 또는 --abnormal과 함께 쓸 수 없습니다.')
try:
    if args.drug is not None:
        adapter = DurLookup() if args.live else MockDrugLookup()
        print('참고용 검색 결과: 결과 없음은 병용 안전을 의미하지 않습니다.')
        print(json.dumps(adapter.lookup(args.drug), ensure_ascii=False, indent=2))
    else:
        source = JsonWearable(args.sample) if args.sample else MockWearable(120 if args.abnormal else 75)
        monitor = HealthMonitor(source, ConsoleAlerts())
        monitor.collect()
        if not args.sample:
            monitor.collect()
        print(monitor.status())
except (RuntimeError, ValueError) as error:
    parser.exit(1, f'{error}\n')
except (OSError, TypeError):
    parser.exit(1, '샘플 파일의 접근 권한과 필드 이름을 확인하세요.\n')
