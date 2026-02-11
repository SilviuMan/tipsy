from typing import Dict, List, Tuple


def is_recipe_available(recipe: Dict, ingredient_to_pump: Dict[str, Dict]) -> bool:
    for step in recipe.get("steps", []):
        ingredient = step.get("ingredient")
        if ingredient not in ingredient_to_pump:
            return False
    return True


def sort_recipes_by_availability(recipes: List[Dict], ingredient_to_pump: Dict[str, Dict]) -> List[Tuple[Dict, bool]]:
    with_flag = [(recipe, is_recipe_available(recipe, ingredient_to_pump)) for recipe in recipes]
    with_flag.sort(key=lambda item: (not item[1], item[0].get("name", "")))
    return with_flag
