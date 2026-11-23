from dataclasses import dataclass
from datetime import datetime
import math

@dataclass(frozen=True)
class Reading:
    recorded_at: str
    heart_rate: float
    spo2: float

    def __post_init__(self):
        if datetime.fromisoformat(self.recorded_at).utcoffset() is None:
            raise ValueError('시간대가 필요합니다.')
        for value, low, high in ((self.heart_rate, 1, 300), (self.spo2, 1, 100)):
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError('측정값 형식 또는 허용 입력 범위를 확인하세요.')
