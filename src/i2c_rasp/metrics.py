from __future__ import annotations

from dataclasses import dataclass
import re


MONITORED_METRIC_NAMES = frozenset(
    {
        "node_cpu_seconds_total",
        "node_cpu_temperature_celsius",
        "node_filesystem_avail_bytes",
        "node_filesystem_size_bytes",
        "node_hwmon_temp_celsius",
        "node_load1",
        "node_memory_MemAvailable_bytes",
        "node_memory_MemTotal_bytes",
        "node_memory_SwapFree_bytes",
        "node_memory_SwapTotal_bytes",
        "node_memory_cache_bytes",
        "node_memory_free_bytes",
        "node_memory_inactive_bytes",
        "node_memory_laundry_bytes",
        "node_memory_size_bytes",
        "node_memory_swap_size_bytes",
        "node_memory_swap_used_bytes",
        "node_network_receive_bytes_total",
        "node_network_transmit_bytes_total",
        "node_pfsense_interface_info",
        "node_pfsense_interface_up",
        "node_thermal_zone_temp",
        "node_uname_info",
    }
)


_SAMPLE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{(?P<labels>.*)\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[-+]?Inf|NaN)"
    r"(?:\s+\d+)?$"
)


@dataclass(frozen=True)
class Sample:
    name: str
    labels: dict[str, str]
    value: float


def parse_prometheus_text(
    text: str,
    include_names: set[str] | frozenset[str] | None = None,
) -> list[Sample]:
    samples: list[Sample] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _SAMPLE_RE.match(line)
        if match is None:
            continue

        name = match.group("name")
        if include_names is not None and name not in include_names:
            continue

        value_text = match.group("value")
        if value_text == "+Inf":
            value = float("inf")
        elif value_text == "-Inf":
            value = float("-inf")
        else:
            value = float(value_text)

        samples.append(
            Sample(
                name=match.group("name"),
                labels=parse_labels(match.group("labels") or ""),
                value=value,
            )
        )

    return samples


def parse_labels(text: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    index = 0

    while index < len(text):
        while index < len(text) and text[index] in " ,":
            index += 1
        if index >= len(text):
            break

        key_start = index
        while index < len(text) and text[index] != "=":
            index += 1
        key = text[key_start:index].strip()
        index += 1

        if index >= len(text) or text[index] != '"':
            break
        index += 1

        value_chars: list[str] = []
        while index < len(text):
            char = text[index]
            if char == "\\" and index + 1 < len(text):
                value_chars.append(_unescape_label_char(text[index + 1]))
                index += 2
                continue
            if char == '"':
                index += 1
                break
            value_chars.append(char)
            index += 1

        labels[key] = "".join(value_chars)

        while index < len(text) and text[index] != ",":
            index += 1
        if index < len(text) and text[index] == ",":
            index += 1

    return labels


def _unescape_label_char(char: str) -> str:
    return {
        "n": "\n",
        "\\": "\\",
        '"': '"',
    }.get(char, char)


class SampleSet:
    def __init__(self, samples: list[Sample]) -> None:
        self.samples = samples

    def values(self, name: str) -> list[Sample]:
        return [sample for sample in self.samples if sample.name == name]

    def first_value(self, name: str, labels: dict[str, str] | None = None) -> float | None:
        for sample in self.values(name):
            if labels is None or all(sample.labels.get(key) == value for key, value in labels.items()):
                return sample.value
        return None

    def by_label(self, name: str, label: str) -> dict[str, Sample]:
        return {
            sample.labels[label]: sample
            for sample in self.values(name)
            if label in sample.labels
        }
