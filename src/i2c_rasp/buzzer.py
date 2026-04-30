from __future__ import annotations

from i2c_rasp.config import BuzzerConfig


class Buzzer:
    def on(self) -> None:
        return

    def off(self) -> None:
        return

    def close(self) -> None:
        return


class GpioBuzzer(Buzzer):
    def __init__(self, pin: int) -> None:
        from gpiozero import Buzzer as GpioZeroBuzzer

        self._buzzer = GpioZeroBuzzer(pin)

    def on(self) -> None:
        self._buzzer.on()

    def off(self) -> None:
        self._buzzer.off()

    def close(self) -> None:
        self._buzzer.close()


def build_buzzer(config: BuzzerConfig) -> Buzzer:
    if not config.enabled:
        return Buzzer()

    try:
        return GpioBuzzer(config.gpio_pin)
    except Exception as exc:
        print(f"Buzzer indisponivel ({exc}); seguindo sem alarme sonoro.", flush=True)
        return Buzzer()
