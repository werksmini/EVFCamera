"""Generate the test mainboard as EAGLE 9 XML (.sch + .brd), which Fusion Electronics imports.

    python3 make_mainboard.py          -> mainboard_test.sch, mainboard_test.brd, netlist.csv

Board: 80 x 56 mm, single-sided through-hole, sized for CNC isolation milling.
Parts:  J1  2x20 female header for the Pi Zero 2 W (plugs onto the Pi's pins)
        SW1-SW5  D-pad: up, down, left, right, OK (6x6 mm tact switches)
        SW6 Back/Menu, SW7 Play
        J2 power in, J3 shutter, J4 thumb wheel, J5 front Fn, J6 top knob, J7 I2C sensors
Tact switches are wired diagonally (pads 1 and 4), which works whichever way the switch is rotated.
"""
import csv
import os
from xml.sax.saxutils import quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = "evfcam"
BOARD_W, BOARD_H = 80.0, 56.0

# --- the circuit ---------------------------------------------------------------------------------
# Pi header pin -> net name (GPIO numbers follow the project GPIO map)
PI_PINS = {
    1: "+3V3", 17: "+3V3", 2: "+5V", 4: "+5V",
    **{p: "GND" for p in (6, 9, 14, 20, 25, 30, 34, 39)},
    3: "SDA", 5: "SCL", 7: "SENSOR_INT",
    11: "SHUTTER_HALF", 13: "SHUTTER_FULL",
    15: "BACK", 16: "PLAY",
    18: "WHEEL_A", 22: "WHEEL_B", 12: "WHEEL_PUSH",
    29: "UP", 31: "DOWN", 33: "LEFT", 35: "RIGHT", 37: "OK",
    32: "KNOB_A", 36: "KNOB_B", 38: "KNOB_PUSH",
    40: "FN",
}
GPIO_OF_PIN = {3: 2, 5: 3, 7: 4, 11: 17, 13: 27, 15: 22, 16: 23, 18: 24, 22: 25, 12: 18,
               29: 5, 31: 6, 33: 13, 35: 19, 37: 26, 32: 12, 36: 16, 38: 20, 40: 21}

# name, board x, y, net (the other side of every switch is GND), label
SWITCHES = [
    ("SW1", 62, 34, "UP", "Up"),
    ("SW2", 62, 14, "DOWN", "Down"),
    ("SW3", 52, 24, "LEFT", "Left"),
    ("SW4", 72, 24, "RIGHT", "Right"),
    ("SW5", 62, 24, "OK", "OK"),
    ("SW6", 30, 32, "BACK", "Back/Menu"),
    ("SW7", 30, 18, "PLAY", "Play"),
]

# name, board x (first pin), y, pins (net per pin), value
HEADERS = [
    ("J2", 6, 26, ["+5V", "GND"], "POWER 5V"),
    ("J3", 14, 6, ["SHUTTER_HALF", "SHUTTER_FULL", "GND"], "SHUTTER"),
    ("J4", 36, 6, ["WHEEL_A", "WHEEL_B", "WHEEL_PUSH", "GND"], "WHEEL"),
    ("J5", 77, 36, ["FN", "GND"], "FN"),
    ("J6", 77, 50, ["KNOB_A", "KNOB_B", "KNOB_PUSH", "GND"], "KNOB"),
    ("J7", 6, 40, ["+3V3", "GND", "SDA", "SCL", "SENSOR_INT"], "I2C"),
]
J1_POS = (40.0, 50.0)          # centre of the 2x20 header, along the top edge
HEADER_VERTICAL = {"J2", "J7", "J5", "J6"}   # these run along the left and right edges


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


