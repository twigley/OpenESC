#!/usr/bin/env python3
"""Build kicad/dual_esc.kicad_pcb from the netlist and place the parts.

Run with KiCad's bundled Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/build_pcb.py [--route]

Connectivity comes from gen_schematic.PARTS (check_schematic.py proves the
drawn schematic matches it). Footprints are linked to their schematic symbols
through the same deterministic UUIDs draw_schematic.py writes, so KiCad's
"Update PCB from Schematic" recognises every part.

Power copper (VBAT, GND, phase nodes, low-side source nodes) is drawn here as
zones; everything else is routed with Freerouting (--route).
"""
import json, os, re, subprocess, sys, uuid
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_schematic as spec

KD = os.path.normpath(os.path.join(HERE, "..", "kicad"))
PCB = os.path.join(KD, "dual_esc.kicad_pcb")
PRO = os.path.join(KD, "dual_esc.kicad_pro")
BIN = os.path.dirname(sys.executable)
FPDIR = os.path.normpath(os.path.join(BIN, "..", "share", "kicad", "footprints"))
LIBS = {"OpenESC_dual": os.path.join(KD, "OpenESC_dual.pretty")}
FREEROUTING = os.path.expandvars(r"%LOCALAPPDATA%\freerouting\freerouting.exe")

W, H = 28.0, 20.0
LAYERS = 4                     # L1 signal+power, L2 GND, L3 VBAT (+GND), L4 signal+power
OX, OY = 100.0, 100.0
mm = pcbnew.FromMM
def P(x, y): return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))

# schematic symbol UUIDs (same scheme as draw_schematic.py)
SCH_NS = uuid.UUID("2b0b8f51-3f0e-4a77-9a55-5b1f2f7e9c01")
def sym_uuid(ref): return str(uuid.uuid5(SCH_NS, "/".join(("s", ref))))

# ------------------------------------------------------------------ placement
# (x, y) mm from the board's top-left corner seen from the top; rot CCW deg.
PLACE = {}
def at(ref, x, y, rot=0, side="F"): PLACE[ref] = (x, y, rot, side)

FX = [7.6, 12.8, 18.0]           # half-bridge column centres (both motors)
Y1, Y2 = 5.4, 14.6               # FET row centres, motor 1 (top) and motor 2
at("P1", 1.6, 3.1)               # BAT+
at("P2", 2.85, 10.0, 90)         # BAT-, lying along x
at("R150", 3.35, 7.3, 180)        # shunt M1: pin 2 (GND) left over BAT-, pin 1 (LS) right into the LS bus
at("R250", 3.35, 12.7, 180)
for k, x in enumerate(FX):
    at(f"Q{101+k}", x, Y1, 90)               # gates at the bottom corners
    at(f"Q{201+k}", x, Y2, 270)              # gates at the top corners
    at(f"P{101+k}", x, 1.85)
    at(f"P{201+k}", x, H - 1.85)

