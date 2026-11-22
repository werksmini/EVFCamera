"""EVFCamera MVP main board: placement, single-sided routing, and files for Fusion and the mill.

    python3 make_pcba.py      -> evfcam_mvp.sch / .brd (Fusion Electronics, EAGLE 9 XML)
                                 gerber/ (bottom copper, outline, drill) and preview.png

One milled board carries everything: the Pi Zero 2 W (plugged in upside down by its pins, so
its header sits in a 2x20 socket here), the Adafruit 6106 charger/boost and the 5580 MAX17048 fuel
gauge (both soldered through by their own header pins), the D-pad, four soft tactile buttons and the
power slide switch.

Coordinates are millimetres, looking at the COMPONENT side (the side the buttons face out of, the
camera's rear) with X to the right and Y up. Copper is only on the other side (EAGLE layer 16,
Bottom), so nothing ever needs a via; anything the router can't fit becomes a short jumper wire.
"""
import json
import math
import os
from xml.sax.saxutils import escape, quoteattr

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from skimage.graph import MCP_Geometric

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "evfcam_mvp"
LIB = "evfcam_mvp"

# --- milling rules -----------------------------------------------------------------------------------
SIG_W = 0.8          # signal trace width
PWR_W = 1.2          # 5 V, battery and the ground return
CLEAR = 0.4          # copper to copper
EDGE = 0.6           # copper to board edge or a drilled hole
GRID = 0.1           # router grid

# --- board outline: notched under the Pi so its HDMI and USB ports stay clear ------------------------
OUTLINE = [(0, 0), (68.5, 0), (68.5, -5), (98.71, -5), (98.71, 62), (0, 62)]
# camera ribbon slot (the Pi Zero cable's narrow end passes through), milled in the free top-right corner
SLOT = ((83.5, 47.0), (97.0, 47.0), 1.6)       # centre line ends and width

# --- parts --------------------------------------------------------------------------------------------
# pad: name -> (x, y, diameter, drill, shape)    shape: round | square | long (EAGLE long pad, R90)
PARTS = {}          # ref -> dict(value, desc, origin, pads, body)
NETS = {}           # (ref, pad) -> net


def part(ref, value, desc, pads, body, origin=None):
    xs = [p[0] for p in pads.values()]
    ys = [p[1] for p in pads.values()]
    if origin is None:
        origin = (round((min(xs) + max(xs)) / 2, 3), round((min(ys) + max(ys)) / 2, 3))
    PARTS[ref] = dict(value=value, desc=desc, origin=origin, pads=pads, body=body)


# J1: 2x20 socket for the Pi. Pin 1 is at the SD-card end (left); odd pins in the row nearer the Pi's
# middle (inner), even pins along the Pi's edge (outer, nearer the buttons).
PI_X1, PI_INNER, PI_OUTER = 8.37, 25.23, 27.77
pi_pads = {}
for n in range(1, 41):
    x = PI_X1 + 2.54 * ((n - 1) // 2)
    y = PI_INNER if n % 2 else PI_OUTER
    # pin 1 is never used (3V3 comes from pin 17), so a smaller pad leaves room for the 5 V trace
    pi_pads[str(n)] = (x, y, 1.6 if n == 1 else 1.8, 1.0, "round")
part("J1", "PI ZERO 2 W", "2x20 2.54 mm female socket; the Pi plugs in upside down by its own pins",
     pi_pads, [(0, 0, 65, 30)], origin=(PI_X1 + 2.54 * 9.5, (PI_INNER + PI_OUTER) / 2))
PI_HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 26.5), (61.5, 26.5)]


def pi_gpio_pin(n):
    return f"J1.{n}"


# Soft tactile buttons (Adafruit 3101): 4.5 x 8 mm pin rectangle. Each side's two pins are joined inside
# the switch: left column = signal (pads 1, 2), right column = ground (pads 3, 4).
def tact3101(ref, value, cx, cy):
    part(ref, value, "Soft tactile button, Adafruit 3101 (left pins = signal, right pins = GND)",
         {"1": (cx - 2.25, cy + 4, 2.0, 1.0, "round"), "2": (cx - 2.25, cy - 4, 2.0, 1.0, "round"),
          "3": (cx + 2.25, cy + 4, 2.0, 1.0, "round"), "4": (cx + 2.25, cy - 4, 2.0, 1.0, "round")},
         [(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5)], origin=(cx, cy))


tact3101("SW1", "FN", 19.5, 54.6)
tact3101("SW2", "MENU", 32.54, 54.6)
tact3101("SW3", "PLAY", 32.54, 43.6)
tact3101("SW5", "SHUTTER", 60.0, 46.5)

# D-pad: Adafruit 504 (Alps SKQU-style 5-way). Pins 1 up, 2 left, 3 down on the left; 6 press, 5 right,
# 4 common on the right. The middle pins are drilled oversize: check their offset with calipers.
DX, DY = 46.2, 46.5
part("SW4", "D-PAD", "5-way navigation switch, Adafruit 504",
     {"1": (DX - 5.15, DY + 3.25, 2.2, 1.2, "round"), "2": (DX - 5.15, DY, 2.4, 1.4, "round"),
      "3": (DX - 5.15, DY - 3.25, 2.2, 1.2, "round"), "6": (DX + 5.15, DY + 3.25, 2.2, 1.2, "round"),
      "5": (DX + 5.15, DY, 2.4, 1.4, "round"), "4": (DX + 5.15, DY - 3.25, 2.2, 1.2, "round")},
     [(DX - 5, DY - 5, DX + 5, DY + 5)], origin=(DX, DY))

