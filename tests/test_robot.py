from datetime import datetime, time
from eldercare_robot.controller import RobotController
from eldercare_robot.fall_detection import FallDetector, MotionSample
from eldercare_robot.guidance import facility_guide, kiosk_guide
from eldercare_robot.medication import MedicationManager, Reminder
from eldercare_robot.mobility import MobilityAssistant

def test_fall_detection_requires_all_signals():
    d = FallDetector()
    assert d.suspicious(MotionSample(True, True, 12))
    assert not d.suspicious(MotionSample(True, False, 12))

def test_fall_alert_stops_mobility():
    r = RobotController()
    assert r.process_motion(MotionSample(True, True, 11)) == "alert_recorded"
    assert not r.mobility.can_move(2.0)
    assert len(r.notifier.events) == 1

def test_medication_deduplication():
    m = MedicationManager([Reminder("약 A", time(9, 0))])
    now = datetime(2026, 11, 3, 9, 0)
    assert m.due(now) == ["약 A"]
    assert m.due(now) == []

def test_obstacle_gate():
    m = MobilityAssistant()
    assert not m.can_move(0.2)
    assert m.can_move(1.0)
    m.stop()
    assert not m.can_move(1.0)

def test_guidance():
    assert facility_guide("elevator")
    assert len(kiosk_guide()) == 4
