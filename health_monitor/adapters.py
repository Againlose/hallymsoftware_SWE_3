import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from .models import Reading

class MockWearable:
    def __init__(self, heart_rate=75, spo2=98):
        self.heart_rate, self.spo2 = heart_rate, spo2

    def read(self):
        return Reading(datetime.now(timezone.utc).isoformat(), self.heart_rate, self.spo2)

class JsonWearable:
    """Read one locally exported wearable sample via the shared JSON contract."""
    def __init__(self, path):
        self.path = path

    def read(self):
        with open(self.path, encoding='utf-8') as stream:
            record = json.load(stream)
        return Reading(**record)

class MockDrugLookup:
    def lookup(self, product):
        return [{'ITEM_NAME': product, 'source': 'MOCK – 실제 의약품 정보 아님'}]

class DurLookup:
    URL = ('https://apis.data.go.kr/1471000/DURPrdlstInfoService03/'
           'getUsjntTabooInfoList')

    def __init__(self, opener=urlopen):
        self.opener = opener

    def lookup(self, product):
        product = product.strip()
        if not 1 <= len(product) <= 100:
            raise ValueError('제품명을 1~100자로 입력하세요.')
        key = os.getenv('DUR_SERVICE_KEY')
        if not key:
            raise RuntimeError('DUR_SERVICE_KEY를 설정하세요.')
        query = urlencode(dict(serviceKey=key, itemName=product, type='json', pageNo=1, numOfRows=10))
        try:
            with self.opener(f'{self.URL}?{query}', timeout=5) as response:
                payload = json.loads(response.read(2_000_001))
            if str(payload['header']['resultCode']) not in ('00', '0'):
                raise ValueError('API error')
            items = payload['body'].get('items') or []
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise ValueError('API response')
            return items
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
        raise RuntimeError('DUR 조회 실패: 승인 상태·제품명·응답 형식을 확인하세요.')
