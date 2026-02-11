# CocktailBot (Raspberry Pi + Kivy)

CocktailBot is a 1080x1080 touch UI for a round display and 10 peristaltic pumps.

## Features
- Kivy touchscreen UI with circular-safe layout and black corner masking.
- Home, Settings, Calibration, Pouring, and Done screens.
- Recipe availability detection based on assigned ingredients.
- One-pump-at-a-time sequential pouring (safety-focused).
- Immediate STOP with pump shutdown event.
- Watchdog error handling in pour manager (`stop_all()` on exception).
- Pump calibration utility (prime 2s + ml/s calculation from 10-second measurement).

## GPIO mapping (BCM)
- Pump 1 -> GPIO5
- Pump 2 -> GPIO6
- Pump 3 -> GPIO13
- Pump 4 -> GPIO19
- Pump 5 -> GPIO26
- Pump 6 -> GPIO16
- Pump 7 -> GPIO20
- Pump 8 -> GPIO21
- Pump 9 -> GPIO12
- Pump 10 -> GPIO25

Each GPIO drives an opto-isolated F5305S MOSFET module. Pump ON means GPIO HIGH.

## Wiring
1. Power each pump from an external pump PSU according to your MOSFET board specs.
2. Common ground between Raspberry Pi GND and MOSFET control GND.
3. Connect each BCM pin listed above to the corresponding MOSFET input.
4. Use flyback-safe wiring and fusing appropriate for your pump current.

## Install
```bash
sudo apt update
sudo apt install -y python3-pip python3-kivy xserver-xorg x11-xserver-utils
pip3 install gpiozero
```

## Prevent screen blanking (required for kiosk mode)
Run once at session start (or autostart script):
```bash
xset s off
xset -dpms
xset s noblank
```
The app also attempts these commands on startup.

## Run
```bash
python3 main.py
```

## Data files
- `data/recipes.json` - cocktail definitions and ml steps.
- `data/pumps.json` - 10 pump GPIO, ingredient assignment, and `ml_per_sec`.

## Calibration workflow
1. Go to **Settings** -> **Open Calibration**.
2. For each pump, tap **Prime 2s** to fill tube.
3. Run pump manually for 10 seconds and measure dispensed ml.
4. Enter measured ml in the field and tap **Save ml/s**.
   - App stores `ml_per_sec = measured_ml / 10`.

## Safety behavior
- App initializes with all pumps OFF.
- STOP immediately calls `stop_all()` and aborts recipe.
- Any pour exception triggers watchdog stop and an error popup.
- App stops all pumps on shutdown/exit.


## Media sources
- Cocktail images are loaded from local files in `assets/cocktails/` (for example `assets/cocktails/whisky_cola.png`).
- Header icons are loaded from local files in `assets/icons/` (`home.png`, `settings.png`).
- If an image file is missing, the app falls back to a built-in Kivy atlas image.
