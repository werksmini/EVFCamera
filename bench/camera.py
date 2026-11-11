"""Live preview with info overlay; press the shutter button (GPIO 27) to take a full-res photo.
Ctrl+C to quit."""
import os
import threading
import time
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from picamera2 import Picamera2, Preview
from libcamera import Transform
from gpiozero import Button

FLIP = True          # bench monitor is flipped with rotate=180; set False for the EVF
W, H = 960, 720      # preview window size = overlay size
X, Y = 320, 0        # preview window position on the 1600x720 screen
IN_FOCUS = 0.95      # green when sharpness is within 95% of the best seen recently
PEAK_DECAY = 0.999   # how fast the "best seen" forgets (0.999 = about 10 s to drop 5%)

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1280, 960)},
    transform=Transform(hflip=FLIP, vflip=FLIP),
)
# stills are never flipped: the flip is only for the upside-down bench monitor
still = picam2.create_still_configuration(buffer_count=1, transform=Transform())
picam2.configure(config)
picam2.start_preview(Preview.DRM, x=X, y=Y, width=W, height=H)
picam2.start()

sensor = picam2.camera_configuration()["sensor"]
mode_txt = f"{sensor['output_size'][0]}x{sensor['output_size'][1]} {sensor['bit_depth']}-bit"


def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


big, small = load_font(30), load_font(20)
WHITE, YELLOW, GREEN = (255, 255, 255, 255), (255, 210, 0, 255), (60, 220, 90, 255)
BAR = (0, 0, 0, 150)


def shutter_txt(us):
    s = us / 1_000_000
    return f"1/{round(1 / s)}" if s < 0.5 else f"{s:.1f}s"


PHOTOS = os.path.expanduser("~/evfpi/photos")
os.makedirs(PHOTOS, exist_ok=True)

shoot = threading.Event()
shutter = Button(27, pull_up=True, bounce_time=0.05)   # switch between GPIO 27 (pin 13) and GND (pin 14)
shutter.when_pressed = shoot.set
saved_msg, saved_until = "", 0.0

peak = 1.0
try:
    while True:
        if shoot.is_set():
            name = os.path.join(PHOTOS, datetime.now().strftime("%Y%m%d_%H%M%S.jpg"))
            picam2.switch_mode_and_capture_file(still, name)
            print("saved", name, flush=True)
            saved_msg, saved_until = "SAVED " + os.path.basename(name), time.monotonic() + 1.5
            shoot.clear()
        md = picam2.capture_metadata()
        exp = md.get("ExposureTime", 0)
        gain = md.get("AnalogueGain", 1.0) * md.get("DigitalGain", 1.0)
        iso = round(gain * 100)
        fps = 1_000_000 / md["FrameDuration"] if md.get("FrameDuration") else 0
        kelvin = md.get("ColourTemperature", 0)
        lux = md.get("Lux", 0)
        fom = md.get("FocusFoM", 0)
        locked = md.get("AeLocked", False)

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # top bar: exposure
        d.rectangle([0, 0, W, 48], fill=BAR)
        d.text((16, 8), shutter_txt(exp) if exp else "--", font=big, fill=WHITE)
        d.text((180, 8), f"ISO {iso}", font=big, fill=WHITE)
        d.text((380, 8), f"{kelvin}K", font=big, fill=WHITE)
        d.text((W - 16, 8), "AE LOCK" if locked else "AE", font=big,
               fill=GREEN if locked else WHITE, anchor="ra")

        # focus square: turns green at peak sharpness
        peak = max(peak * PEAK_DECAY, fom, 1)       # slowly decaying best-focus mark
        in_focus = fom >= IN_FOCUS * peak
        cx, cy = W // 2, H // 2
        d.rectangle([cx - 18, cy - 18, cx + 18, cy + 18],
                    outline=GREEN if in_focus else WHITE, width=3)

        # bottom bar: mode, fps, light, focus meter
        d.rectangle([0, H - 48, W, H], fill=BAR)
        d.text((16, H - 36), f"{mode_txt}   {fps:.0f} fps   {lux:.0f} lux", font=small, fill=WHITE)
        bx0, bx1, by = W - 316, W - 16, H - 24
        d.text((bx0 - 70, H - 36), "FOCUS", font=small, fill=WHITE)
        d.rectangle([bx0, by - 8, bx1, by + 8], outline=WHITE, width=1)
        fill_w = int((bx1 - bx0) * min(fom / peak, 1))
        d.rectangle([bx0, by - 8, bx0 + fill_w, by + 8],
                    fill=GREEN if in_focus else YELLOW)

        if time.monotonic() < saved_until:
            d.rectangle([cx - 230, 70, cx + 230, 120], fill=(0, 0, 0, 180))
            d.text((cx, 95), saved_msg, font=small, fill=GREEN, anchor="mm")

        if FLIP:
            img = img.rotate(180)
        picam2.set_overlay(np.array(img))
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