# Power switch: C&K OS102011MA1QN1 right-angle slide, actuator over the top edge.
SX, SY = 76.0, 59.8
part("SW6", "POWER", "C&K OS102011MA1QN1 right-angle slide switch. Pin 1 side = OFF",
     {"1": (SX, SY, 1.4, 0.9, "long"), "2": (SX + 2, SY, 1.4, 0.9, "long"), "3": (SX + 4, SY, 1.4, 0.9, "long"),
      "T1": (SX - 2.1, SY, 2.6, 1.5, "round"), "T2": (SX + 6.1, SY, 2.6, 1.5, "round")},
     [(SX - 2.3, SY - 2.2, SX + 6.3, SY + 2.2)], origin=(SX + 2, SY))

# Charger: Adafruit 6106 (BQ25185 + 5 V boost), turned so USB-C faces right over the board edge.
# Its 8 header pins go through this board. Remove its screw terminal block first.
CHG_PINS = ["EN", "5V", "VBAT", "GND", "D+", "D-", "VBUS", "VIN"]
CHG_X = [75.215, 77.755, 80.295, 82.835, 85.375, 87.915, 90.455, 92.995]
part("U1", "ADAFRUIT 6106", "BQ25185 charger + 5 V boost breakout, pins through the board",
     {nm: (x, 11.51, 1.8, 1.0, "square" if nm == "VIN" else "round") for nm, x in zip(CHG_PINS, CHG_X)},
     [(69.5, -5, 98.71, 14.05)])
CHG_HOLES = [(72.04, -2.46), (96.17, -2.46), (72.04, 11.51), (96.17, 11.51)]

# Fuel gauge: Adafruit 5580 (MAX17048), header column on the left, battery pins (JP2) through the board.
MAX_PINS = [("VCC", 35.05), ("GND", 32.51), ("SCL", 29.97), ("SDA", 27.43), ("INT", 24.89), ("QSTART", 22.35)]
max_pads = {nm: (72.54, y, 1.8, 1.0, "square" if nm == "VCC" else "round") for nm, y in MAX_PINS}
max_pads["BAT"] = (81.43, 29.97, 1.8, 1.0, "round")
max_pads["BGND"] = (81.43, 27.43, 1.8, 1.0, "round")
part("U2", "ADAFRUIT 5580", "MAX17048 fuel gauge breakout; VIN = 3.3 V (its I2C pull-ups go to VIN)",
     max_pads, [(70, 16, 90.32, 41.4)])

HOLES = [(x, y, 2.75) for x, y in PI_HOLES + CHG_HOLES]      # all for M2.5 nylon screws

# Pads that are the same pin inside the part (EAGLE route="any"): any one of them may carry the trace.
TIED = {
    "J1": {"+3V3": ["1", "17"], "+5V": ["2", "4"], "GND": ["6", "9", "14", "20", "25", "30", "34", "39"]},
    "SW1": {"SIG": ["1", "2"], "GND": ["3", "4"]}, "SW2": {"SIG": ["1", "2"], "GND": ["3", "4"]},
    "SW3": {"SIG": ["1", "2"], "GND": ["3", "4"]}, "SW5": {"SIG": ["1", "2"], "GND": ["3", "4"]},
    "U2": {"GND": ["GND", "BGND"]},
}

# --- the circuit ----------------------------------------------------------------------------------------
GPIO = {12: 18, 16: 23, 18: 24, 22: 25, 24: 8, 26: 7, 36: 16, 38: 20, 40: 21, 3: 2, 5: 3}
for p in ("1", "17"):
    NETS[("J1", p)] = "+3V3"
for p in ("2", "4"):
    NETS[("J1", p)] = "+5V"
for p in TIED["J1"]["GND"]:
    NETS[("J1", p)] = "GND"
NETS[("J1", "3")], NETS[("J1", "5")] = "SDA", "SCL"
BUTTON_PINS = {"FN": 12, "MENU": 16, "PLAY": 18, "UP": 22, "LEFT": 24, "DOWN": 26,
               "RIGHT": 36, "OK": 38, "SHUTTER": 40}
for net, pin in BUTTON_PINS.items():
    NETS[("J1", str(pin))] = net
for ref, net in (("SW1", "FN"), ("SW2", "MENU"), ("SW3", "PLAY"), ("SW5", "SHUTTER")):
    NETS[(ref, "1")] = NETS[(ref, "2")] = net
    NETS[(ref, "3")] = NETS[(ref, "4")] = "GND"
for pad, net in {"1": "UP", "2": "LEFT", "3": "DOWN", "6": "OK", "5": "RIGHT", "4": "GND"}.items():
    NETS[("SW4", pad)] = net
