from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OledConfig:
    enabled: bool = True
    i2c_port: int = 1
    i2c_address: int = 0x3C
    rotate: int = 0


class DisplaySink:
    def show_page(self, lines: list[str], *, flash: bool = False) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        self.show_page([title, time_text, date_text])


class TerminalSink(DisplaySink):
    def show_page(self, lines: list[str], *, flash: bool = False) -> None:
        width = max((len(line) for line in lines), default=0)
        border = "+" + "-" * width + "+"
        body = "\n".join(f"|{line.ljust(width)}|" for line in lines)
        if flash:
            body = f"\033[7m{body}\033[0m"
        print(f"{border}\n{body}\n{border}", flush=True)

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        self.show_page([f"\033[33m{title}\033[0m", time_text, date_text])


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
        self._title_y = 0
        self._time_y = 14
        self._date_y = 52

    def show_page(self, lines: list[str], *, flash: bool = False) -> None:
        with self._canvas(self._device) as draw:
            if flash:
                draw.rectangle((0, 0, self._device.width, self._device.height), outline=255, fill=255)
            for row, raw_line in enumerate(lines[: self._rows]):
                color = 0 if flash else 255
                draw.text((0, row * 16), raw_line[: self._columns], fill=color)

    def close(self) -> None:
        self._device.clear()

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        from PIL import ImageFont

        title_font = ImageFont.load_default()
        date_font = ImageFont.load_default()
        try:
            time_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        except OSError:
            time_font = ImageFont.load_default()

        with self._canvas(self._device) as draw:
            draw.text((0, self._title_y), title, fill=255, font=title_font)
            time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
            time_width = time_bbox[2] - time_bbox[0]
            time_x = max(0, (self._device.width - time_width) // 2)
            draw.text((time_x, self._time_y), time_text, fill=255, font=time_font)
            draw.text((0, self._date_y), date_text, fill=255, font=date_font)
