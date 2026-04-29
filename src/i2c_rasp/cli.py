from __future__ import annotations

import argparse
from time import sleep

from i2c_rasp.config import HostConfig, load_config
from i2c_rasp.render import render_pages, render_terminal_page
from i2c_rasp.scrape import MetricsScraper, ScrapeError
from i2c_rasp.snapshot import SnapshotBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor LCD para metricas pfSense/Kontrol.")
    parser.add_argument("--config", help="Arquivo TOML de configuracao.")
    parser.add_argument("--host", help="Host unico para teste rapido, sem /metrics.")
    parser.add_argument("--port", type=int, default=9100, help="Porta do exporter para --host.")
    parser.add_argument("--url", help="URL completa para teste rapido.")
    parser.add_argument("--once", action="store_true", help="Renderiza uma rodada e encerra.")
    args = parser.parse_args()

    config = load_config(args.config)
    hosts = _resolve_hosts(config.hosts, args.host, args.port, args.url)
    scrapers = {
        host.name: MetricsScraper(host.metrics_url, config.scrape.timeout_seconds)
        for host in hosts
    }
    builders = {host.name: SnapshotBuilder(config.interfaces.include) for host in hosts}

    # Duas coletas por host permitem calcular CPU e throughput de rede na primeira tela.
    for host in hosts:
        _prime_host(host, scrapers[host.name], builders[host.name])
    sleep(min(1.0, config.display.refresh_seconds))

    while True:
        for host in hosts:
            try:
                snapshot = builders[host.name].build(host.name, scrapers[host.name].scrape())
                pages = render_pages(snapshot, config.display.width, config.display.height)
            except ScrapeError as exc:
                pages = [_error_page(host.name, str(exc), config.display.width, config.display.height)]

            for page in pages:
                print(render_terminal_page(page), flush=True)
                if not args.once:
                    sleep(config.display.page_seconds)
        if args.once:
            break
        sleep(config.display.refresh_seconds)


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


if __name__ == "__main__":
    main()
