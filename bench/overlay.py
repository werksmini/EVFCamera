"""Live preview with a viewfinder info overlay.  Ctrl+C to quit."""
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from picamera2 import Picamera2, Preview
from libcamera import Transform

FLIP = True          # bench monitor is flipped with rotate=180; set False for the EVF
W, H = 960, 720      # preview window size = overlay size
X, Y = 320, 0        # preview window position on the 1600x720 screen

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1280, 960)},
    transform=Transform(hflip=FLIP, vflip=FLIP),
)
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


peak = 1.0
try:
    while True:
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

        # thirds grid and centre cross
        for i in (1, 2):
            d.line([(W * i // 3, 48), (W * i // 3, H - 48)], fill=(255, 255, 255, 70), width=1)
            d.line([(0, H * i // 3), (W, H * i // 3)], fill=(255, 255, 255, 70), width=1)
        cx, cy = W // 2, H // 2
        d.line([(cx - 18, cy), (cx + 18, cy)], fill=WHITE, width=2)
        d.line([(cx, cy - 18), (cx, cy + 18)], fill=WHITE, width=2)

        # bottom bar: mode, fps, light, focus meter
        d.rectangle([0, H - 48, W, H], fill=BAR)
        d.text((16, H - 36), f"{mode_txt}   {fps:.0f} fps   {lux:.0f} lux", font=small, fill=WHITE)
        peak = max(peak * 0.995, fom, 1)            # slowly decaying best-focus mark
        bx0, bx1, by = W - 316, W - 16, H - 24
        d.text((bx0 - 70, H - 36), "FOCUS", font=small, fill=WHITE)
        d.rectangle([bx0, by - 8, bx1, by + 8], outline=WHITE, width=1)
        fill_w = int((bx1 - bx0) * min(fom / peak, 1))
        d.rectangle([bx0, by - 8, bx0 + fill_w, by + 8],
                    fill=GREEN if fom >= 0.97 * peak else YELLOW)

        if FLIP:
            img = img.rotate(180)
        picam2.set_overlay(np.array(img))
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
