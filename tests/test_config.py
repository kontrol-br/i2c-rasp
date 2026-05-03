from i2c_rasp.config import HostConfig
from i2c_rasp.config import load_config


def test_host_config_builds_metrics_url_from_host_and_port() -> None:
    host = HostConfig(name="lab", host="10.0.0.1", port=9100)

    assert host.metrics_url == "http://10.0.0.1:9100/metrics"


def test_host_config_accepts_scheme_in_host_for_manual_tests() -> None:
    host = HostConfig(name="lab", host="https://example.test:9443", port=9100)

    assert host.metrics_url == "https://example.test:9443/metrics"


def test_load_config_supports_alert_thresholds_and_buzzer(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[alert_thresholds]
cpu_percent = 80
memory_percent = 85
storage_percent = 90
temperature_celsius = 70

[buzzer]
enabled = true
gpio_pin = 23
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.alert_thresholds.cpu_percent == 80
    assert config.alert_thresholds.memory_percent == 85
    assert config.alert_thresholds.storage_percent == 90
    assert config.alert_thresholds.temperature_celsius == 70
    assert config.buzzer.enabled is True
    assert config.buzzer.gpio_pin == 23


def test_load_config_supports_st7735_display_model(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[oled]
model = "st7735"
spi_port = 0
spi_device = 0
spi_dc_pin = 24
spi_rst_pin = 25
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.oled.model == "st7735"
    assert config.oled.spi_dc_pin == 24