NETS[("SW6", "1")], NETS[("SW6", "2")] = "GND", "EN"
NETS[("SW6", "T1")] = "GND"                          # metal tabs: one grounded, the other shares unused pin 3
NETS[("SW6", "3")] = NETS[("SW6", "T2")] = "SW6_TAB"
NETS.update({("U1", "EN"): "EN", ("U1", "5V"): "+5V", ("U1", "VBAT"): "VBAT", ("U1", "GND"): "GND"})
NETS.update({("U2", "VCC"): "+3V3", ("U2", "GND"): "GND", ("U2", "SCL"): "SCL", ("U2", "SDA"): "SDA",
             ("U2", "BAT"): "VBAT", ("U2", "BGND"): "GND"})

# What the router has to join with copper: (net, width, terminals). Each terminal is a list of pads that
# are already joined inside a part; reaching any one of them is enough. Terminals are joined in order.
ROUTES = [
    ("+5V", PWR_W, [["J1.2", "J1.4"], ["U1.5V"]]),
    ("GND", PWR_W, [["J1.9"], ["U2.GND", "U2.BGND"], ["U1.GND"]]),
    ("VBAT", PWR_W, [["U1.VBAT"], ["U2.BAT"]]),
    ("EN", SIG_W, [["U1.EN"], ["SW6.2"]]),
    ("+3V3", SIG_W, [["J1.17"], ["U2.VCC"]]),
    ("SCL", SIG_W, [["J1.5"], ["U2.SCL"]]),
    ("SDA", SIG_W, [["J1.3"], ["U2.SDA"]]),
    ("FN", SIG_W, [["SW1.2", "SW1.1"], ["J1.12"]]),
    ("GND", SIG_W, [["SW1.4", "SW1.3"], ["J1.14"]]),
    ("MENU", SIG_W, [["SW2.2", "SW2.1"], ["J1.16"]]),
    ("PLAY", SIG_W, [["SW3.2", "SW3.1"], ["J1.18"]]),
    ("GND", SIG_W, [["SW3.4", "SW3.3"], ["J1.20"]]),
    ("GND", SIG_W, [["SW2.4", "SW2.3"], ["SW3.3", "SW3.4"]]),
    ("UP", SIG_W, [["SW4.1"], ["J1.22"]]),
    ("LEFT", SIG_W, [["SW4.2"], ["J1.24"]]),
    ("DOWN", SIG_W, [["SW4.3"], ["J1.26"]]),
    ("GND", SIG_W, [["SW4.4"], ["J1.34"]]),
    ("RIGHT", SIG_W, [["SW4.5"], ["J1.36"]]),
    ("OK", SIG_W, [["SW4.6"], ["J1.38"]]),
    ("SHUTTER", SIG_W, [["SW5.2", "SW5.1"], ["J1.40"]]),
    ("GND", SIG_W, [["SW5.4", "SW5.3"], ["J1.39"]]),
    ("GND", SIG_W, [["SW5.3", "SW5.4"], ["SW6.1"]]),
    ("GND", SIG_W, [["SW6.1"], ["SW6.T1"]]),
    ("SW6_TAB", SIG_W, [["SW6.3"], ["SW6.T2"]]),
]


def pad(key):
    ref, p = key.split(".", 1)
    return PARTS[ref]["pads"][p]


def net_of(ref, p):
    return NETS.get((ref, p)) or f"NC_{ref}_{p}"


# --- geometry -------------------------------------------------------------------------------------------
X0, Y0 = -1.0, -6.0
X1, Y1 = 99.71 + 0.3, 63.0
GW, GH = int(round((X1 - X0) / GRID)) + 1, int(round((Y1 - Y0) / GRID)) + 1


def to_px(x, y):
    return (x - X0) / GRID, (Y1 - y) / GRID


def to_mm(r, c):
    return X0 + c * GRID, Y1 - r * GRID


def mask_draw(fn):
    img = Image.new("1", (GW, GH), 0)
    fn(ImageDraw.Draw(img))
    return np.array(img, dtype=bool)


def draw_pad(d, p, grow=0.0):
    x, y, dia, drill, shape = p
    cx, cy = to_px(x, y)
    r = (dia / 2 + grow) / GRID
    if shape == "square":
        d.rectangle([cx - r, cy - r, cx + r, cy + r], fill=1)
    elif shape == "long":                     # EAGLE long pad turned 90 degrees: dia wide, 2 x dia tall
        h = dia / 2 / GRID
        d.ellipse([cx - r, cy - h - r, cx + r, cy - h + r], fill=1)
        d.ellipse([cx - r, cy + h - r, cx + r, cy + h + r], fill=1)
        d.rectangle([cx - r, cy - h, cx + r, cy + h], fill=1)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)


def draw_track(d, pts, w):
    r = w / 2 / GRID
    px = [to_px(*p) for p in pts]
    d.line(px, fill=1, width=max(1, int(round(w / GRID))))
    for cx, cy in px:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)


def board_mask():
    m = mask_draw(lambda d: d.polygon([to_px(*p) for p in OUTLINE], fill=1))
    (ax, ay), (bx, by), w = SLOT
    m &= ~mask_draw(lambda d: draw_track(d, [(ax, ay), (bx, by)], w))
    return m


