"""Smart Home Control 기기 도메인 구현체."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .exceptions import CommandExecutionError
from .interfaces import SmartDevice
from .models import CommandResult, DeviceStatus, ValveState


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class GasValve(SmartDevice):
    """IoT 가스밸브 자동 차단기 시뮬레이션 모델 (UML: 가스밸브)."""

    DEVICE_TYPE = "gas_valve"

    def __init__(
        self,
        device_id: str = "gas_valve_main",
        name: str = "주방 가스밸브",
        initial_state: ValveState = ValveState.CLOSED,
        opened_minutes: int = 0,
        updated_at: str | None = None,
    ) -> None:
        self._device_id = device_id
        self._name = name
        self.state = initial_state
        self.opened_minutes = max(0, int(opened_minutes)) if initial_state == ValveState.OPEN else 0
        self.updated_at = updated_at or _now_iso()

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_shut_off(self) -> bool:
        """밸브가 잠금(차단) 상태인지 여부 (UML: 차단상태)."""
        return self.state == ValveState.CLOSED

    def get_status(self, source: str = "local") -> DeviceStatus:
        return DeviceStatus(
            device_id=self._device_id,
            device_type=self.DEVICE_TYPE,
            name=self._name,
            state=self.state,
            is_shut_off=self.is_shut_off,
            opened_minutes=self.opened_minutes,
            updated_at=self.updated_at,
            source=source,
        )

    def shut_off(self) -> CommandResult:
        """가스밸브를 차단한다 (UML: 가스차단). 이미 잠긴 경우 멱등하게 성공 처리한다."""
        previous = self.state
        now = _now_iso()
        if self.state == ValveState.CLOSED:
            return CommandResult(
                device_id=self._device_id,
                command="SHUT_OFF",
                success=True,
                previous_state=previous,
                current_state=self.state,
                message=f"이미 {self._name}가 잠겨 있습니다. (시뮬레이션)",
                timestamp=now,
                simulated=True,
            )
        if self.state in (ValveState.ERROR, ValveState.OFFLINE):
            return CommandResult(
                device_id=self._device_id,
                command="SHUT_OFF",
                success=False,
                previous_state=previous,
                current_state=self.state,
                message=f"{self._name} 상태 이상({self.state.value})으로 차단할 수 없습니다. 직접 확인해 주세요. (시뮬레이션)",
                timestamp=now,
                simulated=True,
            )

        self.state = ValveState.CLOSED
        self.opened_minutes = 0
        self.updated_at = now
        return CommandResult(
            device_id=self._device_id,
            command="SHUT_OFF",
            success=True,
            previous_state=previous,
            current_state=self.state,
            message=f"{self._name}를 안전하게 차단했습니다. (시뮬레이션)",
            timestamp=now,
            simulated=True,
        )

    def open_valve(self, opened_minutes: int = 0) -> CommandResult:
        """테스트 및 시연용으로 가스밸브 열림 상태를 시뮬레이션한다."""
        previous = self.state
        now = _now_iso()
        self.state = ValveState.OPEN
        self.opened_minutes = max(0, int(opened_minutes))
        self.updated_at = now
        return CommandResult(
            device_id=self._device_id,
            command="OPEN",
            success=True,
            previous_state=previous,
            current_state=self.state,
            message=f"{self._name} 열림 상태를 시뮬레이션했습니다(경과 {self.opened_minutes}분). (시뮬레이션)",
            timestamp=now,
            simulated=True,
        )

    def handle_command(self, command: str, params: dict[str, Any] | None = None) -> CommandResult:
        normalized = command.strip().upper()
        if normalized == "SHUT_OFF":
            return self.shut_off()
        if normalized == "OPEN":
            minutes = (params or {}).get("opened_minutes", 0)
            return self.open_valve(opened_minutes=int(minutes))
        if normalized == "STATUS":
            state_label = "잠김" if self.is_shut_off else self.state.value
            return CommandResult(
                device_id=self._device_id,
                command="STATUS",
                success=True,
                previous_state=self.state,
                current_state=self.state,
                message=f"{self._name} 현재 상태: {state_label} (시뮬레이션)",
                timestamp=_now_iso(),
                simulated=True,
            )
        raise CommandExecutionError(f"지원하지 않는 명령입니다: {command}")

    def sync_from_payload(self, payload: dict[str, Any]) -> None:
        """API 응답 페이로드와 로컬 기기 상태를 동기화한다."""
        raw_state = payload.get("state")
        if raw_state is not None:
            try:
                self.state = ValveState(str(raw_state))
            except ValueError:
                pass
        if "opened_minutes" in payload:
            try:
                self.opened_minutes = max(0, int(payload["opened_minutes"]))
            except (TypeError, ValueError):
                pass
        if self.state != ValveState.OPEN:
            self.opened_minutes = 0
        if isinstance(payload.get("updated_at"), str) and payload["updated_at"]:
            self.updated_at = payload["updated_at"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self._device_id,
            "device_type": self.DEVICE_TYPE,
            "name": self._name,
            "state": self.state.value,
            "opened_minutes": self.opened_minutes,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GasValve:
        raw_state = str(data.get("state", ValveState.CLOSED.value))
        try:
            state = ValveState(raw_state)
        except ValueError:
            state = ValveState.CLOSED
        try:
            opened_minutes = max(0, int(data.get("opened_minutes", 0)))
        except (TypeError, ValueError):
            opened_minutes = 0
        return cls(
            device_id=str(data.get("device_id", "gas_valve_main")),
            name=str(data.get("name", "주방 가스밸브")),
            initial_state=state,
            opened_minutes=opened_minutes,
            updated_at=data.get("updated_at") if isinstance(data.get("updated_at"), str) else None,
        )
