"""공통 시간 유틸리티: 내부 저장용 UTC ISO 8601 및 표시 계층용 로컬(KST) 변환."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9), name="KST")


def utc_now_iso() -> str:
    """현재 UTC 시각을 RFC 3339 / ISO 8601(초 단위, +00:00) 문자열로 반환한다."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_utc_iso(when: datetime | None = None) -> str:
    """datetime 객체를 UTC ISO 8601 문자열로 정규화한다.

    naive datetime은 로컬 시스템 시간대로 해석해 UTC로 변환한다.
    """
    if when is None:
        return utc_now_iso()
    if when.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo or timezone.utc
        when = when.replace(tzinfo=local_tz)
    return when.astimezone(timezone.utc).isoformat(timespec="seconds")


def format_local_time(iso_str: str, tz: timezone = KST) -> str:
    """ISO 8601 문자열을 표시용 로컬(기본 KST) 문자열로 변환한다.

    타임존 정보가 없는 구버전 naive 문자열도 예외 없이 로컬 시각 형식으로 표시한다.
    """
    if not isinstance(iso_str, str) or not iso_str.strip():
        return str(iso_str)
    normalized = iso_str.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return iso_str
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz)
    label = tz.tzname(dt) or "KST"
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} {label}"
