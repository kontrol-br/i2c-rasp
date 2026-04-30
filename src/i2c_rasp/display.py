from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OledConfig:
    enabled: bool = True
    i2c_port: int = 1
    i2c_address: int = 0x3C
    rotate: int = 0


class DisplaySink:
    def show_page(self, lines: list[str], *, flash: bool = False, frame: int = 0) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        self.show_page([title, time_text, date_text])


class TerminalSink(DisplaySink):
    def show_page(self, lines: list[str], *, flash: bool = False, frame: int = 0) -> None:
        rendered = [_scroll_text(line, max(len(line), 1), frame) for line in lines]
        width = max((len(line) for line in rendered), default=0)
        border = "+" + "-" * width + "+"
        body = "\n".join(f"|{line.ljust(width)}|" for line in rendered)
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
        self._page_font_size = 14

    def show_page(self, lines: list[str], *, flash: bool = False, frame: int = 0) -> None:
        from PIL import ImageFont

        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 11)
            page_font = ImageFont.truetype("DejaVuSans-Bold.ttf", self._page_font_size)
        except OSError:
            title_font = ImageFont.load_default()
            page_font = ImageFont.load_default()

        visible_lines = [line for line in lines[: self._rows] if line.strip()]
        if not visible_lines:
            visible_lines = lines[: self._rows]
        sample_bbox = page_font.getbbox("Ag")
        text_height = max(10, sample_bbox[3] - sample_bbox[1])
        line_height = text_height + 2
        start_y = max(0, (self._device.height - (line_height * len(visible_lines))) // 2)

        with self._canvas(self._device) as draw:
            if flash:
                draw.rectangle((0, 0, self._device.width, self._device.height), outline=255, fill=255)
            for row, raw_line in enumerate(visible_lines):
                color = 0 if flash else 255
                line = _scroll_text(raw_line, self._columns, frame)
                font = title_font if row == 0 else page_font
                draw.text((0, start_y + row * line_height), line, fill=color, font=font)

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


def _scroll_text(text: str, width: int, frame: int) -> str:
    if len(text) <= width:
        return text
    gap = "   "
    loop = text + gap
    start = frame % len(loop)
    doubled = loop + loop
    return doubled[start : start + width]
