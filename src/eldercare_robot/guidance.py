"""Scripted indoor facility and kiosk guidance; no autonomous UI clicking."""
FACILITY_STEPS = {
    "elevator": ["승강기 호출 버튼을 누르세요.", "도착하면 문이 열린 것을 확인하세요.", "목적 층을 누르세요."],
    "intercom": ["인터폰 화면을 확인하세요.", "통화 버튼을 눌러 상대방을 확인하세요."],
}
KIOSK_STEPS = ["화면에서 언어를 선택하세요.", "원하는 메뉴를 선택하세요.", "주문 내용을 확인하세요.", "결제 전 금액을 확인하세요."]

def facility_guide(device: str) -> list[str]:
    if device not in FACILITY_STEPS:
        raise ValueError(f"unsupported facility: {device}")
    return FACILITY_STEPS[device].copy()

def kiosk_guide() -> list[str]:
    return KIOSK_STEPS.copy()
