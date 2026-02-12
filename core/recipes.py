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
        self._recipes = self._extract_recipes(payload)
        return self._recipes

    @staticmethod
    def _extract_recipes(payload) -> List[Dict]:
        if isinstance(payload, list):
            return [recipe for recipe in payload if isinstance(recipe, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("cocktails", "recipes", "drinks"):
            recipes = payload.get(key)
            if isinstance(recipes, list):
                return [recipe for recipe in recipes if isinstance(recipe, dict)]

        return []

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
            for ingredient in self._iter_recipe_ingredients(recipe):
                if ingredient:
                    ingredients.add(ingredient)
        return ingredients

    def _iter_recipe_ingredients(self, recipe: Dict):
        for step in recipe.get("steps", []):
            ingredient = step.get("ingredient")
            if ingredient:
                yield ingredient

        raw_ingredients = recipe.get("ingredients", [])
        if isinstance(raw_ingredients, dict):
            for ingredient in raw_ingredients.keys():
                if ingredient:
                    yield ingredient
            return

        if isinstance(raw_ingredients, list):
            for item in raw_ingredients:
                if isinstance(item, str) and item:
                    yield item
                elif isinstance(item, dict):
                    ingredient = item.get("ingredient") or item.get("name")
                    if ingredient:
                        yield ingredient
