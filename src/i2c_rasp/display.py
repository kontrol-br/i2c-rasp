from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OledConfig:
    enabled: bool = True
    i2c_port: int = 1
    i2c_address: int = 0x3C
    rotate: int = 0


class DisplaySink:
    def show_page(self, lines: list[str]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return


class TerminalSink(DisplaySink):
    def show_page(self, lines: list[str]) -> None:
        width = max((len(line) for line in lines), default=0)
        border = "+" + "-" * width + "+"
        body = "\n".join(f"|{line.ljust(width)}|" for line in lines)
        print(f"{border}\n{body}\n{border}", flush=True)


class SSD1306Sink(DisplaySink):
    def __init__(self, width: int, height: int, config: OledConfig) -> None:
        from luma.core.interface.serial import i2c
        from luma.core.render import canvas
        from luma.oled.device import ssd1306

        self._canvas = canvas
        serial = i2c(port=config.i2c_port, address=config.i2c_address)
        self._device = ssd1306(serial, width=128, height=64, rotate=config.rotate)
        self._columns = width
        self._rows = height

    def show_page(self, lines: list[str]) -> None:
        with self._canvas(self._device) as draw:
            for row, raw_line in enumerate(lines[: self._rows]):
                draw.text((0, row * 16), raw_line[: self._columns], fill=255)

    def close(self) -> None:
        self._device.clear()
