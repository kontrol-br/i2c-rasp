from __future__ import annotations

from dataclasses import dataclass

from i2c_rasp.metrics import SampleSet
from i2c_rasp.scrape import ScrapeResult


@dataclass(frozen=True)
class InterfaceSnapshot:
    name: str
    device: str
    description: str
    up: bool | None
    rx_bps: float | None
    tx_bps: float | None


@dataclass(frozen=True)
class DeviceSnapshot:
    name: str
    hostname: str
    os_name: str
    cpu_percent: float | None
    load1: float | None
    memory_percent: float | None
    swap_percent: float | None
    temperature_celsius: float | None
    root_disk_percent: float | None
    interfaces: list[InterfaceSnapshot]


class SnapshotBuilder:
    def __init__(self, interface_names: list[str] | None = None) -> None:
        self.interface_names = interface_names or []
        self.previous: ScrapeResult | None = None

    def build(self, name: str, current: ScrapeResult) -> DeviceSnapshot:
        previous = self.previous
        snapshot = DeviceSnapshot(
            name=name,
            hostname=_hostname(current.samples) or name,
            os_name=_os_name(current.samples) or "unknown",
            cpu_percent=_cpu_percent(current, previous),
            load1=current.samples.first_value("node_load1"),
            memory_percent=_memory_percent(current.samples),
            swap_percent=_swap_percent(current.samples),
            temperature_celsius=_temperature_celsius(current.samples),
            root_disk_percent=_root_disk_percent(current.samples),
            interfaces=_interfaces(current, previous, self.interface_names),
        )
        self.previous = current
        return snapshot


def _hostname(samples: SampleSet) -> str | None:
    uname = samples.values("node_uname_info")
    if uname:
        return uname[0].labels.get("nodename")
    return None


def _os_name(samples: SampleSet) -> str | None:
    uname = samples.values("node_uname_info")
    if uname:
        return uname[0].labels.get("sysname")
    return None


def _cpu_percent(current: ScrapeResult, previous: ScrapeResult | None) -> float | None:
    if previous is None:
        return None

    current_by_key = {
        (sample.labels.get("cpu", ""), sample.labels.get("mode", "")): sample.value
        for sample in current.samples.values("node_cpu_seconds_total")
    }
    previous_by_key = {
        (sample.labels.get("cpu", ""), sample.labels.get("mode", "")): sample.value
        for sample in previous.samples.values("node_cpu_seconds_total")
    }

    total_delta = 0.0
    idle_delta = 0.0
    for key, current_value in current_by_key.items():
        previous_value = previous_by_key.get(key)
        if previous_value is None:
            continue
        delta = max(0.0, current_value - previous_value)
        total_delta += delta
        if key[1] == "idle":
            idle_delta += delta

    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))


def _memory_percent(samples: SampleSet) -> float | None:
    linux_total = samples.first_value("node_memory_MemTotal_bytes")
    linux_available = samples.first_value("node_memory_MemAvailable_bytes")
    if linux_total and linux_available is not None:
        return _percent(linux_total - linux_available, linux_total)

    total = samples.first_value("node_memory_size_bytes")
    if not total:
        return None

    available = sum(
        value or 0.0
        for value in (
            samples.first_value("node_memory_free_bytes"),
            samples.first_value("node_memory_inactive_bytes"),
            samples.first_value("node_memory_cache_bytes"),
            samples.first_value("node_memory_laundry_bytes"),
        )
    )
    return _percent(total - available, total)


def _swap_percent(samples: SampleSet) -> float | None:
    linux_total = samples.first_value("node_memory_SwapTotal_bytes")
    linux_free = samples.first_value("node_memory_SwapFree_bytes")
    if linux_total and linux_free is not None:
        return _percent(linux_total - linux_free, linux_total)

    total = samples.first_value("node_memory_swap_size_bytes")
    used = samples.first_value("node_memory_swap_used_bytes")
    if not total or used is None:
        return None
    return _percent(used, total)


def _temperature_celsius(samples: SampleSet) -> float | None:
    for metric_name in (
        "node_cpu_temperature_celsius",
        "node_hwmon_temp_celsius",
        "node_thermal_zone_temp",
    ):
        values = [sample.value for sample in samples.values(metric_name)]
        if values:
            return sum(values) / len(values)
    return None


def _root_disk_percent(samples: SampleSet) -> float | None:
    size = samples.first_value("node_filesystem_size_bytes", {"mountpoint": "/"})
    available = samples.first_value("node_filesystem_avail_bytes", {"mountpoint": "/"})
    if not size or available is None:
        return None
    return _percent(size - available, size)


def _interfaces(
    current: ScrapeResult,
    previous: ScrapeResult | None,
    interface_names: list[str],
) -> list[InterfaceSnapshot]:
    infos = current.samples.values("node_pfsense_interface_info")
    if interface_names:
        infos = [sample for sample in infos if sample.labels.get("name") in interface_names]

    previous_rx = previous.samples.by_label("node_network_receive_bytes_total", "device") if previous else {}
    previous_tx = previous.samples.by_label("node_network_transmit_bytes_total", "device") if previous else {}
    current_rx = current.samples.by_label("node_network_receive_bytes_total", "device")
    current_tx = current.samples.by_label("node_network_transmit_bytes_total", "device")
    elapsed = current.scraped_at - previous.scraped_at if previous else None

    snapshots: list[InterfaceSnapshot] = []
    for info in infos:
        logical_name = info.labels.get("name", "")
        device = info.labels.get("interface", logical_name)
        description = info.labels.get("description", logical_name.upper())
        up_value = current.samples.first_value("node_pfsense_interface_up", {"name": logical_name})

        snapshots.append(
            InterfaceSnapshot(
                name=logical_name,
                device=device,
                description=description,
                up=None if up_value is None else up_value == 1,
                rx_bps=_rate(current_rx, previous_rx, device, elapsed),
                tx_bps=_rate(current_tx, previous_tx, device, elapsed),
            )
        )

    return snapshots


def _rate(
    current: dict[str, object],
    previous: dict[str, object],
    device: str,
    elapsed: float | None,
) -> float | None:
    if not elapsed or elapsed <= 0 or device not in current or device not in previous:
        return None
    current_value = getattr(current[device], "value")
    previous_value = getattr(previous[device], "value")
    return max(0.0, (current_value - previous_value) / elapsed)


def _percent(used: float, total: float) -> float | None:
    if total <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * used / total))