def per_motor(m):
    """Place motor m's parts. Motor 2 mirrors motor 1 about y = H/2.
    4-layer layout: VBAT is the L3 plane and GND the L2 plane, so the bottom
    is free for the gate driver, which sits right under the middle phase pad,
    close to its three half-bridges. The MCU is at the bottom right, clear of
    the driver, with room between them for the six gate-input vias."""
    b = 100 * m
    Y = (lambda y: y) if m == 1 else (lambda y: H - y)
    R = (lambda r: r) if m == 1 else (lambda r: (360 - r) % 360)
    a = lambda ref, x, y, rot=0, side="F": at(ref, x, Y(y), R(rot), side)
    # bottom: gate driver under the middle phase pad, gate/SH pins toward the FETs
    a(f"U{b+2}", FX[1], 2.95, 0, "B")
    # bottom, left of the driver: bus caps of FETs A and B, GVDD caps
    a(f"C{b+10}", 4.3, 2.2, 90, "B"); a(f"C{b+11}", 6.4, 2.2, 90, "B")
    a(f"C{b+5}", 8.25, 2.2, 90, "B"); a(f"C{b+6}", 9.55, 2.2, 90, "B")
    # bottom, right of the driver: bootstrap caps, bus cap of FET C
    for k in range(3):
        a(f"C{b+7+k}", 16.6, 0.85 + 1.2 * k, 0, "B")
    a(f"C{b+12}", 18.6, 2.2, 90, "B")
    # bottom: low-side gate pull-downs (to GND) beside each GL escape via
    for k, x in enumerate(FX):
        a(f"R{b+3+k}", x - 2.6, 7.3, 180, "B")
    # bottom middle band: BEMF dividers, neutral network and BEMF filter caps
    parts = [f"R{b+i}" for i in (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)] + [f"C{b+15+k}" for k in range(3)]
    slots = [(4.6 + 1.65 * i, 8.0) for i in range(7)] + [(4.6 + 1.65 * i, 8.9) for i in range(6)]   # 0201
    for ref, (x, y) in zip(parts, slots):
        a(ref, x, y, 0, "B")
    # bottom right: MCU and its support, clear of the driver
    a(f"U{b+1}", 24.7, 4.2, 180, "B")
    for i, ref in enumerate((f"C{b+1}", f"C{b+3}", f"C{b+4}", f"R{b+1}", f"R{b+2}")):
        a(ref, 21.1, 1.0 + 1.15 * i, 0, "B")
    a(f"C{b+2}", 25.0, 7.4, 0, "B")              # VDD pin 17
    a(f"R{b+6}", 21.3, 6.75, 0, "B")            # INA output filter R
    a(f"C{b+14}", 23.0, 7.4, 0, "B")             # filter C at PA6
    # bottom: current-sense amp under BAT-, next to its shunt
    a(f"U{b+3}", 1.7, 8.0, 0, "B")
    a(f"C{b+13}", 1.7, 6.3, 0, "B")
    # top right corner: SWD pads for this MCU
    for i in range(3):
        a(f"P{b+6+i}", 21.2 + 1.45 * i, 1.0, 0)

for m in (1, 2):
    per_motor(m)
# receiver / telemetry pads, top-left corner (2 x 3 grid)
for ref, x, y in (("P104", 1.25, 14.75), ("P204", 3.25, 14.75), ("P3", 1.25, 16.6),
                  ("P4", 3.25, 16.6), ("P105", 1.25, 18.45), ("P205", 3.25, 18.45)):
    at(ref, x, y)
# BEC: top right middle
at("U1", 22.2, 10.0, 0); at("L1", 25.6, 9.9, 0)
at("C9", 25.6, 7.275, 0); at("C10", 25.6, 12.525, 0)
at("C6", 21.4, 7.6, 0); at("C7", 23.2, 7.6, 90); at("C8", 21.4, 12.15, 0)
at("R3", 23.2, 12.4, 90); at("R4", 21.4, 13.1, 0)
at("C5", 21.9, 4.2, 90)                          # buck input 10 uF (top right, VBAT/GND by via)
# 3.3 V LDO: top right, next to the BEC
at("U2", 25.0, 4.0, 90); at("C11", 27.3, 2.6, 90); at("C12", 27.3, 5.4, 90)
# SWD supply / ground pads, Vbat divider
at("P5", 25.55, 1.0, 0); at("P6", 25.55, H - 1.0, 0)
at("R1", 24.0, 14.6, 0); at("R2", 24.0, 15.5, 0)      # Vbat divider on top

OFFBOARD_X = W + 6.0