# --- library: packages, symbols, devices ---------------------------------------------------------
def pkg_pi_header():
    out = ['<package name="PI_HEADER_2X20"><description>2x20 2.54 mm female header for Raspberry Pi. '
           'Odd pins on the lower row, pin 1 square.</description>']
    for n in range(1, 41):
        col = (n - 1) // 2
        x = -24.13 + col * 2.54
        y = -1.27 if n % 2 else 1.27
        shape = "square" if n == 1 else "round"
        out.append(f'<pad name="{n}" x="{f(x)}" y="{f(y)}" drill="1" diameter="1.8" shape="{shape}"/>')
    out.append('<wire x1="-25.4" y1="-2.54" x2="25.4" y2="-2.54" width="0.2" layer="21"/>'
               '<wire x1="25.4" y1="-2.54" x2="25.4" y2="2.54" width="0.2" layer="21"/>'
               '<wire x1="25.4" y1="2.54" x2="-25.4" y2="2.54" width="0.2" layer="21"/>'
               '<wire x1="-25.4" y1="2.54" x2="-25.4" y2="-2.54" width="0.2" layer="21"/>'
               '<text x="-25.4" y="3.2" size="1.27" layer="25">&gt;NAME</text>'
               '<text x="-26.2" y="-2.2" size="1" layer="21" rot="R90">1</text></package>')
    return "".join(out)


def pkg_tact():
    pads = [("1", -3.25, 2.25), ("2", 3.25, 2.25), ("3", -3.25, -2.25), ("4", 3.25, -2.25)]
    out = ['<package name="TACT_6X6_THT"><description>6x6 mm through-hole tact switch, 6.5 x 4.5 mm '
           'pin spacing. Wired on diagonal pads 1 and 4, so it works in any orientation.</description>']
    for name, x, y in pads:
        out.append(f'<pad name="{name}" x="{f(x)}" y="{f(y)}" drill="1" diameter="2" shape="round"/>')
    out.append('<wire x1="-3" y1="-3" x2="3" y2="-3" width="0.2" layer="21"/>'
               '<wire x1="3" y1="-3" x2="3" y2="3" width="0.2" layer="21"/>'
               '<wire x1="3" y1="3" x2="-3" y2="3" width="0.2" layer="21"/>'
               '<wire x1="-3" y1="3" x2="-3" y2="-3" width="0.2" layer="21"/>'
               '<circle x="0" y="0" radius="1.75" width="0.2" layer="21"/>'
               '<text x="-3" y="3.6" size="1.27" layer="25">&gt;NAME</text>'
               '<text x="-3" y="-4.9" size="1" layer="27">&gt;VALUE</text></package>')
    return "".join(out)


def pkg_header(n):
    w = n * 2.54
    out = [f'<package name="HEADER_1X{n}"><description>1x{n} 2.54 mm pin header, pin 1 square.</description>']
    for i in range(n):
        shape = "square" if i == 0 else "round"
        out.append(f'<pad name="{i + 1}" x="{f(i * 2.54)}" y="0" drill="1" diameter="1.8" shape="{shape}"/>')
    out.append(f'<wire x1="-1.27" y1="-1.27" x2="{f(w - 1.27)}" y2="-1.27" width="0.2" layer="21"/>'
               f'<wire x1="{f(w - 1.27)}" y1="-1.27" x2="{f(w - 1.27)}" y2="1.27" width="0.2" layer="21"/>'
               f'<wire x1="{f(w - 1.27)}" y1="1.27" x2="-1.27" y2="1.27" width="0.2" layer="21"/>'
               f'<wire x1="-1.27" y1="1.27" x2="-1.27" y2="-1.27" width="0.2" layer="21"/>'
               f'<text x="-1.27" y="1.8" size="1.27" layer="25">&gt;NAME</text>'
               f'<text x="-1.27" y="-3.2" size="1" layer="27">&gt;VALUE</text></package>')
    return "".join(out)


