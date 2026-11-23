from .service import HealthMonitor
from .adapters import MockWearable, JsonWearable, DurLookup, MockDrugLookup


def create_default_monitor(alerts):
    """Use a local device bridge when explicitly configured; otherwise use Mock."""
    from os import getenv
    path = getenv('HEALTH_WEARABLE_JSON', '').strip()
    return HealthMonitor(JsonWearable(path) if path else MockWearable(), alerts)
