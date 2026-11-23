import tkinter as tk
from tkinter import ttk

from .adapters import MockWearable

try:
    from time_utils import format_local_time
except ImportError:
    def format_local_time(iso_str: str) -> str:  # type: ignore[misc]
        return iso_str


def _format_status_kst(monitor) -> str:
    raw = monitor.status()
    if not monitor.history:
        return raw
    sample = monitor.history[-1]
    prefix, _, _ = raw.rpartition(" | ")
    return f"{prefix} | {format_local_time(sample.recorded_at)}" if prefix else raw


def build_health_monitor_tab(parent, robot, on_state_change):
    monitor = robot.health_monitor
    status = tk.StringVar(master=parent, value=_format_status_kst(monitor))
    ttk.Label(parent, text="건강 모니터링", style="Heading.TLabel").pack(anchor="w", padx=12, pady=8)
    ttk.Label(parent, text="시연용 · 의료 판단 불가 · 외부 알림 미발송 (내부 저장 UTC / 화면 표시 KST)").pack(
        anchor="w", padx=12
    )
    ttk.Label(parent, textvariable=status, wraplength=680).pack(anchor="w", padx=12, pady=8)

    if isinstance(monitor.source, MockWearable):
        sim_frame = ttk.Frame(parent, style="Panel.TFrame")
        sim_frame.pack(anchor="w", padx=12, pady=(0, 8))
        hr_var = tk.IntVar(master=parent, value=int(monitor.source.heart_rate))
        spo2_var = tk.IntVar(master=parent, value=int(monitor.source.spo2))
        ttk.Label(sim_frame, text="가상 심박수(bpm)").pack(side="left", padx=(0, 6))
        tk.Spinbox(sim_frame, from_=30, to=200, textvariable=hr_var, width=5, font=("맑은 고딕", 10)).pack(
            side="left", padx=(0, 12)
        )
        ttk.Label(sim_frame, text="가상 SpO₂(%)").pack(side="left", padx=(0, 6))
        tk.Spinbox(sim_frame, from_=70, to=100, textvariable=spo2_var, width=5, font=("맑은 고딕", 10)).pack(
            side="left", padx=(0, 12)
        )

        def set_preset(hr: int, spo2: int) -> None:
            hr_var.set(hr)
            spo2_var.set(spo2)

        ttk.Button(sim_frame, text="정상값 (75 / 98)", command=lambda: set_preset(75, 98)).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(sim_frame, text="이상값 시연 (125 / 89)", command=lambda: set_preset(125, 89)).pack(side="left")
    else:
        hr_var = None
        spo2_var = None
        ttk.Label(parent, text="로컬 웨어러블 JSON 브리지 모드(HEALTH_WEARABLE_JSON) 활성 중").pack(
            anchor="w", padx=12, pady=(0, 8)
        )

    history = tk.Listbox(
        parent,
        height=8,
        bg="#EAF4FB",
        fg="#15283C",
        font=("맑은 고딕", 10),
        relief="flat",
    )
    history.pack(fill="both", expand=True, padx=12, pady=8)

    def refresh():
        status.set(_format_status_kst(monitor))
        history.delete(0, tk.END)
        for sample in reversed(monitor.history):
            history.insert(
                tk.END,
                f"{format_local_time(sample.recorded_at)} | {sample.heart_rate} bpm | {sample.spo2}%",
            )

    def collect():
        try:
            if isinstance(monitor.source, MockWearable) and hr_var is not None and spo2_var is not None:
                monitor.source.heart_rate = int(hr_var.get())
                monitor.source.spo2 = int(spo2_var.get())
            monitor.collect()
            on_state_change()
            status.set(_format_status_kst(monitor))
        except (OSError, ValueError, TypeError, RuntimeError):
            status.set("수집 또는 저장 실패: 입력·측정 시각·저장 상태를 확인하세요.")
        refresh()

    ttk.Button(parent, text="측정값 수집", command=collect).pack(anchor="w", padx=12, pady=(0, 8))
    refresh()
    return refresh
