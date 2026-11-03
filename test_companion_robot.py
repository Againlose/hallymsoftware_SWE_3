"""표준 라이브러리 unittest: python -m unittest -v"""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from companion_robot import JsonStore, Robot, IntentClassifier, Navigator, MedicationManager


class CompanionRobotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.robot = Robot(JsonStore(Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_intent_recognition(self):
        classifier = IntentClassifier()
        for text, expected in [
            ("안녕하세요", "greeting"), ("약 복용 알려줘", "medication"),
            ("키오스크 사용법", "kiosk"), ("넘어졌어 도와줘", "emergency"),
            ("배터리 잔량 알려줘", "status"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(classifier.classify(text)[0], expected)

    def test_route(self):
        self.assertEqual(Navigator().route("거실", "화장실"), ["거실", "복도", "화장실"])
        self.assertEqual(Navigator().route("거실", "주방"), ["거실", "주방"])

    def test_obstacle(self):
        self.assertIn("주의", self.robot.check_distance(30))
        self.assertIn("임계값", self.robot.check_distance(90))

    def test_medication_due_once_a_day(self):
        manager = MedicationManager()
        manager.add("예시약", "09:00")
        now = datetime(2026, 11, 3, 9, 2)
        self.assertEqual(len(manager.check_due(now)), 1)
        self.assertEqual(manager.check_due(now), [])
        self.assertEqual(len(manager.check_due(datetime(2026, 11, 4, 9, 2))), 1)

    def test_medication_validation(self):
        with self.assertRaises(ValueError):
            self.robot.medications.add("예시약", "25:00")

    def test_fall_detection_is_local_only(self):
        self.robot.trigger_fall()
        self.assertTrue(self.robot.fall.measure())
        self.assertEqual(self.robot.alerts.records[-1]["delivery"], "LOCAL_SIMULATION_ONLY")
        self.robot.reset_emergency()
        self.assertEqual(self.robot.status, "정상")

    def test_conversation_saved_and_reloaded(self):
        response, intent, score = self.robot.start_conversation("안녕하세요")
        self.assertIn("안녕하세요", response)
        self.assertEqual(intent, "greeting")
        restored = Robot(JsonStore(Path(self.tmp.name)))
        self.assertEqual(len(restored.history), 1)
        self.assertEqual(restored.battery, 84)
        restored.start_conversation("배터리 충전")
        self.assertEqual(restored.battery, 100)

    def test_kiosk_guide(self):
        response, intent, _ = self.robot.start_conversation("키오스크 이용 방법")
        self.assertEqual(intent, "kiosk")
        self.assertIn("결제", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
