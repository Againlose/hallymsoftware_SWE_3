"""Smart Home Control API 어댑터 구현체."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .exceptions import ApiConnectionError
from .interfaces import SmartHomeApiClient
from .models import ApiResponse, ValveState


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class MockSmartHomeApiClient(SmartHomeApiClient):
    """네트워크 없이 동작하는 로컬 IoT 가스불 차단기 Mock API 시뮬레이터."""

    def __init__(self, offline: bool = False, fail_commands: bool = False) -> None:
        self._devices: dict[str, dict[str, Any]] = {}
        self.offline = bool(offline)
        self.fail_commands = bool(fail_commands)

    def set_fault_mode(self, offline: bool = False, fail_commands: bool = False) -> None:
        """장애 시나리오 테스트 및 UI 시연을 위한 오류 모드 설정."""
        self.offline = bool(offline)
        self.fail_commands = bool(fail_commands)

    def sync_device_state(self, device_dict: dict[str, Any]) -> None:
        """로컬 기기 상태를 Mock API 저장소에 반영한다."""
        device_id = str(device_dict["device_id"])
        self._devices[device_id] = dict(device_dict)

    def health_check(self) -> bool:
        return not self.offline

    def fetch_device_status(self, device_id: str) -> ApiResponse:
        if self.offline:
            raise ApiConnectionError("가스불 차단기 게이트웨이가 오프라인 상태입니다. (시뮬레이션)")
        record = self._devices.get(device_id)
        if record is None:
            return ApiResponse(
                ok=False,
                status_code=404,
                payload={},
                error_code="DEVICE_NOT_FOUND",
                error_message=f"기기를 찾을 수 없습니다: {device_id}",
            )
        return ApiResponse(
            ok=True,
            status_code=200,
            payload={
                **record,
                "is_shut_off": record.get("state") == ValveState.CLOSED.value,
                "source": "mock_api",
            },
        )

    def send_device_command(
        self, device_id: str, command: str, params: dict[str, Any] | None = None
    ) -> ApiResponse:
        if self.offline:
            raise ApiConnectionError("통신 두절로 가스불 차단기 명령을 전송할 수 없습니다. (시뮬레이션)")
        if self.fail_commands:
            return ApiResponse(
                ok=False,
                status_code=500,
                payload={"device_id": device_id, "command": command},
                error_code="VALVE_ACTUATION_FAILED",
                error_message="가스밸브 차단기 구동에 실패했습니다. 직접 확인해 주세요. (시뮬레이션)",
            )
        record = self._devices.get(device_id)
        if record is None:
            return ApiResponse(
                ok=False,
                status_code=404,
                payload={},
                error_code="DEVICE_NOT_FOUND",
                error_message=f"기기를 찾을 수 없습니다: {device_id}",
            )

        normalized = command.strip().upper()
        if normalized == "SHUT_OFF":
            record["state"] = ValveState.CLOSED.value
            record["opened_minutes"] = 0
            record["updated_at"] = _now_iso()
        elif normalized == "OPEN":
            record["state"] = ValveState.OPEN.value
            record["opened_minutes"] = max(0, int((params or {}).get("opened_minutes", 0)))
            record["updated_at"] = _now_iso()
        elif normalized != "STATUS":
            return ApiResponse(
                ok=False,
                status_code=400,
                payload={"device_id": device_id, "command": command},
                error_code="UNSUPPORTED_COMMAND",
                error_message=f"지원하지 않는 명령입니다: {command}",
            )

        return ApiResponse(
            ok=True,
            status_code=200,
            payload={
                **record,
                "command": normalized,
                "accepted": True,
                "is_shut_off": record.get("state") == ValveState.CLOSED.value,
                "source": "mock_api",
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "offline": self.offline,
            "fail_commands": self.fail_commands,
        }

    def load_from_dict(self, data: dict[str, Any]) -> None:
        self.offline = bool(data.get("offline", False))
        self.fail_commands = bool(data.get("fail_commands", False))
