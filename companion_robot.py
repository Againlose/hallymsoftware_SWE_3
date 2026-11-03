"""단계별 AI 컴패니언 로봇: 외부 API 없이 실행 가능한 교육용 데모.

1단계: 의도 분류·텍스트 대화·기록·프로필
2단계: 약 복용 일정 및 키오스크 안내
3단계: 실내 경로 탐색·가상 거리/터치 센서
4단계: 가상 넘어짐 감지·위험 알림 및 통합

중요: 센서 값과 응급 알림은 시뮬레이션입니다. 실제 기관 연락이 발생하지 않습니다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import re
import threading
from typing import Any


@dataclass
class UserProfile:
    user_id: str = "U001"
    name: str = "사용자"
    preferences: str = "천천히 설명"


@dataclass
class ConversationEntry:
    time: str
    user_message: str
    robot_response: str
    intent: str
    confidence: float


class JsonStore:
    """로컬 JSON에만 저장하며 네트워크로 전송하지 않습니다."""

    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "companion_state.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)


class VoiceProcessor:
    """현재는 텍스트를 음성 인식 결과로 사용합니다. 음성 출력은 선택 기능입니다."""

    def recognize(self, simulated_transcript: str) -> str:
        return " ".join(simulated_transcript.split())

    def speak_async(self, text: str) -> bool:
        try:
            import pyttsx3  # type: ignore[import-not-found]
        except ImportError:
            return False

        def _speak() -> None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 155)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception:
                pass  # 시스템 TTS 엔진 또는 한국어 음성이 없을 수 있습니다.

        threading.Thread(target=_speak, daemon=True).start()
        return True


class Sensor(ABC):
    @abstractmethod
    def measure(self) -> Any:
        raise NotImplementedError


class TouchSensor(Sensor):
    def __init__(self):
        self.pressed = False

    def measure(self) -> bool:
        return self.pressed


class DistanceSensor(Sensor):
    def __init__(self, distance_cm: int = 120):
        self.distance_cm = distance_cm

    def measure(self) -> int:
        return self.distance_cm

    def is_obstacle(self, threshold_cm: int = 50) -> bool:
        return self.measure() < threshold_cm


class FallSensor(Sensor):
    """실물 센서가 아니라 UI 버튼으로 상태를 주입하는 가상 센서."""

    def __init__(self):
        self.fallen = False

    def measure(self) -> bool:
        return self.fallen


class IntentClassifier:
    """한국어 문자 2~3그램 TF-IDF + 코사인 유사도 기반 간단한 의도 분류."""

    EXAMPLES: dict[str, list[str]] = {
        "greeting": ["안녕", "안녕하세요", "좋은 아침", "반가워", "오늘 기분 어때"],
        "medication": ["약 먹을 시간 알려줘", "복약 일정 확인", "약 복용 알려줘", "약 언제 먹지", "약 먹는 시간"],
        "navigation": ["화장실로 이동", "실내 이동 도와줘", "이동 경로 알려줘", "침실로 가고 싶어", "목적지 안내해줘"],
        "kiosk": ["키오스크 이용 방법", "무인 주문 방법", "키오스크 주문 도와줘", "기계로 결제하는 방법", "키오스크 사용법"],
        "status": ["로봇 상태 확인", "배터리 잔량 알려줘", "배터리 몇 퍼센트", "현재 상태 확인", "상태 어때"],
        "charge": ["충전해줘", "배터리 충전", "로봇 충전 시작", "충전이 필요해"],
        "emergency": ["넘어졌어 도와줘", "쓰러졌어", "위험한 상황이야", "긴급 도움 요청", "낙상 발생 도움"],
    }

    def __init__(self):
        self.samples: list[tuple[str, str]] = [
            (intent, sentence) for intent, sentences in self.EXAMPLES.items() for sentence in sentences
        ]
        docs = [self._grams(sentence) for _, sentence in self.samples]
        doc_freq: Counter[str] = Counter()
        for doc in docs:
            doc_freq.update(set(doc))
        n = len(docs)
        self.idf = {term: math.log((n + 1) / (freq + 1)) + 1 for term, freq in doc_freq.items()}
        self.vectors = [self._vector(doc) for doc in docs]

    @staticmethod
    def _grams(s: str) -> Counter[str]:
        s = re.sub(r"\s+", "", s.lower())
        return Counter(s[i:i + k] for k in (2, 3) for i in range(max(0, len(s) - k + 1)))

    def _vector(self, doc: Counter[str]) -> dict[str, float]:
        values = {k: v * self.idf.get(k, 1.0) for k, v in doc.items()}
        norm = math.sqrt(sum(x * x for x in values.values())) or 1.0
        return {k: v / norm for k, v in values.items()}

    def classify(self, text: str) -> tuple[str, float]:
        query = self._vector(self._grams(text))
        if not query:
            return "unknown", 0.0
        scores: dict[str, float] = {}
        for (intent, _), vec in zip(self.samples, self.vectors):
            score = sum(w * vec.get(term, 0.0) for term, w in query.items())
            scores[intent] = max(score, scores.get(intent, 0.0))
        best = max(scores, key=scores.get)
        confidence = scores[best]
        if confidence < 0.20:
            return "unknown", round(confidence, 3)
        return best, round(confidence, 3)


class Navigator:
    """미리 지정한 실내 평면도 그래프에서 BFS 최단 경로(간선 수)를 탐색."""

    GRAPH: dict[str, tuple[str, ...]] = {
        "거실": ("복도", "주방"),
        "복도": ("거실", "침실", "화장실", "현관"),
        "주방": ("거실",),
        "침실": ("복도",),
        "화장실": ("복도",),
        "현관": ("복도",),
    }

    def route(self, start: str, goal: str) -> list[str]:
        if start not in self.GRAPH or goal not in self.GRAPH:
            raise ValueError("등록되지 않은 위치입니다.")
        q = deque([[start]])
        visited = {start}
        while q:
            path = q.popleft()
            here = path[-1]
            if here == goal:
                return path
            for nxt in self.GRAPH[here]:
                if nxt not in visited:
                    visited.add(nxt)
                    q.append(path + [nxt])
        raise ValueError("목적지까지 연결된 경로가 없습니다.")

    def explain(self, start: str, goal: str) -> str:
        path = self.route(start, goal)
        if len(path) == 1:
            return f"이미 {goal}에 있습니다."
        return " → ".join(path) + f"\n총 {len(path) - 1}구간입니다. 실제 자율주행은 지원하지 않습니다."


class AlertService:
    """알림은 프로그램 내 로그로만 생성. 실제 119·보호자에게 전송하지 않음."""

    def __init__(self, records: list[dict[str, str]] | None = None):
        self.records = records if records is not None else []

    def create(self, category: str, message: str, when: datetime | None = None) -> dict[str, str]:
        rec = {"time": (when or datetime.now()).isoformat(timespec="seconds"),
               "category": category, "message": message, "delivery": "LOCAL_SIMULATION_ONLY"}
        self.records.append(rec)
        return rec


class MedicationManager:
    def __init__(self, entries: list[dict[str, str]] | None = None):
        self.entries = entries if entries is not None else []

    def add(self, name: str, hhmm: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("약 이름을 입력하세요.")
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hhmm):
            raise ValueError("시간은 24시간제 HH:MM 형식으로 입력하세요. 예: 09:00")
        self.entries.append({"name": name, "time": hhmm, "last_alert": ""})

    def check_due(self, now: datetime) -> list[str]:
        due: list[str] = []
        for entry in self.entries:
            hour, minute = map(int, entry["time"].split(":"))
            scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # 예약 시각부터 15분 이내에 실행했을 때만 알림
            if scheduled <= now < scheduled + timedelta(minutes=15) and entry.get("last_alert") != now.date().isoformat():
                due.append(f"{entry['name']} 복용 예정 시각 {entry['time']}입니다. 처방을 확인해 주세요.")
                entry["last_alert"] = now.date().isoformat()
        return due


class Robot:
    def __init__(self, store: JsonStore):
        self.store = store
        saved = store.load()
        profile_saved = saved.get("profile", {})
        self.profile = UserProfile(**{k: profile_saved.get(k, getattr(UserProfile(), k))
                                      for k in UserProfile.__dataclass_fields__})
        self.robot_id = "R001"
        self.battery = max(0, min(100, int(saved.get("battery", 85))))
        self.status = saved.get("status", "정상")
        self.history = [ConversationEntry(**item) for item in saved.get("history", [])
                        if isinstance(item, dict) and set(ConversationEntry.__dataclass_fields__).issubset(item)]
        self.medications = MedicationManager(saved.get("medications", []))
        self.alerts = AlertService(saved.get("alerts", []))
        self.touch = TouchSensor()
        self.distance = DistanceSensor()
        self.fall = FallSensor()
        self.navigator = Navigator()
        self.ai_model = IntentClassifier()
        self.voice_processor = VoiceProcessor()
        self.last_reply = ""

    def save(self) -> None:
        self.store.save({"profile": asdict(self.profile), "battery": self.battery,
                         "status": self.status, "history": [asdict(x) for x in self.history[-200:]],
                         "medications": self.medications.entries,
                         "alerts": self.alerts.records[-100:]})

    def start_conversation(self, utterance: str) -> tuple[str, str, float]:
        text = self.voice_processor.recognize(utterance)
        if not text:
            return "입력된 문장이 없습니다.", "unknown", 0.0
        intent, confidence = self.ai_model.classify(text)
        if intent != "charge":
            self.battery = max(0, self.battery - 1)
        reply = self.generate_reply(intent, text)
        self.last_reply = reply
        self.history.append(ConversationEntry(datetime.now().isoformat(timespec="seconds"),
                                              text, reply, intent, confidence))
        self.save()
        return reply, intent, confidence

    def generate_reply(self, intent: str, text: str) -> str:
        if intent == "greeting":
            return f"안녕하세요, {self.profile.name}님. 오늘도 필요한 일을 도와드릴게요."
        if intent == "medication":
            if not self.medications.entries:
                return "아직 등록된 복약 일정이 없습니다. '2단계 · 복약' 탭에서 등록해 주세요."
            return "등록된 복약 일정: " + ", ".join(f"{e['name']} {e['time']}" for e in self.medications.entries)
        if intent == "navigation":
            goal = next((room for room in ("화장실", "침실", "주방", "현관", "복도", "거실") if room in text), "화장실")
            return "실내 지도 예시 경로: " + self.navigator.explain("거실", goal)
        if intent == "kiosk":
            return "키오스크 이용 순서: ① 화면 터치 → ② 메뉴 선택 → ③ 수량 확인 → ④ 결제 방법 선택 → ⑤ 영수증 확인. 실제 기기 조작은 하지 않습니다."
        if intent == "status":
            return f"로봇 {self.robot_id}: {self.status}, 배터리 {self.battery}%."
        if intent == "charge":
            self.battery = 100
            return "충전 시뮬레이션을 마쳤습니다. 배터리가 100%입니다."
        if intent == "emergency":
            self.trigger_fall()
            return "위험 상황을 감지한 것으로 시뮬레이션했습니다. 화면에 긴급 알림 기록을 남겼습니다. 실제 구조 요청은 전송되지 않았습니다."
        return "요청을 정확히 분류하지 못했습니다. '약 복용', '화장실 이동', '키오스크', '상태 확인'처럼 말씀해 주세요."

    def trigger_fall(self) -> None:
        self.fall.fallen = True
        self.status = "위험 감지(시뮬레이션)"
        self.alerts.create("낙상/위험", "넘어짐 감지 → 보호자/응급 지원 기관 알림을 가정해 로컬 로그 작성")
        self.save()

    def reset_emergency(self) -> None:
        self.fall.fallen = False
        self.status = "정상"
        self.save()

    def check_distance(self, distance_cm: int) -> str:
        self.distance.distance_cm = distance_cm
        if self.distance.is_obstacle():
            self.alerts.create("이동 장애물", f"가상 거리 {distance_cm}cm: 전방 장애물 경고")
            self.save()
            return f"주의: {distance_cm}cm 앞에 장애물이 있습니다. 이동을 중지하세요(시뮬레이션)."
        return f"가상 센서 {distance_cm}cm: 현재 임계값(50cm)보다 멉니다."

    def check_medication(self, now: datetime | None = None) -> list[str]:
        due = self.medications.check_due(now or datetime.now())
        for msg in due:
            self.alerts.create("복약", msg, when=now)
        if due:
            self.save()
        return due


def run_gui() -> None:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    BASE = "#0B1524"
    PANEL = "#11253B"
    NAVY = "#143B5D"
    BLUE = "#9DD6FF"
    WHITE = "#F4F8FD"
    MUTED = "#A9BED1"
    FONT = "맑은 고딕"

    robot = Robot(JsonStore(Path(__file__).resolve().parent / "demo_data"))
    root = tk.Tk()
    root.title("AI 컴패니언 로봇 | 4단계 구현 프로토타입")
    root.geometry("1120x740")
    root.minsize(1000, 640)
    root.configure(bg=BASE)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TNotebook", background=BASE, borderwidth=0)
    style.configure("TNotebook.Tab", background=NAVY, foreground=WHITE, font=(FONT, 11, "bold"), padding=(24, 12))
    style.map("TNotebook.Tab", background=[("selected", "#226390")], foreground=[("selected", WHITE)])
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=PANEL, foreground=WHITE, font=(FONT, 11))
    style.configure("Heading.TLabel", background=PANEL, foreground=BLUE, font=(FONT, 15, "bold"))
    style.configure("TButton", font=(FONT, 10, "bold"), padding=(10, 8))
    style.configure("TEntry", padding=7)
    style.configure("TCombobox", padding=6)
    style.configure("Treeview", rowheight=30, font=(FONT, 10), background="#E6F1F9", foreground="#172C3F")
    style.configure("Treeview.Heading", font=(FONT, 10, "bold"))

    tk.Label(root, text="AI COMPANION ROBOT", font=(FONT, 22, "bold"), fg=WHITE, bg=BASE).pack(anchor="w", padx=26, pady=(20, 3))
    subtitle = tk.Label(root, text="실내 생활보조 AI 로봇 · UML 기반 교육용 소프트웨어 시뮬레이션", fg=MUTED, bg=BASE, font=(FONT, 11))
    subtitle.pack(anchor="w", padx=27, pady=(0, 16))
    status_label = tk.Label(root, text="", fg=BLUE, bg=BASE, font=(FONT, 10, "bold"))
    status_label.place(relx=0.99, y=42, anchor="e")

    tabs = ttk.Notebook(root)
    tabs.pack(fill="both", expand=True, padx=26, pady=(0, 20))
    tab1, tab2, tab3, tab4 = (ttk.Frame(tabs, style="Panel.TFrame") for _ in range(4))
    tabs.add(tab1, text="1단계 · 대화/프로필")
    tabs.add(tab2, text="2단계 · 복약/키오스크")
    tabs.add(tab3, text="3단계 · 실내 이동")
    tabs.add(tab4, text="4단계 · 안전/통합")

    def label(parent, text, heading=False):
        return ttk.Label(parent, text=text, style="Heading.TLabel" if heading else "TLabel")

    def update_status():
        status_label.configure(text=f"로봇 상태: {robot.status}     배터리: {robot.battery}%")

    def text_area(parent, height=12):
        w = scrolledtext.ScrolledText(parent, height=height, wrap="word", font=(FONT, 11),
                                      bg="#EAF4FB", fg="#15283C", padx=14, pady=12, relief="flat")
        return w

    # -------- 1단계 --------
    left1 = ttk.Frame(tab1, style="Panel.TFrame")
    left1.pack(side="left", fill="both", expand=True, padx=20, pady=18)
    label(left1, "대화 기능 · 문자 2~3그램 TF-IDF 의도 분류", True).pack(anchor="w", pady=(0, 9))
    conversation_view = text_area(left1, height=17)
    conversation_view.pack(fill="both", expand=True)
    for item in robot.history[-12:]:
        conversation_view.insert("end", f"나: {item.user_message}\n로봇: {item.robot_response}\n\n")
    if not robot.history:
        conversation_view.insert("end", "로봇: 안녕하세요! 약 복용, 실내 이동, 키오스크 이용, 상태 확인을 도와드릴 수 있어요.\n\n")
    conversation_view.configure(state="disabled")
    chat_row = ttk.Frame(left1, style="Panel.TFrame")
    chat_row.pack(fill="x", pady=(12, 0))
    chat_input = ttk.Entry(chat_row, font=(FONT, 11))
    chat_input.pack(side="left", fill="x", expand=True, padx=(0, 9))

    def send_chat(event=None):
        msg = chat_input.get().strip()
        if not msg:
            return
        reply, intent, conf = robot.start_conversation(msg)
        conversation_view.configure(state="normal")
        conversation_view.insert("end", f"나: {msg}\n로봇: {reply}\n[의도: {intent} · 유사도 {conf:.2f}]\n\n")
        conversation_view.see("end")
        conversation_view.configure(state="disabled")
        chat_input.delete(0, "end")
        update_status()
        refresh_alerts()

    ttk.Button(chat_row, text="전송", command=send_chat).pack(side="left")
    ttk.Button(chat_row, text="음성 읽기",
               command=lambda: messagebox.showinfo("음성 출력", "음성 엔진이 없거나 한국어 음성이 설정되지 않았을 수 있습니다.")
               if not robot.voice_processor.speak_async(robot.last_reply or "안녕하세요") else None).pack(side="left", padx=(8, 0))
    chat_input.bind("<Return>", send_chat)
    right1 = ttk.Frame(tab1, style="Panel.TFrame", width=275)
    right1.pack(side="right", fill="y", padx=(0, 25), pady=18)
    label(right1, "사용자 프로필", True).pack(anchor="w", pady=(0, 10))
    label(right1, "이름").pack(anchor="w", pady=(7, 5))
    user_name = ttk.Entry(right1, width=22)
    user_name.insert(0, robot.profile.name)
    user_name.pack(anchor="w")
    label(right1, "사용자 선호사항").pack(anchor="w", pady=(14, 5))
    preference = ttk.Entry(right1, width=22)
    preference.insert(0, robot.profile.preferences)
    preference.pack(anchor="w")

    def save_profile():
        robot.profile.name = user_name.get().strip() or "사용자"
        robot.profile.preferences = preference.get().strip()
        robot.save()
        messagebox.showinfo("완료", "사용자 프로필을 로컬에 저장했습니다.")

    ttk.Button(right1, text="프로필 저장", command=save_profile).pack(anchor="w", pady=(14, 22))
    label(right1, "사용 예시", True).pack(anchor="w", pady=(0, 9))
    label(right1, "• 안녕\n• 약 복용 알려줘\n• 화장실로 이동\n• 키오스크 사용법\n• 배터리 상태 확인\n• 넘어졌어 도와줘").pack(anchor="w")

    # -------- 2단계 --------
    inner2 = ttk.Frame(tab2, style="Panel.TFrame")
    inner2.pack(fill="both", expand=True, padx=25, pady=22)
    label(inner2, "복약 일정 관리 · 시각 일치 시 앱 내부 알림", True).pack(anchor="w", pady=(0, 12))
    input2 = ttk.Frame(inner2, style="Panel.TFrame")
    input2.pack(fill="x")
    label(input2, "약 이름").pack(side="left", padx=(0, 8))
    med_name = ttk.Entry(input2, width=25)
    med_name.pack(side="left", padx=(0, 14))
    label(input2, "시간 (HH:MM)").pack(side="left", padx=(0, 8))
    med_time = ttk.Entry(input2, width=12)
    med_time.insert(0, "09:00")
    med_time.pack(side="left", padx=(0, 12))
    meds_tree = ttk.Treeview(inner2, columns=("name", "time"), show="headings", height=3)
    meds_tree.heading("name", text="등록된 약 이름")
    meds_tree.heading("time", text="복약 시각")
    meds_tree.column("name", width=300)
    meds_tree.column("time", width=160)
    meds_tree.pack(fill="x", pady=(15, 10))
    med_result = label(inner2, "예약 시간부터 15분 이내에 확인한 경우, 하루 한 번만 알림을 기록합니다.")
    med_result.pack(anchor="w", pady=(0, 12))

    def refresh_meds():
        for item in meds_tree.get_children():
            meds_tree.delete(item)
        for i, entry in enumerate(robot.medications.entries):
            meds_tree.insert("", "end", iid=str(i), values=(entry["name"], entry["time"]))

    def add_med():
        try:
            robot.medications.add(med_name.get(), med_time.get())
        except ValueError as exc:
            messagebox.showerror("입력 오류", str(exc))
            return
        robot.save()
        refresh_meds()
        med_name.delete(0, "end")
        med_result.configure(text="복약 일정을 저장했습니다. 실제 알림은 앱 실행 중일 때만 확인합니다.")

    def simulate_med():
        name = robot.medications.entries[0]["name"] if robot.medications.entries else "예시 복약"
        msg = f"[시뮬레이션] {name}: 복용 시각 안내를 앱 내부 알림에 기록했습니다."
        robot.alerts.create("복약 데모", msg)
        robot.save()
        med_result.configure(text=msg)
        refresh_alerts()

    ttk.Button(input2, text="일정 추가", command=add_med).pack(side="left")
    refresh_meds()
    actions2 = ttk.Frame(inner2, style="Panel.TFrame")
    actions2.pack(anchor="w", pady=(2, 10))
    ttk.Button(actions2, text="현재 시간 복약 확인", command=lambda: handle_med_due()).pack(side="left", padx=(0, 10))
    ttk.Button(actions2, text="복약 알림 시연", command=simulate_med).pack(side="left")
    label(inner2, "키오스크 이용 가이드", True).pack(anchor="w", pady=(14, 8))
    kiosk_view = text_area(inner2, height=5)
    kiosk_view.pack(fill="both", expand=True)
    kiosk_view.insert("end", "① 화면 터치\n② 메뉴 및 수량 선택\n③ 주문 내역 확인\n④ 결제 수단 선택\n⑤ 결제 완료 및 영수증 확인\n\n※ 실제 기기 동작이 아닌 단계별 안내입니다.")
    kiosk_view.configure(state="disabled")

    def handle_med_due():
        due = robot.check_medication()
        med_result.configure(text=" | ".join(due) if due else "현재 시각에 해당하는 새 복약 알림은 없습니다.")
        refresh_alerts()

    # -------- 3단계 --------
    inner3 = ttk.Frame(tab3, style="Panel.TFrame")
    inner3.pack(fill="both", expand=True, padx=27, pady=24)
    label(inner3, "실내 이동 보조 · 사전 등록 지도 기반 경로 탐색", True).pack(anchor="w", pady=(0, 15))
    room_row = ttk.Frame(inner3, style="Panel.TFrame")
    room_row.pack(anchor="w", pady=(0, 15))
    label(room_row, "출발").pack(side="left", padx=(0, 9))
    start_var = tk.StringVar(value="거실")
    ttk.Combobox(room_row, textvariable=start_var, state="readonly", values=list(Navigator.GRAPH), width=13).pack(side="left", padx=(0, 18))
    label(room_row, "도착").pack(side="left", padx=(0, 9))
    dest_var = tk.StringVar(value="화장실")
    ttk.Combobox(room_row, textvariable=dest_var, state="readonly", values=list(Navigator.GRAPH), width=13).pack(side="left", padx=(0, 18))
    route_view = text_area(inner3, height=7)
    route_view.pack(fill="x", pady=(0, 16))

    def show_route():
        try:
            txt = robot.navigator.explain(start_var.get(), dest_var.get())
        except ValueError as exc:
            txt = str(exc)
        route_view.configure(state="normal")
        route_view.delete("1.0", "end")
        route_view.insert("end", "추천 경로\n\n" + txt + "\n\n그래프 연결: 거실–복도–침실/화장실/현관, 거실–주방")
        route_view.configure(state="disabled")

    ttk.Button(room_row, text="경로 계산", command=show_route).pack(side="left")
    label(inner3, "거리센서 시뮬레이터 · 50cm 미만일 때 장애물 경고", True).pack(anchor="w", pady=(11, 12))
    distance_value = tk.IntVar(value=120)
    tk.Scale(inner3, from_=10, to=200, orient="horizontal", variable=distance_value, length=540,
             bg=PANEL, fg=WHITE, troughcolor=NAVY, highlightthickness=0,
             font=(FONT, 10)).pack(anchor="w")
    obstacle_result = label(inner3, "가상 측정값을 움직인 뒤 확인하세요.")
    obstacle_result.pack(anchor="w", pady=(10, 13))

    def check_obstacle():
        obstacle_result.configure(text=robot.check_distance(distance_value.get()))
        refresh_alerts()

    ttk.Button(inner3, text="거리센서 확인", command=check_obstacle).pack(anchor="w")
    label(inner3, "※ 실제 공간 인식·구동·장애물 회피는 연결되지 않았습니다.").pack(anchor="w", pady=(16, 0))
    show_route()

    # -------- 4단계 --------
    inner4 = ttk.Frame(tab4, style="Panel.TFrame")
    inner4.pack(fill="both", expand=True, padx=27, pady=24)
    label(inner4, "위험 상황 감지 · 로컬 긴급 알림 시뮬레이션", True).pack(anchor="w", pady=(0, 12))
    label(inner4, "낙상 버튼 → FallSensor 측정 → 위험 상태 전환 → 로컬 이벤트 저장").pack(anchor="w", pady=(0, 15))
    safety_row = ttk.Frame(inner4, style="Panel.TFrame")
    safety_row.pack(anchor="w", pady=(0, 13))

    def fall_action():
        robot.trigger_fall()
        update_status()
        refresh_alerts()
        messagebox.showwarning("위험 상황 시뮬레이션", "위험 상황을 기록했습니다. 보호자 및 119에는 연락하지 않았습니다.")

    def reset_action():
        robot.reset_emergency()
        update_status()
        refresh_alerts()

    def touch_action():
        robot.touch.pressed = True
        robot.alerts.create("터치 입력", "가상 터치센서 버튼 입력 확인")
        robot.save()
        refresh_alerts()
        robot.touch.pressed = False

    ttk.Button(safety_row, text="넘어짐 감지 시연", command=fall_action).pack(side="left", padx=(0, 12))
    ttk.Button(safety_row, text="상태 정상화", command=reset_action).pack(side="left", padx=(0, 12))
    ttk.Button(safety_row, text="터치센서 시연", command=touch_action).pack(side="left")
    label(inner4, "로컬 알림 로그", True).pack(anchor="w", pady=(12, 10))
    alert_view = text_area(inner4, height=16)
    alert_view.pack(fill="both", expand=True)

    def refresh_alerts():
        alert_view.configure(state="normal")
        alert_view.delete("1.0", "end")
        for item in reversed(robot.alerts.records[-35:]):
            alert_view.insert("end", f"[{item['time']}] {item['category']}\n{item['message']}\n(전달 상태: 앱 내부 시뮬레이션)\n\n")
        if not robot.alerts.records:
            alert_view.insert("end", "아직 기록된 알림이 없습니다.")
        alert_view.configure(state="disabled")

    label(inner4, "주의: 실제 낙상 감지 장치, 위치 정보, 구조기관 전송, 응급 대응 기능이 아닙니다.").pack(anchor="w", pady=(12, 0))

    def scheduled_check():
        robot.check_medication()
        refresh_alerts()
        root.after(60_000, scheduled_check)

    refresh_alerts()
    update_status()
    root.after(60_000, scheduled_check)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
