import sys
from types import ModuleType

from i2c_rasp import cli
from i2c_rasp.config import BuzzerConfig


class FakeSink:
    def __init__(self):
        self.calls = []

    def show_page(self, page, flash=False, frame=0):
        self.calls.append((tuple(page), flash))


class FakeBuzzer:
    def __init__(self):
        self.on_count = 0
        self.off_count = 0
        self.events = []

    def on(self):
        self.on_count += 1
        self.events.append("on")

    def off(self):
        self.off_count += 1
        self.events.append("off")


def test_show_page_with_alert_keeps_buzzer_on_while_blinking(monkeypatch):
    sink = FakeSink()
    buzzer = FakeBuzzer()
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(cli, "sleep", fake_sleep)

    cli._show_page_with_alert(sink, buzzer, ["a"], alert=True, page_seconds=1.0, once=False)

    assert buzzer.on_count == 1
    assert buzzer.off_count == 1
    assert buzzer.events == ["on", "off"]
    assert len(sink.calls) >= 4
    assert sink.calls[0][1] is True
    assert any(flash is False for _, flash in sink.calls)
    assert sum(sleeps) == 2.0


def test_show_page_with_alert_once_does_not_sleep():
    sink = FakeSink()
    buzzer = FakeBuzzer()

    cli._show_page_with_alert(sink, buzzer, ["a"], alert=True, page_seconds=1.0, once=True)

    assert sink.calls == [(("a",), True)]
    assert buzzer.on_count == 1
    assert buzzer.off_count == 1


def test_show_page_without_alert_forces_buzzer_off(monkeypatch):
    sink = FakeSink()
    buzzer = FakeBuzzer()
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(cli, "sleep", fake_sleep)

    cli._show_page_with_alert(sink, buzzer, ["ok"], alert=False, page_seconds=1.0, once=False)

    assert buzzer.on_count == 0
    assert buzzer.off_count == 1
    assert sink.calls == [
        (("ok",), False),
        (("ok",), False),
        (("ok",), False),
        (("ok",), False),
    ]
    assert sum(sleeps) == 1.0


def test_show_page_without_alert_once_forces_buzzer_off():
    sink = FakeSink()
    buzzer = FakeBuzzer()

    cli._show_page_with_alert(sink, buzzer, ["ok"], alert=False, page_seconds=1.0, once=True)

    assert sink.calls == [(("ok",), False)]
    assert buzzer.on_count == 0
    assert buzzer.off_count == 1


def test_buzzer_debug_off_holds_buzzer_off(monkeypatch):
    buzzer = FakeBuzzer()
    sleeps = []
    monkeypatch.setattr(cli, "sleep", sleeps.append)

    cli._run_buzzer_debug_action(buzzer, "off", 1.5)

    assert buzzer.events == ["off"]
    assert sleeps == [1.5]


def test_buzzer_debug_on_turns_buzzer_on_for_duration(monkeypatch):
    buzzer = FakeBuzzer()
    sleeps = []
    monkeypatch.setattr(cli, "sleep", sleeps.append)

    cli._run_buzzer_debug_action(buzzer, "on", 2.0)

    assert buzzer.events == ["on"]
    assert sleeps == [2.0]


def test_buzzer_debug_pulse_toggles_and_finishes_off(monkeypatch):
    buzzer = FakeBuzzer()
    sleeps = []
    monkeypatch.setattr(cli, "sleep", sleeps.append)

    cli._run_buzzer_debug_action(buzzer, "pulse", 1.25)

    assert buzzer.events == ["on", "off", "on", "off"]
    assert sleeps == [0.5, 0.5, 0.25]


def test_buzzer_debug_forces_enabled_only_for_audible_tests(monkeypatch):
    built_configs = []

    class DebugBuzzer(FakeBuzzer):
        def close(self):
            self.events.append("close")

    def fake_build_buzzer(config):
        built_configs.append(config)
        return DebugBuzzer()

    monkeypatch.setattr(cli, "build_buzzer", fake_build_buzzer)
    monkeypatch.setattr(cli, "sleep", lambda seconds: None)

    cli._run_buzzer_debug(BuzzerConfig(enabled=False), "off", 0)
    cli._run_buzzer_debug(BuzzerConfig(enabled=False), "on", 0)

    assert [config.enabled for config in built_configs] == [False, True]


def test_buzzer_raw_debug_drives_physical_level_and_closes(monkeypatch):
    devices = []

    class FakeRawOutputDevice:
        def __init__(self, pin, active_high=True, initial_value=False):
            self.pin = pin
            self.active_high = active_high
            self.initial_value = initial_value
            self.value = initial_value
            self.close_count = 0
            devices.append(self)

        def close(self):
            self.close_count += 1

    module = ModuleType("gpiozero")
    module.DigitalOutputDevice = FakeRawOutputDevice
    monkeypatch.setitem(sys.modules, "gpiozero", module)
    sleeps = []
    monkeypatch.setattr(cli, "sleep", sleeps.append)

    cli._run_buzzer_raw_debug(18, high=False, seconds=2.0)
    cli._run_buzzer_raw_debug(18, high=True, seconds=3.0)

    assert [(device.pin, device.active_high, device.initial_value, device.value) for device in devices] == [
        (18, True, False, 0),
        (18, True, True, 1),
    ]
    assert [device.close_count for device in devices] == [1, 1]
    assert sleeps == [2.0, 3.0]


def test_buzzer_debug_raw_actions_skip_normal_buzzer_builder(monkeypatch):
    raw_calls = []

    def fake_raw_debug(gpio_pin, high, seconds):
        raw_calls.append((gpio_pin, high, seconds))

    def fail_build_buzzer(config):
        raise AssertionError("raw debug must not use build_buzzer")

    monkeypatch.setattr(cli, "_run_buzzer_raw_debug", fake_raw_debug)
    monkeypatch.setattr(cli, "build_buzzer", fail_build_buzzer)

    cli._run_buzzer_debug(BuzzerConfig(gpio_pin=24), "raw-low", 4.0)
    cli._run_buzzer_debug(BuzzerConfig(gpio_pin=24), "raw-high", 5.0)

    assert raw_calls == [(24, False, 4.0), (24, True, 5.0)]


def test_buzzer_debug_pin_override_replaces_config_pin(monkeypatch):
    built_configs = []

    class DebugBuzzer(FakeBuzzer):
        def close(self):
            self.events.append("close")

    def fake_build_buzzer(config):
        built_configs.append(config)
        return DebugBuzzer()

    monkeypatch.setattr(cli, "build_buzzer", fake_build_buzzer)
    monkeypatch.setattr(cli, "sleep", lambda seconds: None)

    cli._run_buzzer_debug(BuzzerConfig(gpio_pin=18), "on", 0, gpio_pin=24)

    assert built_configs[0].gpio_pin == 24


def test_buzzer_debug_pin_override_applies_to_raw_debug(monkeypatch):
    raw_calls = []
    monkeypatch.setattr(cli, "_run_buzzer_raw_debug", lambda *args: raw_calls.append(args))

    cli._run_buzzer_debug(BuzzerConfig(gpio_pin=18), "raw-low", 1.0, gpio_pin=24)

    assert raw_calls == [(24, False, 1.0)]
