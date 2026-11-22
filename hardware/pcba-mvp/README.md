# MVP main board (milled, single-sided)

`python3 make_pcba.py` places every part, routes the copper, checks clearances and writes:

| File | Use |
|---|---|
| `evfcam_mvp.sch`, `evfcam_mvp.brd` | Fusion Electronics (EAGLE 9 XML). Upload both together: File > Upload, or drag into the Data Panel |
| `gerber/evfcam_mvp-B_Cu.gbr` | Bottom copper, for isolation milling (FlatCAM, Carbide Copper, Fusion PCB CAM...) |
| `gerber/evfcam_mvp-Edge_Cuts.gbr` | Board outline and camera ribbon slot |
| `gerber/evfcam_mvp-PTH.drl`, `-NPTH.drl` | Pin holes (0.9 / 1.0 / 1.2 / 1.4 / 1.5 mm) and M2.5 screw holes (2.75 mm) |
| `preview.png` | Component side and the mirrored copper side |
| `fusion_sketches.py`, `layout.json` | Draws the layout into the Fusion "PCBA" design |

Needs `numpy scipy scikit-image pillow shapely`.

## Board

98.7 x 67 mm on a 70 x 100 blank, notched under the Pi so HDMI and USB stay clear. Copper only on the
back (EAGLE layer 16). Signal traces 0.8 mm, power (5 V, battery, ground return) 1.2 mm. Every trace
runs at 0, 45 or 90 degrees with no acute corners. The router first finds a layout at 0.4 mm clearance,
then re-routes each connection at 0.65 mm wherever that fits without a detour: the closest copper on
the finished board is 0.6 mm (the power switch's own pin pitch), and 0.6 mm to edges and holes.
Everything is routed: no jumper wires. The gauge's four header pads get fixed, staggered lead-ins so the
four lanes from under the Pi nest neatly.

Viewed from the component side (camera rear), X right, Y up:

| Part | Where | Notes |
|---|---|---|
| J1 Pi socket, 2x20 female | pin 1 at (8.37, 25.23); odd pins inner row, even pins outer row | Pi plugs in upside down by its own pins. Pin 1 pad is smaller so 5 V can pass |
| Pi mounting holes | (3.5, 3.5) (61.5, 3.5) (3.5, 26.5) (61.5, 26.5) | The hand sketch had them at the outline corners |
| SW1 Fn, SW2 Menu | (19.5, 54.6), (32.54, 54.6) | Adafruit 3101; Menu moved up 1 mm to clear Play |
| SW3 Play | (32.54, 43.6) | As drawn by hand |
| SW4 D-pad (504) | (46.2, 46.5) | Middle pins drilled 1.4 mm on the centre line: check the pin offset with calipers before drilling |
| SW5 Shutter | (60.0, 46.5) | 3101 |
| SW6 power slide | pins at (76, 59.8) (78) (80) | C&K OS102011MA1QN1, actuator over the top edge. Pin 1 side = off |
| U1 charger 6106 | header y = 11.51, EN at x 75.2 ... VIN at 93.0 | USB-C over the right edge. Remove the screw terminal |
| U2 gauge 5580 | header column x = 72.54, VCC at top; battery pins at (81.43, 29.97 / 27.43) | |
| Ribbon slot | (83.5 - 97, 47), 1.6 mm wide | The Pi Zero camera cable's narrow end goes through |

## Nets

| Net | From | To |
|---|---|---|
| +5V | charger 5V | Pi pins 2/4 |
| GND (power) | charger GND -> gauge battery GND -> gauge GND | Pi pin 9 |
| VBAT | charger VBAT | gauge battery + |
| EN | charger EN | switch pin 2 (pin 1 = GND, so sliding to pin 1 turns the boost off) |
| +3V3, SCL, SDA | Pi pins 17, 5, 3 | gauge VCC, SCL, SDA (gauge INT not used: the app polls) |
| FN, MENU, PLAY | GPIO 18 / 23 / 24 (pins 12 / 16 / 18) | buttons; grounds on pins 14 and 20 |
| UP, LEFT, DOWN | GPIO 25 / 8 / 7 (pins 22 / 24 / 26) | D-pad; common to pin 34 |
| RIGHT, OK | GPIO 16 / 20 (pins 36 / 38) | D-pad |
| SHUTTER | GPIO 21 (pin 40) | shutter; ground to pin 39, also to the power switch |

`evfcam/config.py` uses the same map.

## Milling and assembly

1. Mill the copper (bottom), drill, then cut the outline and slot. Most CAM tools mirror the bottom
   layer for you; check the result against the right half of `preview.png`.
2. Use nylon screws, standoffs and nuts in all eight 2.75 mm holes: the nuts sit on the copper side,
   some over traces.
3. Solder low parts first: buttons, D-pad, slide switch, then the Pi socket, then the gauge and the
   charger through their own header pins.
4. Height: the Pi stack (socket plus Pi) stands about 10 mm; the 3101 buttons are 5.5 mm, so they need
   caps or the rear panel stepped.