def sym_pi_header():
    out = ['<symbol name="PI_HEADER">'
           '<wire x1="-7.62" y1="-27.94" x2="7.62" y2="-27.94" width="0.254" layer="94"/>'
           '<wire x1="7.62" y1="-27.94" x2="7.62" y2="27.94" width="0.254" layer="94"/>'
           '<wire x1="7.62" y1="27.94" x2="-7.62" y2="27.94" width="0.254" layer="94"/>'
           '<wire x1="-7.62" y1="27.94" x2="-7.62" y2="-27.94" width="0.254" layer="94"/>'
           '<text x="-7.62" y="29.21" size="1.778" layer="95">&gt;NAME</text>'
           '<text x="-7.62" y="-30.48" size="1.778" layer="96">&gt;VALUE</text>']
    for n in range(1, 41):
        row = (n - 1) // 2
        y = 25.4 - row * 2.54
        if n % 2:
            out.append(f'<pin name="P{n}" x="-10.16" y="{f(y)}" length="short" direction="pas" rot="R0"/>')
        else:
            out.append(f'<pin name="P{n}" x="10.16" y="{f(y)}" length="short" direction="pas" rot="R180"/>')
    out.append("</symbol>")
    return "".join(out)


def pi_pin_xy(n):
    row = (n - 1) // 2
    y = 25.4 - row * 2.54
    return (-10.16, y, -1) if n % 2 else (10.16, y, 1)


SYM_SW = ('<symbol name="SWITCH">'
          '<wire x1="-2.54" y1="0" x2="2.54" y2="1.905" width="0.254" layer="94"/>'
          '<circle x="-2.54" y="0" radius="0.3" width="0.254" layer="94"/>'
          '<circle x="2.54" y="0" radius="0.3" width="0.254" layer="94"/>'
          '<text x="-2.54" y="3.81" size="1.778" layer="95">&gt;NAME</text>'
          '<text x="-2.54" y="-3.81" size="1.778" layer="96">&gt;VALUE</text>'
          '<pin name="A" x="-5.08" y="0" visible="off" length="short" direction="pas" rot="R0"/>'
          '<pin name="B" x="5.08" y="0" visible="off" length="short" direction="pas" rot="R180"/>'
          '</symbol>')


def sym_header(n):
    top = 2.54
    bot = -2.54 * n
    out = [f'<symbol name="HEADER_{n}">'
           f'<wire x1="-2.54" y1="{f(top)}" x2="2.54" y2="{f(top)}" width="0.254" layer="94"/>'
           f'<wire x1="2.54" y1="{f(top)}" x2="2.54" y2="{f(bot)}" width="0.254" layer="94"/>'
           f'<wire x1="2.54" y1="{f(bot)}" x2="-2.54" y2="{f(bot)}" width="0.254" layer="94"/>'
           f'<wire x1="-2.54" y1="{f(bot)}" x2="-2.54" y2="{f(top)}" width="0.254" layer="94"/>'
           f'<text x="-2.54" y="{f(top + 1.27)}" size="1.778" layer="95">&gt;NAME</text>'
           f'<text x="-2.54" y="{f(bot - 3.0)}" size="1.778" layer="96">&gt;VALUE</text>']
    for i in range(n):
        out.append(f'<pin name="{i + 1}" x="-5.08" y="{f(-2.54 * i)}" length="short" direction="pas" rot="R0"/>')
    out.append("</symbol>")
    return "".join(out)


def deviceset(name, prefix, symbol, package, connects, description):
    c = "".join(f'<connect gate="G$1" pin="{pin}" pad="{pad}"/>' for pin, pad in connects)
    return (f'<deviceset name="{name}" prefix="{prefix}"><description>{description}</description>'
            f'<gates><gate name="G$1" symbol="{symbol}" x="0" y="0"/></gates>'
            f'<devices><device name="" package="{package}"><connects>{c}</connects>'
            f'<technologies><technology name=""/></technologies></device></devices></deviceset>')


HEADER_SIZES = sorted({len(h[3]) for h in HEADERS})


