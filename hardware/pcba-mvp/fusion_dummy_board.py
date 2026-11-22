"""Fusion script: a "Dummy board (print)" sketch in PCBA with the board outline, ribbon cut-out and every
through hole. Hole sizes are user parameters (nominal + print_clearance) so a 3D-printed placement dummy
can be tuned. Does not save. Data from layout.json (make_pcba.py)."""
import adsk.core, adsk.fusion, json
D = json.loads('{"holes": [[8.37, 25.23, 1.0, "J1.1"], [8.37, 27.77, 1.0, "J1.2"], [10.91, 25.23, 1.0, "J1.3"], [10.91, 27.77, 1.0, "J1.4"], [13.45, 25.23, 1.0, "J1.5"], [13.45, 27.77, 1.0, "J1.6"], [15.99, 25.23, 1.0, "J1.7"], [15.99, 27.77, 1.0, "J1.8"], [18.53, 25.23, 1.0, "J1.9"], [18.53, 27.77, 1.0, "J1.10"], [21.07, 25.23, 1.0, "J1.11"], [21.07, 27.77, 1.0, "J1.12"], [23.61, 25.23, 1.0, "J1.13"], [23.61, 27.77, 1.0, "J1.14"], [26.15, 25.23, 1.0, "J1.15"], [26.15, 27.77, 1.0, "J1.16"], [28.69, 25.23, 1.0, "J1.17"], [28.69, 27.77, 1.0, "J1.18"], [31.23, 25.23, 1.0, "J1.19"], [31.23, 27.77, 1.0, "J1.20"], [33.77, 25.23, 1.0, "J1.21"], [33.77, 27.77, 1.0, "J1.22"], [36.31, 25.23, 1.0, "J1.23"], [36.31, 27.77, 1.0, "J1.24"], [38.85, 25.23, 1.0, "J1.25"], [38.85, 27.77, 1.0, "J1.26"], [41.39, 25.23, 1.0, "J1.27"], [41.39, 27.77, 1.0, "J1.28"], [43.93, 25.23, 1.0, "J1.29"], [43.93, 27.77, 1.0, "J1.30"], [46.47, 25.23, 1.0, "J1.31"], [46.47, 27.77, 1.0, "J1.32"], [49.01, 25.23, 1.0, "J1.33"], [49.01, 27.77, 1.0, "J1.34"], [51.55, 25.23, 1.0, "J1.35"], [51.55, 27.77, 1.0, "J1.36"], [54.09, 25.23, 1.0, "J1.37"], [54.09, 27.77, 1.0, "J1.38"], [56.63, 25.23, 1.0, "J1.39"], [56.63, 27.77, 1.0, "J1.40"], [18.75, 53.0, 1.0, "SW1.1"], [18.75, 45.0, 1.0, "SW1.2"], [23.25, 53.0, 1.0, "SW1.3"], [23.25, 45.0, 1.0, "SW1.4"], [30.75, 53.0, 1.0, "SW2.1"], [30.75, 45.0, 1.0, "SW2.2"], [35.25, 53.0, 1.0, "SW2.3"], [35.25, 45.0, 1.0, "SW2.4"], [30.75, 41.0, 1.0, "SW3.1"], [30.75, 33.0, 1.0, "SW3.2"], [35.25, 41.0, 1.0, "SW3.3"], [35.25, 33.0, 1.0, "SW3.4"], [58.75, 53.0, 1.0, "SW5.1"], [58.75, 45.0, 1.0, "SW5.2"], [63.25, 53.0, 1.0, "SW5.3"], [63.25, 45.0, 1.0, "SW5.4"], [41.85, 46.25, 1.2, "SW4.1"], [41.85, 43.0, 1.4, "SW4.2"], [41.85, 39.75, 1.2, "SW4.3"], [52.15, 46.25, 1.2, "SW4.6"], [52.15, 43.0, 1.4, "SW4.5"], [52.15, 39.75, 1.2, "SW4.4"], [-0.8, 48.7, 0.9, "SW6.1"], [-0.8, 46.7, 0.9, "SW6.2"], [-0.8, 44.7, 0.9, "SW6.3"], [-0.8, 50.8, 1.5, "SW6.T1"], [-0.8, 42.6, 1.5, "SW6.T2"], [84.005, 16.51, 1.0, "U1.EN"], [86.545, 16.51, 1.0, "U1.5V"], [89.085, 16.51, 1.0, "U1.VBAT"], [91.625, 16.51, 1.0, "U1.GND"], [94.165, 16.51, 1.0, "U1.D+"], [96.705, 16.51, 1.0, "U1.D-"], [99.245, 16.51, 1.0, "U1.VBUS"], [101.785, 16.51, 1.0, "U1.VIN"], [85.275, 40.55, 1.0, "U2.VCC"], [85.275, 38.01, 1.0, "U2.GND"], [85.275, 35.47, 1.0, "U2.SCL"], [85.275, 32.93, 1.0, "U2.SDA"], [94.165, 35.47, 1.0, "U2.BAT"], [94.165, 32.93, 1.0, "U2.BGND"], [3.5, 3.5, 2.75, "screw"], [61.5, 3.5, 2.75, "screw"], [3.5, 26.5, 2.75, "screw"], [61.5, 26.5, 2.75, "screw"], [80.83, 2.54, 2.75, "screw"], [104.96, 2.54, 2.75, "screw"], [80.83, 16.51, 2.75, "screw"], [104.96, 16.51, 2.75, "screw"], [85.275, 24.04, 2.75, "screw"], [85.275, 44.36, 2.75, "screw"], [100.515, 24.04, 2.75, "screw"], [100.515, 44.36, 2.75, "screw"]], "outline": [[-3.0, 0.0], [107.5, 0.0], [107.5, 55.0], [-3.0, 55.0]], "slot": [[72.0, 5.0], [78.0, 5.0], [78.0, 25.0], [72.0, 25.0]]}')
SIZES = {0.9: ("hole_switch_pin", "Slide switch pins"), 1.0: ("hole_pin", "Header and button pins"),
         1.2: ("hole_dpad_corner", "D-pad corner pins"), 1.4: ("hole_dpad_mid", "D-pad middle pins"),
         1.5: ("hole_switch_tab", "Slide switch tabs"), 2.75: ("hole_screw", "M2.5 screw holes")}
