"""Smart Home Control 추상 인터페이스 (Port 정의)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ApiResponse, CommandResult, DeviceStatus


class SmartDevice(ABC):
    """UML <<interface>> 스마트기기 대응 추상 인터페이스."""

    @property
    @abstractmethod
    def device_id(self) -> str:
        """기기 고유 식별자."""

    @property
    @abstractmethod
    def name(self) -> str:
        """사용자 표시용 기기 이름."""

    @abstractmethod
    def get_status(self) -> DeviceStatus:
        """현재 기기 상태를 반환한다 (UML: 상태조회)."""

    @abstractmethod
    def handle_command(self, command: str, params: dict[str, Any] | None = None) -> CommandResult:
        """표준 제어 명령을 처리한다 (UML: 명령처리)."""


class SmartHomeApiClient(ABC):
    """가스불 차단기 제어 어댑터 추상 포트."""

    @abstractmethod
    def fetch_device_status(self, device_id: str) -> ApiResponse:
        """제어 어댑터로부터 기기 상태를 조회한다."""

    @abstractmethod
    def send_device_command(
        self, device_id: str, command: str, params: dict[str, Any] | None = None
    ) -> ApiResponse:
        """제어 어댑터로 기기 제어 명령을 전송한다."""

    @abstractmethod
    def health_check(self) -> bool:
        """제어 어댑터/게이트웨이 연결 상태를 점검한다."""