def library(for_board):
    pk = pkg_pi_header() + pkg_tact() + "".join(pkg_header(n) for n in HEADER_SIZES)
    if for_board:
        return f'<library name="{LIB}"><packages>{pk}</packages></library>'
    sy = sym_pi_header() + SYM_SW + "".join(sym_header(n) for n in HEADER_SIZES)
    ds = deviceset("PI_HEADER", "J", "PI_HEADER", "PI_HEADER_2X20",
                   [(f"P{n}", str(n)) for n in range(1, 41)], "Raspberry Pi 40-pin header")
    ds += deviceset("TACT_6X6", "SW", "SWITCH", "TACT_6X6_THT", [("A", "1"), ("B", "4")],
                    "6x6 mm tact switch, diagonal pads")
    for n in HEADER_SIZES:
        ds += deviceset(f"HEADER_1X{n}", "J", f"HEADER_{n}", f"HEADER_1X{n}",
                        [(str(i + 1), str(i + 1)) for i in range(n)], f"1x{n} pin header")
    return (f'<library name="{LIB}"><description>EVFCamera test mainboard parts</description>'
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
            '<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" '
            'altdistance="0.01" altunitdist="inch" altunit="inch"/>'
            f'<layers>{layers}</layers>')


CLASSES = '<classes><class number="0" name="default" width="0" drill="0"></class></classes>'


# --- parts list shared by schematic and board ------------------------------------------------------
def parts():
    """name, deviceset, value, [(pin, pad, net)]"""
    out = [("J1", "PI_HEADER", "PI ZERO 2 W",
            [(f"P{n}", str(n), PI_PINS[n]) for n in range(1, 41) if n in PI_PINS])]
    for name, x, y, net, label in SWITCHES:
        out.append((name, "TACT_6X6", label, [("A", "1", net), ("B", "4", "GND")]))
    for name, x, y, nets, value in HEADERS:
        out.append((name, f"HEADER_1X{len(nets)}", value,
                    [(str(i + 1), str(i + 1), nets[i]) for i in range(len(nets))]))
    return out


