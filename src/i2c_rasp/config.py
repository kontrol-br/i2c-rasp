from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from urllib.parse import urlsplit

from i2c_rasp.display import OledConfig


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class HostConfig:
    name: str = "kontrol"
    host: str = "10.0.0.1"
    port: int = 9100
    scheme: str = "http"
    metrics_path: str = "/metrics"

    @property
    def metrics_url(self) -> str:
        parsed = urlsplit(self.host)
        if parsed.scheme and parsed.netloc:
            base_host = parsed.hostname or self.host
            scheme = parsed.scheme
            port = parsed.port or self.port
        else:
            base_host = self.host.removeprefix("http://").removeprefix("https://")
            scheme = self.scheme
            port = self.port

        path = self.metrics_path if self.metrics_path.startswith("/") else f"/{self.metrics_path}"
        return f"{scheme}://{base_host}:{port}{path}"


@dataclass(frozen=True)
class ScrapeConfig:
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class DisplayConfig:
    width: int = 20
    height: int = 4
    page_seconds: float = 4.0
    refresh_seconds: float = 2.0


@dataclass(frozen=True)
class InterfaceConfig:
    include: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlertThresholdsConfig:
    cpu_percent: float | None = None
    memory_percent: float | None = None
    temperature_celsius: float | None = None
    storage_percent: float | None = None


@dataclass(frozen=True)
class BuzzerConfig:
    enabled: bool = False
    gpio_pin: int = 18
    mode: str = "active"
    active_high: bool = True
    frequency_hz: int = 2000
    duty_cycle: float = 0.5

    def __post_init__(self) -> None:
        if self.mode not in {"active", "pwm"}:
            raise ValueError('buzzer.mode deve ser "active" ou "pwm"')
        if self.frequency_hz <= 0:
            raise ValueError("buzzer.frequency_hz deve ser maior que zero")
        if not 0.0 < self.duty_cycle <= 1.0:
            raise ValueError("buzzer.duty_cycle deve estar entre 0 e 1")


@dataclass(frozen=True)
class AppConfig:
    hosts: list[HostConfig] = field(default_factory=lambda: [HostConfig()])
    scrape: ScrapeConfig = field(default_factory=ScrapeConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    interfaces: InterfaceConfig = field(default_factory=InterfaceConfig)
    oled: OledConfig = field(default_factory=OledConfig)
    alert_thresholds: AlertThresholdsConfig = field(default_factory=AlertThresholdsConfig)
    buzzer: BuzzerConfig = field(default_factory=BuzzerConfig)


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return AppConfig()

    data = _load_toml(path)
    host_entries = data.get("hosts", [])
    if not host_entries and "target" in data:
        target = data["target"]
        host_entries = [
            {
                "name": target.get("name", "kontrol"),
                "host": target.get("host", target.get("metrics_url", "http://10.0.0.1:9100/metrics")),
                "port": target.get("port", 9100),
            }
        ]

    return AppConfig(
        hosts=[HostConfig(**entry) for entry in host_entries] or [HostConfig()],
        scrape=ScrapeConfig(**data.get("scrape", {})),
        display=DisplayConfig(**data.get("display", {})),
        interfaces=InterfaceConfig(**data.get("interfaces", {})),
        oled=OledConfig(**_filter_dataclass_kwargs(OledConfig, data.get("oled", {}))),
        alert_thresholds=AlertThresholdsConfig(**data.get("alert_thresholds", {})),
        buzzer=BuzzerConfig(**data.get("buzzer", {})),
    )


def _filter_dataclass_kwargs(cls, raw: dict) -> dict:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in raw.items() if key in allowed}


def _load_toml(path: str | Path) -> dict:
    config_path = Path(path)
    raw = config_path.read_text(encoding="utf-8")
    try:
        return tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(_format_toml_error(config_path, raw, exc)) from exc


def _format_toml_error(path: Path, raw: str, exc: tomllib.TOMLDecodeError) -> str:
    lines = raw.splitlines()
    lineno = getattr(exc, "lineno", None)
    colno = getattr(exc, "colno", None)
    if lineno is None or colno is None:
        match = re.search(r"\(at line (\d+), column (\d+)\)", str(exc))
        if match:
            lineno = int(match.group(1))
            colno = int(match.group(2))
    location = f"linha {lineno}, coluna {colno}" if lineno and colno else "local desconhecido"
    message = f"Erro no TOML {path} ({location}): {str(exc)}"

    if not lineno or lineno < 1 or lineno > len(lines):
        return message

    line = lines[lineno - 1]
    pointer = ""
    if colno and colno > 0:
        pointer = "\n" + " " * (colno - 1) + "^"

    hints = []
    stripped = line.strip()
    if stripped and not stripped.startswith(("#", "[")) and "=" not in stripped:
        hints.append("Esta linha parece nao ter '='. Em TOML, comentarios precisam comecar com '#'.")
    if "//" in line:
        hints.append("TOML nao aceita comentario com '//'; use '#'.")
    if ":" in line and "=" not in line:
        hints.append("TOML usa 'chave = valor', nao 'chave: valor'.")

    hint_text = "" if not hints else "\nDica: " + " ".join(hints)
    return f"{message}\n{lineno:>4}: {line}{pointer}{hint_text}"
