"""Smart Home Control 제어기 구현 (UML: 스마트홈제어기)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .adapters import MockSmartHomeApiClient
from .devices import GasValve
from .exceptions import ApiConnectionError, DeviceNotFoundError
from .interfaces import SmartDevice, SmartHomeApiClient
from .models import CommandResult, DeviceStatus, ValveState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SmartHomeController:
    """인터페이스(SmartDevice, SmartHomeApiClient)에만 의존하는 스마트홈 제어기."""

    DEFAULT_GAS_VALVE_ID = "gas_valve_main"

    def __init__(
        self,
        api_client: SmartHomeApiClient | None = None,
        long_open_threshold_minutes: int = 30,
    ) -> None:
        self.api_client: SmartHomeApiClient = api_client if api_client is not None else MockSmartHomeApiClient()
        self.long_open_threshold_minutes = max(1, int(long_open_threshold_minutes))
        self._devices: dict[str, SmartDevice] = {}

    def register_device(self, device: SmartDevice) -> None:
        """스마트기기를 제어기에 등록하고 어댑터와 초기 상태를 동기화한다."""
        self._devices[device.device_id] = device
        self._sync_to_api(device)

    def _sync_to_api(self, device: SmartDevice) -> None:
        if not hasattr(self.api_client, "sync_device_state"):
            return
        if hasattr(device, "to_dict"):
            payload = device.to_dict()  # type: ignore[attr-defined]
        else:
            status = device.get_status()
            payload = {
                "device_id": status.device_id,
                "device_type": status.device_type,
                "name": status.name,
                "state": status.state.value,
                "opened_minutes": status.opened_minutes,
                "updated_at": status.updated_at,
            }
        self.api_client.sync_device_state(payload)  # type: ignore[attr-defined]

    def get_device(self, device_id: str = DEFAULT_GAS_VALVE_ID) -> SmartDevice:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceNotFoundError(f"등록되지 않은 스마트기기입니다: {device_id}")
        return device

    def list_devices(self) -> list[SmartDevice]:
        return list(self._devices.values())

    def get_device_status(self, device_id: str = DEFAULT_GAS_VALVE_ID) -> DeviceStatus:
        """기기 상태를 조회한다 (UML: 기기상태조회)."""
        device = self.get_device(device_id)
        response = self.api_client.fetch_device_status(device_id)
        if not response.ok:
            raise ApiConnectionError(response.error_message or "기기 상태 조회에 실패했습니다.")
        if hasattr(device, "sync_from_payload"):
            device.sync_from_payload(response.payload)  # type: ignore[attr-defined]
        if isinstance(device, GasValve):
            return device.get_status(source=str(response.payload.get("source", "api")))
        return device.get_status()

    def request_gas_shutoff(self, device_id: str = DEFAULT_GAS_VALVE_ID) -> CommandResult:
        """가스밸브 차단을 요청한다 (UML: 가스차단요청). 통신·명령 실패 시 안전 실패 결과를 반환한다."""
        device = self.get_device(device_id)
        previous_state = device.get_status().state
        now = _now_iso()

        try:
            response = self.api_client.send_device_command(device_id, "SHUT_OFF")
        except ApiConnectionError as exc:
            return CommandResult(
                device_id=device_id,
                command="SHUT_OFF",
                success=False,
                previous_state=previous_state,
                current_state=previous_state,
                message=f"통신 오류로 가스 차단에 실패했습니다: {exc}",
                timestamp=now,
                simulated=True,
            )

        if not response.ok:
            return CommandResult(
                device_id=device_id,
                command="SHUT_OFF",
                success=False,
                previous_state=previous_state,
                current_state=previous_state,
                message=response.error_message or "가스 차단 명령 실행에 실패했습니다. (시뮬레이션)",
                timestamp=now,
                simulated=True,
            )

        result = device.handle_command("SHUT_OFF")
        self._sync_to_api(device)
        return result

    def simulate_gas_open(
        self, device_id: str = DEFAULT_GAS_VALVE_ID, opened_minutes: int = 0
    ) -> CommandResult:
        """시뮬레이션/테스트용으로 가스밸브 열림 상태와 경과 시간을 설정한다."""
        device = self.get_device(device_id)
        result = device.handle_command("OPEN", {"opened_minutes": opened_minutes})
        self._sync_to_api(device)
        return result

    def check_gas_safety(self, device_id: str = DEFAULT_GAS_VALVE_ID) -> tuple[bool, str]:
        """장시간 개방 및 이상 상태를 점검해 (안전 여부, 안내 문구)를 반환한다."""
        try:
            status = self.get_device_status(device_id)
        except ApiConnectionError as exc:
            return False, f"가스밸브 통신 오류로 안전 상태를 확인할 수 없습니다: {exc}"

        if status.state == ValveState.OPEN and status.opened_minutes >= self.long_open_threshold_minutes:
            return (
                False,
                f"경고: {status.name}가 {status.opened_minutes}분째 열려 있습니다"
                f"(임계치 {self.long_open_threshold_minutes}분). 가스를 차단해 주세요. (시뮬레이션)",
            )
        if status.state in (ValveState.ERROR, ValveState.OFFLINE):
            return False, f"주의: {status.name} 상태 이상({status.state.value})이 감지되었습니다. (시뮬레이션)"
        if status.state == ValveState.OPEN:
            return (
                True,
                f"{status.name}가 열려 있습니다(경과 {status.opened_minutes}분 / "
                f"임계치 {self.long_open_threshold_minutes}분). (시뮬레이션)",
            )
        return True, f"{status.name}가 안전하게 잠겨 있습니다. (시뮬레이션)"

    def set_fault_mode(self, offline: bool = False, fail_commands: bool = False) -> None:
        """어댑터가 장애 주입을 지원하는 경우 오류 모드를 설정한다."""
        if hasattr(self.api_client, "set_fault_mode"):
            self.api_client.set_fault_mode(offline=offline, fail_commands=fail_commands)  # type: ignore[attr-defined]

    def to_dict(self) -> dict[str, Any]:
        devices_data: dict[str, Any] = {}
        for device_id, device in self._devices.items():
            if hasattr(device, "to_dict"):
                devices_data[device_id] = device.to_dict()  # type: ignore[attr-defined]
        fault_mode = (
            self.api_client.to_dict()  # type: ignore[attr-defined]
            if hasattr(self.api_client, "to_dict")
            else {"offline": False, "fail_commands": False}
        )
        return {
            "long_open_threshold_minutes": self.long_open_threshold_minutes,
            "fault_mode": fault_mode,
            "devices": devices_data,
        }

    def load_from_dict(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        threshold = data.get("long_open_threshold_minutes")
        if isinstance(threshold, int) and threshold >= 1:
            self.long_open_threshold_minutes = threshold

        fault_mode = data.get("fault_mode")
        if isinstance(fault_mode, dict) and hasattr(self.api_client, "load_from_dict"):
            self.api_client.load_from_dict(fault_mode)  # type: ignore[attr-defined]

        devices_raw = data.get("devices")
        if isinstance(devices_raw, dict):
            for device_id, item in devices_raw.items():
                if not isinstance(item, dict):
                    continue
                if item.get("device_type", GasValve.DEVICE_TYPE) == GasValve.DEVICE_TYPE:
                    valve = GasValve.from_dict(item)
                    self._devices[device_id] = valve
                    self._sync_to_api(valve)


def create_default_controller() -> SmartHomeController:
    """기본 Mock 어댑터와 주방 가스밸브가 등록된 SmartHomeController를 생성한다."""
    controller = SmartHomeController(api_client=MockSmartHomeApiClient())
    controller.register_device(GasValve(device_id=SmartHomeController.DEFAULT_GAS_VALVE_ID, name="주방 가스밸브"))
    return controller
