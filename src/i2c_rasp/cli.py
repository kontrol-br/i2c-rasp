from __future__ import annotations

import argparse
from time import sleep
from datetime import datetime
from zoneinfo import ZoneInfo

from i2c_rasp.alerting import evaluate_page_alerts
from i2c_rasp.buzzer import build_buzzer
from i2c_rasp.config import HostConfig, load_config
from i2c_rasp.display import SSD1306Sink, TerminalSink
from i2c_rasp.render import render_pages
from i2c_rasp.scrape import MetricsScraper, ScrapeError
from i2c_rasp.snapshot import SnapshotBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor LCD para metricas pfSense/Kontrol.")
    parser.add_argument("--config", help="Arquivo TOML de configuracao.")
    parser.add_argument("--host", help="Host unico para teste rapido, sem /metrics.")
    parser.add_argument("--port", type=int, default=9100, help="Porta do exporter para --host.")
    parser.add_argument("--url", help="URL completa para teste rapido.")
    parser.add_argument("--once", action="store_true", help="Renderiza uma rodada e encerra.")
    parser.add_argument("--terminal", action="store_true", help="Forca saida no terminal em vez do OLED.")
    args = parser.parse_args()

    config = load_config(args.config)
    hosts = _resolve_hosts(config.hosts, args.host, args.port, args.url)
    scrapers = {
        host.name: MetricsScraper(host.metrics_url, config.scrape.timeout_seconds)
        for host in hosts
    }
    builders = {host.name: SnapshotBuilder(config.interfaces.include) for host in hosts}

    sink = _build_sink(config.display.width, config.display.height, config.oled, args.terminal)
    buzzer = build_buzzer(config.buzzer)

    # Duas coletas por host permitem calcular CPU e throughput de rede na primeira tela.
    for host in hosts:
        _prime_host(host, scrapers[host.name], builders[host.name])
    sleep(min(1.0, config.display.refresh_seconds))

    while True:
        for host in hosts:
            try:
                snapshot = builders[host.name].build(host.name, scrapers[host.name].scrape())
                pages = render_pages(snapshot, config.display.width, config.display.height)
                alerts = evaluate_page_alerts(snapshot, config.alert_thresholds)
            except ScrapeError as exc:
                pages = [
                    _error_page(
                        host.name,
                        str(exc),
                        config.display.width,
                        config.display.height,
                    )
                ]
                alerts = None

            for index, page in enumerate(pages):
                flash = bool(alerts and ((index == 0 and alerts.summary) or (index == len(pages) - 1 and alerts.storage)))
                if flash:
                    buzzer.on()
                sink.show_page(page, flash=flash)
                if flash:
                    buzzer.off()
                if not args.once:
                    sleep(config.display.page_seconds)

        title, time_text, date_text = _clock_content()
        sink.show_clock(title, time_text, date_text)
        if not args.once:
            sleep(config.display.page_seconds)
        if args.once:
            break
        sleep(config.display.refresh_seconds)

    sink.close()
    buzzer.close()


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


if __name__ == "__main__":
    main()


def _build_sink(width: int, height: int, oled_config, force_terminal: bool):
    if force_terminal or not oled_config.enabled:
        return TerminalSink()
    try:
        return SSD1306Sink(width, height, oled_config)
    except Exception as exc:
        print(
            f"OLED indisponivel ({exc}); usando terminal. "
            "Verifique se o pacote foi instalado/atualizado com: pip install -e .",
            flush=True,
        )
        return TerminalSink()
