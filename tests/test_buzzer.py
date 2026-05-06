import sys
from types import ModuleType

from i2c_rasp.buzzer import GpioBuzzer, build_buzzer
from i2c_rasp.config import BuzzerConfig


class FakeDigitalBuzzer:
    instances = []

    def __init__(self, pin, active_high=True, initial_value=False):
        self.pin = pin
        self.active_high = active_high
        self.initial_value = initial_value
        self.on_count = 0
        self.off_count = 0
        self.close_count = 0
        FakeDigitalBuzzer.instances.append(self)

    def on(self):
        self.on_count += 1

    def off(self):
        self.off_count += 1

    def close(self):
        self.close_count += 1


class FakePWMOutputDevice:
    instances = []

    def __init__(self, pin, active_high=True, initial_value=0, frequency=100):
        self.pin = pin
        self.active_high = active_high
        self.initial_value = initial_value
        self.frequency = frequency
        self.value = initial_value
        self.values = [initial_value]
        self.off_count = 0
        self.close_count = 0
        FakePWMOutputDevice.instances.append(self)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == "value" and hasattr(self, "values"):
            self.values.append(value)

    def off(self):
        self.off_count += 1
        self.value = 0

    def close(self):
        self.close_count += 1


def install_fake_gpiozero(monkeypatch):
    module = ModuleType("gpiozero")
    module.Buzzer = FakeDigitalBuzzer
    module.PWMOutputDevice = FakePWMOutputDevice
    monkeypatch.setitem(sys.modules, "gpiozero", module)


def test_gpio_buzzer_uses_bcm_pin_and_polarity_for_active_modules(monkeypatch):
    FakeDigitalBuzzer.instances.clear()
    install_fake_gpiozero(monkeypatch)

    buzzer = GpioBuzzer(BuzzerConfig(enabled=True, gpio_pin=24, active_high=False))
    buzzer.on()
    buzzer.off()
    buzzer.close()

    device = FakeDigitalBuzzer.instances[0]
    assert device.pin == 24
    assert device.active_high is False
    assert device.initial_value is False
    assert device.on_count == 1
    assert device.off_count == 1
    assert device.close_count == 1


def test_gpio_buzzer_pwm_mode_drives_passive_buzzers_with_tone(monkeypatch):
    FakePWMOutputDevice.instances.clear()
    install_fake_gpiozero(monkeypatch)

    buzzer = GpioBuzzer(
        BuzzerConfig(
            enabled=True,
            gpio_pin=18,
            mode="pwm",
            frequency_hz=2500,
            duty_cycle=0.25,
        )
    )
    buzzer.on()
    buzzer.off()
    buzzer.close()

    device = FakePWMOutputDevice.instances[0]
    assert device.pin == 18
    assert device.frequency == 2500
    assert device.values == [0, 0.25, 0]
    assert device.value == 0
    assert device.off_count == 1
    assert device.close_count == 1


def test_build_buzzer_disabled_returns_noop_buzzer():
    buzzer = build_buzzer(BuzzerConfig(enabled=False))

    assert type(buzzer).__name__ == "Buzzer"
