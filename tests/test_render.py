from i2c_rasp.render import render_pages
from i2c_rasp.snapshot import DeviceSnapshot


def test_render_pages_has_dedicated_cpu_memory_storage_temperature_pages() -> None:
    snapshot = DeviceSnapshot(
        name="lab",
        hostname="kontrol",
        os_name="FreeBSD",
        cpu_percent=50,
        load1=0.9,
        memory_percent=70,
        swap_percent=25,
        temperature_celsius=61,
        root_disk_percent=55,
        interfaces=[],
    )

    pages = render_pages(snapshot, 20, 4)

    assert [page.kind for page in pages] == ["cpu", "memory", "storage", "temperature"]


def test_render_pages_keeps_long_lines_for_scrolling() -> None:
    snapshot = DeviceSnapshot(
        name="lab-with-very-very-long-name",
        hostname="host-with-very-very-long-name",
        os_name="FreeBSD",
        cpu_percent=50,
        load1=0.9,
        memory_percent=70,
        swap_percent=25,
        temperature_celsius=61,
        root_disk_percent=55,
        interfaces=[],
    )

    pages = render_pages(snapshot, 20, 4)

    assert len(pages[0].lines[1]) > 20
