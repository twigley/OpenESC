#!/usr/bin/env python3
"""Negotiated-congestion router (PathFinder style) for the outer layers.

Run with KiCad's Python after build_pcb.py:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/negroute.py [iterations]

Same grid and fixed-obstacle map as gridroute.py (pads, power zones, plane
fanout vias). Routed copper is not a hard obstacle: every connection is routed
each round, cells used by other nets cost extra (present congestion x history),
and nets that still overlap are ripped up and rerouted until no cell is shared.
"""
import heapq, math, os, sys, time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gridroute as gr, route_pcb, build_pcb

F, B = gr.F, gr.B
G = gr.G
R_TRK = (0.1 + 0.115 + gr.CLR) / G       # track centre keep-off from another net's track centre (0.345 mm)
R_VIA = (0.2 + 0.1 + gr.CLR) / G          # via centre keep-off from another net's track centre (0.43 mm)
DEBUG = os.environ.get('NEG_DEBUG') == '1'
STEPS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414))
VIA_COST = 12.0

def disc(r):
    n = int(r) + 1
    return [(di, dj) for di in range(-n, n + 1) for dj in range(-n, n + 1) if di * di + dj * dj < r * r]
D_TRK, D_VIA = disc(R_TRK), disc(R_VIA)

class Router:
    def __init__(self, g):
        self.g = g
        n = g.nx * g.ny
        self.occ = {L: [0] * n for L in gr.LAYERS}        # how many nets' footprints cover a cell
        self.hist = {L: [0.0] * n for L in gr.LAYERS}
        self.pres = 0.5
        self.foot = {}                                    # net -> {(L,k): count}

    def footprint(self, path):
        """Cells a routed path blocks for other nets (tracks dilated, vias wider, both layers)."""
        nx, ny = self.g.nx, self.g.ny
        out = set()
        for idx, (L, k) in enumerate(path):
            if self.g.cu[L][k] == self.cur_nid: continue      # inside the net's own pad / zone copper
            i, j = k % nx, k // nx
            via = idx > 0 and path[idx - 1][0] != L and path[idx - 1][1] == k
            for dset, layers in ((D_VIA, gr.LAYERS),) if via else ((D_TRK, (L,)),):
                for di, dj in dset:
                    ii, jj = i + di, j + dj
                    if 0 <= ii < nx and 0 <= jj < ny:
                        for LL in layers: out.add((LL, jj * nx + ii))
        return out

    def add(self, net, cells):
        f = self.foot.setdefault(net, {})
        for c in cells:
            if f.get(c, 0) == 0: self.occ[c[0]][c[1]] += 1
            f[c] = f.get(c, 0) + 1

    def rip(self, net):
        for c, cnt in self.foot.pop(net, {}).items():
            self.occ[c[0]][c[1]] -= 1

    def cost(self, net, L, k):
        own = 1 if self.foot.get(net, {}).get((L, k), 0) else 0
        other = self.occ[L][k] - own
        if other <= 0: return 0.0
        return (1.0 + self.hist[L][k]) * self.pres * other

    def search(self, nid, net, starts, goal, budget=1500000):
        g = self.g; nx = g.nx
        gl = list(goal)
        gx = [k % nx for _, k in gl]; gy = [k // nx for _, k in gl]
        cx, cy = sum(gx) / len(gx), sum(gy) / len(gy)
        rad = max(math.hypot(x - cx, y - cy) for x, y in zip(gx, gy))
        h = lambda i, j: max(0.0, math.hypot(i - cx, j - cy) - rad)
        best = {}; prev = {}; pq = []
        for s in starts:
            best[s] = 0.0; heapq.heappush(pq, (h(s[1] % nx, s[1] // nx), 0.0, s, None))
        n = 0
        while pq:
            f, c, node, pk = heapq.heappop(pq)
            if node in prev: continue
            prev[node] = pk
            if node in goal:
                path = []
                while node is not None: path.append(node); node = prev[node]
                return path[::-1]
            n += 1
            if n > budget: return None
            L, k = node; i, j = k % nx, k // nx
            for di, dj, w in STEPS:
                ii, jj = i + di, j + dj
                if not (0 <= ii < nx and 0 <= jj < g.ny): continue
                kk = jj * nx + ii; nn = (L, kk)
                if nn in prev: continue
                if not g.ok_trk(L, kk, nid) and nn not in goal: continue
                if di and dj and (not g.ok_trk(L, j * nx + ii, nid) or not g.ok_trk(L, jj * nx + i, nid)): continue
                nc = c + w * (1.0 if L in (F, B) else 1.02) + self.cost(net, L, kk)
                if nc < best.get(nn, 1e18):
                    best[nn] = nc; heapq.heappush(pq, (nc + h(ii, jj), nc, nn, node))
            if g.ok_via(k, nid) and g.edge_ok(i, j, gr.VIA_D / 2):
                for L2 in gr.LAYERS:
                    nn = (L2, k)
                    if L2 == L or nn in prev or not g.ok_trk(L2, k, nid): continue
                    nc = c + VIA_COST + self.cost(net, L2, k) + self.cost(net, L, k)
                    if nc < best.get(nn, 1e18):
                        best[nn] = nc; heapq.heappush(pq, (nc + h(i, j), nc, nn, node))
        return None

VIP = {}     # pad (ref, number) -> via-in-pad position
def via_in_pads(board, refs=("U101", "U102", "U201", "U202"), d=0.3, drill=0.15):
    """Filled via-in-pad on every signal pin of the drivers and MCUs (JLC multilayer
    minimum 0.15 mm hole / 0.25 mm via, epoxy filled and capped). Vias sit 0.2 mm
    from the pad centre along its length, alternating ends pin to pin, so adjacent
    vias at 0.4 / 0.5 mm pitch keep clearance."""
    n = 0
    for ref in refs:
        fp = board.FindFootprintByReference(ref)
        for p in fp.Pads():
            net = p.GetNetname()
            if not net or net in ("GND", "VBAT"): continue
            bb = p.GetBoundingBox(); c = p.GetPosition()
            num = int(p.GetNumber()) if p.GetNumber().isdigit() else 0
            s = 1 if num % 2 else -1
            off = gr.mm(0.2) * s
            v = c + (pcbnew.VECTOR2I(off, 0) if bb.GetWidth() > bb.GetHeight() else pcbnew.VECTOR2I(0, off))
            if not route_pcb.item_clear(board, v, d / 2, 0.13, net, (F, B), zones=False):
                v = c - (v - c)
                if not route_pcb.item_clear(board, v, d / 2, 0.13, net, (F, B), zones=False):
                    print("no via-in-pad for", ref, p.GetNumber()); continue
            via = pcbnew.PCB_VIA(board); via.SetPosition(v); via.SetWidth(gr.mm(d)); via.SetDrill(gr.mm(drill))
            via.SetNet(p.GetNet()); board.Add(via)
            VIP[(ref, p.GetNumber())] = v; n += 1
    return n

def pad_cells(g, p):
    out = set()
    v = VIP.get((p.GetParentFootprint().GetReference(), p.GetNumber()))
    if v is not None:                                  # the in-pad via reaches every layer
        i0 = int((v.x - g.x0) / gr.mm(G)); j0 = int((v.y - g.y0) / gr.mm(G))
        for di in range(-2, 3):
            for dj in range(-2, 3):
                for L in gr.LAYERS: out.add((L, (j0 + dj) * g.nx + i0 + di))
    for L in gr.LAYERS:
        if not p.IsOnLayer(L): continue
        bb = p.GetBoundingBox(); sh = p.GetEffectiveShape(L)
        i0 = int((bb.GetLeft() - g.x0) / gr.mm(G)); i1 = int((bb.GetRight() - g.x0) / gr.mm(G)) + 1
        j0 = int((bb.GetTop() - g.y0) / gr.mm(G)); j1 = int((bb.GetBottom() - g.y0) / gr.mm(G)) + 1
        for j in range(max(0, j0), min(g.ny, j1 + 1)):
            for i in range(max(0, i0), min(g.nx, i1 + 1)):
                if sh.Collide(pcbnew.SHAPE_CIRCLE(g.cell(i, j), 1), 0):
                    out.add((L, j * g.nx + i))
    return out

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    board = pcbnew.LoadBoard(gr.PCB)
    route_pcb.fill(board)
    print("fanout:", route_pcb.fanout(board), flush=True)
    print("via-in-pad:", via_in_pads(board), flush=True)
    route_pcb.fill(board)
    g = gr.Grid(board)
    for p in board.GetPads(): g.add_item(p)
    vset = set((v.x, v.y) for v in VIP.values())
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) and (t.GetPosition().x, t.GetPosition().y) in vset:
            g.is_pad = True; g.add_item(t); g.is_pad = False   # part of its pad, not seed copper
        else:
            g.add_item(t)
    for z in board.Zones():
        if not z.GetIsRuleArea() and (z.IsOnLayer(F) or z.IsOnLayer(B)): g.add_zone(z)
    nets = {}
    for p in board.GetPads():
        n = p.GetNetname()
        if n and n not in gr.SKIP: nets.setdefault(n, []).append(p)
    width = lambda n: 0.25 if (n.startswith(("M1_G", "M2_G")) or n[-2:] in ("_A", "_B", "_C")) else 0.2
    # per net: pads (cells) and the net's existing fixed copper (zones, taps)
    info = {}
    for n, pads in nets.items():
        nid = g.nid(n)
        fixed = set((L, k) for L in gr.LAYERS for k, o in enumerate(g.np[L]) if o == nid)
        pcs = [pad_cells(g, p) for p in pads]
        pcs = [c for c in pcs if c]
        info[n] = (nid, fixed, pcs, pads[0].GetNet())
    R = Router(g)
    routes = {}
    order = sorted(nets, key=lambda n: (0 if ("_G" in n or "_IN" in n or "_BST" in n) else 1, n))
    todo = list(order)
    for it in range(iters):
        t0 = time.time(); failed = []
        for n in todo:
            R.rip(n)
            nid, fixed, pcs, _ = info[n]
            tree = set(fixed) | set(pcs[0]) if not fixed else set(fixed)
            rest = pcs[1:] if not fixed else pcs[:]
            paths = []
            while rest:
                cx = sum(k % g.nx for _, k in list(tree)[:200]) / min(200, len(tree))
                rest.sort(key=lambda pc: min(abs(k % g.nx - cx) for _, k in list(pc)[:5]))
                pc = rest.pop(0)
                if pc & tree: tree |= pc; continue
                R.cur_nid = nid
                path = R.search(nid, n, tree, pc)
                if not path: failed.append(n); break
                paths.append(path); tree |= set(path) | pc
                R.add(n, R.footprint(path))
            routes[n] = paths
        # conflicts: a net's track centres (or via centres) inside another net's keep-off footprint
        conflicted = set(); dbg = []
        for n, paths in routes.items():
            own = R.foot.get(n, {})
            for path in paths:
                for c in path:
                    if g.cu[c[0]][c[1]] == info[n][0]: continue
                    if R.occ[c[0]][c[1]] - (1 if own.get(c, 0) else 0) > 0:
                        conflicted.add(n); R.hist[c[0]][c[1]] += 0.5
                        if DEBUG and len(dbg) < 12 and n not in [d[0] for d in dbg]:
                            others = [m for m, f in R.foot.items() if m != n and f.get(c)]
                            dbg.append((n, others, round(c[1] % g.nx * G, 2), round(c[1] // g.nx * G, 2), "F" if c[0] == F else "B"))
        if DEBUG: print("conflicts:", dbg, flush=True)
        print(f"iter {it}: {len(todo)} rerouted, {len(conflicted)} nets overlap, {len(set(failed))} unroutable, {time.time()-t0:.0f}s", flush=True)
        if not conflicted and not failed:
            break
        R.pres *= 1.8
        todo = sorted(conflicted | set(failed), key=order.index)
    # emit every net that is overlap-free and complete
    bad = set(failed) | conflicted
    nt = 0
    for n, paths in routes.items():
        if n in bad: continue
        for path in paths:
            gr.emit(board, g, path, info[n][3], width(n)); nt += 1
    print("emitted paths", nt, "nets left unrouted:", sorted(bad), flush=True)
    build_pcb.gnd_fill(board, board.GetNetInfo().GetNetItem("GND"))
    route_pcb.fill(board)
    print("stitching vias:", route_pcb.stitch(board), flush=True)
    route_pcb.fill(board)
    pcbnew.SaveBoard(gr.PCB, board)

if __name__ == "__main__":
    main()
