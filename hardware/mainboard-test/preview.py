"""Draw a top-view PNG of mainboard_test.brd: outline, pads, part boxes and airwires (unrouted connections).
Also prints the tightest pad spacing, as a quick check for isolation milling.

    python3 preview.py  -> mainboard_preview.png
"""
import itertools
import math
import os

from lxml import etree
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
brd = etree.parse(os.path.join(HERE, "mainboard_test.brd"))

pk = {p.get("name"): [(pd.get("name"), float(pd.get("x")), float(pd.get("y")), float(pd.get("diameter")))
                      for pd in p.iter("pad")] for p in brd.iter("package")}
pads, parts = {}, {}
for e in brd.iter("element"):
    x0, y0 = float(e.get("x")), float(e.get("y"))
    rot = math.radians(int((e.get("rot") or "R0")[1:]))
    c, s = math.cos(rot), math.sin(rot)
    pts = []
    for n, px, py, d in pk[e.get("package")]:
        p = (x0 + px * c - py * s, y0 + px * s + py * c, d)
        pads[(e.get("name"), n)] = p
        pts.append(p)
    parts[e.get("name")] = (e.get("value"), pts)
net_of = {(cr.get("element"), cr.get("pad")): sg.get("name") for sg in brd.iter("signal") for cr in sg.iter("contactref")}
xs = [float(w.get(k)) for w in brd.iter("wire") if w.get("layer") == "20" for k in ("x1", "x2")]
ys = [float(w.get(k)) for w in brd.iter("wire") if w.get("layer") == "20" for k in ("y1", "y2")]
W, H = max(xs), max(ys)

gaps = sorted((math.dist(a[:2], b[:2]) - (a[2] + b[2]) / 2, ka, kb)
              for (ka, a), (kb, b) in itertools.combinations(pads.items(), 2)
              if ka[0] != kb[0] and not (net_of.get(ka) and net_of.get(ka) == net_of.get(kb)))
print(f"closest copper between different parts: {gaps[0][0]:.2f} mm ({gaps[0][1]}, {gaps[0][2]})")

S, M = 12, 30
img = Image.new("RGB", (int(W * S) + 2 * M, int(H * S) + 2 * M + 40), (24, 60, 40))
d = ImageDraw.Draw(img)
X = lambda x: M + x * S
Y = lambda y: M + (H - y) * S
d.rectangle([X(0), Y(H), X(W), Y(0)], fill=(206, 168, 96), outline="black", width=2)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)

nets = {}
for k, v in pads.items():
    if net_of.get(k):
        nets.setdefault(net_of[k], []).append(v[:2])
for n, pts in nets.items():                       # airwires as a minimum spanning tree, like the PCB editor
    done, rest = [pts[0]], pts[1:]
    col = (40, 40, 200) if n == "GND" else (200, 40, 40) if n.startswith("+") else (70, 70, 70)
    while rest:
        a, b = min(((a, b) for a in done for b in rest), key=lambda ab: math.dist(*ab))
        d.line([X(a[0]), Y(a[1]), X(b[0]), Y(b[1])], fill=col, width=1)
        done.append(b)
        rest.remove(b)
for (part, pad), (x, y, dia) in pads.items():
    r = dia / 2 * S
    shape = d.rectangle if pad == "1" and not part.startswith("SW") else d.ellipse
    shape([X(x) - r, Y(y) - r, X(x) + r, Y(y) + r], fill=(184, 115, 51), outline="black")
    d.ellipse([X(x) - 0.5 * S, Y(y) - 0.5 * S, X(x) + 0.5 * S, Y(y) + 0.5 * S], fill=(30, 30, 30))
for name, (value, pts) in parts.items():
    cx = sum(p[0] for p in pts) / len(pts)
    top = max(p[1] for p in pts)
    if name.startswith("SW"):
        d.rectangle([X(cx - 3), Y(top + 0.75), X(cx + 3), Y(top - 5.25)], outline="white")
        label, ly = value.upper(), top + 2.2
    elif name == "J1":
        label, ly = "J1  Pi Zero 2 W header (odd pins on the lower row)", top + 2.2
    else:
        label, ly = f"{name} {value}", top + 2.2
    lx = min(max(cx, 8), W - 8)
    d.text((X(lx), Y(ly)), label, fill="white", font=font, anchor="mm", stroke_width=2, stroke_fill="black")
d.text((M, img.height - 30), f"{W:g} x {H:g} mm, top view.  Airwires (unrouted): grey = signals, blue = GND, "
       "red = power.  Square pad = pin 1.", fill="white", font=small)
img.save(os.path.join(HERE, "mainboard_preview.png"))
print("wrote mainboard_preview.png")