# --- router -----------------------------------------------------------------------------------------------
class Router:
    def __init__(self):
        self.nid = {}
        self.owner = np.zeros((GH, GW), np.int32)        # which net's copper is on each cell (0 = none)
        for ref, pt in PARTS.items():
            for p, geo in pt["pads"].items():
                m = mask_draw(lambda d: draw_pad(d, geo))
                self.owner[m] = self.id(net_of(ref, p))
        holes = mask_draw(lambda d: [d.ellipse([to_px(x, y)[0] - (r / 2 + EDGE - CLEAR) / GRID,
                                                to_px(x, y)[1] - (r / 2 + EDGE - CLEAR) / GRID,
                                                to_px(x, y)[0] + (r / 2 + EDGE - CLEAR) / GRID,
                                                to_px(x, y)[1] + (r / 2 + EDGE - CLEAR) / GRID], fill=1)
                                     for x, y, r in HOLES])
        self.owner[holes] = -1
        inside = board_mask()
        self.edge_dist = ndimage.distance_transform_edt(inside) * GRID
        self.tracks = []                                   # (net, width, points)

    def id(self, net):
        return self.nid.setdefault(net, len(self.nid) + 1)

    def forbidden(self, net, w, extra=0.0):
        nid = self.id(net)
        other = (self.owner != 0) & (self.owner != nid)
        dist = ndimage.distance_transform_edt(~other) * GRID
        # half a grid step of margin covers rasterising error
        lim = CLEAR + w / 2 + GRID * 0.75 + extra
        return (dist < lim) | (self.edge_dist < EDGE + w / 2 + GRID * 0.75 + extra), dist

    def route(self, net, w, terminals):
        """Join the terminals in order; returns the list of polylines or None if one can't be reached."""
        block, dist = self.forbidden(net, w)
        strict, _ = self.forbidden(net, w, extra=0.15)
        cost = 1.0 + 2.5 * np.clip((CLEAR + w / 2 + 0.6 - dist) / 0.6, 0, 1)     # keep off other copper
        cost[block] = -1
        rc = lambda k: tuple(int(round(v)) for v in to_px(*pad(k)[:2])[::-1])
        tree = [rc(k) for k in terminals[0]]
        lines = []
        for term in terminals[1:]:
            ends = [rc(k) for k in term]
            for p in tree + ends:
                cost[p] = 1.0
            mcp = MCP_Geometric(cost, fully_connected=True)
            cum, _ = mcp.find_costs(tree, ends, find_all_ends=False)
            reached = [e for e in ends if np.isfinite(cum[e])]
            if not reached:
                return None
            end = min(reached, key=lambda e: cum[e])
            path = mcp.traceback(end)
            pts = simplify(path, block, strict)
            lines.append(pts)
            tree += path + ends
        for pts in lines:
            m = mask_draw(lambda d: draw_track(d, pts, w))
            self.owner[m & (self.owner == 0)] = self.id(net)
            self.tracks.append((net, w, pts))
        return lines


def seg_ok(a, b, block):
    n = int(max(abs(a[0] - b[0]), abs(a[1] - b[1])) * 2) + 1
    rr = np.rint(np.linspace(a[0], b[0], n)).astype(int)
    cc = np.rint(np.linspace(a[1], b[1], n)).astype(int)
    return not block[rr, cc].any()


def simplify(path, block, strict):
    """Straighten a grid path into as few segments as stay legal (with a little extra margin if possible)."""
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        best = i + 1
        for j in range(i + 2, len(path)):
            if seg_ok(path[i], path[j], strict) or (seg_ok(path[i], path[j], block) and
                                                    strict[path[i]] and strict[path[j]]):
                best = j
            elif j - best > 60:
                break
        out.append(path[best])
        i = best
    return [tuple(round(v, 3) for v in to_mm(*p)) for p in out]


def autoroute(max_rounds=24):
    order = list(range(len(ROUTES)))
    best = None
    for rnd in range(max_rounds):
        r = Router()
        failed = []
        for k in order:
            net, w, terms = ROUTES[k]
            if r.route(net, w, terms) is None:
                failed.append(k)
        print(f"  round {rnd + 1}: {len(ROUTES) - len(failed)}/{len(ROUTES)} routed"
              + (f", failed {[ROUTES[k][0] + ' ' + ROUTES[k][2][0][0] for k in failed]}" if failed else ""))
        if best is None or len(failed) < len(best[1]):
            best = (r, failed)
        if not failed:
            break
        order = failed + [k for k in order if k not in failed]       # hardest first next time
    return best


# --- design rule check with exact geometry --------------------------------------------------------------
def drc(tracks):
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import unary_union
    shapes = []                    # (net, geometry, label)
    for ref, pt in PARTS.items():
        for p, (x, y, dia, drill, shape) in pt["pads"].items():
            if shape == "square":
                g = box(x - dia / 2, y - dia / 2, x + dia / 2, y + dia / 2)
            elif shape == "long":
                g = LineString([(x, y - dia / 2), (x, y + dia / 2)]).buffer(dia / 2)
            else:
                g = Point(x, y).buffer(dia / 2)
            shapes.append((net_of(ref, p), g, f"{ref}.{p}"))
    for net, w, pts in tracks:
        shapes.append((net, LineString(pts).buffer(w / 2), f"track {net}"))
    worst = (9e9, "", "")
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            if shapes[i][0] == shapes[j][0]:
                continue
            dd = shapes[i][1].distance(shapes[j][1])
            if dd < CLEAR - 0.02:
                print(f"  DRC: {dd:.3f} mm between {shapes[i][2]} and {shapes[j][2]}")
            if dd < worst[0]:
                worst = (dd, shapes[i][2], shapes[j][2])
    edge = Polygon(OUTLINE).exterior
    (ax, ay), (bx, by), sw = SLOT
    cut = unary_union([edge, LineString([(ax, ay), (bx, by)]).buffer(sw / 2).exterior] +
                      [Point(x, y).buffer(r / 2).exterior for x, y, r in HOLES])
    e = min(((s[1].distance(cut), s[2]) for s in shapes), key=lambda t: t[0])
    return worst, e


