from i2c_rasp.metrics import SampleSet, parse_prometheus_text
from i2c_rasp.scrape import ScrapeResult
from i2c_rasp.snapshot import SnapshotBuilder


def test_snapshot_uses_freebsd_memory_and_pfsense_interfaces() -> None:
    text = """
node_uname_info{nodename="kontrol-lab",sysname="FreeBSD"} 1
node_cpu_seconds_total{cpu="0",mode="idle"} 100
node_cpu_seconds_total{cpu="0",mode="system"} 10
node_cpu_seconds_total{cpu="0",mode="user"} 10
node_memory_size_bytes 1000
node_memory_free_bytes 200
node_memory_inactive_bytes 100
node_memory_cache_bytes 0
node_memory_laundry_bytes 0
node_memory_swap_size_bytes 100
node_memory_swap_used_bytes 25
node_cpu_temperature_celsius{cpu="0"} 42
node_load1 0.5
node_filesystem_size_bytes{mountpoint="/"} 1000
node_filesystem_avail_bytes{mountpoint="/"} 250
node_pfsense_interface_info{name="wan",interface="igc0",description="WAN"} 1
node_pfsense_interface_up{name="wan"} 1
node_network_receive_bytes_total{device="igc0"} 1000
node_network_transmit_bytes_total{device="igc0"} 2000
"""
    result = ScrapeResult("http://example.test", 1.0, SampleSet(parse_prometheus_text(text)))

    snapshot = SnapshotBuilder(["wan"]).build("lab", result)

    assert snapshot.hostname == "kontrol-lab"
    assert snapshot.memory_percent == 70
    assert snapshot.swap_percent == 25
    assert snapshot.root_disk_percent == 75
    assert snapshot.interfaces[0].up is True