NAME = "Dummy board (print)"


def P(x, y):
    return adsk.core.Point3D.create(x / 10.0, -y / 10.0, 0)


def run(_context: str):
    app = adsk.core.Application.get()
    doc = [d for d in app.documents if d.name == "PCBA"][0]
    doc.activate()
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    up = des.userParameters
    if not up.itemByName("print_clearance"):
        up.add("print_clearance", adsk.core.ValueInput.createByString("0.2 mm"), "mm",
               "Added to every hole diameter for the printed dummy")
    for size, (pname, comment) in SIZES.items():
        expr = f"{size} mm + print_clearance"
        p = up.itemByName(pname)
        if p:
            p.expression = expr
        else:
            up.add(pname, adsk.core.ValueInput.createByString(expr), "mm", comment)
    old = root.sketches.itemByName(NAME)
    if old:
        old.deleteMe()
    s = root.sketches.add(root.xZConstructionPlane)
    s.name = NAME
    s.isComputeDeferred = True
    lines = s.sketchCurves.sketchLines
    for poly in (D["outline"], D["slot"]):
        segs = [lines.addByTwoPoints(P(*a), P(*b)) for a, b in zip(poly, poly[1:] + poly[:1])]
        for i, l in enumerate(segs):            # close the loop and pin it in place
            if i:
                s.geometricConstraints.addCoincident(segs[i - 1].endSketchPoint, l.startSketchPoint)
        s.geometricConstraints.addCoincident(segs[-1].endSketchPoint, segs[0].startSketchPoint)
        for l in segs:
            l.isFixed = True
    first = {}
    for x, y, drill, label in D["holes"]:
        c = s.sketchCurves.sketchCircles.addByCenterRadius(P(x, y), drill / 20.0)
        c.centerSketchPoint.isFixed = True
        if drill in first:
            s.geometricConstraints.addEqual(first[drill], c)
        else:
            first[drill] = c
            dim = s.sketchDimensions.addDiameterDimension(c, P(x + 2, y + 2))
            dim.parameter.expression = SIZES[drill][0]
    s.isComputeDeferred = False
    print(NAME, "circles", s.sketchCurves.sketchCircles.count, "profiles", s.profiles.count,
          "fully constrained", s.isFullyConstrained)
    for size, (pname, _) in SIZES.items():
        print(pname, up.itemByName(pname).expression, round(up.itemByName(pname).value * 10, 3), "mm")
