"""Smart Home Control 도메인 및 API 예외 계층."""
from __future__ import annotations


class SmartHomeError(Exception):
    """스마트홈 모듈 최상위 예외."""


class DeviceNotFoundError(SmartHomeError):
    """등록되지 않은 기기를 조회하거나 제어하려 할 때 발생."""


class ApiConnectionError(SmartHomeError):
    """스마트홈 차단기 API 연결 실패 또는 타임아웃 시 발생."""


class CommandExecutionError(SmartHomeError):
    """지원하지 않는 명령이거나 기기 제어 실행에 실패할 때 발생."""
