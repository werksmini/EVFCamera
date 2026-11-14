# Bouldering-hold grips

Seeded generator for smooth, brightly coloured grips that bolt onto the camera body, shaped like cast climbing holds.
Output: watertight STL in **millimetres** (set Unit Type = Millimeter when inserting into Fusion).

![front](front_sheet.png)
![rear](rear_sheet.png)

## Styles (sized for the slimmer body)

| Style | Shape | Finished size W × H × depth | Screw |
| --- | --- | --- | --- |
| `front-crimp` | Rounded square edge on the lens side, top leans over it, flatter face behind | ~14–18 × 44–54 × 6 mm | M2.5 |
| `front-pinch` | Narrow fin with two rounded flanks | ~12–14 × 44–54 × 6–7 mm | M2.5 |
| `rear-crimp` | Small thumb edge on the EVF side | ~11–14 × 18–22 × 4.5 mm | M2 |
| `rear-sloper` | Low dome with a shallow thumb dish | ~12–14 × 18–22 × 4.5 mm | M2 |

Each comes as **2-bolt** or **1-bolt**.

## Standard hole patterns (three tapped holes in a vertical line)

| | Front | Rear |
| --- | --- | --- |
| Body holes | M2.5 at y = −10, 0, +10 mm | M2 at y = −5, 0, +5 mm |
| 2-bolt grip | SHCS at ±10 (20 mm spacing) | SHCS at ±5 (10 mm spacing) |
| 1-bolt grip | SHCS at 0 + M2.5 × 4 set screw, 2.5 mm proud, at +10 | SHCS at 0 + M2 × 3 set screw, 2 mm proud, at +5 |
| Clearance hole / counterbore | Ø2.8 / Ø4.9 (head Ø4.5) | Ø2.4 / Ø4.1 (head Ø3.8) |
| Material under head (seat) | 1.8 mm | 1.2 mm |
| Screw, ~4 mm thread engagement | M2.5 × 6 | M2 × 5 |
| Locator pocket | Ø2.9 × 2.8 mm | Ø2.4 × 2.3 mm |

The holes are close fits that allow for MJF printing ~0.1 mm small. Every grip is checked for:
- head ≥ 0.3 mm below the surface;
- side wall around the counterbore ≥ 1.5 mm (front) or 1.2 mm (rear);
- ≥ 1.2 mm of material over the locator pocket.

## Use

```bash
pip install numpy scipy scikit-image trimesh matplotlib
python3 gripgen.py front-crimp --bolts 2 --good 3     # first 3 seeds passing every check -> out/*.stl + .json
python3 gripgen.py rear-sloper --bolts 1 --seeds 5    # one specific design
python3 sheet.py front front_sheet.png                # contact sheet: every front style x bolt count
```

A name like `front-crimp-2b_s01` always regenerates the same grip.

## How it works (v2)

Each grip is one continuous swept form, described as a signed distance field (negative inside, positive outside):

1. **Spine:** a gently curved line up the grip (a bow plus a slight S-bend).
2. **Envelope:** width and height taper to rounded ends along the spine (a superellipse), and one end can be fuller than the other, giving the bean shape.
3. **Cross-section** swept along the spine:
   - **crimp:** squarer on the edge side, softer on the back, sheared so the top overhangs the edge;
   - **pinch:** a tall rounded section with a slight waist;
   - **sloper:** a low dome with a dish cut in.
4. **Fasteners:** no bosses (they showed as bumps on thin grips). Each grip is shifted so its thickest part sits over the hole line, and seeds too thin to carry the screws are rejected. The mating face is cut flat at z = 0, and the holes are cut last, exactly.
5. **Checks on every seed:**
   - see the limits under the hole patterns above.
6. **Mesh:** marching cubes on a 0.25 mm grid, keeping the largest piece.

Nothing random is added to the surface, so curvature stays continuous. `gripgen_v1.py` is the earlier lumpy, blob-based generator.

Coordinates: x across the camera (−x = lens side on the front, EVF side on the rear), y up, z out of the body. For the other hand, mirror x.

## Into Fusion

**Insert > Insert Mesh**, set **Unit Type = Millimeter**, then place the flat face on the body.
To get a solid: **Mesh > Modify > Convert Mesh** (Faceted), or Remesh first and then convert (Organic).

## Making them

- **MJF PA12:** tough, with a slight grain that suits the look.
- **For fluoro colours:**
  - print in white and dye it (RIT DyeMore), or
  - cast pigmented urethane from a silicone mould of an MJF master.
