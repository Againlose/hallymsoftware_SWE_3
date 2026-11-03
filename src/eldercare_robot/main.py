"""Run a deterministic demo with simulated sensor input."""
from datetime import datetime, time
from .controller import RobotController
from .fall_detection import MotionSample
from .guidance import facility_guide, kiosk_guide
from .medication import MedicationManager, Reminder

def main() -> None:
    controller = RobotController()
    print("[모의 낙상 이벤트]", controller.process_motion(MotionSample(True, True, 12)))
    print("[이동 가능]", controller.mobility.can_move(2.0))
    manager = MedicationManager([Reminder("예시 복약 알림", time(9, 0))])
    print("[복약 알림]", manager.due(datetime(2026, 11, 3, 9, 0)))
    print("[시설 안내]", facility_guide("elevator"))
    print("[키오스크 안내]", kiosk_guide())
    print("[보호자 알림 기록]", controller.notifier.events)

if __name__ == "__main__":
    main()
