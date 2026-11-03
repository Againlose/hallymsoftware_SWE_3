"""Simulated safety gate; NOT a physical robot motion controller."""
from dataclasses import dataclass

@dataclass
class MobilityAssistant:
    minimum_clearance_m: float = 0.6
    emergency_stopped: bool = False

    def can_move(self, obstacle_distance_m: float) -> bool:
        return (not self.emergency_stopped and
                obstacle_distance_m >= self.minimum_clearance_m)

    def stop(self) -> None:
        self.emergency_stopped = True

    def reset_after_manual_check(self) -> None:
        """In real hardware, reset must require an authorized physical safety check."""
        self.emergency_stopped = False
