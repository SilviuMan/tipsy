import json
from pathlib import Path
from typing import Dict, List, Set


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECIPES_FILE = DATA_DIR / "recipes.json"


class RecipeStore:
    def __init__(self, recipes_file: Path = RECIPES_FILE):
        self.recipes_file = recipes_file
        self._recipes: List[Dict] = []
        self.load()

    def load(self) -> List[Dict]:
        with self.recipes_file.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self._recipes = payload.get("cocktails", [])
        return self._recipes

    @property
    def recipes(self) -> List[Dict]:
        return self._recipes

    def get_recipe_by_id(self, recipe_id: str) -> Dict:
        for recipe in self._recipes:
            if recipe.get("id") == recipe_id:
                return recipe
        raise KeyError(f"Recipe '{recipe_id}' not found")

    def get_all_ingredients(self) -> Set[str]:
        ingredients: Set[str] = set()
        for recipe in self._recipes:
            for step in recipe.get("steps", []):
                ingredient = step.get("ingredient")
                if ingredient:
                    ingredients.add(ingredient)
        return ingredients
