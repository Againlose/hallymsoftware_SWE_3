"""AI 컴패니언 로봇 Smart Home Control 독립 패키지."""
from __future__ import annotations

from .adapters import MockSmartHomeApiClient
from .controller import SmartHomeController, create_default_controller
from .devices import GasValve
from .exceptions import (
    ApiConnectionError,
    CommandExecutionError,
    DeviceNotFoundError,
    SmartHomeError,
)
from .interfaces import SmartDevice, SmartHomeApiClient
from .models import ApiResponse, CommandResult, DeviceStatus, ValveState
from .ui import build_smart_home_tab

__all__ = [
    "ApiConnectionError",
    "ApiResponse",
    "CommandExecutionError",
    "CommandResult",
    "DeviceNotFoundError",
    "DeviceStatus",
    "GasValve",
    "MockSmartHomeApiClient",
    "SmartDevice",
    "SmartHomeApiClient",
    "SmartHomeController",
    "SmartHomeError",
    "ValveState",
    "build_smart_home_tab",
    "create_default_controller",
]