# ---------------------------------------------------------------- build
def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LIBS.get(lib) or os.path.join(FPDIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    assert fp, f"footprint {fpid} not found in {path}"
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

def main():
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(LAYERS)
    for L in (pcbnew.In1_Cu, pcbnew.In2_Cu):     # plane layers: the router stays off them
        board.SetLayerType(L, pcbnew.LT_POWER)
    nets = {}
    def net(n):
        if n not in nets:
            ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
        return nets[n]
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    park = []
    for ref, sym, val, fpid, pins, mpn in spec.PARTS:
        if ref in spec.OFF_BOARD: continue
        fp = load_fp(fpid)
        fp.SetReference(ref); fp.SetValue(val)
        fp.SetPath(pcbnew.KIID_PATH("/" + sym_uuid(ref)))
        board.Add(fp)
        for pad in fp.Pads():
            n = pins.get(pad.GetNumber())
            if n: pad.SetNet(net(n))
        if ref not in PLACE: park.append(fp); print("parked", ref); continue
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(P(x, y))
        if side == "B": fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
    y, xo = 0.0, OFFBOARD_X
    for fp in park:
        fp.SetPosition(P(xo, y)); bb = fp.GetBoundingBox(False)
        fp.Move(pcbnew.VECTOR2I(0, mm(OY + y) - bb.GetTop())); y += pcbnew.ToMM(bb.GetHeight()) + 0.5
        if y > 30: y, xo = 0.0, xo + 8
    power_copper(board, net)
    flush_zones(board, net)
    if os.environ.get("ESC_KEEPOUTS", "0") == "1":
        flush_keepouts(board)      # only for a Freerouting run (route_pcb.py)
    KEEPOUT.clear()                # top/bottom GND fills are added after routing
    board.BuildConnectivity()
    pcbnew.SaveBoard(PCB, board)
    set_stackup(PCB)
    write_rules()
    print(f"placed {len(PLACE)}, parked {len(park)}, nets {len(nets)}")

# ------------------------------------------------------------- power copper
VIA_D, VIA_DRILL = 0.5, 0.25
ZONES = {}   # (net name, layer, prio, thermal) -> [polygon]; merged per key in flush_zones()
KEEPOUT = {}  # layer -> [rect]: router keep-outs just inside the power copper
def add_zone(board, netinfo, layer, pts, prio=0, thermal=False, keepout=True):
    ZONES.setdefault((netinfo.GetNetname(), layer, prio, thermal), []).append(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if keepout and len(pts) == 4:
        x1, x2, y1, y2 = min(xs) + 0.5, max(xs) - 0.5, min(ys) + 0.5, max(ys) - 0.5
        if x2 - x1 > 0.4 and y2 - y1 > 0.4:
            KEEPOUT.setdefault(layer, []).append(rect(x1, y1, x2, y2))
def flush_keepouts(board):
    """Rule areas (no tracks, no vias) over the power copper so Freerouting
    leaves it alone; a 0.5 mm rim stays open so nets can still reach it."""
    for layer, rects in KEEPOUT.items():
        ps = pcbnew.SHAPE_POLY_SET()
        for pts in rects:
            one = pcbnew.SHAPE_POLY_SET(); one.NewOutline()
            for x, y in pts: one.Append(mm(OX + x), mm(OY + y))
            ps.BooleanAdd(one)
        ps.Simplify()
        # holes round every pre-placed via, so the router doesn't see them as violations
        for v in board.GetTracks():
            if isinstance(v, pcbnew.PCB_VIA):
                c, h = v.GetPosition(), mm(0.45)
                sq = pcbnew.SHAPE_POLY_SET(); sq.NewOutline()
                for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h)): sq.Append(c.x + dx, c.y + dy)
                ps.BooleanSubtract(sq)
        ps.Fracture()
        for i in range(ps.OutlineCount()):
            ch = ps.COutline(i)
            z = pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetLayer(layer)
            z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False)
            z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
            z.SetZoneName("router keep-out")
            o = z.Outline(); o.NewOutline()
            for j in range(ch.PointCount()): o.Append(ch.CPoint(j).x, ch.CPoint(j).y)
            board.Add(z)
    KEEPOUT.clear()
def flush_zones(board, net):
    for (name, layer, prio, thermal), polys in ZONES.items():
        ps = pcbnew.SHAPE_POLY_SET()
        for pts in polys:
            one = pcbnew.SHAPE_POLY_SET(); one.NewOutline()
            for x, y in pts: one.Append(mm(OX + x), mm(OY + y))
            ps.BooleanAdd(one)
        ps.Simplify()
        for i in range(ps.OutlineCount()):
            ch = ps.COutline(i)
            make_zone(board, net(name), layer, [(ch.CPoint(j).x, ch.CPoint(j).y) for j in range(ch.PointCount())], prio, thermal)
    ZONES.clear()
def make_zone(board, netinfo, layer, pts_iu, prio, thermal, clearance=0.2, min_w=0.2):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(netinfo); z.SetAssignedPriority(prio)
    o = z.Outline(); o.NewOutline()
    for x, y in pts_iu: o.Append(int(x), int(y))
    z.SetLocalClearance(mm(clearance)); z.SetMinThickness(mm(min_w))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(0.25)); z.SetThermalReliefSpokeWidth(mm(0.4))
    board.Add(z); return z
def rect(x1, y1, x2, y2): return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
def add_via(board, netinfo, x, y, d=VIA_D, drill=VIA_DRILL):
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(x, y)); v.SetWidth(mm(d)); v.SetDrill(mm(drill))
    v.SetNet(netinfo); board.Add(v); return v

