import threading
import time
from typing import Callable, Dict, List, Optional

from hardware.pump_driver import PumpDriver


class PourManager:
    def __init__(self, pump_driver: PumpDriver):
        self.pump_driver = pump_driver
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def stop(self) -> None:
        self.stop_event.set()
        self.pump_driver.stop_all()

    def _sleep_interruptible(self, seconds: float) -> bool:
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self.stop_event.is_set():
                return False
            time.sleep(0.05)
        return True

    def run_recipe(
        self,
        recipe: Dict,
        ingredient_to_pump: Dict[str, Dict],
        on_step: Callable[[str, int, int], None],
        on_done: Callable[[], None],
        on_stopped: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        if self.is_running():
            return

        self.stop_event.clear()

        def worker() -> None:
            try:
                steps: List[Dict] = recipe.get("steps", [])
                total = len(steps)
                for idx, step in enumerate(steps, start=1):
                    if self.stop_event.is_set():
                        self.pump_driver.stop_all()
                        on_stopped()
                        return

                    ingredient = step["ingredient"]
                    ml = float(step["ml"])
                    pump = ingredient_to_pump.get(ingredient)
                    if not pump:
                        raise RuntimeError(f"Ingredient '{ingredient}' is not assigned to a pump")

                    ml_per_sec = float(pump.get("ml_per_sec", 0))
                    if ml_per_sec <= 0:
                        raise RuntimeError(f"Invalid ml_per_sec for pump {pump['id']}")

                    duration = ml / ml_per_sec
                    on_step(ingredient, idx, total)
                    self.pump_driver.start(pump["id"])
                    completed = self._sleep_interruptible(duration)
                    self.pump_driver.stop(pump["id"])

                    if not completed or self.stop_event.is_set():
                        self.pump_driver.stop_all()
                        on_stopped()
                        return

                self.pump_driver.stop_all()
                on_done()
            except Exception as exc:
                self.pump_driver.stop_all()
                on_error(str(exc))

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()
