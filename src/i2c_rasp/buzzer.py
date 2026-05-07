from __future__ import annotations

from i2c_rasp.config import BuzzerConfig


class Buzzer:
    def on(self) -> None:
        return

    def off(self) -> None:
        return

    def close(self) -> None:
        return


class ReleasedGpioBuzzer(Buzzer):
    """Keep the buzzer GPIO as a floating input without driving low or high."""

    def __init__(self, config: BuzzerConfig) -> None:
        self._gpio_pin = config.gpio_pin
        self._release_device = None
        self.off()

    def on(self) -> None:
        self.off()

    def off(self) -> None:
        self._ensure_released()

    def close(self) -> None:
        self._close_release_device()

    def _ensure_released(self) -> None:
        if self._release_device is not None:
            return

        from gpiozero import DigitalInputDevice

        self._release_device = DigitalInputDevice(
            self._gpio_pin,
            pull_up=None,
            active_state=False,
        )

    def _close_release_device(self) -> None:
        if self._release_device is None:
            return
        self._release_device.close()
        self._release_device = None


class GpioBuzzer(Buzzer):
    def __init__(self, config: BuzzerConfig) -> None:
        self._config = config
        self._buzzer = None
        self._is_primed_off = False
        self._on_value = config.duty_cycle if config.mode == "pwm" else None

    def on(self) -> None:
        self._ensure_device()
        self._is_primed_off = False
        if self._on_value is None:
            self._buzzer.on()
            return
        self._buzzer.value = self._on_value

    def off(self) -> None:
        if self._buzzer is None and self._is_primed_off:
            return
        self._ensure_device()
        self._close_output_device()
        self._is_primed_off = True

    def close(self) -> None:
        self._close_output_device()
        self._is_primed_off = False

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

    def _close_output_device(self) -> None:
        if self._buzzer is None:
            return
        self._buzzer.off()
        self._buzzer.close()
        self._buzzer = None


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
                f"{config.gpio_pin} sera mantido como entrada flutuante/alta impedancia.",
                flush=True,
            )
            return ReleasedGpioBuzzer(config)

        print(
            "Buzzer habilitado: "
            f"GPIO={config.gpio_pin}, mode={config.mode}, active_high={config.active_high}. "
            "O GPIO e desligado no start e so e reaberto durante pulsos.",
            flush=True,
        )
        return GpioBuzzer(config)
    except Exception as exc:
        print(f"Buzzer indisponivel ({exc}); seguindo sem alarme sonoro.", flush=True)
        return Buzzer()
