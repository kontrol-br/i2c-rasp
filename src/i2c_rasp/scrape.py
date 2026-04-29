from __future__ import annotations

from dataclasses import dataclass
from time import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from i2c_rasp.metrics import MONITORED_METRIC_NAMES, SampleSet, parse_prometheus_text


@dataclass(frozen=True)
class ScrapeResult:
    url: str
    scraped_at: float
    samples: SampleSet


class ScrapeError(RuntimeError):
    pass


class MetricsScraper:
    def __init__(self, metrics_url: str, timeout_seconds: float = 5.0) -> None:
        self.metrics_url = metrics_url
        self.timeout_seconds = timeout_seconds

    def scrape(self) -> ScrapeResult:
        request = Request(
            self.metrics_url,
            headers={"User-Agent": "i2c-rasp/0.1"},
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset, errors="replace")
        except URLError as exc:
            raise ScrapeError(f"falha ao coletar {self.metrics_url}: {exc}") from exc
        except TimeoutError as exc:
            raise ScrapeError(f"timeout ao coletar {self.metrics_url}") from exc

        return ScrapeResult(
            url=self.metrics_url,
            scraped_at=time(),
            samples=SampleSet(parse_prometheus_text(text, include_names=MONITORED_METRIC_NAMES)),
        )
