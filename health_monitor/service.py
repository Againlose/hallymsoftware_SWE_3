from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
from .interfaces import WearableSource, AlertSink
from .models import Reading

class HealthMonitor:
    def __init__(self, source: WearableSource, alerts: AlertSink, *, clock=None):
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.source = source
        self.alerts = alerts
        self.history = deque(maxlen=100)
        self._notified = set()

    @staticmethod
    def abnormal(reading):
        return reading.heart_rate < 50 or reading.heart_rate > 110 or reading.spo2 < 92

    def collect(self):
        reading = self.source.read()
        if self.history and datetime.fromisoformat(reading.recorded_at) <= datetime.fromisoformat(self.history[-1].recorded_at):
            raise ValueError('중복 또는 과거 측정값입니다.')
        timestamp = datetime.fromisoformat(reading.recorded_at)
        age = (self._clock() - timestamp).total_seconds()
        if not -10 <= age <= 300:
            raise ValueError("측정값이 오래되었거나 미래 시각입니다.")
        adjacent = bool(self.history) and (timestamp - datetime.fromisoformat(self.history[-1].recorded_at)).total_seconds() <= 120
        self.history.append(reading)
        if not adjacent:
            self._notified.clear()
        if not self.abnormal(reading):
            self._notified.clear()
        elif adjacent and self.abnormal(self.history[-2]):
            for audience in ('사용자', '보호자'):
                if audience not in self._notified:
                    self.alerts.create(f'건강/{audience}', f'[로컬 시뮬레이션] {audience} 알림: 연속 이상 범위 감지. 기기 상태와 측정값을 확인하세요.')
                    self._notified.add(audience)
        return reading

    def status(self):
        if not self.history:
            return '측정 기록 없음'
        sample = self.history[-1]
        label = '시연 기준 범위 이탈' if self.abnormal(sample) else '시연 기준 범위 내'
        if (self._clock() - datetime.fromisoformat(sample.recorded_at)).total_seconds() > 300:
            label = '오래된 기록 · 현재 상태 알 수 없음'
        return f'{label} | 심박 {sample.heart_rate} bpm | 산소포화도 {sample.spo2}% | {sample.recorded_at}'

    def snapshot(self):
        return {'history': [asdict(r) for r in self.history], 'notified': sorted(self._notified)}

    def restore(self, data):
        self.history.clear()
        self._notified.clear()
        if not isinstance(data, dict) or not isinstance(data.get('history'), list):
            return
        for row in data['history'][-100:]:
            try:
                sample = Reading(**row)
                if not self.history or datetime.fromisoformat(sample.recorded_at) > datetime.fromisoformat(self.history[-1].recorded_at):
                    self.history.append(sample)
            except (TypeError, ValueError, OverflowError):
                continue
        notified = data.get('notified')
        if self.history and self.abnormal(self.history[-1]) and isinstance(notified, list):
            self._notified = {name for name in ('사용자', '보호자') if name in notified}
