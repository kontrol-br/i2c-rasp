from __future__ import annotations

from i2c_rasp.config import BuzzerConfig


class Buzzer:
    def on(self) -> None:
        return

    def off(self) -> None:
        return

    def close(self) -> None:
        return


class DisabledGpioBuzzer(Buzzer):
    """Keep the configured GPIO in the inactive state without sounding alerts."""

    def __init__(self, config: BuzzerConfig) -> None:
        from gpiozero import DigitalOutputDevice

        self._device = DigitalOutputDevice(
            config.gpio_pin,
            active_high=config.active_high,
            initial_value=False,
        )
        self.off()

    def on(self) -> None:
        self.off()

    def off(self) -> None:
        self._device.off()

    def close(self) -> None:
        self.off()
        self._device.close()


class GpioBuzzer(Buzzer):
    def __init__(self, config: BuzzerConfig) -> None:
        self._config = config
        self._buzzer = None
        self._on_value = config.duty_cycle if config.mode == "pwm" else None
        self.off()

    def on(self) -> None:
        self._ensure_device()
        if self._on_value is None:
            self._buzzer.on()
            return
        self._buzzer.value = self._on_value

    def off(self) -> None:
        if self._buzzer is None:
            return
        self._buzzer.off()
        self._buzzer.close()
        self._buzzer = None

    def close(self) -> None:
        self.off()

    def _ensure_device(self) -> None:
        if self._buzzer is not None:
            return

        if self._config.mode == "pwm":
            self._buzzer = _build_pwm_buzzer(self._config)
            return

        from gpiozero import Buzzer as GpioZeroBuzzer

        self._buzzer = GpioZeroBuzzer(
            self._config.gpio_pin,
            active_high=self._config.active_high,
            initial_value=False,
        )


def _build_pwm_buzzer(config: BuzzerConfig):
    from gpiozero import PWMOutputDevice

    return PWMOutputDevice(
        config.gpio_pin,
        active_high=config.active_high,
        initial_value=0,
        frequency=config.frequency_hz,
    )


def build_buzzer(config: BuzzerConfig) -> Buzzer:
    try:
        if not config.enabled:
            print(
                "Buzzer desabilitado; GPIO "
                f"{config.gpio_pin} sera liberado/alta impedancia enquanto o servico roda.",
                flush=True,
            )
            return Buzzer()

        print(
            "Buzzer habilitado: "
            f"GPIO={config.gpio_pin}, mode={config.mode}, active_high={config.active_high}. "
            "O GPIO fica liberado quando o buzzer esta em off.",
            flush=True,
        )
        return GpioBuzzer(config)
    except Exception as exc:
        print(f"Buzzer indisponivel ({exc}); seguindo sem alarme sonoro.", flush=True)
        return Buzzer()
