"""Fall *suspicion* logic; real sensor fusion and clinical validation are TODO."""
from dataclasses import dataclass

@dataclass(frozen=True)
class MotionSample:
    horizontal_posture: bool
    sudden_motion: bool
    immobile_seconds: float

class FallDetector:
    def __init__(self, immobility_threshold: float = 10.0):
        if immobility_threshold <= 0:
            raise ValueError("threshold must be positive")
        self.threshold = immobility_threshold

    def suspicious(self, sample: MotionSample) -> bool:
        return (sample.horizontal_posture and sample.sudden_motion
                and sample.immobile_seconds >= self.threshold)
