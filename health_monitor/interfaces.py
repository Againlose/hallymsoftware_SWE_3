from typing import Protocol
from .models import Reading

class WearableSource(Protocol):
    def read(self) -> Reading: ...

class AlertSink(Protocol):
    def create(self, category: str, message: str): ...

class DrugLookup(Protocol):
    def lookup(self, product: str) -> list[dict]: ...
