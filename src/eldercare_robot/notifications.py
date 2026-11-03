"""Safe local notification sink; no emergency-service dispatch."""
from dataclasses import dataclass, field

@dataclass
class GuardianNotifier:
    events: list[str] = field(default_factory=list)

    def notify(self, message: str) -> None:
        self.events.append(message)
