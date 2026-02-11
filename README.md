# CocktailBot (Raspberry Pi 4 + Waveshare 5" 1080×1080 Round Touch)

Touch UI cocktail maker that:
- Shows a carousel of cocktails
- Enables only cocktails whose required ingredients are mapped to pumps
- Runs pumps sequentially (one at a time) by timed pours
- Has a big red STOP button to immediately stop all pumps

## Hardware
- Raspberry Pi 4
- Waveshare 5inch 1080×1080 LCD (HDMI + USB touch)
- 10x Peristaltic pumps (6V)
- 10x F5305S MOSFET PWM switch modules (one per pump)
- 6V pump power supply (separate from Raspberry Pi power)
- (Recommended) Flyback diode per pump + bulk capacitor on 6V rail

## Display setup (Waveshare 1080×1080)
Edit `/boot/config.txt` and add:

hdmi_group=2
hdmi_mode=87
hdmi_pixel_freq_limit=356000000
hdmi_timings=1080 0 68 32 100 1080 0 12 4 16 0 0 0 60 0 85500000 0

Connect:
- HDMI -> display
- USB (touch) -> Raspberry Pi USB
- Power display via 5V Type-C

## Pump wiring (F5305S module)
Each pump uses one MOSFET switch module.

Load/pump side:
- Pump PSU +6V -> DC+
- Pump PSU GND -> DC-
- Pump + -> OUT+
- Pump - -> OUT-

Control side:
- Pi GPIO -> IN+
- Pi GND -> IN-

Recommended:
- Flyback diode across each pump motor (stripe to pump +)

## GPIO mapping (BCM numbering)
Pump 1: GPIO5  (Pin 29)
Pump 2: GPIO6  (Pin 31)
Pump 3: GPIO13 (Pin 33)
Pump 4: GPIO19 (Pin 35)
Pump 5: GPIO26 (Pin 37)
Pump 6: GPIO16 (Pin 36)
Pump 7: GPIO20 (Pin 38)
Pump 8: GPIO21 (Pin 40)
Pump 9: GPIO12 (Pin 32)
Pump10: GPIO25 (Pin 22)

## Install (Raspberry Pi OS Desktop)
sudo apt update
sudo apt install -y python3-venv python3-pip git \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

mkdir -p ~/cocktailbot
cd ~/cocktailbot
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install kivy gpiozero pillow

## Run
source ~/cocktailbot/.venv/bin/activate
python ~/cocktailbot/main.py

## Configuration
### Recipes
Recipes are stored in `data/recipes.json`:
- name
- image path (fallback image used if missing)
- steps: ingredient + ml

### Pump config
`data/pumps.json`:
- pump id
- gpio (BCM)
- ingredient assigned
- ml_per_sec (calibration value)

## Calibration
You MUST calibrate ml_per_sec per pump:
- Put tube into measuring cylinder
- Run pump for 10 seconds
- Measure ml output
- ml_per_sec = ml / 10
Save into pumps.json

## Safety
- App forces all pumps OFF at startup and on exit
- STOP button immediately stops all pumps and aborts recipe
- Only one pump runs at a time by design
