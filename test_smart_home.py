"""Smart Home Control 단위 및 통합 테스트: python -m unittest -v"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from companion_robot import IntentClassifier, JsonStore, Robot
from smart_home import (
    ApiResponse,
    CommandExecutionError,
    DeviceNotFoundError,
    GasValve,
    SmartDevice,
    SmartHomeApiClient,
    SmartHomeController,
    ValveState,
    create_default_controller,
)


class _FakeApiClient(SmartHomeApiClient):
    """외부 API 교체 가능성(DIP)을 검증하기 위한 최소 테스트 어댑터."""

    def __init__(self) -> None:
        self.commands: list[tuple[str, str]] = []
        self.state = ValveState.OPEN.value

    def fetch_device_status(self, device_id: str) -> ApiResponse:
        return ApiResponse(
            ok=True,
            status_code=200,
            payload={
                "device_id": device_id,
                "state": self.state,
                "opened_minutes": 15 if self.state == ValveState.OPEN.value else 0,
                "source": "fake_api",
            },
        )

    def send_device_command(self, device_id: str, command: str, params=None) -> ApiResponse:
        self.commands.append((device_id, command))
        if command == "SHUT_OFF":
            self.state = ValveState.CLOSED.value
        return ApiResponse(
            ok=True,
            status_code=200,
            payload={"device_id": device_id, "command": command, "state": self.state},
        )

    def health_check(self) -> bool:
        return True


class SmartHomeControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JsonStore(Path(self.tmp.name))
        self.controller = create_default_controller()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_tc_sh_01_gas_valve_initial_state_and_interface(self) -> None:
        valve = GasValve()
        self.assertIsInstance(valve, SmartDevice)
        status = valve.get_status()
        self.assertEqual(status.state, ValveState.CLOSED)
        self.assertTrue(valve.is_shut_off)
        self.assertTrue(status.is_shut_off)

    def test_tc_sh_02_simulate_gas_open_and_status(self) -> None:
        self.controller.simulate_gas_open(opened_minutes=10)
        status = self.controller.get_device_status()
        self.assertEqual(status.state, ValveState.OPEN)
        self.assertFalse(status.is_shut_off)
        self.assertEqual(status.opened_minutes, 10)
        self.assertEqual(status.source, "mock_api")

    def test_tc_sh_03_gas_shutoff_success(self) -> None:
        self.controller.simulate_gas_open(opened_minutes=12)
        result = self.controller.request_gas_shutoff()
        self.assertTrue(result.success)
        self.assertEqual(result.previous_state, ValveState.OPEN)
        self.assertEqual(result.current_state, ValveState.CLOSED)
        status = self.controller.get_device_status()
        self.assertEqual(status.opened_minutes, 0)
        self.assertTrue(status.is_shut_off)

    def test_tc_sh_04_gas_shutoff_idempotent_when_already_closed(self) -> None:
        result = self.controller.request_gas_shutoff()
        self.assertTrue(result.success)
        self.assertEqual(result.previous_state, ValveState.CLOSED)
        self.assertEqual(result.current_state, ValveState.CLOSED)
        self.assertIn("이미", result.message)

    def test_tc_sh_05_unregistered_device_and_unsupported_command(self) -> None:
        with self.assertRaises(DeviceNotFoundError):
            self.controller.get_device_status("unknown_device")
        valve = self.controller.get_device()
        with self.assertRaises(CommandExecutionError):
            valve.handle_command("INVALID_CMD")

    def test_tc_sh_06_long_open_safety_check_and_robot_alert(self) -> None:
        self.controller.simulate_gas_open(opened_minutes=10)
        safe_ok, _ = self.controller.check_gas_safety()
        self.assertTrue(safe_ok)

        self.controller.simulate_gas_open(opened_minutes=35)
        safe_warn, warn_msg = self.controller.check_gas_safety()
        self.assertFalse(safe_warn)
        self.assertIn("경고", warn_msg)

        robot = Robot(self.store)
        robot.smart_home.simulate_gas_open(opened_minutes=40)
        robot_ok, robot_msg = robot.check_gas_safety()
        self.assertFalse(robot_ok)
        self.assertIn("40분", robot_msg)
        self.assertEqual(robot.alerts.records[-1]["category"], "스마트홈/가스 경고")

    def test_tc_sh_07_api_offline_fail_safe(self) -> None:
        self.controller.simulate_gas_open(opened_minutes=20)
        self.controller.set_fault_mode(offline=True)
        result = self.controller.request_gas_shutoff()
        self.assertFalse(result.success)
        self.assertEqual(result.current_state, ValveState.OPEN)
        self.assertIn("통신 오류", result.message)

    def test_tc_sh_08_api_command_failure_fail_safe(self) -> None:
        self.controller.simulate_gas_open(opened_minutes=20)
        self.controller.set_fault_mode(fail_commands=True)
        result = self.controller.request_gas_shutoff()
        self.assertFalse(result.success)
        self.assertEqual(result.current_state, ValveState.OPEN)
        self.assertEqual(self.controller.get_device().get_status().state, ValveState.OPEN)

    def test_tc_sh_09_custom_api_client_injection_dip(self) -> None:
        fake_client = _FakeApiClient()
        controller = SmartHomeController(api_client=fake_client)
        controller.register_device(GasValve(initial_state=ValveState.OPEN, opened_minutes=15))

        status = controller.get_device_status()
        self.assertEqual(status.source, "fake_api")
        result = controller.request_gas_shutoff()
        self.assertTrue(result.success)
        self.assertEqual(result.current_state, ValveState.CLOSED)
        self.assertEqual(fake_client.commands, [("gas_valve_main", "SHUT_OFF")])

    def test_tc_sh_10_intent_classifier_no_collision(self) -> None:
        classifier = IntentClassifier()
        cases = [
            ("가스불 확인해줘", "smart_home_status"),
            ("가스밸브 상태 알려줘", "smart_home_status"),
            ("가스불 꺼줘", "smart_home_shutoff"),
            ("가스 차단해줘", "smart_home_shutoff"),
            ("안녕하세요", "greeting"),
            ("약 복용 알려줘", "medication"),
            ("키오스크 사용법", "kiosk"),
            ("넘어졌어 도와줘", "emergency"),
            ("배터리 잔량 알려줘", "status"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(classifier.classify(text)[0], expected)

    def test_tc_sh_11_robot_conversation_and_alert_integration(self) -> None:
        robot = Robot(self.store)
        robot.smart_home.simulate_gas_open(opened_minutes=5)
        reply_status, intent_status, _ = robot.start_conversation("가스불 확인해줘")
        self.assertEqual(intent_status, "smart_home_status")
        self.assertIn("열려 있습니다", reply_status)

        reply_off, intent_off, _ = robot.start_conversation("가스불 꺼줘")
        self.assertEqual(intent_off, "smart_home_shutoff")
        self.assertIn("차단", reply_off)
        self.assertTrue(robot.smart_home.get_device_status().is_shut_off)
        self.assertEqual(robot.alerts.records[-1]["category"], "스마트홈/가스")
        self.assertEqual(robot.alerts.records[-1]["delivery"], "LOCAL_SIMULATION_ONLY")

    def test_tc_sh_12_json_persistence_and_legacy_compatibility(self) -> None:
        # 구버전 companion_state.json(smart_home 키 없음) 호환성 확인
        self.store.save({"battery": 77, "status": "정상"})
        legacy_robot = Robot(self.store)
        self.assertTrue(legacy_robot.smart_home.get_device_status().is_shut_off)

        # 상태 및 장애 모드 저장/복원 검증
        legacy_robot.smart_home.simulate_gas_open(opened_minutes=40)
        legacy_robot.smart_home.set_fault_mode(offline=False, fail_commands=True)
        legacy_robot.save()

        restored = Robot(self.store)
        status = restored.smart_home.get_device_status()
        self.assertEqual(status.state, ValveState.OPEN)
        self.assertEqual(status.opened_minutes, 40)
        self.assertTrue(getattr(restored.smart_home.api_client, "fail_commands", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
