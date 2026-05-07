from __future__ import annotations

import argparse
import signal
from datetime import datetime
from time import sleep
from zoneinfo import ZoneInfo

from i2c_rasp.alerting import evaluate_page_alerts
from i2c_rasp.buzzer import build_buzzer
from i2c_rasp.config import BuzzerConfig, ConfigError, HostConfig, load_config
from i2c_rasp.display import SSD1306Sink, ST7735Sink, TerminalSink
from i2c_rasp.render import RenderedPage, render_pages
from i2c_rasp.scrape import MetricsScraper, ScrapeError
from i2c_rasp.snapshot import SnapshotBuilder

FRAME_STEP_SECONDS = 0.25
ALERT_BUZZER_PULSES = 3
ALERT_BUZZER_ON_SECONDS = 0.2
ALERT_BUZZER_OFF_SECONDS = 0.15


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor LCD para metricas pfSense/Kontrol.")
    parser.add_argument("--config", help="Arquivo TOML de configuracao.")
    parser.add_argument("--host", help="Host unico para teste rapido, sem /metrics.")
    parser.add_argument("--port", type=int, default=9100, help="Porta do exporter para --host.")
    parser.add_argument("--url", help="URL completa para teste rapido.")
    parser.add_argument("--once", action="store_true", help="Renderiza uma rodada e encerra.")
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Forca saida no terminal em vez do OLED.",
    )
    parser.add_argument(
        "--buzzer-debug",
        choices=("off", "on", "pulse", "raw-low", "raw-high"),
        help="Testa somente o buzzer e encerra; raw-low/raw-high ignoram active_high.",
    )
    parser.add_argument(
        "--buzzer-debug-seconds",
        type=float,
        default=5.0,
        help="Duracao do teste --buzzer-debug, em segundos.",
    )
    parser.add_argument(
        "--buzzer-debug-pin",
        type=int,
        help="Sobrescreve buzzer.gpio_pin apenas para --buzzer-debug.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Valida o arquivo TOML e encerra sem iniciar display, scraping ou GPIO.",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(str(exc), flush=True)
        raise SystemExit(2) from exc

    print(f"Config carregada: {args.config or '<padrao>'}; codigo={__file__}", flush=True)
    _log_display_gpio_usage(config.oled)
    if args.check_config:
        print("Configuracao valida.", flush=True)
        return
    if args.buzzer_debug:
        _run_buzzer_debug(
            config.buzzer,
            args.buzzer_debug,
            args.buzzer_debug_seconds,
            gpio_pin=args.buzzer_debug_pin,
        )
        return

    hosts = _resolve_hosts(config.hosts, args.host, args.port, args.url)
    scrapers = {
        host.name: MetricsScraper(host.metrics_url, config.scrape.timeout_seconds)
        for host in hosts
    }
    builders = {host.name: SnapshotBuilder(config.interfaces.include) for host in hosts}

    sink = _build_sink(config.display.width, config.display.height, config.oled, args.terminal)
    buzzer = build_buzzer(config.buzzer)
    buzzer.off()
    _install_shutdown_handlers()

    try:
        # Duas coletas por host permitem calcular CPU e throughput de rede na primeira tela.
        for host in hosts:
            _prime_host(host, scrapers[host.name], builders[host.name])
        sleep(min(1.0, config.display.refresh_seconds))
        sink.run_startup_self_test()

        while True:
            for host in hosts:
                try:
                    snapshot = builders[host.name].build(host.name, scrapers[host.name].scrape())
                    pages = render_pages(snapshot, config.display.width, config.display.height)
                    alerts = evaluate_page_alerts(snapshot, config.alert_thresholds)
                except ScrapeError as exc:
                    pages = [
                        RenderedPage(
                            kind="error",
                            lines=_error_page(
                                host.name,
                                str(exc),
                                config.display.width,
                                config.display.height,
                            ),
                        )
                    ]
                    alerts = None

                for page in pages:
                    flash = bool(
                        alerts
                        and (
                            (page.kind == "cpu" and alerts.cpu)
                            or (page.kind == "memory" and alerts.memory)
                            or (page.kind == "storage" and alerts.storage)
                            or (page.kind == "temperature" and alerts.temperature)
                        )
                    )
                    _show_page_with_alert(
                        sink=sink,
                        buzzer=buzzer,
                        page=page.lines,
                        alert=flash,
                        page_seconds=config.display.page_seconds,
                        once=args.once,
                    )

            _show_rainbow_cycle(sink, config.display.page_seconds, args.once)

            title, time_text, date_text = _clock_content()
            sink.show_clock(title, time_text, date_text)
            if not args.once:
                sleep(config.display.page_seconds)
            if args.once:
                break
            sleep(config.display.refresh_seconds)
    finally:
        buzzer.close()
        sink.close()


def _log_display_gpio_usage(oled_config) -> None:
    if oled_config.enabled and oled_config.model.lower() == "st7735":
        print(
            "Display ST7735 usando GPIOs: "
            f"DC={oled_config.spi_dc_pin}, RST={oled_config.spi_rst_pin}. "
            "Nao conecte o buzzer nesses GPIOs.",
            flush=True,
        )


def _run_buzzer_debug(
    config: BuzzerConfig,
    action: str,
    seconds: float,
    *,
    gpio_pin: int | None = None,
) -> None:
    effective_config = _replace_buzzer_config(config, gpio_pin=gpio_pin)
    pin_source = "CLI" if gpio_pin is not None else "config"
    print(
        "DEBUG buzzer: "
        f"action={action}, seconds={seconds}, enabled={effective_config.enabled}, "
        f"GPIO={effective_config.gpio_pin} ({pin_source}), "
        f"mode={effective_config.mode}, active_high={effective_config.active_high}, "
        f"frequency_hz={effective_config.frequency_hz}, duty_cycle={effective_config.duty_cycle}.",
        flush=True,
    )
    if action in {"raw-low", "raw-high"}:
        _run_buzzer_raw_debug(effective_config.gpio_pin, action == "raw-high", seconds)
        return

    force_enabled = action in {"on", "pulse"}
    buzzer = build_buzzer(
        _replace_buzzer_config(effective_config, enabled=force_enabled)
    )
    try:
        _run_buzzer_debug_action(buzzer, action, seconds)
    finally:
        buzzer.close()
        print("DEBUG buzzer: finalizado; comando off/close enviado.", flush=True)


def _replace_buzzer_config(
    config: BuzzerConfig,
    **overrides,
) -> BuzzerConfig:
    return BuzzerConfig(**{**config.__dict__, **{k: v for k, v in overrides.items() if v is not None}})


def _run_buzzer_raw_debug(gpio_pin: int, high: bool, seconds: float) -> None:
    from gpiozero import DigitalOutputDevice

    level = "HIGH" if high else "LOW"
    print(
        f"DEBUG buzzer RAW: GPIO={gpio_pin} em nivel fisico {level}; "
        "este teste ignora active_high/mode.",
        flush=True,
    )
    device = DigitalOutputDevice(gpio_pin, active_high=True, initial_value=high)
    try:
        device.value = 1 if high else 0
        sleep(max(0.0, seconds))
    finally:
        device.close()
        print("DEBUG buzzer RAW: GPIO liberado.", flush=True)


def _run_buzzer_debug_action(buzzer, action: str, seconds: float) -> None:
    duration = max(0.0, seconds)
    if action == "off":
        buzzer.off()
        sleep(duration)
        return

    if action == "on":
        buzzer.on()
        sleep(duration)
        return

    elapsed = 0.0
    buzzer_is_on = False
    while elapsed < duration:
        if buzzer_is_on:
            buzzer.off()
            buzzer_is_on = False
        else:
            buzzer.on()
            buzzer_is_on = True
        step = min(0.5, duration - elapsed)
        sleep(step)
        elapsed += step

    buzzer.off()


def _install_shutdown_handlers() -> None:
    def _shutdown(signum, _frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)


def _resolve_hosts(
    configured_hosts: list[HostConfig],
    host: str | None,
    port: int,
    url: str | None,
) -> list[HostConfig]:
    if url:
        return [HostConfig(name="manual", host=url, port=port)]
    if host:
        return [HostConfig(name=host, host=host, port=port)]
    return configured_hosts


def _prime_host(host: HostConfig, scraper: MetricsScraper, builder: SnapshotBuilder) -> None:
    try:
        builder.build(host.name, scraper.scrape())
    except ScrapeError:
        return


def _error_page(name: str, message: str, width: int, height: int) -> list[str]:
    lines = [name, "SCRAPE ERROR", message]
    fitted = [line[:width].ljust(width) for line in lines[:height]]
    while len(fitted) < height:
        fitted.append(" " * width)
    return fitted


def _clock_content() -> tuple[str, str, str]:
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    timezone_label = "SAO PAULO, BRASIL"
    time_line = now.strftime("%H:%M")
    date_line = now.strftime("%d/%m/%Y")
    return timezone_label, time_line, date_line


def _show_page_with_alert(
    sink,
    buzzer,
    page: list[str],
    alert: bool,
    page_seconds: float,
    once: bool,
) -> None:
    if not alert:
        buzzer.off()
        if once:
            sink.show_page(page, flash=False, frame=0)
            return
        _animate_page(sink, page, page_seconds, flash=False, flash_blink=False)
        return

    total_seconds = page_seconds * 2.0
    try:
        print(f"Alerta sonoro: {ALERT_BUZZER_PULSES} pulsos curtos.", flush=True)
        _pulse_buzzer(
            buzzer,
            pulses=ALERT_BUZZER_PULSES,
            on_seconds=ALERT_BUZZER_ON_SECONDS,
            off_seconds=ALERT_BUZZER_OFF_SECONDS,
        )
        if once:
            buzzer.on()
            sink.show_page(page, flash=True, frame=0)
            return
        _animate_alert_page(sink, buzzer, page, total_seconds)
    finally:
        buzzer.off()


def _pulse_buzzer(buzzer, *, pulses: int, on_seconds: float, off_seconds: float) -> None:
    for index in range(max(0, pulses)):
        buzzer.on()
        sleep(on_seconds)
        buzzer.off()
        if index < pulses - 1:
            sleep(off_seconds)


def _animate_page(
    sink,
    page: list[str],
    total_seconds: float,
    flash: bool,
    flash_blink: bool,
) -> None:
    elapsed = 0.0
    frame = 0
    while elapsed < total_seconds:
        flash_on = frame % 2 == 0 if flash_blink else flash
        sink.show_page(page, flash=flash_on, frame=frame)
        step = min(FRAME_STEP_SECONDS, total_seconds - elapsed)
        sleep(step)
        elapsed += step
        frame += 1


def _build_sink(width: int, height: int, oled_config, force_terminal: bool):
    if force_terminal or not oled_config.enabled:
        return TerminalSink()
    try:
        if oled_config.model.lower() == "st7735":
            return ST7735Sink(width, height, oled_config)
        return SSD1306Sink(width, height, oled_config)
    except Exception as exc:
        print(
            f"OLED indisponivel ({exc}); usando terminal. "
            "Verifique se o pacote foi instalado/atualizado com: pip install -e .",
            flush=True,
        )
        return TerminalSink()


def _show_rainbow_cycle(sink, page_seconds: float, once: bool) -> None:
    sink.show_rainbow(frame=0)
    if not once:
        sleep(page_seconds)


if __name__ == "__main__":
    main()
