from i2c_rasp.metrics import parse_labels, parse_prometheus_text


def test_parse_labels_with_escaped_values() -> None:
    assert parse_labels(r'name="wan",description="WAN \"VIVO\"",path="a\\b"') == {
        "name": "wan",
        "description": 'WAN "VIVO"',
        "path": r"a\b",
    }


def test_parse_prometheus_text_ignores_comments() -> None:
    samples = parse_prometheus_text(
        """
# HELP node_load1 1m load average.
# TYPE node_load1 gauge
node_load1 0.42
node_pfsense_interface_up{name="wan"} 1
"""
    )

    assert samples[0].name == "node_load1"
    assert samples[0].value == 0.42
    assert samples[1].labels == {"name": "wan"}


def test_parse_prometheus_text_can_filter_metric_names() -> None:
    samples = parse_prometheus_text(
        """
go_goroutines 12
node_load1 0.42
node_memory_size_bytes 1000
""",
        include_names=frozenset({"node_load1"}),
    )

    assert len(samples) == 1
    assert samples[0].name == "node_load1"
