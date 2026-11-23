import tkinter as tk
from tkinter import ttk


def build_health_monitor_tab(parent, robot, on_state_change):
    monitor = robot.health_monitor
    status = tk.StringVar(master=parent, value=monitor.status())
    ttk.Label(parent, text='건강 모니터링', style='Heading.TLabel').pack(anchor='w', padx=12, pady=8)
    ttk.Label(parent, text='시연용 · 의료 판단 불가 · 외부 알림 미발송').pack(anchor='w', padx=12)
    ttk.Label(parent, textvariable=status, wraplength=520).pack(anchor='w', padx=12, pady=8)
    history = tk.Listbox(parent, height=8)
    history.pack(fill='both', expand=True, padx=12, pady=8)

    def refresh():
        history.delete(0, tk.END)
        for sample in reversed(monitor.history):
            history.insert(tk.END, f'{sample.recorded_at} | {sample.heart_rate} bpm | {sample.spo2}%')

    def collect():
        try:
            monitor.collect()
            on_state_change()
            status.set(monitor.status())
        except (OSError, ValueError, TypeError, RuntimeError):
            status.set('수집 또는 저장 실패: 입력·측정 시각·저장 상태를 확인하세요.')
        refresh()

    ttk.Button(parent, text='측정값 수집', command=collect).pack(anchor='w', padx=12)
    refresh()
