"""Fusion script: draws the MVP board layout as sketches in the open "PCBA" design (XZ plane, the
same convention as the hand-drawn "Pi" sketch: sketch x = board X, sketch y = -board Y, mm).
One sketch per part plus corrected mounting holes and the outline. Does not save.
Run from Utilities > Scripts and Add-Ins, or paste into the Fusion MCP script tool.
Data comes from layout.json, written by make_pcba.py."""
import adsk.core, adsk.fusion, json
L = json.loads('{"parts": {"J1": {"value": "PI ZERO 2 W", "pads": {"1": [8.37, 25.23, 1.6, 1.0, "round"], "2": [8.37, 27.77, 1.8, 1.0, "round"], "3": [10.91, 25.23, 1.8, 1.0, "round"], "4": [10.91, 27.77, 1.8, 1.0, "round"], "5": [13.45, 25.23, 1.8, 1.0, "round"], "6": [13.45, 27.77, 1.8, 1.0, "round"], "7": [15.989999999999998, 25.23, 1.8, 1.0, "round"], "8": [15.989999999999998, 27.77, 1.8, 1.0, "round"], "9": [18.53, 25.23, 1.8, 1.0, "round"], "10": [18.53, 27.77, 1.8, 1.0, "round"], "11": [21.07, 25.23, 1.8, 1.0, "round"], "12": [21.07, 27.77, 1.8, 1.0, "round"], "13": [23.61, 25.23, 1.8, 1.0, "round"], "14": [23.61, 27.77, 1.8, 1.0, "round"], "15": [26.15, 25.23, 1.8, 1.0, "round"], "16": [26.15, 27.77, 1.8, 1.0, "round"], "17": [28.689999999999998, 25.23, 1.8, 1.0, "round"], "18": [28.689999999999998, 27.77, 1.8, 1.0, "round"], "19": [31.229999999999997, 25.23, 1.8, 1.0, "round"], "20": [31.229999999999997, 27.77, 1.8, 1.0, "round"], "21": [33.769999999999996, 25.23, 1.8, 1.0, "round"], "22": [33.769999999999996, 27.77, 1.8, 1.0, "round"], "23": [36.31, 25.23, 1.8, 1.0, "round"], "24": [36.31, 27.77, 1.8, 1.0, "round"], "25": [38.85, 25.23, 1.8, 1.0, "round"], "26": [38.85, 27.77, 1.8, 1.0, "round"], "27": [41.39, 25.23, 1.8, 1.0, "round"], "28": [41.39, 27.77, 1.8, 1.0, "round"], "29": [43.93, 25.23, 1.8, 1.0, "round"], "30": [43.93, 27.77, 1.8, 1.0, "round"], "31": [46.47, 25.23, 1.8, 1.0, "round"], "32": [46.47, 27.77, 1.8, 1.0, "round"], "33": [49.01, 25.23, 1.8, 1.0, "round"], "34": [49.01, 27.77, 1.8, 1.0, "round"], "35": [51.55, 25.23, 1.8, 1.0, "round"], "36": [51.55, 27.77, 1.8, 1.0, "round"], "37": [54.089999999999996, 25.23, 1.8, 1.0, "round"], "38": [54.089999999999996, 27.77, 1.8, 1.0, "round"], "39": [56.629999999999995, 25.23, 1.8, 1.0, "round"], "40": [56.629999999999995, 27.77, 1.8, 1.0, "round"]}, "body": [[0, 0, 65, 30]]}, "SW1": {"value": "FN", "pads": {"1": [17.25, 58.6, 2.0, 1.0, "round"], "2": [17.25, 50.6, 2.0, 1.0, "round"], "3": [21.75, 58.6, 2.0, 1.0, "round"], "4": [21.75, 50.6, 2.0, 1.0, "round"]}, "body": [[16.0, 51.1, 23.0, 58.1]]}, "SW2": {"value": "MENU", "pads": {"1": [30.29, 58.6, 2.0, 1.0, "round"], "2": [30.29, 50.6, 2.0, 1.0, "round"], "3": [34.79, 58.6, 2.0, 1.0, "round"], "4": [34.79, 50.6, 2.0, 1.0, "round"]}, "body": [[29.04, 51.1, 36.04, 58.1]]}, "SW3": {"value": "PLAY", "pads": {"1": [30.29, 47.6, 2.0, 1.0, "round"], "2": [30.29, 39.6, 2.0, 1.0, "round"], "3": [34.79, 47.6, 2.0, 1.0, "round"], "4": [34.79, 39.6, 2.0, 1.0, "round"]}, "body": [[29.04, 40.1, 36.04, 47.1]]}, "SW5": {"value": "SHUTTER", "pads": {"1": [57.75, 50.5, 2.0, 1.0, "round"], "2": [57.75, 42.5, 2.0, 1.0, "round"], "3": [62.25, 50.5, 2.0, 1.0, "round"], "4": [62.25, 42.5, 2.0, 1.0, "round"]}, "body": [[56.5, 43.0, 63.5, 50.0]]}, "SW4": {"value": "D-PAD", "pads": {"1": [41.050000000000004, 49.75, 2.2, 1.2, "round"], "2": [41.050000000000004, 46.5, 2.4, 1.4, "round"], "3": [41.050000000000004, 43.25, 2.2, 1.2, "round"], "6": [51.35, 49.75, 2.2, 1.2, "round"], "5": [51.35, 46.5, 2.4, 1.4, "round"], "4": [51.35, 43.25, 2.2, 1.2, "round"]}, "body": [[41.2, 41.5, 51.2, 51.5]]}, "SW6": {"value": "POWER", "pads": {"1": [76.0, 59.8, 1.4, 0.9, "long"], "2": [78.0, 59.8, 1.4, 0.9, "long"], "3": [80.0, 59.8, 1.4, 0.9, "long"], "T1": [73.9, 59.8, 2.6, 1.5, "round"], "T2": [82.1, 59.8, 2.6, 1.5, "round"]}, "body": [[73.7, 57.599999999999994, 82.3, 62.0]]}, "U1": {"value": "ADAFRUIT 6106", "pads": {"EN": [75.215, 11.51, 1.8, 1.0, "round"], "5V": [77.755, 11.51, 1.8, 1.0, "round"], "VBAT": [80.295, 11.51, 1.8, 1.0, "round"], "GND": [82.835, 11.51, 1.8, 1.0, "round"], "D+": [85.375, 11.51, 1.8, 1.0, "round"], "D-": [87.915, 11.51, 1.8, 1.0, "round"], "VBUS": [90.455, 11.51, 1.8, 1.0, "round"], "VIN": [92.995, 11.51, 1.8, 1.0, "square"]}, "body": [[69.5, -5, 98.71, 14.05]]}, "U2": {"value": "ADAFRUIT 5580", "pads": {"VCC": [72.54, 35.05, 1.8, 1.0, "square"], "GND": [72.54, 32.51, 1.8, 1.0, "round"], "SCL": [72.54, 29.97, 1.8, 1.0, "round"], "SDA": [72.54, 27.43, 1.8, 1.0, "round"], "INT": [72.54, 24.89, 1.8, 1.0, "round"], "QSTART": [72.54, 22.35, 1.8, 1.0, "round"], "BAT": [81.43, 29.97, 1.8, 1.0, "round"], "BGND": [81.43, 27.43, 1.8, 1.0, "round"]}, "body": [[70, 16, 90.32, 41.4]]}}, "holes": [[3.5, 3.5, 2.75], [61.5, 3.5, 2.75], [3.5, 26.5, 2.75], [61.5, 26.5, 2.75], [72.04, -2.46, 2.75], [96.17, -2.46, 2.75], [72.04, 11.51, 2.75], [96.17, 11.51, 2.75]], "outline": [[0, 0], [68.5, 0], [68.5, -5], [98.71, -5], [98.71, 62], [0, 62]], "slot": [[83.5, 47.0], [97.0, 47.0], 1.6]}')
NAMES = {"J1": "Pi socket J1", "SW1": "Button Fn", "SW2": "Button Menu", "SW3": "Button Play (layout)",
         "SW4": "D-pad 504", "SW5": "Button Shutter", "SW6": "Power switch", "U1": "Charger 6106", "U2": "Fuel gauge 5580"}

