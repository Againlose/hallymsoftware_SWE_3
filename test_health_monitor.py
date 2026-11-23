import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from health_monitor import HealthMonitor, DurLookup, JsonWearable
from health_monitor.models import Reading

class Source:
    def __init__(self, readings):
        self.readings = iter(readings)

    def read(self):
        return next(self.readings)

class Alerts:
    def __init__(self):
        self.messages = []

    def create(self, category, message):
        self.messages.append((category, message))

class HealthTests(unittest.TestCase):
    NOW = datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc)

    def monitor(self, pulses):
        return HealthMonitor(Source(Reading(f'2026-01-01T00:00:{i:02}+00:00', p, 98)
                                    for i, p in enumerate(pulses)), Alerts(), clock=lambda: self.NOW)

    def test_two_audiences_and_reset(self):
        monitor = self.monitor([120, 120, 120, 75, 120, 120])
        monitor.collect()
        self.assertEqual([], monitor.alerts.messages)
        for _ in range(5):
            monitor.collect()
        self.assertEqual(['건강/사용자', '건강/보호자'] * 2,
                         [kind for kind, _ in monitor.alerts.messages])

    def test_restore_and_dedup(self):
        monitor = self.monitor([120, 120, 120])
        monitor.collect()
        monitor.collect()
        state = json.loads(json.dumps(monitor.snapshot()))
        monitor.restore(None)
        self.assertEqual('측정 기록 없음', monitor.status())
        monitor.restore(state)
        monitor.collect()
        self.assertEqual(2, len(monitor.alerts.messages))

    def test_invalid_and_duplicate(self):
        with self.assertRaises(ValueError):
            Reading('2026-01-01T00:00:00+00:00', 75, float('nan'))
        sample = Reading('2026-01-01T00:00:00+00:00', 75, 98)
        monitor = HealthMonitor(Source([sample, sample]), Alerts(), clock=lambda: self.NOW)
        monitor.collect()
        with self.assertRaises(ValueError):
            monitor.collect()
        self.assertEqual(1, len(monitor.history))

    def test_threshold_boundaries(self):
        for pulse, spo2, expected in [(50, 92, False), (110, 92, False), (49, 98, True), (111, 98, True), (75, 91, True)]:
            self.assertEqual(expected, HealthMonitor.abnormal(Reading('2026-01-01T00:00:00+00:00', pulse, spo2)))

    def test_dur_offline_contract(self):
        def opener(url, timeout):
            self.assertIn('serviceKey=fake%2Bkey', url)
            self.assertIn('itemName=', url)
            self.assertEqual(5, timeout)
            return io.BytesIO(b'{"header":{"resultCode":"00"},"body":{"items":[{"ITEM_NAME":"demo"}]}}')
        with patch.dict(os.environ, {'DUR_SERVICE_KEY': 'fake+key'}):
            self.assertEqual([{'ITEM_NAME': 'demo'}], DurLookup(opener).lookup('데모'))

    def test_dur_failure_does_not_show_secret(self):
        def opener(url, timeout):
            raise OSError(url)
        with patch.dict(os.environ, {'DUR_SERVICE_KEY': 'fake-secret'}):
            with self.assertRaises(RuntimeError) as caught:
                DurLookup(opener).lookup('데모')
        self.assertNotIn('fake-secret', str(caught.exception))
        self.assertIsNone(caught.exception.__context__)

    def test_stale_and_future_rejected(self):
        for seconds in (-301, 11):
            reading = Reading((self.NOW + timedelta(seconds=seconds)).isoformat(), 120, 98)
            monitor = HealthMonitor(Source([reading]), Alerts(), clock=lambda: self.NOW)
            with self.assertRaises(ValueError):
                monitor.collect()
            self.assertFalse(monitor.history)

    def test_gap_breaks_episode(self):
        readings = [Reading((self.NOW + timedelta(seconds=s)).isoformat(), 120, 98)
                    for s in (-122, -1, 0)]
        monitor = HealthMonitor(Source(readings), Alerts(), clock=lambda: self.NOW)
        monitor.collect()
        monitor.collect()
        self.assertEqual([], monitor.alerts.messages)
        monitor.collect()
        self.assertEqual(2, len(monitor.alerts.messages))

    def test_json_bridge_and_size_limit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.json'
            path.write_text(json.dumps(dict(recorded_at=self.NOW.isoformat(), heart_rate=75, spo2=98)))
            self.assertEqual(75, JsonWearable(path).read().heart_rate)
            path.write_bytes(b' ' * 8193)
            with self.assertRaises(ValueError):
                JsonWearable(path).read()

    def test_live_requires_key_without_network(self):
        with patch.dict(os.environ, {'DUR_SERVICE_KEY': ''}):
            with self.assertRaisesRegex(RuntimeError, 'DUR_SERVICE_KEY'):
                DurLookup(lambda *_: self.fail('Unexpected HTTP call')).lookup('데모')