# --- EAGLE library, schematic, board --------------------------------------------------------------------
def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def package_xml(ref):
    pt = PARTS[ref]
    ox, oy = pt["origin"]
    out = [f'<package name="{ref}_PKG"><description>{escape(pt["desc"])}</description>']
    for p, (x, y, dia, drill, shape) in pt["pads"].items():
        extra = ' shape="long" rot="R90"' if shape == "long" else f' shape="{shape}"'
        out.append(f'<pad name="{p}" x="{f(x - ox)}" y="{f(y - oy)}" drill="{f(drill)}" '
                   f'diameter="{f(dia)}"{extra}/>')
    for x0, y0, x1, y1 in pt["body"]:
        a, b, c, d = x0 - ox, y0 - oy, x1 - ox, y1 - oy
        for p1, p2 in (((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))):
            out.append(f'<wire x1="{f(p1[0])}" y1="{f(p1[1])}" x2="{f(p2[0])}" y2="{f(p2[1])}" '
                       f'width="0.15" layer="21"/>')
    out.append(f'<text x="{f(pt["body"][0][0] - ox)}" y="{f(pt["body"][0][3] - oy + 0.6)}" size="1.2" '
               f'layer="25">&gt;NAME</text></package>')
    return "".join(out)


def pins_of(ref):
    """Schematic pins: (pin name, [pads])  -- tied pads share one pin."""
    tied = TIED.get(ref, {})
    seen = {p for pads in tied.values() for p in pads}
    out = [(nm, pads) for nm, pads in tied.items()]
    out += [(f"P{p}" if p.isdigit() else p, [p]) for p in PARTS[ref]["pads"] if p not in seen]
    return out


def symbol_xml(ref):
    pins = pins_of(ref)
    n = len(pins)
    h = 2.54 * (n + 1)
    out = [f'<symbol name="{ref}_SYM">'
           f'<wire x1="0" y1="0" x2="15.24" y2="0" width="0.254" layer="94"/>'
           f'<wire x1="15.24" y1="0" x2="15.24" y2="{f(-h)}" width="0.254" layer="94"/>'
           f'<wire x1="15.24" y1="{f(-h)}" x2="0" y2="{f(-h)}" width="0.254" layer="94"/>'
           f'<wire x1="0" y1="{f(-h)}" x2="0" y2="0" width="0.254" layer="94"/>'
           f'<text x="0" y="1.27" size="1.778" layer="95">&gt;NAME</text>'
           f'<text x="0" y="{f(-h - 2.54)}" size="1.778" layer="96">&gt;VALUE</text>']
    for i, (nm, _) in enumerate(pins):
        out.append(f'<pin name="{nm}" x="-5.08" y="{f(-2.54 * (i + 1))}" length="middle" direction="pas"/>')
    out.append("</symbol>")
    return "".join(out)


def library(for_board):
    pk = "".join(package_xml(r) for r in PARTS)
    if for_board:
        return f'<library name="{LIB}"><packages>{pk}</packages></library>'
    sy = "".join(symbol_xml(r) for r in PARTS)
    ds = ""
    for r in PARTS:
        conn = "".join(f'<connect gate="G$1" pin="{nm}" pad="{" ".join(pads)}"'
                       f'{" route=" + chr(34) + "any" + chr(34) if len(pads) > 1 else ""}/>'
                       for nm, pads in pins_of(r))
        ds += (f'<deviceset name="{r}_DEV" prefix="{r[:-1] if r[-1].isdigit() else r}">'
               f'<description>{escape(PARTS[r]["desc"])}</description>'
               f'<gates><gate name="G$1" symbol="{r}_SYM" x="0" y="0"/></gates>'
               f'<devices><device name="" package="{r}_PKG"><connects>{conn}</connects>'
               f'<technologies><technology name=""/></technologies></device></devices></deviceset>')
    return (f'<library name="{LIB}"><description>EVFCamera MVP board parts</description>'
            f'<packages>{pk}</packages><symbols>{sy}</symbols><devicesets>{ds}</devicesets></library>')


LAYERS = [(1, "Top", 4), (16, "Bottom", 1), (17, "Pads", 2), (18, "Vias", 2), (19, "Unrouted", 6),
          (20, "Dimension", 24), (21, "tPlace", 7), (22, "bPlace", 7), (23, "tOrigins", 15),
          (24, "bOrigins", 15), (25, "tNames", 7), (26, "bNames", 7), (27, "tValues", 7),
          (28, "bValues", 7), (29, "tStop", 7), (30, "bStop", 7), (31, "tCream", 7), (32, "bCream", 7),
          (39, "tKeepout", 4), (40, "bKeepout", 1), (41, "tRestrict", 4), (42, "bRestrict", 1),
          (43, "vRestrict", 2), (44, "Drills", 7), (45, "Holes", 7), (46, "Milling", 3),
          (47, "Measures", 7), (48, "Document", 7), (49, "Reference", 7), (51, "tDocu", 7),
          (52, "bDocu", 7), (91, "Nets", 2), (92, "Busses", 1), (93, "Pins", 2), (94, "Symbols", 4),
          (95, "Names", 7), (96, "Values", 7), (97, "Info", 7), (98, "Guide", 6)]