def P(x, y):
    return adsk.core.Point3D.create(x / 10.0, -y / 10.0, 0)

def run(_context: str):
    app = adsk.core.Application.get()
    doc = [d for d in app.documents if d.name == "PCBA"][0]
    doc.activate()
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    plane = root.xZConstructionPlane
    def sk(name):
        s = root.sketches.add(plane)
        s.name = name
        s.isComputeDeferred = True
        return s
    def rect(s, x0, y0, x1, y1):
        s.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))
    for ref, pt in L["parts"].items():
        if ref in ("J1", "SW3"):          # already in the user's "Pi" and "Button - Soft Tactile" sketches
            continue
        s = sk(NAMES[ref])
        for name, (x, y, dia, drill, shape) in pt["pads"].items():
            c = s.sketchCurves.sketchCircles
            c.addByCenterRadius(P(x, y), drill / 20.0)
            if shape == "square":
                rect(s, x - dia/2, y - dia/2, x + dia/2, y + dia/2)
            elif shape == "long":
                rect(s, x - dia/2, y - dia, x + dia/2, y + dia)
            else:
                c.addByCenterRadius(P(x, y), dia / 20.0)
        for x0, y0, x1, y1 in pt["body"]:
            rect(s, x0, y0, x1, y1)
        s.isComputeDeferred = False
    s = sk("Mounting holes (corrected)")
    for x, y, dd in L["holes"]:
        s.sketchCurves.sketchCircles.addByCenterRadius(P(x, y), dd / 20.0)
    s.isComputeDeferred = False
    s = sk("Board outline + ribbon slot")
    o = L["outline"]
    for a, b in zip(o, o[1:] + o[:1]):
        s.sketchCurves.sketchLines.addByTwoPoints(P(*a), P(*b))
    (ax, ay), (bx, by), w = L["slot"]
    ln = s.sketchCurves.sketchLines
    r = w / 2
    ln.addByTwoPoints(P(ax, ay + r), P(bx, by + r))
    ln.addByTwoPoints(P(ax, ay - r), P(bx, by - r))
    arcs = s.sketchCurves.sketchArcs
    arcs.addByThreePoints(P(bx, by + r), P(bx + r, by), P(bx, by - r))
    arcs.addByThreePoints(P(ax, ay + r), P(ax - r, ay), P(ax, ay - r))
    s.isComputeDeferred = False
    print("sketches:", [x.name for x in root.sketches])
