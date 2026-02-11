import json
from pathlib import Path
from typing import Dict, List, Optional


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PUMPS_FILE = DATA_DIR / "pumps.json"


class PumpStore:
    def __init__(self, pumps_file: Path = PUMPS_FILE):
        self.pumps_file = pumps_file
        self._data: Dict = {}
        self.load()

    def load(self) -> Dict:
        with self.pumps_file.open("r", encoding="utf-8") as fh:
            self._data = json.load(fh)
        return self._data

    def save(self) -> None:
        with self.pumps_file.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
            fh.write("\n")

    @property
    def pumps(self) -> List[Dict]:
        return self._data.get("pumps", [])

    def get_pump(self, pump_id: int) -> Dict:
        for pump in self.pumps:
            if pump.get("id") == pump_id:
                return pump
        raise KeyError(f"Pump '{pump_id}' not found")

    def set_ingredient(self, pump_id: int, ingredient: Optional[str]) -> None:
        pump = self.get_pump(pump_id)
        pump["ingredient"] = ingredient
        self.save()

    def set_ml_per_sec(self, pump_id: int, ml_per_sec: float) -> None:
        pump = self.get_pump(pump_id)
        pump["ml_per_sec"] = float(ml_per_sec)
        self.save()

    def ingredient_to_pump(self) -> Dict[str, Dict]:
        mapping: Dict[str, Dict] = {}
        for pump in self.pumps:
            ingredient = pump.get("ingredient")
            if ingredient:
                mapping[ingredient] = pump
        return mapping

    def pump_id_to_gpio(self) -> Dict[int, int]:
        return {pump["id"]: pump["gpio"] for pump in self.pumps}
