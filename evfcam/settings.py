"""Everything the user can change, in one place, saved to a JSON file so it survives restarts."""
import json
import os
from dataclasses import asdict, dataclass, fields

DEFAULT_PATH = os.path.expanduser("~/.config/evfcam/settings.json")


@dataclass
class Settings:
    # Shooting
    file_format: str = "JPEG"            # JPEG | RAW+JPEG
    jpeg_quality: int = 93
    aspect: str = "4:3"                  # 4:3 | 3:2 | 1:1 | 16:9
    # Exposure
    exp_mode: str = "Auto"               # Auto | Shutter (priority) | Manual
    shutter_us: int = 8000               # used in Shutter and Manual
    iso: int = 200                       # used in Manual
    ev: float = 0.0                      # used in Auto and Shutter
    metering: str = "Centre"             # Centre | Spot | Average
    # Colour
    wb: str = "Auto"                     # Auto | Daylight | Cloudy | Tungsten | Fluorescent | Indoor
    contrast: int = 0                    # -2..+2 steps
    saturation: int = 0
    sharpness: int = 0
    mono: bool = False
    # Lens
    lens: str = "17 mm f/1.7"
    # Display
    capture_flash: bool = True
    review_s: float = 0.0
    focus_square: bool = True
    focus_bar: bool = True
    info: str = "Full"                   # Full | Minimal

    @classmethod
    def load(cls, path=DEFAULT_PATH):
        s = cls()
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return s                     # first run, or a damaged file: defaults
        from .menu import valid          # only accept values the menu offers
        for fld in fields(cls):
            if fld.name in data and valid(fld.name, data[fld.name]):
                setattr(s, fld.name, data[fld.name])
        return s

    def save(self, path=DEFAULT_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(asdict(self), f, indent=2)
        os.replace(tmp, path)            # never leaves a half-written file behind

    @property
    def raw(self):
        return self.file_format == "RAW+JPEG"
