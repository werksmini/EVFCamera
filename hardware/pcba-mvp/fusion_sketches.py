"""Fusion script: draws the MVP board layout as sketches in the open "PCBA" design (XZ plane, the
same convention as the "Pi" and "Skeleton" sketches: sketch x = board X, sketch y = -board Y, mm).
Replaces the sketches it drew before (matched by name); leaves every other sketch alone. Does not save.
Data comes from layout.json, written by make_pcba.py; regenerate this file with make_fusion_script.py."""
import adsk.core, adsk.fusion, json
L = json.loads('{"parts": {"SW1": {"value": "FN", "pads": {"1": [18.75, 53.0, 2.0, 1.0, "round"], "2": [18.75, 45.0, 2.0, 1.0, "round"], "3": [23.25, 53.0, 2.0, 1.0, "round"], "4": [23.25, 45.0, 2.0, 1.0, "round"]}, "body": [[17.5, 45.5, 24.5, 52.5]]}, "SW2": {"value": "MENU", "pads": {"1": [30.75, 53.0, 2.0, 1.0, "round"], "2": [30.75, 45.0, 2.0, 1.0, "round"], "3": [35.25, 53.0, 2.0, 1.0, "round"], "4": [35.25, 45.0, 2.0, 1.0, "round"]}, "body": [[29.5, 45.5, 36.5, 52.5]]}, "SW3": {"value": "PLAY", "pads": {"1": [30.75, 41.0, 2.0, 1.0, "round"], "2": [30.75, 33.0, 2.0, 1.0, "round"], "3": [35.25, 41.0, 2.0, 1.0, "round"], "4": [35.25, 33.0, 2.0, 1.0, "round"]}, "body": [[29.5, 33.5, 36.5, 40.5]]}, "SW5": {"value": "SHUTTER", "pads": {"1": [58.75, 53.0, 2.0, 1.0, "round"], "2": [58.75, 45.0, 2.0, 1.0, "round"], "3": [63.25, 53.0, 2.0, 1.0, "round"], "4": [63.25, 45.0, 2.0, 1.0, "round"]}, "body": [[57.5, 45.5, 64.5, 52.5]]}, "SW4": {"value": "D-PAD", "pads": {"1": [41.85, 46.25, 2.2, 1.2, "round"], "2": [41.85, 43.0, 2.4, 1.4, "round"], "3": [41.85, 39.75, 2.2, 1.2, "round"], "6": [52.15, 46.25, 2.2, 1.2, "round"], "5": [52.15, 43.0, 2.4, 1.4, "round"], "4": [52.15, 39.75, 2.2, 1.2, "round"]}, "body": [[42.0, 38.0, 52.0, 48.0]]}, "SW6": {"value": "POWER", "pads": {"1": [-0.8, 48.7, 1.4, 0.9, "longh"], "2": [-0.8, 46.7, 1.4, 0.9, "longh"], "3": [-0.8, 44.7, 1.4, 0.9, "longh"], "T1": [-0.8, 50.8, 2.6, 1.5, "round"], "T2": [-0.8, 42.6, 2.6, 1.5, "round"]}, "body": [[-3.0, 42.4, 1.4, 51.0]]}, "U1": {"value": "ADAFRUIT 6106", "pads": {"EN": [84.005, 16.51, 1.8, 1.0, "round"], "5V": [86.545, 16.51, 1.8, 1.0, "round"], "VBAT": [89.085, 16.51, 1.8, 1.0, "round"], "GND": [91.625, 16.51, 1.8, 1.0, "round"], "D+": [94.165, 16.51, 1.8, 1.0, "round"], "D-": [96.705, 16.51, 1.8, 1.0, "round"], "VBUS": [99.245, 16.51, 1.8, 1.0, "round"], "VIN": [101.785, 16.51, 1.8, 1.0, "square"]}, "body": [[78.29, 0, 107.5, 19.05]]}, "U2": {"value": "ADAFRUIT 5580", "pads": {"VCC": [85.275, 40.55, 1.8, 1.0, "square"], "GND": [85.275, 38.01, 1.8, 1.0, "round"], "SCL": [85.275, 35.47, 1.8, 1.0, "round"], "SDA": [85.275, 32.93, 1.8, 1.0, "round"], "BAT": [94.165, 35.47, 1.8, 1.0, "round"], "BGND": [94.165, 32.93, 1.8, 1.0, "round"]}, "body": [[82.735, 21.5, 103.055, 46.9]]}}, "holes": [[3.5, 3.5, 2.75], [61.5, 3.5, 2.75], [3.5, 26.5, 2.75], [61.5, 26.5, 2.75], [80.83, 2.54, 2.75], [104.96, 2.54, 2.75], [80.83, 16.51, 2.75], [104.96, 16.51, 2.75], [85.275, 24.04, 2.75], [85.275, 44.36, 2.75], [100.515, 24.04, 2.75], [100.515, 44.36, 2.75]], "outline": [[-3.0, 0.0], [107.5, 0.0], [107.5, 55.0], [-3.0, 55.0]], "slot": [[72.0, 5.0], [78.0, 5.0], [78.0, 25.0], [72.0, 25.0]]}')
NAMES = {"SW1": "Button Fn", "SW2": "Button Menu", "SW3": "Button Play", "SW4": "D-pad 504",
         "SW5": "Button Shutter", "SW6": "Power switch", "U1": "Charger 6106", "U2": "Fuel gauge 5580"}
OLD = list(NAMES.values()) + ["Mounting holes (corrected)", "Mounting holes", "Board outline + ribbon slot",
                              "Board outline + ribbon cut-out"]


def P(x, y):
    return adsk.core.Point3D.create(x / 10.0, -y / 10.0, 0)


def run(_context: str):
    app = adsk.core.Application.get()
    doc = [d for d in app.documents if d.name == "PCBA"][0]
    doc.activate()
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for name in OLD:
        s = root.sketches.itemByName(name)
        if s:
            s.deleteMe()

    def sk(name):
        s = root.sketches.add(root.xZConstructionPlane)
        s.name = name
        s.isComputeDeferred = True
        return s

    def rect(s, x0, y0, x1, y1):
        s.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))

    def poly(s, pts):
        for a, b in zip(pts, pts[1:] + pts[:1]):
            s.sketchCurves.sketchLines.addByTwoPoints(P(*a), P(*b))

    for ref, pt in L["parts"].items():
        if ref not in NAMES:
            continue
        s = sk(NAMES[ref])
        for name, (x, y, dia, drill, shape) in pt["pads"].items():
            c = s.sketchCurves.sketchCircles
            c.addByCenterRadius(P(x, y), drill / 20.0)
            if shape == "square":
                rect(s, x - dia / 2, y - dia / 2, x + dia / 2, y + dia / 2)
            elif shape == "long":
                rect(s, x - dia / 2, y - dia, x + dia / 2, y + dia)
            elif shape == "longh":
                rect(s, x - dia, y - dia / 2, x + dia, y + dia / 2)
            else:
                c.addByCenterRadius(P(x, y), dia / 20.0)
        for x0, y0, x1, y1 in pt["body"]:
            rect(s, x0, y0, x1, y1)
        s.isComputeDeferred = False
    s = sk("Mounting holes")
    for x, y, dd in L["holes"]:
        s.sketchCurves.sketchCircles.addByCenterRadius(P(x, y), dd / 20.0)
    s.isComputeDeferred = False
    s = sk("Board outline + ribbon cut-out")
    poly(s, [tuple(p) for p in L["outline"]])
    poly(s, [tuple(p) for p in L["slot"]])
    s.isComputeDeferred = False
    print("sketches:", [x.name for x in root.sketches])