def head():
    layers = "".join(f'<layer number="{n}" name="{nm}" color="{c}" fill="1" visible="yes" active="yes"/>'
                     for n, nm, c in LAYERS)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE eagle SYSTEM "eagle.dtd">\n'
            '<eagle version="9.6.2"><drawing><settings><setting alwaysvectorfont="no"/>'
            '<setting verticaltext="up"/></settings>'
            '<grid distance="0.5" unitdist="mm" unit="mm" style="lines" multiple="1" display="no" '
            'altdistance="0.1" altunitdist="mm" altunit="mm"/>'
            f'<layers>{layers}</layers>')


CLASSES = ('<classes><class number="0" name="default" width="0.8" drill="0"><clearance class="0" value="0.4"/>'
           '</class><class number="1" name="power" width="1.2" drill="0"><clearance class="1" value="0.4"/>'
           '</class></classes>')
POWER_NETS = {"+5V", "GND", "VBAT"}


def schematic():
    instances, parts_xml, nets = [], [], {}
    for i, r in enumerate(PARTS):
        parts_xml.append(f'<part name="{r}" library="{LIB}" deviceset="{r}_DEV" device="" '
                         f'value={quoteattr(PARTS[r]["value"])}/>')
        px, py = 20 + (i % 4) * 60, 170 - (i // 4) * 80
        instances.append(f'<instance part="{r}" gate="G$1" x="{f(px)}" y="{f(py)}"/>')
        for k, (nm, pads) in enumerate(pins_of(r)):
            net = net_of(r, pads[0])
            if net.startswith("NC_"):
                continue
            y = py - 2.54 * (k + 1)
            x1, x2 = px - 5.08, px - 15.24
            nets.setdefault(net, []).append(
                f'<segment><pinref part="{r}" gate="G$1" pin="{nm}"/>'
                f'<wire x1="{f(x1)}" y1="{f(y)}" x2="{f(x2)}" y2="{f(y)}" width="0.1524" layer="91"/>'
                f'<label x="{f(x2)}" y="{f(y)}" size="1.27" layer="95" rot="R180" xref="yes"/></segment>')
    net_xml = "".join(f'<net name="{n}" class="{1 if n in POWER_NETS else 0}">{"".join(s)}</net>'
                      for n, s in sorted(nets.items()))
    title = ('<plain><text x="0" y="200" size="3.81" layer="97">EVFCamera MVP main board</text>'
             '<text x="0" y="194" size="1.778" layer="97">Pi Zero 2 W socket, 6106 charger/boost, '
             '5580 fuel gauge, D-pad, Fn, Menu, Play, Shutter, power switch. Nets join by label.</text></plain>')
    return (head() + '<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">'
            f'<libraries>{library(False)}</libraries><attributes/><variantdefs/>{CLASSES}'
            f'<parts>{"".join(parts_xml)}</parts>'
            f'<sheets><sheet>{title}<instances>{"".join(instances)}</instances><busses/>'
            f'<nets>{net_xml}</nets></sheet></sheets></schematic></drawing></eagle>\n')


def board(tracks):
    elements, sig = [], {}
    for r, pt in PARTS.items():
        ox, oy = pt["origin"]
        elements.append(f'<element name="{r}" library="{LIB}" package="{r}_PKG" '
                        f'value={quoteattr(pt["value"])} x="{f(ox)}" y="{f(oy)}"/>')
        tied = {p: nm for nm, pads in TIED.get(r, {}).items() for p in pads}
        for p in pt["pads"]:
            net = net_of(r, p)
            if net.startswith("NC_"):
                continue
            route = ' route="any"' if p in tied else ""
            sig.setdefault(net, []).append(f'<contactref element="{r}" pad="{p}"{route}/>')
    for net, w, pts in tracks:
        for a, b in zip(pts, pts[1:]):
            sig[net].append(f'<wire x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" '
                            f'width="{f(w)}" layer="16"/>')
    plain = "".join(f'<wire x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" width="0" layer="20"/>'
                    for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]))
    (ax, ay), (bx, by), sw = SLOT
    r = sw / 2
    plain += (f'<wire x1="{f(ax)}" y1="{f(ay + r)}" x2="{f(bx)}" y2="{f(by + r)}" width="0" layer="20"/>'
              f'<wire x1="{f(bx)}" y1="{f(by + r)}" x2="{f(bx)}" y2="{f(by - r)}" width="0" layer="20" curve="-180"/>'
              f'<wire x1="{f(bx)}" y1="{f(by - r)}" x2="{f(ax)}" y2="{f(ay - r)}" width="0" layer="20"/>'
              f'<wire x1="{f(ax)}" y1="{f(ay - r)}" x2="{f(ax)}" y2="{f(ay + r)}" width="0" layer="20" curve="-180"/>')
    plain += "".join(f'<hole x="{f(x)}" y="{f(y)}" drill="{f(d)}"/>' for x, y, d in HOLES)
    plain += ('<text x="2" y="59.5" size="1.5" layer="21">EVFCAM MVP v0.1</text>'
              '<text x="84" y="49.2" size="1" layer="21">CAMERA RIBBON</text>')
    classes = {n: 1 if n in POWER_NETS else 0 for n in sig}
    sig_xml = "".join(f'<signal name="{n}" class="{classes[n]}">{"".join(c)}</signal>' for n, c in sorted(sig.items()))
    rules = ('<designrules name="evfcam_mill"><param name="layerSetup" value="(1*16)"/>'
             '<param name="mdWireWire" value="0.4mm"/><param name="mdWirePad" value="0.4mm"/>'
             '<param name="mdPadPad" value="0.4mm"/><param name="mdCopperDimension" value="0.6mm"/>'
             '<param name="msWidth" value="0.8mm"/></designrules>')
    return (head() + f'<board><plain>{plain}</plain><libraries>{library(True)}</libraries>'
            f'<attributes/><variantdefs/>{CLASSES}{rules}<elements>{"".join(elements)}</elements>'
            f'<signals>{sig_xml}</signals></board></drawing></eagle>\n')


