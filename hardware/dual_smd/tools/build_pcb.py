#!/usr/bin/env python3
"""Build kicad/dual_esc.kicad_pcb from the schematic (KiCad's "Update PCB from
Schematic", scripted) and place the parts.

Run with KiCad's bundled Python, e.g. on Windows:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/build_pcb.py

Steps: export the netlist with kicad-cli, load every footprint, link it to its
schematic symbol (so the GUI's Update PCB keeps working), assign nets, draw a
30 x 25 mm outline, set a 2-layer 2 oz stackup, and place parts from PLACE.
Parts that do not fit on the board are parked to the right of it (OFFBOARD)
so the shortfall is visible.
"""
import os, re, subprocess, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KD = os.path.normpath(os.path.join(HERE, "..", "kicad"))
SCH = os.path.join(KD, "dual_esc.kicad_sch")
PCB = os.path.join(KD, "dual_esc.kicad_pcb")
BIN = os.path.dirname(sys.executable)
CLI = os.path.join(BIN, "kicad-cli.exe" if os.name == "nt" else "kicad-cli")
FPDIR = os.environ.get("KICAD10_FOOTPRINT_DIR") or os.path.normpath(os.path.join(BIN, "..", "share", "kicad", "footprints"))
LIBS = {"OpenESC_dual": os.path.join(KD, "OpenESC_dual.pretty")}

W, H = 30.0, 25.0          # board, mm
OX, OY = 100.0, 100.0      # board top-left in KiCad coordinates
mm = pcbnew.FromMM

# ------------------------------------------------------------------ netlist
def sexpr(s):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    st = [[]]
    for t in tok:
        if t == "(": st.append([])
        elif t == ")": x = st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return st[0][0]
def kids(n, k): return [c for c in n if isinstance(c, list) and c and c[0] == k]
def val(n, k):
    c = kids(n, k)
    return c[0][1] if c and len(c[0]) > 1 else ""

def read_netlist():
    out = os.path.join(KD, "dual_esc.net.tmp")
    subprocess.run([CLI, "sch", "export", "netlist", "-o", out, SCH], check=True)
    root = sexpr(open(out, encoding="utf8").read()); os.remove(out)
    comps = {}
    for c in kids(kids(root, "components")[0], "comp"):
        tst = kids(c, "tstamps")[0][1]
        comps[val(c, "ref")] = dict(value=val(c, "value"), fp=val(c, "footprint"), uuid=tst)
    nets = {}
    for n in kids(kids(root, "nets")[0], "net"):
        name = val(n, "name")
        for node in kids(n, "node"):
            nets[(val(node, "ref"), val(node, "pin"))] = name
    return comps, nets

# ---------------------------------------------------------------- placement
# (x, y) are mm from the board's top-left corner, seen from the top.
# side "F" = top, "B" = bottom. rot in degrees (KiCad, CCW).
PLACE = {}
def at(ref, x, y, rot=0, side="F"): PLACE[ref] = (x, y, rot, side)

# Top: battery pads on the left short edge.
at("P1", 2.3, 12.5)
# Top: three half-bridge columns per motor. M1 in the top half (phase pads on
# the top edge), M2 mirrored in the bottom half. In each column the high side is
# on the left with its sources (phase) toward the edge and drain (VBAT) toward
# the middle; the low side is on the right with its drain (phase) toward the edge
# and sources (GND) toward the middle; the 10 uF 1206 sits just inboard.
COLS = [9.1, 17.45, 25.8]
for m in (1, 2):
    edge_y, fet_y, cap_y = (2.3, 7.05, 10.35) if m == 1 else (H - 2.3, H - 7.05, H - 10.35)
    hs_rot, ls_rot = (270, 90) if m == 1 else (90, 270)
    for k, cx in enumerate(COLS):
        q = 6 * (m - 1) + 2 * k
        at(f"P{1 + 3*(m-1) + k + 1}", cx, edge_y)
        at(f"Q{q + 1}", cx - 1.97, fet_y, hs_rot)
        at(f"Q{q + 2}", cx + 1.97, fet_y, ls_rot)
        at(f"C{10 + 3*(m-1) + k + 1}", cx, cap_y, 0)

