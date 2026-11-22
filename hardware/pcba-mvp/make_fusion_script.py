"""Writes fusion_sketches.py from layout.json (run after make_pcba.py)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "layout.json")))
d.pop("tracks")
d["parts"] = {k: v for k, v in d["parts"].items() if k != "J1"}
rnd = lambda o: round(o, 3) if isinstance(o, float) else [rnd(i) for i in o] if isinstance(o, list) else {k: rnd(v) for k, v in o.items()} if isinstance(o, dict) else o
t = open(os.path.join(HERE, "fusion_sketches.py.tmpl")).read().replace("__DATA__", repr(json.dumps(rnd(d))))
open(os.path.join(HERE, "fusion_sketches.py"), "w").write(t)
print("wrote fusion_sketches.py", len(t))
