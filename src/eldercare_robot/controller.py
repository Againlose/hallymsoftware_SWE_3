"""Safety-priority orchestration for simulated events."""
from dataclasses import dataclass, field
from .fall_detection import FallDetector, MotionSample
from .mobility import MobilityAssistant
from .notifications import GuardianNotifier

@dataclass
class RobotController:
    fall_detector: FallDetector = field(default_factory=FallDetector)
    mobility: MobilityAssistant = field(default_factory=MobilityAssistant)
    notifier: GuardianNotifier = field(default_factory=GuardianNotifier)

    def process_motion(self, sample: MotionSample, user_confirmed_safe: bool = False) -> str:
        if not self.fall_detector.suspicious(sample):
            return "normal"
        self.mobility.stop()
        if user_confirmed_safe:
            return "manual_review_required"
        self.notifier.notify("낙상 의심: 사용자 응답 확인 및 보호자 연락 필요")
        return "alert_recorded"
