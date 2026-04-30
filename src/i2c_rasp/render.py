from __future__ import annotations

from dataclasses import dataclass

from i2c_rasp.snapshot import DeviceSnapshot, InterfaceSnapshot


@dataclass(frozen=True)
class RenderedPage:
    kind: str
    lines: list[str]


def render_pages(snapshot: DeviceSnapshot, width: int, height: int) -> list[RenderedPage]:
    pages = [
        RenderedPage(
            kind="cpu",
            lines=_fit_lines(
                [
                    "CPU",
                    f"HOST {snapshot.hostname}",
                    f"USO {_fmt_percent(snapshot.cpu_percent)}",
                    f"LOAD {_fmt_number(snapshot.load1)}",
                ],
                width,
                height,
            ),
        ),
        RenderedPage(
            kind="memory",
            lines=_fit_lines(
                [
                    "MEMORIA",
                    f"HOST {snapshot.hostname}",
                    f"RAM {_fmt_percent(snapshot.memory_percent)}",
                    f"SWAP {_fmt_percent(snapshot.swap_percent)}",
                ],
                width,
                height,
            ),
        ),
    ]

    for interface in snapshot.interfaces:
        pages.append(RenderedPage(kind="interface", lines=_render_interface(interface, width, height)))

    pages.extend(
        [
            RenderedPage(
                kind="storage",
                lines=_fit_lines(
                    [
                        "STORAGE",
                        f"HOST {snapshot.hostname}",
                        f"ROOT {_fmt_percent(snapshot.root_disk_percent)}",
                    ],
                    width,
                    height,
                ),
            ),
            RenderedPage(
                kind="temperature",
                lines=_fit_lines(
                    [
                        "TEMPERATURA",
                        f"HOST {snapshot.hostname}",
                        f"CPU {_fmt_temp(snapshot.temperature_celsius)}",
                    ],
                    width,
                    height,
                ),
            ),
        ]
    )
    return pages


def render_terminal_page(lines: list[str]) -> str:
    if not lines:
        return ""
    width = max(len(line) for line in lines)
    border = "+" + "-" * width + "+"
    body = "\n".join(f"|{line.ljust(width)}|" for line in lines)
    return f"{border}\n{body}\n{border}"


def _render_interface(interface: InterfaceSnapshot, width: int, height: int) -> list[str]:
    status = "UP" if interface.up else "DOWN" if interface.up is False else "?"
    return _fit_lines(
        [
            f"{interface.description} {status}",
            f"dev {interface.device}",
            f"RX {_fmt_bps(interface.rx_bps)}",
            f"TX {_fmt_bps(interface.tx_bps)}",
        ],
        width,
        height,
    )


def _fit_lines(lines: list[str], width: int, height: int) -> list[str]:
    fitted = [line.ljust(width) if len(line) < width else line for line in lines[:height]]
    while len(fitted) < height:
        fitted.append(" " * width)
    return fitted


def _fmt_percent(value: float | None) -> str:
    if value is None:
        return "--%"
    return f"{value:>4.1f}%"


def _fmt_number(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.2f}"


def _fmt_temp(value: float | None) -> str:
    if value is None:
        return "--C"
    return f"{value:.1f}C"


def _fmt_bps(value: float | None) -> str:
    if value is None:
        return "--/s"
    units = ("B/s", "KB/s", "MB/s", "GB/s")
    scaled = value
    unit = units[0]
    for unit in units:
        if scaled < 1024 or unit == units[-1]:
            break
        scaled /= 1024
    return f"{scaled:.1f}{unit}"
