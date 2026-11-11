# EVFCamera

A compact rangefinder-style digital camera built on a Raspberry Pi Zero 2 W and the Raspberry Pi HQ camera, with C/CS-mount lenses. You compose, review and change settings entirely through a 0.4" 1280×960 micro-OLED eye-level EVF.

## Hardware

| Part | Choice |
| --- | --- |
| Computer | Raspberry Pi Zero 2 W (hostname `EVFPi`) |
| Sensor | Raspberry Pi HQ camera (Sony IMX477) |
| Viewfinder | 0.4" 1280×960 HDMI micro-OLED, 12.5× eyepiece |
| Lenses | Fujinon-TV 9 mm f/1.4, 17 mm f/1.7 (C-mount) |
| Shutter | Alps SKRNPEE010 two-stage switch (bench: 6×6 tact switch) |
| Power | Adafruit bq25185 USB-C charger + 5 V boost, 1-cell Li-ion |
| Sensors | Deferred: MAX17048 fuel gauge, VCNL4040 eye sensor (I²C pins kept free) |

## Repository layout

| Folder | Contents |
| --- | --- |
| `bench/` | Standalone test scripts used while bringing up the hardware |
| `hardware/kicad/` | Footprints and PCB files |
| `docs/` | Roadmap and design notes |

| `evfcam/` | The camera app |
| `tests/` | Mode and control tests (run anywhere with the fake camera) |
| `tools/` | Helpers, e.g. `render_screens.py` draws every screen to PNG |

See [docs/roadmap.md](docs/roadmap.md) for the architecture and milestones.

## Setup on the Pi

Raspberry Pi OS Lite (64-bit), then:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo raspi-config nonint do_i2c 0
sudo apt install -y python3-picamera2 --no-install-recommends
sudo apt install -y rpicam-apps-lite python3-pil python3-evdev python3-numpy python3-gpiozero i2c-tools git

mkdir -p ~/evfpi && cd ~/evfpi
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
# later, for the deferred sensors:
# pip install adafruit-blinka adafruit-circuitpython-max1704x adafruit-circuitpython-vcnl4040
git clone https://github.com/werksmini/EVFCamera.git
```

Bench monitor (Waveshare 10.4" 1600×720, mounted upside down): add to the single line in `/boot/firmware/cmdline.txt`, then reboot:

```text
video=HDMI-A-1:1600x720,rotate=180
```

For the EVF instead: `video=HDMI-A-1:1280x960@60D`.

## Running the camera app

```bash
cd ~/evfpi/EVFCamera && git pull
python3 -m evfcam            # bench monitor (flipped, 960x720 window)
python3 -m evfcam --evf      # 0.4" EVF, 1280x960, not flipped
python3 -m evfcam --fake     # no camera: work on the UI anywhere
python3 -m evfcam --review 1 # show each shot for 1 s after saving (default off)
python3 -m evfcam --no-flash # no border flash at the shutter press
```

At the shutter press the screen goes dark with a white border and a red dot until the photo is saved, then live view returns with "SAVED". In Shoot mode, the EV readout turns red with "MAX" when the exposure can't get any brighter.

Controls, typed in the SSH terminal or on a keyboard plugged into the Pi:

| Key | Camera control | Shoot | Magnify | Menu | Playback |
| --- | --- | --- | --- | --- | --- |
| Space | Shutter (full) | Take photo | Take photo | Close | Close |
| `h` | Shutter (half) | – | Close | Close | Close |
| Enter | OK | Magnify 5× | 10×, then off | Open page | – |
| Arrows | D-pad | – | – | Move | ← → browse |
| `m` | Menu | Open menu | Close | Close | Close |
| `p` | Play | Playback | Playback | – | Close |
| `b` / Backspace | Back | Reset EV | Close | Up a level | Close |
| `[` `]` | Thumb wheel | EV −/+ ⅓ | – | – | Browse |
| `q` | – | Quit | Quit | Quit | Quit |

The bench shutter button on GPIO 27 also works. Photos save to `~/evfpi/photos`.

Run the tests: `python3 tests/test_modes.py`

## Bench scripts

| Script | What it does |
| --- | --- |
| `bench/preview.py` | Live preview only |
| `bench/overlay.py` | Preview with exposure info and focus meter overlay |
| `bench/camera.py` | Overlay + shutter button on GPIO 27 (header pin 13, other leg to GND pin 14); saves full-res JPEGs to `~/evfpi/photos` |

```bash
cd ~/evfpi && source .venv/bin/activate
python3 EVFCamera/bench/camera.py
```

Set `FLIP = False` at the top of a script when using the EVF instead of the flipped bench monitor.
