"""The camera: preview, metadata, magnify, still capture, overlay.

Camera     talks to the real HQ camera through Picamera2.
FakeCamera has the same methods and runs anywhere, for developing the UI off the Pi.
"""
import math
import time

import numpy as np


class Camera:
    def __init__(self, cfg):
        from libcamera import Transform
        from picamera2 import Picamera2, Preview

        self.p = Picamera2()
        flip = Transform(hflip=cfg.flip, vflip=cfg.flip)
        self.flipped = cfg.flip
        self.preview_cfg = self.p.create_preview_configuration(
            main={"size": cfg.preview_size},
            sensor={"output_size": cfg.sensor_mode},
            transform=flip,
        )
        # Photos are never flipped: the flip is only for an upside-down screen.
        self.still_cfg = self.p.create_still_configuration(buffer_count=1, transform=Transform())
        self.p.configure(self.preview_cfg)
        self.p.start_preview(Preview.DRM, x=cfg.win_x, y=cfg.win_y,
                             width=cfg.win_w, height=cfg.win_h)
        self.p.start()

        self.full_crop = self.p.capture_metadata()["ScalerCrop"]   # whole field of view
        s = self.p.camera_configuration()["sensor"]
        self.mode_txt = f"{s['output_size'][0]}x{s['output_size'][1]} {s['bit_depth']}-bit"

    def metadata(self) -> dict:
        return self.p.capture_metadata()

    def set_zoom(self, zoom: float):
        x, y, w, h = self.full_crop
        nw, nh = int(w / zoom), int(h / zoom)
        self.p.set_controls({"ScalerCrop": (x + (w - nw) // 2, y + (h - nh) // 2, nw, nh)})

    def set_ev(self, ev: float):
        self.p.set_controls({"ExposureValue": ev})

    def wait_frame(self):
        """Block until the next preview frame, so an overlay just set is actually on screen."""
        self.p.capture_metadata()

    def grab_preview(self):
        """The current preview frame as a PIL image, upright (undoing the bench-monitor flip)."""
        from PIL import Image
        arr = self.p.capture_array("main")           # XBGR8888 -> [R, G, B, 255] per pixel
        img = Image.fromarray(arr[:, :, :3])
        return img.rotate(180) if self.flipped else img

    def capture(self, path: str):
        self.set_zoom(1)
        self.p.switch_mode_and_capture_file(self.still_cfg, path)

    def show_overlay(self, rgba: np.ndarray):
        self.p.set_overlay(rgba)

    def close(self):
        self.p.stop()
        self.p.close()


class FakeCamera:
    """Stand-in for development: made-up metadata, writes a test image when 'capturing'."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.mode_txt = "2028x1520 12-bit (fake)"
        self.zoom = 1
        self.ev = 0.0
        self.last_overlay = None
        self.t0 = time.monotonic()

    def metadata(self) -> dict:
        t = time.monotonic() - self.t0
        return {
            "ExposureTime": 8000, "AnalogueGain": 2.0, "DigitalGain": 1.0,
            "FrameDuration": 33333, "ColourTemperature": 5200, "Lux": 320.0,
            "FocusFoM": 900 + 600 * math.sin(t), "AeLocked": True,
        }

    def set_zoom(self, zoom):
        self.zoom = zoom

    def set_ev(self, ev):
        self.ev = ev

    def wait_frame(self):
        pass

    def grab_preview(self):
        from PIL import Image
        return Image.new("RGB", (1280, 960), (90, 120, 160))

    def capture(self, path):
        from PIL import Image
        w, h = 4056 // 4, 3040 // 4
        gx = np.linspace(0, 255, w, dtype=np.uint8)[None, :].repeat(h, 0)
        gy = np.linspace(0, 255, h, dtype=np.uint8)[:, None].repeat(w, 1)
        Image.fromarray(np.dstack([gx, gy, 255 - gx])).save(path, quality=90)

    def show_overlay(self, rgba):
        self.last_overlay = rgba

    def close(self):
        pass
