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
| Sensors | MAX17048 fuel gauge, VCNL4040 eye sensor (I²C) |

## Repository layout

| Folder | Contents |
| --- | --- |
| `bench/` | Standalone test scripts used while bringing up the hardware |
| `hardware/kicad/` | Footprints and PCB files |
| `docs/` | Roadmap and design notes |

The camera app itself will live in `evfcam/` (see [docs/roadmap.md](docs/roadmap.md)).

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
pip install adafruit-blinka adafruit-circuitpython-max1704x adafruit-circuitpython-vcnl4040
git clone https://github.com/werksmini/EVFCamera.git
```

Bench monitor (Waveshare 10.4" 1600×720, mounted upside down): add to the single line in `/boot/firmware/cmdline.txt`, then reboot:

```text
video=HDMI-A-1:1600x720,rotate=180
```

For the EVF instead: `video=HDMI-A-1:1280x960@60D`.

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
