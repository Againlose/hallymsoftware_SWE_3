"""In-memory medication schedule; no medical dosing recommendations."""
from dataclasses import dataclass
from datetime import datetime, time

@dataclass(frozen=True)
class Reminder:
    name: str
    at: time

class MedicationManager:
    def __init__(self, reminders: list[Reminder]):
        self.reminders = reminders
        self._sent: set[tuple[str, str]] = set()

    def due(self, now: datetime) -> list[str]:
        today = now.date().isoformat()
        due_names = []
        for reminder in self.reminders:
            key = (today, reminder.name)
            if now.time().replace(second=0, microsecond=0) == reminder.at and key not in self._sent:
                due_names.append(reminder.name)
                self._sent.add(key)
        return due_names
