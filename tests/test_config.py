from i2c_rasp.config import HostConfig


def test_host_config_builds_metrics_url_from_host_and_port() -> None:
    host = HostConfig(name="lab", host="10.0.0.1", port=9100)

    assert host.metrics_url == "http://10.0.0.1:9100/metrics"


def test_host_config_accepts_scheme_in_host_for_manual_tests() -> None:
    host = HostConfig(name="lab", host="https://example.test:9443", port=9100)

    assert host.metrics_url == "https://example.test:9443/metrics"