def power_copper(board, net):
    """Hand-drawn power copper. Top: phase nodes up/down to their pads,
    low-side source (LS) gaps + bus to the shunt, small VBAT islands at each
    FET drain with vias to the L3 VBAT plane. L2 is solid GND. BAT+ / BAT-
    via arrays go to L3 / L2. Low-priority GND fill on top and bottom."""
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    for m, Y, s in ((1, Y1, 1), (2, Y2, -1)):
        yy = (lambda y: y) if m == 1 else (lambda y: H - y)   # mirror motor 2
        for k, (x, p) in enumerate(zip(FX, "ABC")):
            d = 1 if m == 1 else -1        # LS gap side: left for M1, right for M2
            # phase node: wide copper from the phase pad down to the switch pad (pad 9)
            nx1, nx2 = (x - 0.955, x + 0.089) if m == 1 else (x - 0.089, x + 0.955)
            KEEPOUT.setdefault(F, []).append(rect(x - 1.85, yy(0.8), x + 1.85, yy(3.25)))
            add_zone(board, net(f"M{m}_{p}"), F, [(x - 2.35, yy(0.3)), (x + 2.35, yy(0.3)), (x + 2.35, yy(3.75)),
                     (nx2, yy(3.75)), (nx2, yy(5.4)), (nx1, yy(5.4)), (nx1, yy(3.75)), (x - 2.35, yy(3.75))], prio=5)
            # phase tap via (outside the keep-out) so the router can reach the node from the bottom
            add_via(board, net(f"M{m}_{p}"), *((15.0, yy(0.65)) if k == 1 else (x + 2.05, yy(1.2))))
            # LS gap beside the S2 pins, running into the LS bus; notched round the
            # low-side gate pin (G2) and its escape via
            o, i = (x - 2.6, x - 1.9) if m == 1 else (x + 2.6, x + 1.9)
            pin = x - 1.15 if m == 1 else x + 1.15
            add_zone(board, net(f"M{m}_LS"), F, [(o, yy(4.0)), (pin, yy(4.0)), (pin, yy(5.95)), (i, yy(5.95)),
                                                  (i, yy(7.6)), (o, yy(7.6))], prio=4)
            KEEPOUT.setdefault(F, []).append(rect(min(o, i) + 0.2, yy(4.5) if m == 1 else yy(7.1), max(o, i) - 0.2, yy(7.1) if m == 1 else yy(4.5)))
            # gate escape vias just below the gate pins (G2 = low side, G1 = high side)
            for gx, gnet in ((x - 1.38 * d, f"M{m}_GL{p}"), (x + 1.38 * d, f"M{m}_GH{p}")):
                v = add_via(board, net(gnet), gx, yy(7.0))
                t = pcbnew.PCB_TRACK(board); t.SetStart(P(gx, yy(6.375))); t.SetEnd(P(gx, yy(7.0)))
                t.SetWidth(mm(0.25)); t.SetLayer(F); t.SetNet(net(gnet)); board.Add(t)
            # VBAT island: drain pins + pad 10, with vias to the bottom VBAT pour
            vx1, vx2 = (x + 0.389, x + 2.25) if m == 1 else (x - 2.25, x - 0.389)
            add_zone(board, net("VBAT"), F, rect(vx1, yy(Y1 - 1.3), vx2, yy(Y1 + 0.55)), prio=4)
            # vias down to the L3 VBAT plane: in pad 10 and beside the drain pins.
            # FET B sits over the driver (bottom), so its vias stay clear of the driver pads;
            # FET C's gap is over the MCU support column.
            vi = x + 1.95 * d
            if k == 0:
                gap, pad10 = (-0.95, -0.25), (-0.95, -0.32, 0.32, 0.95)
            elif k == 1:
                gap, pad10 = (0.45,), (0.45, 1.05)
            else:
                gap, pad10 = (), (-0.95, -0.32, 0.32, 0.95)
            for dy in gap:
                add_via(board, net("VBAT"), vi, yy(Y1 + dy))
            for dy in pad10:
                add_via(board, net("VBAT"), x + 0.672 * d, yy(Y1 + dy))
        # M2 LS gap for FET1 is on its right, so the shunt pad needs its own patch
        add_zone(board, net(f"M{m}_LS"), F, rect(4.2, yy(6.3), 5.6, yy(8.4)), prio=4)
        # LS bus under the FET row, from the shunt to the last FET
        add_zone(board, net(f"M{m}_LS"), F, rect(5.6, yy(7.45), 20.3, yy(9.65)), prio=4)
        add_via(board, net(f"M{m}_LS"), 5.95, yy(9.25))      # LS tap for the INA186 Kelvin lead
    # inner planes: L2 (In1) solid GND, L3 (In2) VBAT over the power area, GND beyond
    make_zone(board, net("GND"), pcbnew.In1_Cu, [(mm(OX + x), mm(OY + y)) for x, y in rect(0, 0, W, H)], 1, False)
    make_zone(board, net("VBAT"), pcbnew.In2_Cu, [(mm(OX + x), mm(OY + y)) for x, y in rect(0, 0, 24.0, H)], 2, False)
    make_zone(board, net("GND"), pcbnew.In2_Cu, [(mm(OX + x), mm(OY + y)) for x, y in rect(24.4, 0, W, H)], 1, False)
    # top GND at BAT- and the shunt ground ends
    add_zone(board, net("GND"), F, rect(0.3, 6.1, 3.1, 13.9), prio=3)
    # via arrays: BAT+ to bottom VBAT, BAT- to bottom GND
    for x in (0.9, 1.6, 2.3):
        for y in (4.2, 5.0):
            add_via(board, net("VBAT"), x, y)
        for y in (9.3, 10.0, 10.7):
            add_via(board, net("GND"), x, y)

