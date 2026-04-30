from __future__ import annotations

from dataclasses import dataclass

from i2c_rasp.config import AlertThresholdsConfig
from i2c_rasp.snapshot import DeviceSnapshot


@dataclass(frozen=True)
class PageAlerts:
    summary: bool
    storage: bool


def evaluate_page_alerts(snapshot: DeviceSnapshot, thresholds: AlertThresholdsConfig) -> PageAlerts:
    return PageAlerts(
        summary=_summary_alert(snapshot, thresholds),
        storage=_storage_alert(snapshot, thresholds),
    )


def _summary_alert(snapshot: DeviceSnapshot, thresholds: AlertThresholdsConfig) -> bool:
    return _above(snapshot.cpu_percent, thresholds.cpu_percent) or _above(
        snapshot.memory_percent, thresholds.memory_percent
    )


def _storage_alert(snapshot: DeviceSnapshot, thresholds: AlertThresholdsConfig) -> bool:
    return _above(snapshot.temperature_celsius, thresholds.temperature_celsius) or _above(
        snapshot.root_disk_percent, thresholds.storage_percent
    )


def _above(value: float | None, threshold: float | None) -> bool:
    return threshold is not None and value is not None and value >= threshold
