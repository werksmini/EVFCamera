"""Plain live preview on the HDMI screen. Press Enter to stop."""
from picamera2 import Picamera2, Preview
from libcamera import Transform

FLIP = True          # bench monitor is flipped with rotate=180; set False for the EVF

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1280, 960)},
    transform=Transform(hflip=FLIP, vflip=FLIP),
)
picam2.configure(config)
picam2.start_preview(Preview.DRM, x=320, y=0, width=960, height=720)
picam2.start()
input("Previewing. Press Enter to stop.")
picam2.stop()
