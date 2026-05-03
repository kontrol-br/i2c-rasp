from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OledConfig:
    enabled: bool = True
    model: str = "ssd1306"
    i2c_port: int = 1
    i2c_address: int = 0x3C
    rotate: int = 0
    spi_port: int = 0
    spi_device: int = 0
    spi_dc_pin: int = 24
    spi_rst_pin: int = 25
    spi_h_offset: int = 1
    spi_v_offset: int = 26
    spi_bgr: bool = True
    spi_invert: bool = False




def _draw_decorative_border(draw, width: int, height: int, color: str = "#0033cc") -> None:
    draw.rectangle((0, 0, width - 1, height - 1), outline=color, width=2)


class DisplaySink:
    def show_page(self, lines: list[str], *, flash: bool = False, frame: int = 0) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        self.show_page([title, time_text, date_text])

    def show_rainbow(self, frame: int = 0) -> None:
        return


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


class ST7735Sink(DisplaySink):
    def __init__(self, width: int, height: int, config: OledConfig) -> None:
        from luma.core.interface.serial import spi
        from luma.core.render import canvas
        from luma.lcd.device import st7735

        self._canvas = canvas
        serial = spi(port=config.spi_port, device=config.spi_device, gpio_DC=config.spi_dc_pin, gpio_RST=config.spi_rst_pin)
        # O driver luma.lcd para ST7735 aceita o layout wide 160x80 (e nao 80x160).
        # A rotacao continua sendo controlada por `config.rotate`.
        try:
            self._device = st7735(
                serial,
                width=160,
                height=80,
                rotate=config.rotate,
                h_offset=config.spi_h_offset,
                v_offset=config.spi_v_offset,
                bgr=config.spi_bgr,
                invert=config.spi_invert,
            )
        except TypeError as exc:
            if "invert" not in str(exc):
                raise
            # Compatibilidade com versões de luma.lcd sem argumento `invert`.
            self._device = st7735(
                serial,
                width=160,
                height=80,
                rotate=config.rotate,
                h_offset=config.spi_h_offset,
                v_offset=config.spi_v_offset,
                bgr=config.spi_bgr,
            )
        self._set_st7735_inversion(config.spi_invert)
        self._columns = width
        self._rows = height

    def _set_st7735_inversion(self, invert: bool) -> None:
        # INVON=0x21 / INVOFF=0x20 no controlador ST7735.
        command = 0x21 if invert else 0x20
        if hasattr(self._device, "command"):
            try:
                self._device.command(command)
            except Exception:
                return

    def show_page(self, lines: list[str], *, flash: bool = False, frame: int = 0) -> None:
        from PIL import ImageFont

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 12)
        except OSError:
            font = ImageFont.load_default()

        colors = ["red", "orange", "yellow", "#00ff00", "cyan", "blue", "magenta", "#00ff00"]
        visible_lines = [line for line in lines[: self._rows] if line.strip()] or lines[: self._rows]
        bbox = font.getbbox("Ag")
        text_height = max(10, bbox[3] - bbox[1])
        top_margin = 4
        bottom_margin = 4
        available_height = max(1, self._device.height - top_margin - bottom_margin)
        line_height = max(text_height + 2, available_height // max(1, len(visible_lines)))
        with self._canvas(self._device) as draw:
            # Mantem fundo preto em todos os estados.
            draw.rectangle((0, 0, self._device.width, self._device.height), fill="black")
            _draw_decorative_border(draw, self._device.width, self._device.height)
            for row, line in enumerate(visible_lines):
                y = top_margin + row * line_height
                color = "white" if flash else colors[row % len(colors)]
                _draw_scrolling_text(draw, line, font, y, color, frame, self._device.width, x_offset=3)

    def show_clock(self, title: str, time_text: str, date_text: str) -> None:
        from PIL import ImageFont

        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 12)
            time_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
            date_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 11)
        except OSError:
            title_font = ImageFont.load_default()
            time_font = ImageFont.load_default()
            date_font = ImageFont.load_default()

        with self._canvas(self._device) as draw:
            draw.rectangle((0, 0, self._device.width, self._device.height), fill="black")
            _draw_decorative_border(draw, self._device.width, self._device.height)
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = max(0, (self._device.width - title_width) // 2)
            draw.text((title_x, 0), title, fill="#ffff00", font=title_font)
            time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
            time_width = time_bbox[2] - time_bbox[0]
            time_x = max(0, (self._device.width - time_width) // 2)
            draw.text((time_x, 16), time_text, fill="#1500d1", font=time_font)
            date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
            date_width = date_bbox[2] - date_bbox[0]
            date_x = max(0, (self._device.width - date_width) // 2)
            draw.text((date_x, self._device.height - 12), date_text, fill="white", font=date_font)

    def show_rainbow(self, frame: int = 0) -> None:
        colors = ["#ff2b5f", "#f7b42c", "#7ac143", "#3b82d6"]
        stripe_width = 34
        slant = 30
        x_start = -16
        y_bottom = self._device.height
        y_top = 0
        with self._canvas(self._device) as draw:
            draw.rectangle((0, 0, self._device.width, self._device.height), fill="black")
            for idx, color in enumerate(colors):
                x0 = x_start + idx * stripe_width
                x1 = x0 + stripe_width
                draw.polygon([(x0, y_bottom), (x1, y_bottom), (x1 + slant, y_top), (x0 + slant, y_top)], fill=color)
            _draw_decorative_border(draw, self._device.width, self._device.height)

    def close(self) -> None:
        self._device.clear()


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
        self._page_title_y = 0
        self._page_body_start_y = 14

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

        with self._canvas(self._device) as draw:
            if flash:
                draw.rectangle((0, 0, self._device.width, self._device.height), outline=255, fill=255)
            for row, raw_line in enumerate(visible_lines):
                color = 0 if flash else 255
                if row == 0:
                    _draw_scrolling_text(
                        draw=draw,
                        text=raw_line,
                        font=title_font,
                        y=self._page_title_y,
                        color=color,
                        frame=frame,
                        device_width=self._device.width,
                    )
                    continue
                body_row = row - 1
                y = self._page_body_start_y + body_row * line_height
                _draw_scrolling_text(
                    draw=draw,
                    text=raw_line,
                    font=page_font,
                    y=y,
                    color=color,
                    frame=frame,
                    device_width=self._device.width,
                )

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
    max_offset = len(text) - width
    offset = _ping_pong_offset(frame, max_offset, step=1)
    return text[offset : offset + width]


def _draw_scrolling_text(draw, text: str, font, y: int, color: int | str, frame: int, device_width: int, x_offset: int = 0) -> None:
    clean_text = text.rstrip()
    if not clean_text:
        return

    text_bbox = draw.textbbox((0, 0), clean_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    available_width = max(1, device_width - x_offset)
    if text_width <= available_width:
        draw.text((x_offset, y), clean_text, fill=color, font=font)
        return

    speed_pixels_per_frame = 2
    max_offset = text_width - available_width
    offset = _ping_pong_offset(frame, max_offset, step=speed_pixels_per_frame)
    draw.text((x_offset - offset, y), clean_text, fill=color, font=font)


def _ping_pong_offset(frame: int, max_offset: int, step: int) -> int:
    if max_offset <= 0:
        return 0
    path = list(range(0, max_offset + 1, step))
    if path[-1] != max_offset:
        path.append(max_offset)
    if len(path) == 1:
        return path[0]
    cycle = path + path[-2:0:-1]
    return cycle[frame % len(cycle)]