STACKUP = """		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.07))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "None")
			(dielectric_constraints no)
		)
"""
def set_stackup(path):
    """4-layer 1.6 mm (JLC04161H-7628 style), 2 oz outer / 0.5 oz inner. pcbnew's
    Python API can't edit the stackup, so it is written into (setup)."""
    s = open(path, encoding="utf8").read()
    s = re.sub(r"\n\t\t\(stackup\n.*?\n\t\t\)\n", "\n", s, flags=re.S)
    s = s.replace("\t(setup\n", "\t(setup\n" + STACKUP, 1)
    open(path, "w", encoding="utf8").write(s)

def gnd_fill(board, gnd):
    """Whole-board GND fill on both layers, lowest priority (added after routing)."""
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        make_zone(board, gnd, L, [(mm(OX + x), mm(OY + y)) for x, y in rect(0.0, 0.0, W, H)], 0, True)

# ------------------------------------------------------------- design rules
NETCLASSES = [
    dict(name="Default", clearance=0.13, track_width=0.2, via_diameter=0.45, via_drill=0.2),
    dict(name="Gate", clearance=0.13, track_width=0.25, via_diameter=0.45, via_drill=0.2),
    dict(name="Power", clearance=0.15, track_width=0.3, via_diameter=0.5, via_drill=0.25),
    dict(name="Plane", clearance=0.15, track_width=0.3, via_diameter=0.4, via_drill=0.2),
]
PATTERNS = [("Gate", "M?_GH?"), ("Gate", "M?_GL?"), ("Gate", "M?_A"), ("Gate", "M?_B"), ("Gate", "M?_C"),
            ("Plane", "VBAT"), ("Plane", "GND"), ("Power", "M?_LS"),
            ("Power", "+5V"), ("Power", "BEC_SW")]
def write_rules():
    pro = json.load(open(PRO)) if os.path.exists(PRO) else {}
    ns = pro.setdefault("net_settings", {})
    base = dict(bus_width=12, diff_pair_gap=0.25, diff_pair_via_gap=0.25, diff_pair_width=0.2,
                line_style=0, microvia_diameter=0.3, microvia_drill=0.1, pcb_color="rgba(0, 0, 0, 0.000)",
                schematic_color="rgba(0, 0, 0, 0.000)", wire_width=6, priority=2147483647)
    ns["classes"] = [dict(base, **c) for c in NETCLASSES]
    ns["netclass_patterns"] = [dict(netclass=c, pattern=p) for c, p in PATTERNS]
    ns["meta"] = {"version": 4}
    ds = pro.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(dict(min_clearance=0.13, min_track_width=0.15, min_via_diameter=0.4,
        min_through_hole_diameter=0.2, min_via_annular_width=0.1, min_copper_edge_clearance=0.3,
        min_hole_to_hole=0.25, min_hole_clearance=0.2, min_connection=0.12, solder_mask_to_copper_clearance=0.0))
    pro.setdefault("meta", {"filename": "dual_esc.kicad_pro", "version": 3})
    json.dump(pro, open(PRO, "w"), indent=2)

if __name__ == "__main__":
    main()
