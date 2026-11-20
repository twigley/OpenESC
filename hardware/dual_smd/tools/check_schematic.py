#!/usr/bin/env python3
"""Rebuild connectivity of kicad/dual_esc.kicad_sch the way KiCad does and
compare it with the intended netlist in gen_schematic.PARTS.

Rules modelled: wire endpoints join; a pin, label or wire endpoint lying
anywhere on a wire joins that wire; coincident pins join; labels and global
labels join by name; power symbols join by name. Crossing wires do not join.
Also reports pins left unconnected without a no-connect flag."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_schematic as spec

def parse(s):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    st = [[]]
    for t in tok:
        if t == '(': st.append([])
        elif t == ')': x = st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1] if t.startswith('"') else t)
    assert len(st) == 1 and len(st[0]) == 1, "unbalanced parentheses"
    return st[0][0]

f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad", "dual_esc.kicad_sch")
root = parse(open(f).read())
find = lambda n, k: [c for c in n if isinstance(c, list) and c and c[0] == k]
P = lambda x, y: (round(float(x), 3), round(float(y), 3))

libs = {}
for s in find(find(root, "lib_symbols")[0], "symbol"):
    pins = {}
    for sub in find(s, "symbol"):
        for p in find(sub, "pin"):
            at = find(p, "at")[0]
            pins[find(p, "number")[0][1]] = (float(at[1]), float(at[2]), find(p, "name")[0][1])
    libs[s[1]] = (pins, ["power"] in s)

parent = {}
def fnd(a):
    parent.setdefault(a, a)
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
def join(a, b): parent[fnd(a)] = fnd(b)

segs = []
for w in find(root, "wire"):
    a, b = [P(x[1], x[2]) for x in find(find(w, "pts")[0], "xy")]
    segs.append((a, b)); join(("pt", a), ("pt", b))
def on_wire(p):
    for a, b in segs:
        if (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or \
           (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])):
            yield a
for a, b in segs:                       # wire endpoint landing on another wire
    for e in (a, b):
        for w in on_wire(e): join(("pt", e), ("pt", w))

pin_nodes = {}; errs = []
for s in find(root, "symbol"):
    lib = find(s, "lib_id")[0][1]; at = find(s, "at")[0]; X, Y = float(at[1]), float(at[2])
    assert at[3] == "0", "rotation not modelled"
    ref = [p[2] for p in find(s, "property") if p[1] == "Reference"][0]
    pins, power = libs[lib]
    for num, (px, py, name) in pins.items():
        pt = P(X + px, Y - py)
        node = ("pin", ref, num)
        join(node, ("pt", pt))
        for w in on_wire(pt): join(("pt", pt), ("pt", w))
        if power: join(node, ("net", name))
        else: pin_nodes[node] = pt
for kind in ("label", "global_label"):
    for l in find(root, kind):
        at = find(l, "at")[0]; pt = P(at[1], at[2])
        join(("pt", pt), ("net", l[1]))
        hits = list(on_wire(pt))
        if not hits: errs.append(f"{kind} {l[1]} at {pt} touches no wire")
        for w in hits: join(("pt", pt), ("pt", w))
ncs = {P(find(n, "at")[0][1], find(n, "at")[0][2]) for n in find(root, "no_connect")}

groups = {}
for node in pin_nodes: groups.setdefault(fnd(node), set()).add(f"{node[1]}.{node[2]}")
got = set()
for g, pins in groups.items():
    if len(pins) == 1:
        (only,) = pins; ref, num = only.split(".")
        named = any(fnd(("net", n)) == g for n in ("GND", "VBAT", "+5V"))
        if pin_nodes[("pin", ref, num)] in ncs: continue
        if not named: errs.append(f"{only} is not connected to anything")
    got.add(frozenset(pins))
want = set()
for net, pins in {}.items(): pass
nets = {}
for ref, sym, val, fp, pins, mpn in spec.PARTS:
    for num, net in pins.items():
        if net is not None: nets.setdefault(net, set()).add(f"{ref}.{num}")
want = {frozenset(v) for v in nets.values()}
for g in got - want:
    errs.append(f"drawn net not in spec: {sorted(g)}")
for g in want - got:
    errs.append(f"spec net not drawn as one net: {sorted(g)}")
print("\n".join(errs) if errs else f"OK: {len(pin_nodes)} pins, {len(want)} nets, drawn wiring matches the spec netlist")
sys.exit(1 if errs else 0)
