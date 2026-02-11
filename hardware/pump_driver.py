from typing import Dict

try:
    from gpiozero import OutputDevice
except Exception:  # pragma: no cover - dev fallback on non-RPi machines
    class OutputDevice:  # type: ignore
        def __init__(self, pin: int, initial_value: bool = False):
            self.pin = pin
            self.value = initial_value

        def on(self) -> None:
            self.value = True

        def off(self) -> None:
            self.value = False

        def close(self) -> None:
            self.off()


class PumpDriver:
    def __init__(self, pump_id_to_gpio: Dict[int, int]):
        self.devices: Dict[int, OutputDevice] = {
            pump_id: OutputDevice(gpio_pin, initial_value=False)
            for pump_id, gpio_pin in pump_id_to_gpio.items()
        }
        self.stop_all()

    def start(self, pump_id: int) -> None:
        self.stop_all()
        device = self.devices[pump_id]
        device.on()  # high = ON

    def stop(self, pump_id: int) -> None:
        device = self.devices[pump_id]
        device.off()  # low = OFF

    def stop_all(self) -> None:
        for device in self.devices.values():
            device.off()

    def close(self) -> None:
        self.stop_all()
        for device in self.devices.values():
            device.close()
