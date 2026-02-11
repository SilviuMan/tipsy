import atexit
import subprocess

from kivy.config import Config

Config.set("graphics", "width", "1080")
Config.set("graphics", "height", "1080")
Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager

from app.screens import CalibrationScreen, DoneScreen, HomeScreen, PouringScreen, SettingsScreen
from core.pumps import PumpStore
from core.recipes import RecipeStore
from hardware.pour_manager import PourManager
from hardware.pump_driver import PumpDriver


class CocktailBotApp(App):
    def build(self):
        self.title = "CocktailBot"
        self.recipe_store = RecipeStore()
        self.pump_store = PumpStore()
        self.pump_driver = PumpDriver(self.pump_store.pump_id_to_gpio())
        self.pour_manager = PourManager(self.pump_driver)

        atexit.register(self.safe_shutdown)
        self.prevent_screen_sleep()

        Builder.load_file("app/app.kv")

        self.sm = ScreenManager()
        self.sm.app = self
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(CalibrationScreen(name="calibration"))
        self.sm.add_widget(PouringScreen(name="pouring"))
        self.sm.add_widget(DoneScreen(name="done"))
        return self.sm

    def prevent_screen_sleep(self):
        commands = [
            ["xset", "s", "off"],
            ["xset", "-dpms"],
            ["xset", "s", "noblank"],
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, check=False)
            except Exception:
                pass

    def refresh_home(self):
        self.sm.get_screen("home").refresh()

    def go_home(self):
        self.sm.current = "home"
        self.refresh_home()

    def go_settings(self):
        self.sm.current = "settings"

    def show_calibration(self):
        self.sm.current = "calibration"

    def start_pour(self, recipe):
        self.sm.current = "pouring"
        pouring = self.sm.get_screen("pouring")
        pouring.status_text = "Starting..."
        pouring.progress_text = "0/0"

        ingredient_map = self.pump_store.ingredient_to_pump()

        self.pour_manager.run_recipe(
            recipe=recipe,
            ingredient_to_pump=ingredient_map,
            on_step=lambda ingredient, step, total: Clock.schedule_once(
                lambda *_: pouring.set_step(ingredient, step, total)
            ),
            on_done=lambda: Clock.schedule_once(lambda *_: self._go_done()),
            on_stopped=lambda: Clock.schedule_once(lambda *_: setattr(pouring, "status_text", "Stopped")),
            on_error=lambda err: Clock.schedule_once(lambda *_: self.show_error(f"Pour error: {err}")),
        )

    def stop_pour(self):
        self.pour_manager.stop()
        self.pump_driver.stop_all()

    def _go_done(self):
        self.sm.current = "done"

    def show_error(self, message: str):
        self.stop_pour()
        content = Popup(title="Error", size_hint=(0.8, 0.4))
        btn = Button(text=f"{message}\n\nTap to go Home")
        btn.bind(on_release=lambda *_: (content.dismiss(), self.go_home()))
        content.content = btn
        content.open()

    def on_stop(self):
        self.safe_shutdown()

    def safe_shutdown(self):
        try:
            self.pour_manager.stop()
        except Exception:
            pass
        try:
            self.pump_driver.stop_all()
        except Exception:
            pass
        try:
            self.pump_driver.close()
        except Exception:
            pass


if __name__ == "__main__":
    CocktailBotApp().run()
