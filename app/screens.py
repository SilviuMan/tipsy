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
from kivy.uix.popup import Popup
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.metrics import dp

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

        image_path = Path(image_source)
        if image_path.is_absolute():
            return str(image_path) if image_path.exists() else fallback

        app = App.get_running_app()
        base_dir = Path(getattr(app, "base_dir", Path.cwd()))
        resolved = base_dir / image_path
        return str(resolved) if resolved.exists() else fallback

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


class IngredientRow(RecycleDataViewBehavior, ButtonBehavior, Label):
    ingredient = StringProperty("")
    popup = None
    drag_threshold = dp(12)

    def refresh_view_attrs(self, rv, index, data):
        self.ingredient = data.get("ingredient", "")
        self.text = self.ingredient
        self.popup = data.get("popup")
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_move(self, touch):
        if touch.grab_current is self and "ingredient_row_touch_start" in touch.ud:
            start_x, start_y = touch.ud["ingredient_row_touch_start"]
            if abs(touch.x - start_x) > self.drag_threshold or abs(touch.y - start_y) > self.drag_threshold:
                touch.ungrab(self)
                return False
        return Label.on_touch_move(self, touch)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.ud["ingredient_row_touch_start"] = touch.pos
        return super().on_touch_down(touch)

    def on_release(self):
        if self.popup:
            self.popup.pick(self.ingredient)


class IngredientPickerPopup(Popup):
    def __init__(self, ingredients: List[str], on_pick, **kwargs):
        super().__init__(**kwargs)
        self.title = "Assign ingredient to pump"
        self.size_hint = (0.75, 0.75)
        self.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.auto_dismiss = False
        self.on_pick = on_pick
        self.ingredients = sorted(ingredients)

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))

        self.search = TextInput(
            hint_text="Search ingredient",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
        )
        self.search.bind(text=lambda *_: self.render_list())
        root.add_widget(self.search)

        self.rv = RecycleView(bar_width=dp(8), scroll_type=["bars", "content"])
        self.rv.viewclass = "IngredientRow"
        lm = RecycleBoxLayout(
            default_size=(None, dp(56)),
            default_size_hint=(1, None),
            size_hint_y=None,
            spacing=dp(6),
            padding=(0, dp(4)),
            orientation="vertical",
        )
        lm.bind(minimum_height=lm.setter("height"))
        self.rv.add_widget(lm)
        self.rv.layout_manager = lm
        root.add_widget(self.rv)

        actions = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        clear_btn = Button(text="Clear")
        clear_btn.bind(on_release=lambda *_: self.pick(None))
        close_btn = Button(text="Close")
        close_btn.bind(on_release=lambda *_: self.dismiss())
        actions.add_widget(clear_btn)
        actions.add_widget(close_btn)
        root.add_widget(actions)

        self.content = root
        self.render_list()

    def render_list(self):
        term = self.search.text.lower().strip()
        self.rv.data = [
            {"ingredient": ingredient, "popup": self}
            for ingredient in self.ingredients
            if not term or term in ingredient.lower()
        ]

    def pick(self, ingredient: Optional[str]):
        self.on_pick(ingredient)
        self.dismiss()


class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh()

    def confirm_exit(self):
        app = self.manager.app
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text="Exit CocktailBot?\nPumps will be stopped safely."))
        actions = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        popup = Popup(
            title="Confirm Exit",
            size_hint=(0.62, 0.34),
            auto_dismiss=False,
        )
        cancel_btn = Button(text="Cancel")
        exit_btn = Button(text="Exit")
        cancel_btn.bind(on_release=lambda *_: popup.dismiss())

        def do_exit(*_):
            popup.dismiss()
            app.safe_shutdown()
            app.stop()

        exit_btn.bind(on_release=do_exit)
        actions.add_widget(cancel_btn)
        actions.add_widget(exit_btn)
        content.add_widget(actions)
        popup.content = content
        popup.open()

    def handle_row(self, pump_id: int, kind: str):
        if kind == "calibration":
            self.manager.app.show_calibration()
            return
        if kind == "exit":
            self.confirm_exit()
            return
        if kind == "pump" and pump_id >= 0:
            self.open_picker(pump_id)

    def refresh(self):
        app = self.manager.app
        rows = [
            {"pump_id": -1, "kind": "calibration", "text": "Open Calibration", "button_text": "Open"},
            {"pump_id": -2, "kind": "exit", "text": "Exit App", "button_text": "Exit"},
        ]

        for pump in app.pump_store.pumps:
            ingredient = pump.get("ingredient") or "<unassigned>"
            rows.append(
                {
                    "pump_id": pump["id"],
                    "kind": "pump",
                    "text": f"Pump {pump['id']} (GPIO {pump['gpio']}): {ingredient}",
                    "button_text": "Assign",
                }
            )

        self.ids.pump_rv.data = rows

    def open_picker(self, pump_id: int, *_):
        app = self.manager.app
        ingredients = list(app.recipe_store.get_all_ingredients())

        def on_pick(ingredient):
            app.pump_store.set_ingredient(pump_id, ingredient)
            self.refresh()
            app.refresh_home()

        IngredientPickerPopup(ingredients, on_pick).open()


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
