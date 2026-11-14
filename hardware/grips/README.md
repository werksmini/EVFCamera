# Bouldering-hold grips

Seeded generator for smooth, brightly coloured grips that bolt onto the camera body, shaped like cast climbing holds.
Output: watertight STL in **millimetres** (set Unit Type = Millimeter when inserting into Fusion).

![front](front_sheet.png)
![rear](rear_sheet.png)

## Styles

| Style | Shape | Footprint W × H | Height |
| --- | --- | --- | --- |
| `front-crimp` | Rounded square edge on the lens side, top leans over it, face slopes back | 18–24 × 44–54 mm | ~10–14 mm |
| `front-pinch` | Narrow fin with two rounded flanks | 14–18 × 44–54 mm | 11–15 mm |
| `rear-crimp` | Small thumb edge on the EVF side | 16–21 × 31–35 mm | ~7–8 mm |
| `rear-sloper` | Smooth dome with a shallow thumb dish | 18–23 × 31–35 mm | 7–9 mm |

Each comes as **2-bolt** or **1-bolt**.

## Standard hole pattern (the same on every grip position)

Three M2.5 tapped holes in the body, in a vertical line at **y = −10, 0, +10 mm (10 mm pitch)**. Any grip fits any position.

- **2-bolt:** M2.5 SHCS at ±10 mm (20 mm spacing).
- **1-bolt:** M2.5 SHCS in the centre hole. Against rotation, an **M2.5 × 4 set screw** stands 2.5 mm proud in the +10 hole and sits in a Ø3.0 × 3.2 mm pocket in the grip. No pressed dowel needed.
- Grip holes: Ø3.0 clearance, Ø5.2 counterbore (MJF allowance).
- Screws: front M2.5×8, rear M2.5×6 or ×8, assuming ~4 mm of thread in the body.

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
4. **Fasteners:** soft bosses blend in under each fastener. The mating face is cut flat at z = 0, and the holes are cut last, exactly.
5. **Checks on every seed:**
   - ≥ 2.5 mm wall around each counterbore;
   - the screw head ≥ 0.3 mm below the surface;
   - ≥ 1.5 mm of material over the locator pocket.
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