# --- Gerber and Excellon for the mill --------------------------------------------------------------------
def g6(v):
    return str(int(round(v * 1e6)))


def gerbers(tracks, outdir):
    os.makedirs(outdir, exist_ok=True)
    ap, body = {}, []

    def aperture(spec):
        if spec not in ap:
            ap[spec] = 10 + len(ap)
        return ap[spec]

    for r, pt in PARTS.items():
        for p, (x, y, dia, drill, shape) in pt["pads"].items():
            if shape == "square":
                a = aperture(f"R,{dia:.3f}X{dia:.3f}")
            elif shape == "long":
                a = aperture(f"O,{dia:.3f}X{2 * dia:.3f}")
            else:
                a = aperture(f"C,{dia:.3f}")
            body.append(f"D{a}*\nX{g6(x)}Y{g6(y)}D03*")
    for net, w, pts in tracks:
        a = aperture(f"C,{w:.3f}")
        body.append(f"D{a}*\nX{g6(pts[0][0])}Y{g6(pts[0][1])}D02*")
        body += [f"X{g6(x)}Y{g6(y)}D01*" for x, y in pts[1:]]
    hdr = ("%TF.GenerationSoftware,EVFCamera,make_pcba.py,0.1*%\n%TF.FileFunction,Copper,L1,Bot*%\n"
           "%TF.FilePolarity,Positive*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n")
    aps = "".join(f"%ADD{n}{s}*%\n" for s, n in ap.items())
    with open(os.path.join(outdir, f"{NAME}-B_Cu.gbr"), "w") as fh:
        fh.write(hdr + aps + "G01*\n" + "\n".join(body) + "\nM02*\n")

    # outline: board edge and ribbon slot as zero-width-ish lines
    (ax, ay), (bx, by), sw = SLOT
    rr = sw / 2
    lines = [f"X{g6(OUTLINE[0][0])}Y{g6(OUTLINE[0][1])}D02*"]
    lines += [f"X{g6(x)}Y{g6(y)}D01*" for x, y in OUTLINE[1:] + OUTLINE[:1]]
    lines += [f"X{g6(ax)}Y{g6(ay + rr)}D02*", f"X{g6(bx)}Y{g6(by + rr)}D01*",
              "G75*", "G02*", f"X{g6(bx)}Y{g6(by - rr)}I0J{g6(-rr)}D01*", "G01*",
              f"X{g6(ax)}Y{g6(ay - rr)}D01*", "G02*", f"X{g6(ax)}Y{g6(ay + rr)}I0J{g6(rr)}D01*", "G01*"]
    with open(os.path.join(outdir, f"{NAME}-Edge_Cuts.gbr"), "w") as fh:
        fh.write("%TF.FileFunction,Profile,NP*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n%ADD10C,0.100*%\nD10*\nG01*\n"
                 + "\n".join(lines) + "\nM02*\n")

    # drill: plated (component pins) and non-plated (screw holes) in separate files
    def excellon(path, holes):
        tools = sorted({d for _, _, d in holes})
        out = ["M48", "METRIC,TZ"] + [f"T{i + 1}C{d:.3f}" for i, d in enumerate(tools)] + ["%"]
        for i, d in enumerate(tools):
            out.append(f"T{i + 1}")
            out += [f"X{x:.3f}Y{y:.3f}" for x, y, dd in holes if dd == d]
        out.append("M30")
        with open(path, "w") as fh:
            fh.write("\n".join(out) + "\n")

    excellon(os.path.join(outdir, f"{NAME}-PTH.drl"),
             [(x, y, dr) for pt in PARTS.values() for (x, y, dia, dr, sh) in pt["pads"].values()])
    excellon(os.path.join(outdir, f"{NAME}-NPTH.drl"), HOLES)