# --- schematic -----------------------------------------------------------------------------------------
def schematic():
    plist = parts()
    place = {"J1": (60.96, 101.6)}
    for i, (name, *_rest) in enumerate(SWITCHES):
        place[name] = (127.0, 152.4 - i * 12.7)
    for i, (name, *_rest) in enumerate(HEADERS):
        place[name] = (20.32 + (i % 3) * 45.72, 45.72 - (i // 3) * 30.48)
    instances, part_xml = [], []
    nets = {}
    for name, ds, value, pins in plist:
        part_xml.append(f'<part name="{name}" library="{LIB}" deviceset="{ds}" device="" value={quoteattr(value)}/>')
        px, py = place[name]
        instances.append(f'<instance part="{name}" gate="G$1" x="{f(px)}" y="{f(py)}"/>')
        for pin, pad, net in pins:
            if name == "J1":
                sx, sy, d = pi_pin_xy(int(pin[1:]))
            elif ds == "TACT_6X6":
                sx, sy, d = (-5.08, 0, -1) if pin == "A" else (5.08, 0, 1)
            else:
                sx, sy, d = -5.08, -2.54 * (int(pin) - 1), -1
            x1, y1 = px + sx, py + sy
            x2 = x1 + d * 7.62
            label_x = x2 if d > 0 else x2 - 0.0
            seg = (f'<segment><pinref part="{name}" gate="G$1" pin="{pin}"/>'
                   f'<wire x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y1)}" width="0.1524" layer="91"/>'
                   f'<label x="{f(label_x)}" y="{f(y1)}" size="1.27" layer="95"'
                   f'{"" if d > 0 else " rot=" + chr(34) + "R180" + chr(34)} xref="yes"/></segment>')
            nets.setdefault(net, []).append(seg)
    net_xml = "".join(f'<net name="{n}" class="0">{"".join(s)}</net>' for n, s in sorted(nets.items()))
    title = ('<plain><text x="0" y="170" size="3.81" layer="97">EVFCamera test mainboard</text>'
             '<text x="0" y="164" size="1.778" layer="97">Pi Zero 2 W header, D-pad, Back, Play, '
             'connectors for shutter, thumb wheel, Fn, top knob, I2C, 5 V. Nets join by label name.</text></plain>')
    return (head() + '<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">'
            f'<libraries>{library(False)}</libraries><attributes/><variantdefs/>{CLASSES}'
            f'<parts>{"".join(part_xml)}</parts>'
            f'<sheets><sheet>{title}<instances>{"".join(instances)}</instances><busses/>'
            f'<nets>{net_xml}</nets></sheet></sheets></schematic></drawing></eagle>\n')


# --- board -----------------------------------------------------------------------------------------------
def board():
    pos = {"J1": (J1_POS[0], J1_POS[1], "R0")}
    for name, x, y, *_ in SWITCHES:
        pos[name] = (x, y, "R0")
    for name, x, y, *_ in HEADERS:
        rot = "R0"
        if name in HEADER_VERTICAL:
            rot = "R270" if x > BOARD_W / 2 else "R90"     # pin 1 at the top on the right edge
        pos[name] = (x, y, rot)
    pkg_of = {"PI_HEADER": "PI_HEADER_2X20", "TACT_6X6": "TACT_6X6_THT"}
    elements, signals = [], {}
    for name, ds, value, pins in parts():
        x, y, rot = pos[name]
        package = pkg_of.get(ds, ds)
        elements.append(f'<element name="{name}" library="{LIB}" package="{package}" value={quoteattr(value)} '
                        f'x="{f(x)}" y="{f(y)}" rot="{rot}"/>')
        for pin, pad, net in pins:
            signals.setdefault(net, []).append(f'<contactref element="{name}" pad="{pad}"/>')
    outline = [(0, 0, BOARD_W, 0), (BOARD_W, 0, BOARD_W, BOARD_H), (BOARD_W, BOARD_H, 0, BOARD_H), (0, BOARD_H, 0, 0)]
    plain = "".join(f'<wire x1="{f(a)}" y1="{f(b)}" x2="{f(c)}" y2="{f(d)}" width="0" layer="20"/>'
                    for a, b, c, d in outline)
    plain += ('<text x="2" y="52.5" size="1.6" layer="21">EVFCAM MAINBOARD TEST v0.1</text>'
              '<text x="14" y="2.2" size="1" layer="21">SHUTTER H F G</text>'
              '<text x="36" y="2.2" size="1" layer="21">WHEEL A B P G</text>'
              '<text x="70.5" y="31" size="1" layer="21">FN G</text>'
              '<text x="70.5" y="54" size="1" layer="21">KNOB</text>')
    sig_xml = "".join(f'<signal name="{n}">{"".join(c)}</signal>' for n, c in sorted(signals.items()))
    return (head() + f'<board><plain>{plain}</plain><libraries>{library(True)}</libraries>'
            f'<attributes/><variantdefs/>{CLASSES}<elements>{"".join(elements)}</elements>'
            f'<signals>{sig_xml}</signals></board></drawing></eagle>\n')


def netlist_csv(path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["net", "connections"])
        nets = {}
        for name, ds, value, pins in parts():
            for pin, pad, net in pins:
                label = f"{name}.{pad}"
                if name == "J1" and int(pad) in GPIO_OF_PIN:
                    label += f" (GPIO {GPIO_OF_PIN[int(pad)]})"
                nets.setdefault(net, []).append(label)
        for n in sorted(nets):
            w.writerow([n, " ".join(nets[n])])


if __name__ == "__main__":
    for fname, text in (("mainboard_test.sch", schematic()), ("mainboard_test.brd", board())):
        with open(os.path.join(HERE, fname), "w") as fh:
            fh.write(text)
        print("wrote", fname)
    netlist_csv(os.path.join(HERE, "netlist.csv"))
    print("wrote netlist.csv")
