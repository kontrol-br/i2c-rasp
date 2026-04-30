from i2c_rasp.alerting import evaluate_page_alerts
from i2c_rasp.config import AlertThresholdsConfig
from i2c_rasp.snapshot import DeviceSnapshot


def test_alerts_flag_cpu_memory_storage_temperature_pages() -> None:
    snapshot = DeviceSnapshot(
        name="lab",
        hostname="lab",
        os_name="FreeBSD",
        cpu_percent=91,
        load1=0.5,
        memory_percent=70,
        swap_percent=20,
        temperature_celsius=76,
        root_disk_percent=85,
        interfaces=[],
    )
    thresholds = AlertThresholdsConfig(
        cpu_percent=90,
        memory_percent=80,
        temperature_celsius=75,
        storage_percent=90,
    )

    alerts = evaluate_page_alerts(snapshot, thresholds)

    assert alerts.cpu is True
    assert alerts.memory is False
    assert alerts.storage is False
    assert alerts.temperature is True
