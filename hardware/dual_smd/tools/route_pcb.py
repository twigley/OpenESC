#!/usr/bin/env python3
"""Route kicad/dual_esc.kicad_pcb with Freerouting and finish it.

Run with KiCad's bundled Python after build_pcb.py:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route_pcb.py [passes]

Steps: fill zones, export Specctra DSN (inner layers are power planes, so the
router stays on L1/L4 and drops vias into L2 GND / L3 VBAT), run Freerouting,
import the session, remove the router keep-outs, refill, add GND stitching
vias where the top/bottom GND fill has room, refill and save.
"""
import math, os, subprocess, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KD = os.path.normpath(os.path.join(HERE, "..", "kicad"))
PCB = os.path.join(KD, "dual_esc.kicad_pcb")
WORK = os.path.join(KD, "route")
FREEROUTING = os.path.expandvars(r"%LOCALAPPDATA%\freerouting\freerouting.exe")
mm = pcbnew.FromMM

def fill(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

def route(board, passes):
    os.makedirs(WORK, exist_ok=True)
    dsn, ses = os.path.join(WORK, "dual_esc.dsn"), os.path.join(WORK, "dual_esc.ses")
    fill(board)
    assert pcbnew.ExportSpecctraDSN(board, dsn)
    prepare_dsn(dsn)
    log = open(os.path.join(WORK, "freerouting.log"), "w")
    subprocess.run([FREEROUTING, "-de", dsn, "-do", ses, "-mp", str(passes), "-mt", "7",
                    "--gui.enabled=false"], stdout=log, stderr=subprocess.STDOUT, check=True)
    assert pcbnew.ImportSpecctraSES(board, ses)

PLANE_NETS = ("GND", "VBAT")
def prepare_dsn(path):
    """GND and VBAT are served by the L2/L3 planes and by fanout vias placed
    here beforehand, so the router gets them with one pin each (nothing to
    route). All pre-placed copper is marked 'protect' so the router keeps it."""
    import re
    s = open(path).read()
    for n in PLANE_NETS:
        s = re.sub(r"(\(net %s\s*\(pins\s+)([^\s()]+)[^()]*\)" % re.escape(n), r"\g<1>\g<2>)", s, count=1)
    s = s.replace("(type route)", "(type protect)")
    # inner planes: the router would treat them as solid copper and refuse every
    # other-net via; KiCad fills them with via clearances afterwards anyway
    s = re.sub(r"\(plane \S+ \(polygon In[12]\.Cu [^()]*\)\)\s*", "", s)
    open(path, "w").write(s)

def item_clear(board, pos, r, clr, net, layers, extra=()):
    """True if a disc of radius r at pos keeps clr from every other-net item on
    the given copper layers (tracks, vias incl. hole spacing, pads, zone fills)."""
    acc = mm(r + clr)
    for t in list(board.GetTracks()) + list(extra):
        if isinstance(t, pcbnew.PCB_VIA):
            dist = (t.GetPosition() - pos).EuclideanNorm()
            need = mm(r) + t.GetWidth(pcbnew.F_Cu) / 2 + (mm(clr) if t.GetNetname() != net else mm(0.1))
            if dist < need: return False
        elif t.GetNetname() != net and t.GetLayer() in layers and t.HitTest(pos, acc):
            return False
    for p in board.GetPads():
        if p.GetNetname() == net: continue
        if any(p.IsOnLayer(L) for L in layers) and p.HitTest(pos, acc): return False
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() == net: continue
        for L in layers:
            if L in (pcbnew.F_Cu, pcbnew.B_Cu) and z.IsOnLayer(L) and z.HitTestFilledArea(L, pos, acc):
                return False
    return True

def fanout(board, nets=PLANE_NETS, d=0.45, drill=0.2):
    """Give every SMD pad of a plane net its own via to the plane: in the pad for
    big pads, otherwise just outside it with a short 0.3 mm track."""
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    done = missed = 0
    for p in list(board.GetPads()):
        n = p.GetNetname()
        if n not in nets: continue
        L = F if p.IsOnLayer(F) else B
        c = p.GetPosition()
        same = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == n and z.IsOnLayer(L)]
        if any(z.HitTestFilledArea(L, c, 0) for z in same):
            continue                          # already in same-net copper that has vias
        sz = p.GetSize()
        net = p.GetNet()
        if min(pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)) >= 1.4:
            spots = [c]                      # exposed pad / big pad: via in pad
        else:
            spots = []
            for dist in (0.65, 0.8, 1.0, 1.25, 1.55):
                for k in range(16):
                    a = 2 * math.pi * k / 16
                    spots.append(c + pcbnew.VECTOR2I(int(mm(dist) * math.cos(a)), int(mm(dist) * math.sin(a))))
        edge = board.GetBoardEdgesBoundingBox()
        m_e = mm(0.3 + d / 2)
        spots = [v for v in spots if edge.GetLeft() + m_e < v.x < edge.GetRight() - m_e
                 and edge.GetTop() + m_e < v.y < edge.GetBottom() - m_e]
        for v in spots:
            if v != c and not p.HitTest(v, 0) is False and p.HitTest(v, mm(0.05)):
                continue                      # skip spots still on the pad (small pads)
            if not item_clear(board, v, d / 2, 0.15, n, (F, B)):
                continue
            if v != c:
                mid = pcbnew.VECTOR2I((v.x + c.x) // 2, (v.y + c.y) // 2)
                if not item_clear(board, mid, 0.15, 0.15, n, (L,)):
                    continue
                t = pcbnew.PCB_TRACK(board); t.SetStart(c); t.SetEnd(v); t.SetWidth(mm(0.3))
                t.SetLayer(L); t.SetNet(net); board.Add(t)
            via = pcbnew.PCB_VIA(board); via.SetPosition(v); via.SetWidth(mm(d)); via.SetDrill(mm(drill))
            via.SetNet(net); board.Add(via)
            done += 1
            break
        else:
            missed += 1
            print("no fanout for", p.GetParentFootprint().GetReference(), p.GetNumber(), n)
    return done, missed

def stitch(board, pitch=1.2, d=0.45, drill=0.2, clr=0.2):
    """GND vias on a grid wherever the via lands in GND fill on top or bottom
    and keeps clearance to every other-net item on the outer layers."""
    gnd = board.GetNetInfo().GetNetItem("GND")
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    r = d / 2
    others = [t for t in board.GetTracks() if t.GetNetname() != "GND" or isinstance(t, pcbnew.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    pads = [p for p in board.GetPads() if p.GetNetname() != "GND"]
    gpads = [p for p in board.GetPads() if p.GetNetname() == "GND"]
    zones_other = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() != "GND"
                   and (z.IsOnLayer(F) or z.IsOnLayer(B))]
    gz = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    added = 0
    y = y0 + 0.8
    while y < y1 - 0.7:
        x = x0 + 0.8
        while x < x1 - 0.7:
            pos = pcbnew.VECTOR2I(mm(x), mm(y))
            ok = any(z.HitTestFilledArea(L, pos, 0) for z in gz for L in (F, B) if z.IsOnLayer(L))
            acc = mm(r + clr)
            if ok:
                for t in others:
                    if isinstance(t, pcbnew.PCB_VIA):
                        if (t.GetPosition() - pos).EuclideanNorm() < mm(r + t.GetWidth(F) / 2e6 + 0.25):
                            ok = False; break
                    elif t.HitTest(pos, acc):
                        ok = False; break
            if ok:
                for p in pads:
                    if (p.IsOnLayer(F) or p.IsOnLayer(B)) and p.HitTest(pos, acc):
                        ok = False; break
            if ok:
                for p in gpads:              # keep stitching vias out of pads (paste)
                    if p.HitTest(pos, mm(r + 0.1)):
                        ok = False; break
            if ok:
                for z in zones_other:
                    for L in (F, B):
                        if z.IsOnLayer(L) and z.HitTestFilledArea(L, pos, acc):
                            ok = False; break
                    if not ok: break
            if ok:
                v = pcbnew.PCB_VIA(board); v.SetPosition(pos); v.SetWidth(mm(d)); v.SetDrill(mm(drill))
                v.SetNet(gnd); board.Add(v); others.append(v); added += 1
            x += pitch
        y += pitch
    return added

def main():
    passes = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    board = pcbnew.LoadBoard(PCB)
    fill(board)
    print("fanout (vias, missed):", fanout(board))
    route(board, passes)
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName() == "router keep-out":
            board.Remove(z)
    sys.path.insert(0, HERE)
    import build_pcb
    build_pcb.gnd_fill(board, board.GetNetInfo().GetNetItem("GND"))
    fill(board)
    n = stitch(board)
    fill(board)
    pcbnew.SaveBoard(PCB, board)
    print(f"routed; {n} GND stitching vias")

if __name__ == "__main__":
    main()
