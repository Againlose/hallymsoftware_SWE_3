"""통합 모듈(코어 · Smart Home · Health Monitor · Family Memory Archive) 연동 테스트."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import time
import unittest

from companion_robot import IntentClassifier, JsonStore, MedicationManager, Robot
from health_monitor import HealthMonitor
from health_monitor.adapters import MockWearable
from smart_home import ValveState
from time_utils import format_local_time


class _FakeChatModel:
    """향후 Ollama 등 외부 대화 모델 교체 가능성(DI) 검증용 스텁."""

    def classify(self, text: str) -> tuple[str, float]:
        return "greeting", 0.99


class _FakeMedicationManager(MedicationManager):
    """향후 복약 리마인더 고도화 모듈 교체 가능성(DI) 검증용 스텁."""

    def __init__(self) -> None:
        super().__init__([{"name": "고도화약", "time": "08:30", "last_alert": ""}])


class IntegratedPrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = JsonStore(Path(self.tmp.name))

    def test_robot_health_monitor_persistence_and_alerts(self) -> None:
        robot = Robot(self.store)
        self.assertIsInstance(robot.health_monitor.source, MockWearable)

        # 정상 1회 수집
        robot.health_monitor.collect()
        self.assertEqual(len(robot.health_monitor.history), 1)
        time.sleep(0.02)

        # 연속 2회 이상 징후 수집 -> 사용자/보호자 로컬 알림 각 1건
        robot.health_monitor.source.heart_rate = 125
        robot.health_monitor.source.spo2 = 89
        robot.health_monitor.collect()
        time.sleep(0.02)
        robot.health_monitor.collect()
        robot.save()

        health_alerts = [rec for rec in robot.alerts.records if rec["category"].startswith("건강/")]
        self.assertEqual([rec["category"] for rec in health_alerts], ["건강/사용자", "건강/보호자"])
        self.assertTrue(all(rec["delivery"] == "LOCAL_SIMULATION_ONLY" for rec in health_alerts))

        # 재시작 복원 후 이력 및 중복 억제(_notified) 유지 확인
        reloaded = Robot(self.store)
        self.assertEqual(len(reloaded.health_monitor.history), 3)
        time.sleep(0.02)
        reloaded.health_monitor.source.heart_rate = 125
        reloaded.health_monitor.source.spo2 = 89
        reloaded.health_monitor.collect()
        reloaded_alerts = [rec for rec in reloaded.alerts.records if rec["category"].startswith("건강/")]
        self.assertEqual(len(reloaded_alerts), 2)

    def test_all_modules_end_to_end_persistence(self) -> None:
        robot = Robot(self.store)
        robot.update_profile("홍길동", "큰 글씨")
        robot.medications.add("혈압약", "09:00")
        robot.smart_home.simulate_gas_open(opened_minutes=35)
        robot.check_gas_safety()
        robot.health_monitor.collect()

        archive_id = robot.memory_archive.create_archive(robot.profile.user_id, "개인 보관함")
        robot.memory_archive.create_memory(
            robot.profile.user_id, archive_id, "봄 나들이", "공원에 다녀왔다."
        )
        robot.save()

        restored = Robot(self.store)
        self.assertEqual(restored.profile.name, "홍길동")
        self.assertEqual(len(restored.medications.entries), 1)
        self.assertEqual(restored.smart_home.get_device_status().state, ValveState.OPEN)
        self.assertEqual(restored.smart_home.get_device_status().opened_minutes, 35)
        self.assertEqual(len(restored.health_monitor.history), 1)
        memories = restored.memory_archive.search(restored.profile.user_id, "나들이")
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["title"], "봄 나들이")

    def test_profile_name_syncs_to_memory_archive(self) -> None:
        robot = Robot(self.store)
        robot.update_profile("김어르신", "천천히")
        family_id = robot.memory_archive.create_family(robot.profile.user_id, "우리 가족")
        members = robot.memory_archive.list_members(robot.profile.user_id, family_id)
        self.assertEqual(members[0]["display_name"], "김어르신")

        # 재시작 후 saved profile 이름과 DB 이름도 일치 유지
        reloaded = Robot(self.store)
        self.assertEqual(reloaded.profile.name, "김어르신")

    def test_new_intents_and_full_regression_no_collision(self) -> None:
        classifier = IntentClassifier()
        cases = [
            ("안녕하세요", "greeting"),
            ("약 복용 알려줘", "medication"),
            ("화장실로 이동", "navigation"),
            ("키오스크 사용법", "kiosk"),
            ("배터리 잔량 알려줘", "status"),
            ("배터리 충전", "charge"),
            ("넘어졌어 도와줘", "emergency"),
            ("가스불 확인해줘", "smart_home_status"),
            ("가스불 꺼줘", "smart_home_shutoff"),
            ("심박수 알려줘", "health_check"),
            ("건강 상태 확인해줘", "health_check"),
            ("가족 기억 찾아줘", "memory_search"),
            ("저장된 추억 검색해줘", "memory_search"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(classifier.classify(text)[0], expected)

        robot = Robot(self.store)
        robot.health_monitor.collect()
        archive_id = robot.memory_archive.create_archive(robot.profile.user_id, "가족")
        robot.memory_archive.create_memory(robot.profile.user_id, archive_id, "동해 여행", "바다를 보았다.")

        health_reply, health_intent, _ = robot.start_conversation("심박수 알려줘")
        self.assertEqual(health_intent, "health_check")
        self.assertIn("KST", health_reply)

        mem_reply, mem_intent, _ = robot.start_conversation("동해 기억 찾아줘")
        self.assertEqual(mem_intent, "memory_search")
        self.assertIn("동해 여행", mem_reply)

    def test_utc_storage_and_kst_display_formatting(self) -> None:
        robot = Robot(self.store)
        robot.start_conversation("가스불 꺼줘")
        alert_time = robot.alerts.records[-1]["time"]
        conv_time = robot.history[-1].time
        valve_time = robot.smart_home.get_device_status().updated_at

        for ts in (alert_time, conv_time, valve_time):
            dt = datetime.fromisoformat(ts)
            self.assertIsNotNone(dt.tzinfo)
            self.assertEqual(dt.utcoffset(), timedelta(0))

        self.assertEqual(format_local_time("2026-11-23T15:00:00+00:00"), "2026-11-24 00:00:00 KST")
        self.assertEqual(format_local_time("2026-11-23T15:00:00Z"), "2026-11-24 00:00:00 KST")
        self.assertEqual(format_local_time("2026-11-24T01:02:09"), "2026-11-24 01:02:09 KST")

    def test_robot_di_extensibility_for_future_modules(self) -> None:
        robot = Robot(
            self.store,
            ai_model=_FakeChatModel(),
            medications=_FakeMedicationManager(),
        )
        self.assertEqual(robot.medications.entries[0]["name"], "고도화약")
        reply, intent, conf = robot.start_conversation("아무 문장")
        self.assertEqual(intent, "greeting")
        self.assertEqual(conf, 0.99)
        self.assertIn("안녕하세요", reply)


if __name__ == "__main__":
    unittest.main(verbosity=2)