# --- picture --------------------------------------------------------------------------------------------
def preview(tracks, failed, path):
    S, M = 9, 26
    W = 98.71 + 2
    H = 67 + 2
    img = Image.new("RGB", (int(2 * W * S) + 3 * M, int(H * S) + 2 * M + 70), (28, 30, 34))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    colours = {"+5V": (230, 80, 60), "VBAT": (240, 150, 40), "GND": (90, 140, 255), "+3V3": (220, 90, 200),
               "EN": (120, 220, 120)}

    def view(ox, mirror):
        def P(x, y):
            xx = (98.71 - x) if mirror else x
            return ox + (xx + 1) * S, M + (63 - y) * S
        d.polygon([P(*p) for p in OUTLINE], fill=(196, 160, 92) if mirror else (40, 92, 60), outline="black")
        (ax, ay), (bx, by), sw = SLOT
        d.line([P(ax, ay), P(bx, by)], fill=(28, 30, 34), width=int(sw * S))
        for (ax_, ay_) in ((ax, ay), (bx, by)):
            cx, cy = P(ax_, ay_)
            d.ellipse([cx - sw / 2 * S, cy - sw / 2 * S, cx + sw / 2 * S, cy + sw / 2 * S], fill=(28, 30, 34))
        if not mirror:
            for r, pt in PARTS.items():
                for x0, y0, x1, y1 in pt["body"]:
                    a, b = P(x0, y1), P(x1, y0)
                    d.rectangle([a, b], outline=(235, 235, 235), width=1)
                bx0, by0, bx1, by1 = pt["body"][0]
                lab = {"J1": "Pi Zero 2 W (outline)", "U1": "6106 charger", "U2": "5580 gauge"}.get(r, pt["value"])
                d.text(P((bx0 + bx1) / 2, (by0 + by1) / 2 if r in ("J1", "U1", "U2") else by1 + 1.2), lab,
                       fill="white", font=font, anchor="mm", stroke_width=2, stroke_fill="black")
        for net, w, pts in tracks:
            col = (184, 115, 51) if mirror else colours.get(net, (200, 200, 200))
            d.line([P(*p) for p in pts], fill=col, width=max(2, int(w * S)), joint="curve")
            for p in pts:
                cx, cy = P(*p)
                d.ellipse([cx - w / 2 * S, cy - w / 2 * S, cx + w / 2 * S, cy + w / 2 * S], fill=col)
        for r, pt in PARTS.items():
            for p, (x, y, dia, drill, shape) in pt["pads"].items():
                cx, cy = P(x, y)
                rr = dia / 2 * S
                col = (184, 115, 51) if mirror else (205, 170, 80)
                if shape == "square":
                    d.rectangle([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
                elif shape == "long":
                    d.rounded_rectangle([cx - rr, cy - 2 * rr, cx + rr, cy + 2 * rr], radius=rr, fill=col)
                else:
                    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
                rd = drill / 2 * S
                d.ellipse([cx - rd, cy - rd, cx + rd, cy + rd], fill=(20, 20, 20))
        for x, y, dr in HOLES:
            cx, cy = P(x, y)
            d.ellipse([cx - dr / 2 * S, cy - dr / 2 * S, cx + dr / 2 * S, cy + dr / 2 * S], fill=(20, 20, 20),
                      outline="white")
        for k in failed:
            net, w, terms = ROUTES[k]
            a, b = pad(terms[0][0]), pad(terms[-1][0])
            d.line([P(*a[:2]), P(*b[:2])], fill=(255, 255, 0), width=2)

    view(M, False)
    view(2 * M + W * S, True)
    d.text((M, M + H * S + 8), "COMPONENT SIDE (camera rear): parts, and the copper behind them coloured by net",
           fill="white", font=font)
    d.text((2 * M + W * S, M + H * S + 8), "COPPER SIDE, mirrored, as you'll see it on the mill", fill="white",
           font=font)
    d.text((M, M + H * S + 30), f"{98.71:g} x 67 mm. Traces {SIG_W} mm signal, {PWR_W} mm power, {CLEAR} mm "
           "clearance. Red 5V, orange battery, blue GND, magenta 3V3, green EN. Yellow = jumper wire.",
           fill=(200, 200, 200), font=small)
    img.save(path)


def main():
    print("routing...")
    r, failed = autoroute()
    worst, edge = drc(r.tracks)
    print(f"closest copper between nets: {worst[0]:.3f} mm ({worst[1]} / {worst[2]})")
    print(f"closest copper to an edge, slot or hole: {edge[0]:.3f} mm ({edge[1]})")
    if failed:
        print("needs jumper wires:", [ROUTES[k][0] + " " + " -> ".join(t[0] for t in ROUTES[k][2]) for k in failed])
    with open(os.path.join(HERE, f"{NAME}.sch"), "w") as fh:
        fh.write(schematic())
    with open(os.path.join(HERE, f"{NAME}.brd"), "w") as fh:
        fh.write(board(r.tracks))
    with open(os.path.join(HERE, f"{NAME}.lbr"), "w") as fh:
        fh.write(head() + library(False) + "</drawing></eagle>\n")
    gerbers(r.tracks, os.path.join(HERE, "gerber"))
    preview(r.tracks, failed, os.path.join(HERE, "preview.png"))
    with open(os.path.join(HERE, "layout.json"), "w") as fh:        # used to draw the Fusion sketches
        json.dump({"parts": {k: {"value": v["value"], "pads": v["pads"], "body": v["body"]}
                             for k, v in PARTS.items()},
                   "holes": HOLES, "outline": OUTLINE, "slot": SLOT,
                   "tracks": r.tracks}, fh)
    print("wrote", f"{NAME}.sch/.brd/.lbr, gerber/, preview.png, layout.json")


if __name__ == "__main__":
    main()
