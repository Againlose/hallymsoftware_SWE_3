"""Smart Home Control 데이터 모델 정의."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValveState(str, Enum):
    """IoT 가스밸브의 시뮬레이션 상태."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SHUTTING_OFF = "SHUTTING_OFF"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


@dataclass
class DeviceStatus:
    """스마트홈 기기 상태 조회 결과."""

    device_id: str
    device_type: str
    name: str
    state: ValveState
    is_shut_off: bool
    opened_minutes: int
    updated_at: str
    source: str = "local"


@dataclass
class CommandResult:
    """스마트홈 기기 제어 명령 실행 결과."""

    device_id: str
    command: str
    success: bool
    previous_state: ValveState
    current_state: ValveState
    message: str
    timestamp: str
    simulated: bool = True


@dataclass
class ApiResponse:
    """스마트홈 제어 API 어댑터 표준 응답 모델."""

    ok: bool
    status_code: int
    payload: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
