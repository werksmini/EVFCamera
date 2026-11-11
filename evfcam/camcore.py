"""The camera: preview, metadata, magnify, settings, still capture, overlay.

Camera     talks to the real HQ camera through Picamera2.
FakeCamera has the same methods and runs anywhere, for developing the UI off the Pi.
"""
import math
import time

import numpy as np

ASPECTS = {"4:3": (4, 3), "3:2": (3, 2), "1:1": (1, 1), "16:9": (16, 9)}
WB_MODES = {"Auto": "Auto", "Daylight": "Daylight", "Cloudy": "Cloudy", "Tungsten": "Tungsten",
            "Fluorescent": "Fluorescent", "Indoor": "Indoor"}
METERING = {"Centre": "CentreWeighted", "Spot": "Spot", "Average": "Matrix"}


def aspect_rect(full, aspect):
    """Largest centred rectangle of the given aspect inside full = (x, y, w, h). Even sizes."""
    x, y, w, h = full
    a, b = ASPECTS[aspect]
    if abs(w * b - h * a) <= 0.01 * h * a:   # within 1%: use it all (the sensor is 4056x3040, not exactly 4:3)
        return full
    if w * b > h * a:                    # too wide: trim the sides
        nw, nh = h * a // b, h
    else:                                # too tall: trim top and bottom
        nw, nh = w, w * b // a
    nw, nh = nw // 2 * 2, nh // 2 * 2
    return (x + (w - nw) // 2, y + (h - nh) // 2, nw, nh)


def control_values(s):
    """Turn Settings into libcamera control values (as plain names; Camera converts the enums)."""
    shutter_fixed = s.exp_mode in ("Shutter", "Manual")
    gain_fixed = s.exp_mode == "Manual"
    c = {
        "ExposureTimeMode": "Manual" if shutter_fixed else "Auto",
        "AnalogueGainMode": "Manual" if gain_fixed else "Auto",
        "ExposureValue": 0.0 if gain_fixed else float(s.ev),
        "AeMeteringMode": METERING[s.metering],
        "AwbEnable": True,
        "AwbMode": WB_MODES[s.wb],
        "Contrast": 1.0 + 0.25 * s.contrast,
        "Saturation": 0.0 if s.mono else 1.0 + 0.25 * s.saturation,
        "Sharpness": max(0.0, 1.0 + 0.5 * s.sharpness),
    }
    if shutter_fixed:
        c["ExposureTime"] = int(s.shutter_us)
        # the preview can't run faster than the shutter: slow the frame rate for long exposures
        c["FrameDurationLimits"] = (min(33333, s.shutter_us), max(33333, s.shutter_us))
    else:
        c["FrameDurationLimits"] = (16667, 66667)
    if gain_fixed:
        c["AnalogueGain"] = s.iso / 100
    return c


class Camera:
    def __init__(self, cfg):
        from libcamera import Transform
        from picamera2 import Picamera2, Preview

        self.Transform = Transform
        self.p = Picamera2()
        self.flipped = cfg.flip
        self.preview_cfg = self.p.create_preview_configuration(
            main={"size": cfg.preview_size},
            sensor={"output_size": cfg.sensor_mode},
            transform=Transform(hflip=cfg.flip, vflip=cfg.flip),
        )
        self.p.configure(self.preview_cfg)
        self.p.start_preview(Preview.DRM, x=cfg.win_x, y=cfg.win_y,
                             width=cfg.win_w, height=cfg.win_h)
        self.p.start()

        self.full_crop = self.p.capture_metadata()["ScalerCrop"]   # whole field of view
        s = self.p.camera_configuration()["sensor"]
        self.mode_txt = f"{s['output_size'][0]}x{s['output_size'][1]} {s['bit_depth']}-bit"
        self.raw = False
        self.still_cfg = None

    # --- settings ------------------------------------------------------------------------
    def apply(self, settings):
        """Exposure, colour and tone settings, applied to the live camera."""
        from libcamera import controls as C
        available = self.p.camera_controls
        enums = {
            "ExposureTimeMode": lambda v: getattr(C.ExposureTimeModeEnum, v),
            "AnalogueGainMode": lambda v: getattr(C.AnalogueGainModeEnum, v),
            "AeMeteringMode": lambda v: getattr(C.AeMeteringModeEnum, v),
            "AwbMode": lambda v: getattr(C.AwbModeEnum, v),
        }
        wanted = control_values(settings)
        if "ExposureTimeMode" not in available:          # older libcamera: one on/off switch
            wanted["AeEnable"] = wanted["AnalogueGainMode"] == "Auto"
        out = {}
        for k, v in wanted.items():
            if k in available or k == "AeEnable" and "AeEnable" in available:
                out[k] = enums[k](v) if k in enums else v
        self.p.set_controls(out)

    def update_still(self, settings):
        """File format, JPEG quality and aspect ratio: rebuild the still-photo configuration."""
        x, y, w, h = aspect_rect(self.full_crop, settings.aspect)
        self.raw = settings.raw
        self.still_cfg = self.p.create_still_configuration(
            main={"size": (w, h)},
            raw={} if self.raw else None,
            buffer_count=1,                              # saves memory on the Zero
            transform=self.Transform(),                  # photos are never flipped
            controls={"ScalerCrop": (x, y, w, h)},
        )
        self.p.options["quality"] = settings.jpeg_quality

    # --- live view --------------------------------------------------------------------------
    def metadata(self) -> dict:
        return self.p.capture_metadata()

    def set_zoom(self, zoom: float):
        x, y, w, h = self.full_crop
        nw, nh = int(w / zoom), int(h / zoom)
        self.p.set_controls({"ScalerCrop": (x + (w - nw) // 2, y + (h - nh) // 2, nw, nh)})

    def wait_frame(self):
        """Block until the next preview frame, so an overlay just set is actually on screen."""
        self.p.capture_metadata()

    def grab_preview(self):
        """The current preview frame as a PIL image, upright (undoing the bench-monitor flip)."""
        from PIL import Image
        arr = self.p.capture_array("main")           # XBGR8888 -> [R, G, B, 255] per pixel
        img = Image.fromarray(arr[:, :, :3])
        return img.rotate(180) if self.flipped else img

    # --- photos ------------------------------------------------------------------------------
    def capture(self, path: str):
        """Take a photo. Returns the list of files written."""
        self.set_zoom(1)
        if not self.raw:
            self.p.switch_mode_and_capture_file(self.still_cfg, path)
            return [path]
        dng = path[:-4] + ".dng"
        req = self.p.switch_mode_and_capture_request(self.still_cfg)
        try:
            req.save("main", path)
            req.save_dng(dng)
        finally:
            req.release()
        return [path, dng]

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
        self.full_crop = (0, 0, 4056, 3040)
        self.zoom = 1
        self.controls = {}
        self.still = None
        self.last_overlay = None
        self.t0 = time.monotonic()

    @property
    def ev(self):
        return self.controls.get("ExposureValue", 0.0)

    def apply(self, settings):
        self.controls = control_values(settings)

    def update_still(self, settings):
        self.still = {"size": aspect_rect(self.full_crop, settings.aspect)[2:],
                      "raw": settings.raw, "quality": settings.jpeg_quality}

    def metadata(self) -> dict:
        t = time.monotonic() - self.t0
        c = self.controls
        return {
            "ExposureTime": c.get("ExposureTime", 8000),
            "AnalogueGain": c.get("AnalogueGain", 2.0), "DigitalGain": 1.0,
            "FrameDuration": 33333, "ColourTemperature": 5200, "Lux": 320.0,
            "FocusFoM": 900 + 600 * math.sin(t), "AeLocked": True,
        }

    def set_zoom(self, zoom):
        self.zoom = zoom

    def wait_frame(self):
        pass

    def grab_preview(self):
        from PIL import Image
        return Image.new("RGB", (1280, 960), (90, 120, 160))

    def capture(self, path):
        from PIL import Image
        w, h = (v // 4 for v in (self.still or {"size": (4056, 3040)})["size"])
        gx = np.linspace(0, 255, w, dtype=np.uint8)[None, :].repeat(h, 0)
        gy = np.linspace(0, 255, h, dtype=np.uint8)[:, None].repeat(w, 1)
        Image.fromarray(np.dstack([gx, gy, 255 - gx])).save(path, quality=90)
        files = [path]
        if self.still and self.still["raw"]:
            with open(path[:-4] + ".dng", "wb") as f:
                f.write(b"fake dng")
            files.append(path[:-4] + ".dng")
        return files

    def show_overlay(self, rgba):
        self.last_overlay = rgba

    def close(self):
        pass
