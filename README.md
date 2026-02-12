# CocktailBot (Raspberry Pi + Kivy)
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
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

## Install Python and project packages (Raspberry Pi)

### 1) Install Python + system packages
```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv python3-kivy \
  xserver-xorg x11-xserver-utils
```

### 2) Create a virtual environment (recommended)
Run these commands from your project folder on Raspberry Pi OS (for example `~/tipsy`):
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install gpiozero
```

### 3) Start the app
```bash
source .venv/bin/activate
python main.py
```

If you do not want a virtual environment, install directly with:
```bash
pip3 install --user gpiozero
```

## Make a clickable executable

You have two practical options on Raspberry Pi.

### Option A (recommended): Desktop launcher that runs the app
Create a launcher script:
```bash
cat > ~/Desktop/run-cocktailbot.sh << 'EOF'
#!/usr/bin/env bash
cd ~/tipsy
source .venv/bin/activate
python main.py
EOF
chmod +x ~/Desktop/run-cocktailbot.sh
```

Create a clickable desktop icon:
```bash
cat > ~/Desktop/CocktailBot.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=CocktailBot
Comment=Start CocktailBot
Exec=/home/pi/Desktop/run-cocktailbot.sh
Terminal=false
Path=/home/pi/tipsy
Icon=utilities-terminal
EOF
chmod +x ~/Desktop/CocktailBot.desktop
```

> If your username or project folder is different, update both `Exec=` and `Path=` in the `.desktop` file.

### Option B: Build a single-file binary with PyInstaller
```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --onefile --name cocktailbot main.py
```

Binary output will be in `dist/cocktailbot`.

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
3. Use one of two methods:
   - **Run 10s**: pump runs automatically for 10 seconds, then enter measured ml and tap **Save from 10s**.
   - **Hold for Manual**: press and hold while liquid fills your measuring cup to 100 ml, then release and tap **Save 100ml**.
4. Saved calibration writes `ml_per_sec` into `data/pumps.json`, so values persist after reboot/app restart.

## Safety behavior
- App initializes with all pumps OFF.
- STOP immediately calls `stop_all()` and aborts recipe.
- Any pour exception triggers watchdog stop and an error popup.
- App stops all pumps on shutdown/exit.


## Media sources
- Cocktail images are loaded from local files in `assets/cocktails/` (for example `assets/cocktails/whisky_cola.png`).
- Header icons are loaded from local files in `assets/icons/` (`home.png`, `settings.png`).
- If an image file is missing, the app falls back to a built-in Kivy atlas image.
