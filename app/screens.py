from functools import partial
from typing import List, Optional

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from core.availability import sort_recipes_by_availability


class HeaderBar(BoxLayout):
    home_disabled = BooleanProperty(False)
    settings_disabled = BooleanProperty(False)


class CocktailCard(BoxLayout):
    recipe_id = StringProperty("")
    recipe_name = StringProperty("")
    image_path = StringProperty("")
    available = BooleanProperty(True)


class HomeScreen(Screen):
    selected_recipe_id = StringProperty("")
    selected_recipe_name = StringProperty("")
    selected_available = BooleanProperty(False)
    recipes_ui = ListProperty([])

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = self.manager.app
        ingredient_map = app.pump_store.ingredient_to_pump()
        recipes = sort_recipes_by_availability(app.recipe_store.recipes, ingredient_map)
        self.recipes_ui = [
            {
                "id": r[0]["id"],
                "name": r[0]["name"],
                "image": r[0].get("image", "atlas://data/images/defaulttheme/button"),
                "available": r[1],
            }
            for r in recipes
        ]
        carousel = self.ids.cocktail_carousel
        carousel.clear_widgets()
        for item in self.recipes_ui:
            card = CocktailCard(
                recipe_id=item["id"],
                recipe_name=item["name"],
                image_path=item["image"],
                available=item["available"],
            )
            carousel.add_widget(card)
        if self.recipes_ui:
            carousel.index = 0
            self.select_by_index(0)

    def select_by_index(self, idx: int):
        if idx < 0 or idx >= len(self.recipes_ui):
            return
        item = self.recipes_ui[idx]
        self.selected_recipe_id = item["id"]
        self.selected_recipe_name = item["name"]
        self.selected_available = item["available"]

    def on_carousel_index(self, index: int):
        self.select_by_index(index)

    def prepare_selected(self):
        if not self.selected_recipe_id or not self.selected_available:
            return
        app = self.manager.app
        recipe = app.recipe_store.get_recipe_by_id(self.selected_recipe_id)
        app.start_pour(recipe)


class IngredientPickerModal(ModalView):
    def __init__(self, ingredients: List[str], on_pick, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = True
        self.on_pick = on_pick
        self.ingredients = sorted(ingredients)

        root = BoxLayout(orientation="vertical", spacing=8, padding=8)
        self.search = TextInput(hint_text="Search ingredient", size_hint_y=None, height=50)
        self.search.bind(text=lambda *_: self.render_list())
        root.add_widget(self.search)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)

        none_btn = Button(text="Clear assignment", size_hint_y=None, height=60)
        none_btn.bind(on_release=lambda *_: self.pick(None))
        root.add_widget(none_btn)

        self.add_widget(root)
        self.render_list()

    def render_list(self):
        term = self.search.text.lower().strip()
        self.list_box.clear_widgets()
        for ingredient in self.ingredients:
            if term and term not in ingredient.lower():
                continue
            btn = Button(text=ingredient, size_hint_y=None, height=60)
            btn.bind(on_release=partial(self._pick_button, ingredient))
            self.list_box.add_widget(btn)

    def _pick_button(self, ingredient, *_):
        self.pick(ingredient)

    def pick(self, ingredient: Optional[str]):
        self.on_pick(ingredient)
        self.dismiss()


class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        container = self.ids.pump_list
        container.clear_widgets()
        app = self.manager.app

        open_calib = Button(text="Open Calibration", size_hint_y=None, height=90)
        open_calib.bind(on_release=lambda *_: self.manager.app.show_calibration())
        container.add_widget(open_calib)

        for pump in app.pump_store.pumps:
            row = BoxLayout(size_hint_y=None, height=90, spacing=8)
            ingredient = pump.get("ingredient") or "<unassigned>"
            label = Label(text=f"Pump {pump['id']} (GPIO {pump['gpio']}): {ingredient}", halign="left", valign="middle")
            label.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
            btn = Button(text="Assign", size_hint_x=None, width=160)
            btn.bind(on_release=partial(self.open_picker, pump["id"]))
            row.add_widget(label)
            row.add_widget(btn)
            container.add_widget(row)

    def open_picker(self, pump_id: int, *_):
        app = self.manager.app
        ingredients = list(app.recipe_store.get_all_ingredients())

        def on_pick(ingredient):
            app.pump_store.set_ingredient(pump_id, ingredient)
            self.refresh()
            app.refresh_home()

        IngredientPickerModal(ingredients, on_pick).open()


class CalibrationScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        container = self.ids.calibration_list
        container.clear_widgets()
        app = self.manager.app
        for pump in app.pump_store.pumps:
            row = BoxLayout(size_hint_y=None, height=120, spacing=8)
            info = Label(
                text=f"Pump {pump['id']} GPIO {pump['gpio']} | Ingredient: {pump.get('ingredient') or '<unassigned>'} | ml/s: {pump.get('ml_per_sec', 0):.2f}",
                halign="left",
                valign="middle",
            )
            info.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))

            prime_btn = Button(text="Prime 2s", size_hint_x=None, width=150)
            prime_btn.bind(on_release=partial(self.prime, pump["id"]))

            measure_input = TextInput(hint_text="ml in 10s", multiline=False, input_filter="float", size_hint_x=None, width=150)
            save_btn = Button(text="Save ml/s", size_hint_x=None, width=150)
            save_btn.bind(on_release=partial(self.save_calibration, pump["id"], measure_input))

            row.add_widget(info)
            row.add_widget(prime_btn)
            row.add_widget(measure_input)
            row.add_widget(save_btn)
            container.add_widget(row)

    def prime(self, pump_id: int, *_):
        app = self.manager.app
        app.pour_manager.stop()

        def do_prime(_dt):
            try:
                app.pump_driver.start(pump_id)
                Clock.schedule_once(lambda *_: app.pump_driver.stop(pump_id), 2)
            except Exception as exc:
                app.show_error(f"Prime failed: {exc}")

        Clock.schedule_once(do_prime, 0)

    def save_calibration(self, pump_id: int, measure_input: TextInput, *_):
        text = measure_input.text.strip()
        if not text:
            return
        ml_in_10s = float(text)
        ml_per_sec = ml_in_10s / 10.0
        self.manager.app.pump_store.set_ml_per_sec(pump_id, ml_per_sec)
        self.refresh()


class PouringScreen(Screen):
    status_text = StringProperty("Ready")
    progress_text = StringProperty("0/0")

    def set_step(self, ingredient: str, step: int, total: int):
        self.status_text = f"Pumping: {ingredient}"
        self.progress_text = f"Step {step}/{total}"

    def confirm_stop(self):
        app = self.manager.app
        app.stop_pour()
        popup = Popup(
            title="Stopped",
            content=Button(text="Back to Home", on_release=lambda *_: self._close_and_home()),
            size_hint=(0.6, 0.4),
        )
        self._stop_popup = popup
        popup.open()

    def _close_and_home(self):
        if hasattr(self, "_stop_popup"):
            self._stop_popup.dismiss()
        self.manager.app.go_home()


class DoneScreen(Screen):
    pass
