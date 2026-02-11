from functools import partial
from pathlib import Path
from time import monotonic
from typing import Dict, List, Optional

from kivy.app import App
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
    home_icon_url = StringProperty("assets/icons/home.png")
    settings_icon_url = StringProperty("assets/icons/settings.png")

    def go_home(self):
        app = App.get_running_app()
        if app and hasattr(app, "go_home"):
            app.go_home()

    def go_settings(self):
        app = App.get_running_app()
        if app and hasattr(app, "go_settings"):
            app.go_settings()


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
                "image": self.resolve_image_source(r[0].get("image")),
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

    def resolve_image_source(self, image_source: Optional[str]) -> str:
        fallback = "atlas://data/images/defaulttheme/button"
        if not image_source:
            return fallback

        if image_source.startswith(("atlas://", "http://", "https://")):
            return image_source

        return image_source if Path(image_source).exists() else fallback

    def select_by_index(self, idx: Optional[int]):
        if idx is None:
            return
        if idx < 0 or idx >= len(self.recipes_ui):
            return
        item = self.recipes_ui[idx]
        self.selected_recipe_id = item["id"]
        self.selected_recipe_name = item["name"]
        self.selected_available = item["available"]

    def on_carousel_index(self, index: Optional[int]):
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._manual_started_at: Dict[int, float] = {}
        self._manual_elapsed_s: Dict[int, float] = {}
        self._manual_buttons: Dict[int, Button] = {}

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        container = self.ids.calibration_list
        container.clear_widgets()
        app = self.manager.app
        for pump in app.pump_store.pumps:
            panel = BoxLayout(orientation="vertical", size_hint_y=None, height=210, spacing=6)

            info = Label(
                text=f"Pump {pump['id']} GPIO {pump['gpio']} | Ingredient: {pump.get('ingredient') or '<unassigned>'} | ml/s: {pump.get('ml_per_sec', 0):.2f}",
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=42,
            )
            info.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))

            controls = BoxLayout(size_hint_y=None, height=80, spacing=8)
            prime_btn = Button(text="Prime 2s", size_hint_x=None, width=120)
            prime_btn.bind(on_release=partial(self.prime, pump["id"]))

            auto_10s_btn = Button(text="Run 10s", size_hint_x=None, width=120)
            auto_10s_btn.bind(on_release=partial(self.run_ten_seconds, pump["id"]))

            hold_btn = Button(text="Hold for Manual", size_hint_x=None, width=180)
            hold_btn.bind(on_press=partial(self.manual_start, pump["id"]))
            hold_btn.bind(on_release=partial(self.manual_stop, pump["id"]))
            self._manual_buttons[pump["id"]] = hold_btn

            manual_save_btn = Button(text="Save 100ml", size_hint_x=None, width=120)
            manual_save_btn.bind(on_release=partial(self.save_manual_100ml, pump["id"]))

            controls.add_widget(prime_btn)
            controls.add_widget(auto_10s_btn)
            controls.add_widget(hold_btn)
            controls.add_widget(manual_save_btn)

            measure_row = BoxLayout(size_hint_y=None, height=70, spacing=8)
            measure_input = TextInput(hint_text="ml measured in 10s", multiline=False, input_filter="float")
            save_btn = Button(text="Save from 10s", size_hint_x=None, width=170)
            save_btn.bind(on_release=partial(self.save_calibration, pump["id"], measure_input))
            measure_row.add_widget(measure_input)
            measure_row.add_widget(save_btn)

            status = Label(
                text="Manual 100ml: not measured yet",
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=32,
            )
            status.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
            status_id = f"manual_status_{pump['id']}"
            setattr(self, status_id, status)

            panel.add_widget(info)
            panel.add_widget(controls)
            panel.add_widget(measure_row)
            panel.add_widget(status)
            container.add_widget(panel)

    def _status_label(self, pump_id: int) -> Label:
        return getattr(self, f"manual_status_{pump_id}")

    def prime(self, pump_id: int, *_):
        app = self.manager.app
        app.pour_manager.stop()

        try:
            app.pump_driver.start(pump_id)
            Clock.schedule_once(lambda *_: app.pump_driver.stop(pump_id), 2)
        except Exception as exc:
            app.show_error(f"Prime failed: {exc}")

    def run_ten_seconds(self, pump_id: int, *_):
        app = self.manager.app
        app.pour_manager.stop()
        status = self._status_label(pump_id)
        status.text = "Auto run: pumping for 10 seconds..."
        try:
            app.pump_driver.start(pump_id)
            Clock.schedule_once(lambda *_: self._finish_ten_seconds(pump_id), 10)
        except Exception as exc:
            app.show_error(f"10s calibration failed: {exc}")

    def _finish_ten_seconds(self, pump_id: int):
        self.manager.app.pump_driver.stop(pump_id)
        status = self._status_label(pump_id)
        status.text = "Auto run complete: measure ml dispensed and use 'Save from 10s'."

    def manual_start(self, pump_id: int, *_):
        app = self.manager.app
        app.pour_manager.stop()
        self._manual_started_at[pump_id] = monotonic()
        btn = self._manual_buttons.get(pump_id)
        if btn:
            btn.text = "Release to Stop"
        status = self._status_label(pump_id)
        status.text = "Manual run: pumping... release button at 100ml."
        try:
            app.pump_driver.start(pump_id)
        except Exception as exc:
            app.show_error(f"Manual calibration start failed: {exc}")

    def manual_stop(self, pump_id: int, *_):
        app = self.manager.app
        start = self._manual_started_at.pop(pump_id, None)
        app.pump_driver.stop(pump_id)

        btn = self._manual_buttons.get(pump_id)
        if btn:
            btn.text = "Hold for Manual"

        if start is None:
            return

        elapsed = max(monotonic() - start, 0.01)
        self._manual_elapsed_s[pump_id] = elapsed
        ml_per_sec = 100.0 / elapsed
        status = self._status_label(pump_id)
        status.text = f"Manual 100ml time: {elapsed:.2f}s (est {ml_per_sec:.2f} ml/s). Tap Save 100ml."

    def save_manual_100ml(self, pump_id: int, *_):
        elapsed = self._manual_elapsed_s.get(pump_id)
        if not elapsed:
            self._status_label(pump_id).text = "No manual run recorded yet for this pump."
            return

        ml_per_sec = 100.0 / elapsed
        self.manager.app.pump_store.set_ml_per_sec(pump_id, ml_per_sec)
        self._status_label(pump_id).text = f"Saved manual calibration: {ml_per_sec:.2f} ml/s"
        self.refresh()

    def save_calibration(self, pump_id: int, measure_input: TextInput, *_):
        text = measure_input.text.strip()
        if not text:
            return
        ml_in_10s = float(text)
        ml_per_sec = ml_in_10s / 10.0
        self.manager.app.pump_store.set_ml_per_sec(pump_id, ml_per_sec)
        self._status_label(pump_id).text = f"Saved 10s calibration: {ml_per_sec:.2f} ml/s"
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
