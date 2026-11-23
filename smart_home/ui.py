"""Tkinter GUI '5단계 · 스마트홈' 탭 빌더."""
from __future__ import annotations

from typing import Any, Callable


def build_smart_home_tab(
    parent: Any,
    robot: Any,
    on_state_change: Callable[[], None] | None = None,
) -> Callable[[], None]:
    """기존 Tkinter 테마와 호환되는 가스불 차단기 제어·시뮬레이션 탭을 구성한다."""
    import tkinter as tk
    from tkinter import scrolledtext, ttk

    from .exceptions import SmartHomeError
    from .models import ValveState

    try:
        from time_utils import format_local_time
    except ImportError:
        def format_local_time(iso_str: str) -> str:  # type: ignore[misc]
            return iso_str

    PANEL = "#11253B"
    NAVY = "#143B5D"
    WHITE = "#F4F8FD"
    FONT = "맑은 고딕"

    inner = ttk.Frame(parent, style="Panel.TFrame")
    inner.pack(fill="both", expand=True, padx=27, pady=24)

    ttk.Label(
        inner,
        text="스마트홈 가스불 차단기 · IoT 상태 조회 및 차단 시뮬레이션",
        style="Heading.TLabel",
    ).pack(anchor="w", pady=(0, 10))
    ttk.Label(
        inner,
        text="가스밸브 상태 확인, 원격 차단 요청, 장시간 개방 및 통신 장애(Fail-Safe)를 시뮬레이션합니다.",
        style="TLabel",
    ).pack(anchor="w", pady=(0, 14))

    status_var = tk.StringVar(value="")
    ttk.Label(inner, textvariable=status_var, style="Heading.TLabel").pack(anchor="w", pady=(0, 12))

    ctrl_row = ttk.Frame(inner, style="Panel.TFrame")
    ctrl_row.pack(anchor="w", pady=(0, 14))

    output_box = scrolledtext.ScrolledText(
        inner,
        height=9,
        wrap="word",
        font=(FONT, 11),
        bg="#EAF4FB",
        fg="#15283C",
        padx=14,
        pady=12,
        relief="flat",
    )

    def append_log(message: str) -> None:
        output_box.configure(state="normal")
        output_box.insert("end", message + "\n")
        output_box.see("end")
        output_box.configure(state="disabled")

    def refresh_status_label() -> None:
        try:
            st = robot.smart_home.get_device_status()
            state_txt = "잠김(차단됨)" if st.is_shut_off else f"{st.state.value} (경과 {st.opened_minutes}분)"
            status_var.set(f"주방 가스밸브 상태: {state_txt} · 최근 갱신 {format_local_time(st.updated_at)}")
        except SmartHomeError as exc:
            status_var.set(f"주방 가스밸브 상태: 통신 오류 ({exc})")

    def notify_parent() -> None:
        refresh_status_label()
        if on_state_change is not None:
            on_state_change()

    def handle_check_status() -> None:
        append_log(robot.get_gas_status_summary())
        notify_parent()

    def handle_shutoff() -> None:
        result = robot.shut_off_gas()
        append_log(result.message)
        notify_parent()

    def handle_safety_check() -> None:
        _, msg = robot.check_gas_safety()
        append_log(msg)
        notify_parent()

    ttk.Button(ctrl_row, text="가스 상태 조회", command=handle_check_status).pack(side="left", padx=(0, 10))
    ttk.Button(ctrl_row, text="가스 차단 실행", command=handle_shutoff).pack(side="left", padx=(0, 10))
    ttk.Button(ctrl_row, text="장시간 개방 안전 점검", command=handle_safety_check).pack(side="left")

    ttk.Label(inner, text="시뮬레이션 입력 (가상 열림 시간 & 장애 주입)", style="Heading.TLabel").pack(
        anchor="w", pady=(8, 8)
    )
    sim_row = ttk.Frame(inner, style="Panel.TFrame")
    sim_row.pack(anchor="w", pady=(0, 10))

    open_minutes_var = tk.IntVar(value=35)
    ttk.Label(sim_row, text="열림 경과 시간(분)", style="TLabel").pack(side="left", padx=(0, 10))
    tk.Scale(
        sim_row,
        from_=0,
        to=120,
        orient="horizontal",
        variable=open_minutes_var,
        length=280,
        bg=PANEL,
        fg=WHITE,
        troughcolor=NAVY,
        highlightthickness=0,
        font=(FONT, 10),
    ).pack(side="left", padx=(0, 14))

    def handle_simulate_open() -> None:
        res = robot.smart_home.simulate_gas_open(opened_minutes=open_minutes_var.get())
        robot.save()
        append_log(res.message)
        notify_parent()

    ttk.Button(sim_row, text="가스 열림 시뮬레이션", command=handle_simulate_open).pack(side="left")

    fault_row = ttk.Frame(inner, style="Panel.TFrame")
    fault_row.pack(anchor="w", pady=(0, 12))
    offline_var = tk.BooleanVar(value=bool(getattr(robot.smart_home.api_client, "offline", False)))
    fail_cmd_var = tk.BooleanVar(value=bool(getattr(robot.smart_home.api_client, "fail_commands", False)))

    def apply_faults() -> None:
        robot.smart_home.set_fault_mode(offline=offline_var.get(), fail_commands=fail_cmd_var.get())
        robot.save()
        append_log(
            f"[장애 시뮬레이션 설정] 오프라인={offline_var.get()}, 명령실패={fail_cmd_var.get()}"
        )
        notify_parent()

    tk.Checkbutton(
        fault_row,
        text="API 오프라인 장애 시뮬레이션",
        variable=offline_var,
        command=apply_faults,
        bg=PANEL,
        fg=WHITE,
        selectcolor=NAVY,
        activebackground=PANEL,
        activeforeground=WHITE,
        font=(FONT, 10),
    ).pack(side="left", padx=(0, 18))
    tk.Checkbutton(
        fault_row,
        text="차단기 구동 실패 시뮬레이션",
        variable=fail_cmd_var,
        command=apply_faults,
        bg=PANEL,
        fg=WHITE,
        selectcolor=NAVY,
        activebackground=PANEL,
        activeforeground=WHITE,
        font=(FONT, 10),
    ).pack(side="left")

    output_box.pack(fill="both", expand=True, pady=(4, 10))
    append_log("안내: 가스불 차단기 제어 기능은 로컬 시뮬레이션으로 동작합니다.")
    output_box.configure(state="disabled")

    ttk.Label(
        inner,
        text="※ 실제 아파트 홈넷/가스밸브 하드웨어와 연결되지 않은 소프트웨어 시뮬레이션입니다.",
        style="TLabel",
    ).pack(anchor="w")

    refresh_status_label()
    return refresh_status_label