# Bottom: one DRV8300 under each motor's bridges, gate and pull-down resistors
# between it and the bridges, bootstrap caps beside it, GVDD caps at pin 7.
for m in (1, 2):
    top = m == 1
    uy = 6.6 if top else H - 6.6
    at(f"U{m}", 14.0, uy, 90 if top else 270, "B")
    ry1, ry2 = (0.85, 1.95) if top else (H - 0.85, H - 1.95)
    for i in range(6):
        at(f"R{6*(m-1) + i + 1}", 8.6 + 2.15 * i, ry1, 0, "B")
        at(f"R{12 + 6*(m-1) + i + 1}", 8.6 + 2.15 * i, ry2, 0, "B")
    for k in range(3):
        at(f"C{3*(m-1) + k + 1}", 19.3, uy + (-2.0 + 2.0 * k) * (1 if top else -1), 0, "B")
    at(f"C{6 + m}", 9.2, uy + (1.0 if top else -1.0), 90, "B")
    at(f"C{8 + m}", 9.2, uy + (-2.0 if top else 2.0), 90, "B")
# Bottom: MCU block on the left, under the battery pads.
at("U3", 4.6, 12.5, 0, "B")
at("Y1", 4.6, 17.2, 0, "B")
at("C23", 1.0, 10.6, 90, "B"); at("C24", 1.0, 12.5, 90, "B"); at("C25", 8.4, 12.5, 90, "B")
at("C26", 8.4, 14.4, 90, "B"); at("R25", 8.4, 10.6, 90, "B"); at("C28", 1.0, 14.4, 90, "B")
at("U4", 3.0, 5.0, 0, "B"); at("C21", 3.0, 2.0, 0, "B"); at("C22", 3.0, 8.0, 0, "B")
at("C27", 3.0, 20.6, 0, "B")
# Bottom: speed connectors on the right short edge, cable exit to the right.
at("J3", 26.4, 6.0, 90, "B"); at("J4", 26.4, 19.0, 90, "B")

OFFBOARD_X = W + 8.0       # parts without a place on the board are parked here

# ---------------------------------------------------------------------- build
def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LIBS.get(lib) or os.path.join(FPDIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    assert fp, f"footprint {fpid} not found in {path}"
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

def main():
    comps, pin_net = read_netlist()
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_CopperEdgeClearance = mm(0.3)
    netinfo = {}
    def net(name):
        if name not in netinfo:
            ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); netinfo[name] = ni
        return netinfo[name]

    # outline
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(OX + a[0]), mm(OY + a[1]))); s.SetEnd(pcbnew.VECTOR2I(mm(OX + b[0]), mm(OY + b[1])))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    park = []
    for ref in sorted(comps, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
        c = comps[ref]
        fp = load_fp(c["fp"])
        fp.SetReference(ref); fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        board.Add(fp)
        for pad in fp.Pads():
            n = pin_net.get((ref, pad.GetNumber()))
            if n and not n.startswith("unconnected-"):
                pad.SetNet(net(n))
        if ref in PLACE:
            x, y, rot, side = PLACE[ref]
        else:
            park.append(ref); continue
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
    # park the rest beside the board, in a column
    y = 0.0
    for ref in park:
        fp = board.FindFootprintByReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + OFFBOARD_X), mm(OY + y)))
        bb = fp.GetBoundingBox(False)            # footprint origin need not be its centre
        fp.Move(pcbnew.VECTOR2I(0, mm(OY + y) - bb.GetTop()))
        y += pcbnew.ToMM(bb.GetHeight()) + 1.5
    t = pcbnew.PCB_TEXT(board)
    t.SetText("NOT ON BOARD (no room in 30 x 25 mm):\n" + " ".join(park) if park else "")
    t.SetPosition(pcbnew.VECTOR2I(mm(OX + W + 2), mm(OY - 3))); t.SetLayer(pcbnew.Cmts_User)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT); board.Add(t)
    board.BuildConnectivity()
    pcbnew.SaveBoard(PCB, board)
    set_stackup_2oz(PCB)
    print(f"footprints={len(comps)} nets={len(netinfo)} placed={len(comps) - len(park)} parked={park}")

STACKUP = """		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 1" (type "core") (thickness 1.45) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.07))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "None")
			(dielectric_constraints no)
		)
"""
def set_stackup_2oz(path):
    """pcbnew's Python API can't edit the stackup, so write it into (setup)."""
    s = open(path, encoding="utf8").read()
    s = re.sub(r"\n\t\t\(stackup\n.*?\n\t\t\)\n", "\n", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + STACKUP, 1)
    open(path, "w", encoding="utf8").write(s)

if __name__ == "__main__":
    main()
