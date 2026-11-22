# MVP main board (milled, single-sided)

`python3 make_pcba.py` places every part, routes the copper, checks clearances and writes:

| File | Use |
|---|---|
| `evfcam_mvp.sch`, `evfcam_mvp.brd` | Fusion Electronics (EAGLE 9 XML). Upload both together: File > Upload, or drag into the Data Panel |
| `gerber/evfcam_mvp-B_Cu.gbr` | Bottom copper, for isolation milling (FlatCAM, Carbide Copper, Fusion PCB CAM...) |
| `gerber/evfcam_mvp-Edge_Cuts.gbr` | Board outline and camera ribbon slot |
| `gerber/evfcam_mvp-PTH.drl`, `-NPTH.drl` | Pin holes (0.9 / 1.0 / 1.2 / 1.4 / 1.5 mm) and M2.5 screw holes (2.75 mm) |
| `preview.png` | Component side and the mirrored copper side |
| `fusion_sketches.py`, `layout.json` | Draws the layout into the Fusion "PCBA" design (`make_fusion_script.py` rebuilds it) |

Needs `numpy scipy scikit-image pillow shapely`.

## Board

Layout follows the "Skeleton" sketch in the Fusion PCBA design (105 x 55 mm, Pi in the bottom-left
corner), widened to 110.5 x 55 mm to make it routable on one side:

- **3 mm added on the left.** EN (charger to power switch) runs up the left edge outside the Pi's
  screws; the only gap at the end of the Pi header is taken by 5 V. The switch stays flush with the
  new left edge.
- **Cut-out, charger and gauge moved 2.5 mm right.** Five lanes (3V3, GND, SCL, SDA, 5V) climb between
  the Pi's top-right screw and the ribbon cut-out.

Copper on the back only (EAGLE layer 16). Signal traces 0.8 mm, power (5 V, battery, ground return)
1.2 mm, all at 0/45/90 degrees with no acute corners. The bus from under the Pi to the gauge and
charger is laid as fixed nested lanes; everything else is auto-routed, first at 0.4 mm clearance, then
each connection again at 0.65 mm where it fits without a detour. Closest copper: 0.5 mm (two bus lanes);
0.7 mm to edges, holes and the cut-out. No jumper wires.

Viewed from the component side (camera rear), X right, Y up, origin at the Pi's bottom-left corner:

| Part | Where | Notes |
|---|---|---|
| J1 Pi socket, 2x20 female | pin 1 at (8.37, 25.23); odd pins inner row | Pi plugs in upside down by its own pins |
| Pi screws | (3.5, 3.5) (61.5, 3.5) (3.5, 26.5) (61.5, 26.5) | |
| SW1 Fn, SW2 Menu | centres (21, 49), (33, 49) | Adafruit 3101 |
| SW3 Play | (33, 37) | 3101 |
| SW4 D-pad (504) | (47, 43) | Check the middle-pin offset with calipers before drilling |
| SW5 Shutter | (61, 49) | 3101 |
| SW6 power slide | pins at (-0.8, 44.7 / 46.7 / 48.7) | Actuator out of the left edge. Top pin = GND, so **slide up = off** |
| Ribbon cut-out | x 72-78, y 5-25 | Beside the Pi's camera connector |
| U1 charger 6106 | bottom-right corner, x 78.29-107.5; header y = 16.51 | USB-C over the right edge; 4 screws. Remove the screw terminal |
| U2 gauge 5580 | x 82.74-103.06, y 21.5-46.9; header column x = 85.28 | Fit only 4 header pins (VIN, GND, SCL, SDA) plus the 2 battery pins; 4 screws |

Battery: plugs into the charger's JST-PH socket as before. The board carries the charger's VBAT and
GND pins to the gauge's battery pins; leave the gauge's own battery connectors empty.

## Nets

| Net | From | To |
|---|---|---|
| +5V | charger 5V | Pi pins 2/4 |
| GND (power) | charger GND -> gauge battery GND; gauge GND | Pi pin 9 |
| VBAT | charger VBAT | gauge battery + |
| EN | charger EN | switch pin 2 (top pin = GND via Pi pin 6, so sliding up turns the boost off) |
| +3V3, SCL, SDA | Pi pins 17, 5, 3 | gauge VCC, SCL, SDA (gauge INT not used: the app polls) |
| FN, MENU, PLAY | GPIO 18 / 23 / 24 (pins 12 / 16 / 18) | buttons; grounds on pins 14 and 20 |
| UP, LEFT, DOWN | GPIO 25 / 8 / 7 (pins 22 / 24 / 26) | D-pad; common to pin 34 |
| RIGHT, OK | GPIO 16 / 20 (pins 36 / 38) | D-pad |
| SHUTTER | GPIO 21 (pin 40) | shutter; ground to pin 39 |

`evfcam/config.py` uses the same map.

## Milling and assembly

1. Mill the copper (bottom), drill, then cut the outline and slot. Most CAM tools mirror the bottom
   layer for you; check the result against the right half of `preview.png`.
2. Use nylon screws, standoffs and nuts in all twelve 2.75 mm holes: the nuts sit on the copper side,
   some over traces.
3. Solder low parts first: buttons, D-pad, slide switch, then the Pi socket, then the gauge and the
   charger through their own header pins.
4. Height: the Pi stack (socket plus Pi) stands about 10 mm; the 3101 buttons are 5.5 mm, so they need
   caps or the rear panel stepped.
