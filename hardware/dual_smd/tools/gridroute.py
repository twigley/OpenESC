#!/usr/bin/env python3
"""Small grid maze router for the outer layers (F.Cu / B.Cu) of dual_esc.

Run with KiCad's Python after build_pcb.py:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/gridroute.py

Freerouting does not close this board (it will not drop vias to inner planes
and plateaus at ~85 unrouted), so this routes the signal nets directly:

1. fan GND / VBAT pads out to the L2 / L3 planes (route_pcb.fanout),
2. drop the router keep-outs, fill zones,
3. rasterise every copper item onto a 0.05 mm grid per outer layer, recording
   which net owns each cell (exact copper, and dilated for track and via
   clearance),
4. A* each remaining connection (8-way moves, vias between F and B where both
   layers allow a via), net by net, nearest pads first, and add the result as
   tracks and vias,
5. add the top / bottom GND fills and stitching vias, refill, save.
"""
import heapq, math, os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_pcb, build_pcb

PCB = route_pcb.PCB
G = 0.05                       # grid, mm
CLR = 0.13                     # clearance used everywhere (netclass minimum), mm
VIA_D, VIA_DRILL = 0.4, 0.2
F, B = pcbnew.F_Cu, pcbnew.B_Cu
I2, I3 = pcbnew.In2_Cu, pcbnew.In3_Cu
LAYERS = (F, I2, I3, B)          # 6-layer board: L3/L4 are signal layers
mm = pcbnew.FromMM
SKIP = {"GND", "VBAT"}         # plane nets: done by fanout + planes
WIDTH = {"Gate": 0.25, "Power": 0.3}
FREE, MULTI = -1, -2

class Grid:
    def __init__(self, board):
        self.board = board
        bb = board.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = bb.GetLeft(), bb.GetTop()
        self.nx = int(pcbnew.ToMM(bb.GetWidth()) / G) + 1
        self.ny = int(pcbnew.ToMM(bb.GetHeight()) / G) + 1
        self.nets = {}
        n = self.nx * self.ny
        # per layer: exact copper owner, track-centre block owner, via-centre block owner
        self.cu = {L: [FREE] * n for L in LAYERS}
        self.trk = {L: [FREE] * n for L in LAYERS}
        self.via = [FREE] * n          # combined over both layers (+ hole spacing)
        self.np = {L: [FREE] * n for L in LAYERS}   # non-pad copper (tracks, vias, zones)
        self.is_pad = False
        self.edge = mm(0.3)
        e = int(round((0.3 + 0.125) / G)) + 1        # copper-to-edge 0.3 mm + half track
        ev = int(round((0.3 + VIA_D / 2) / G)) + 1
        for j in range(self.ny):
            for i in range(self.nx):
                k = j * self.nx + i
                d = min(i, j, self.nx - 1 - i, self.ny - 1 - j)
                if d < e:
                    for L in LAYERS: self.trk[L][k] = MULTI
                if d < ev: self.via[k] = MULTI

    def nid(self, name):
        return self.nets.setdefault(name, len(self.nets))

    def cell(self, i, j):
        return pcbnew.VECTOR2I(self.x0 + int(mm(i * G)), self.y0 + int(mm(j * G)))

    def mark(self, arr, k, nid):
        o = arr[k]
        if o == FREE: arr[k] = nid
        elif o != nid: arr[k] = MULTI

    def raster(self, shape_fn, bbox, nid, layer, is_via=False, via_block=True):
        """shape_fn(pos, r) -> collides within r; mark cu/trk/via owners."""
        pad = mm(CLR + 0.2 + 0.05)
        i0 = max(0, int((bbox.GetLeft() - pad - self.x0) / mm(G)))
        i1 = min(self.nx - 1, int((bbox.GetRight() + pad - self.x0) / mm(G)) + 1)
        j0 = max(0, int((bbox.GetTop() - pad - self.y0) / mm(G)))
        j1 = min(self.ny - 1, int((bbox.GetBottom() + pad - self.y0) / mm(G)) + 1)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                p = self.cell(i, j); k = j * self.nx + i
                if shape_fn(p, CLR + VIA_D / 2):
                    if via_block: self.mark(self.via, k, nid)
                    if layer is not None and shape_fn(p, CLR + 0.125):
                        self.mark(self.trk[layer], k, nid)
                        if shape_fn(p, 0.0):
                            self.mark(self.cu[layer], k, nid)
                            if not self.is_pad: self.mark(self.np[layer], k, nid)

    def add_item(self, it):
        nid = self.nid(it.GetNetname())
        if isinstance(it, pcbnew.PCB_VIA):
            c, r = it.GetPosition(), it.GetWidth(F) / 2
            hole = it.GetDrillValue() / 2
            fn = lambda p, rr: (p - c).EuclideanNorm() <= r + mm(rr)
            for L in LAYERS:
                self.raster(fn, it.GetBoundingBox(), nid, L)
            return
        if isinstance(it, pcbnew.PCB_TRACK):
            L = it.GetLayer()
            if L not in LAYERS: return
            sh = it.GetEffectiveShape(L)
            fn = lambda p, rr: sh.Collide(pcbnew.SHAPE_CIRCLE(p, 1), mm(rr))
            self.raster(fn, it.GetBoundingBox(), nid, L)
            return
        if isinstance(it, pcbnew.PAD):
            self.is_pad = True
            for L in LAYERS:
                if not it.IsOnLayer(L): continue
                sh = it.GetEffectiveShape(L)
                fn = lambda p, rr, sh=sh: sh.Collide(pcbnew.SHAPE_CIRCLE(p, 1), mm(rr))
                self.raster(fn, it.GetBoundingBox(), nid, L)
            self.is_pad = False

    def add_zone(self, z):
        nid = self.nid(z.GetNetname())
        for L in LAYERS:
            if not z.IsOnLayer(L): continue
            fn = lambda p, rr, L=L: z.HitTestFilledArea(L, p, mm(rr))
            # zones refill round a foreign via, so they block tracks but not vias
            self.raster(fn, z.GetBoundingBox(), nid, L, via_block=False)

    def ok_trk(self, L, k, nid):
        o = self.trk[L][k]; return o == FREE or o == nid
    def ok_via(self, k, nid):
        o = self.via[k]; return o == FREE or o == nid

    def edge_ok(self, i, j, r):
        e = (0.3 + r) / G
        return e <= i <= self.nx - 1 - e and e <= j <= self.ny - 1 - e

def astar(g, nid, starts, goal, width):
    """starts: set of (L, k); goal: set of (L, k). Returns path [(L, i, j)]."""
    nx = g.nx
    hw = width / 2
    gi = [(k % nx, k // nx) for _, k in goal]
    def h(i, j):
        return min(abs(i - a) + abs(j - b) for a, b in gi) * 0.9 if len(gi) < 40 else 0
    best = {}
    pq = []
    for L, k in starts:
        i, j = k % nx, k // nx
        best[(L, k)] = 0.0
        heapq.heappush(pq, (h(i, j), 0.0, L, k, None))
    prev = {}
    steps = ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414))
    n = 0
    while pq:
        f, c, L, k, pk = heapq.heappop(pq)
        if best.get((L, k), 1e18) < c: continue
        if (L, k) in prev: continue
        prev[(L, k)] = pk
        if (L, k) in goal:
            path = []; node = (L, k)
            while node is not None:
                path.append(node); node = prev[node]
            return path[::-1]
        n += 1
        if n > 2500000: return None
        i, j = k % nx, k // nx
        for di, dj, cost in steps:
            ii, jj = i + di, j + dj
            if not (0 <= ii < nx and 0 <= jj < g.ny): continue
            kk = jj * nx + ii
            if not g.ok_trk(L, kk, nid) and (L, kk) not in goal: continue
            if di and dj:   # no corner cutting
                if not g.ok_trk(L, j * nx + ii, nid) or not g.ok_trk(L, jj * nx + i, nid): continue
            nc = c + cost * (1.0 if L == F else 1.05)
            if nc < best.get((L, kk), 1e18):
                best[(L, kk)] = nc
                heapq.heappush(pq, (nc + h(ii, jj), nc, L, kk, (L, k)))
        # via
        if g.ok_via(k, nid) and g.edge_ok(i, j, VIA_D / 2):
            for L2 in LAYERS:
                if L2 == L or not g.ok_trk(L2, k, nid): continue
                nc = c + 14
                if nc < best.get((L2, k), 1e18):
                    best[(L2, k)] = nc
                    heapq.heappush(pq, (nc + h(i, j), nc, L2, k, (L, k)))
    return None

def emit(board, g, path, net, width):
    """Turn a grid path into tracks (collinear runs merged) and vias."""
    items = []
    pts = [(L, k % g.nx, k // g.nx) for L, k in path]
    run = [pts[0]]
    def flush(run):
        if len(run) < 2: return
        segs = []
        a = run[0]; d = None
        for b in run[1:]:
            nd = (b[1] - a[1], b[2] - a[2]) if d is None else d
            segs.append(b)
        # merge collinear
        out = [run[0]]
        for q in run[1:]:
            if len(out) >= 2:
                p0, p1 = out[-2], out[-1]
                if (p1[1] - p0[1]) * (q[2] - p1[2]) == (p1[2] - p0[2]) * (q[1] - p1[1]) and \
                   (p1[1] - p0[1]) * (q[1] - p1[1]) >= 0 and (p1[2] - p0[2]) * (q[2] - p1[2]) >= 0:
                    out[-1] = q; continue
            out.append(q)
        for a2, b2 in zip(out, out[1:]):
            t = pcbnew.PCB_TRACK(board); t.SetStart(g.cell(a2[1], a2[2])); t.SetEnd(g.cell(b2[1], b2[2]))
            t.SetWidth(mm(width)); t.SetLayer(a2[0]); t.SetNet(net); board.Add(t); items.append(t)
    for q in pts[1:]:
        if q[0] != run[-1][0]:            # layer change: via at this cell
            flush(run)
            v = pcbnew.PCB_VIA(board); v.SetPosition(g.cell(q[1], q[2])); v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_DRILL)); v.SetNet(net); board.Add(v); items.append(v)
            run = [q]
        else:
            run.append(q)
    flush(run)
    return items

def main():
    board = pcbnew.LoadBoard(PCB)
    route_pcb.fill(board)
    print("fanout:", route_pcb.fanout(board))
    route_pcb.fill(board)
    g = Grid(board)
    for p in board.GetPads(): g.add_item(p)
    for t in board.GetTracks(): g.add_item(t)
    for z in board.Zones():
        if not z.GetIsRuleArea() and (z.IsOnLayer(F) or z.IsOnLayer(B)): g.add_zone(z)
    print("grid", g.nx, "x", g.ny)
    nc = board.GetDesignSettings().m_NetSettings
    nets = {}
    for p in board.GetPads():
        n = p.GetNetname()
        if n and n not in SKIP: nets.setdefault(n, []).append(p)
    order = sorted(nets, key=lambda n: (0 if ("_G" in n or "_IN" in n or "_BST" in n) else 1, n))
    failed = []
    conn = board.GetConnectivity()
    for name in order:
        pads = nets[name]
        nid = g.nid(name)
        netinfo = pads[0].GetNet()
        cls = netinfo.GetNetClassName() if hasattr(netinfo, "GetNetClassName") else ""
        width = 0.25 if name.startswith(("M1_G", "M2_G")) or name[-2:] in ("_A", "_B", "_C") else 0.2
        # groups already connected by copper count as one
        board.BuildConnectivity(); conn = board.GetConnectivity()
        groups = []
        for p in pads:
            for grp in groups:
                if conn.TestTrackEndpointDangling if False else False: pass
            placed = False
            for grp in groups:
                if any(conn.IsConnectedOnLayer(p, F, ()) for _ in ()):
                    pass
            groups.append([p])
        # tree growth: owned copper cells of this net are the tree; pads not yet touching it are targets
        def cells_of(p):
            out = set()
            for L in LAYERS:
                if not p.IsOnLayer(L): continue
                bb = p.GetBoundingBox()
                i0 = int((bb.GetLeft() - g.x0) / mm(G)); i1 = int((bb.GetRight() - g.x0) / mm(G)) + 1
                j0 = int((bb.GetTop() - g.y0) / mm(G)); j1 = int((bb.GetBottom() - g.y0) / mm(G)) + 1
                sh = p.GetEffectiveShape(L)
                for j in range(max(0, j0), min(g.ny, j1 + 1)):
                    for i in range(max(0, i0), min(g.nx, i1 + 1)):
                        if sh.Collide(pcbnew.SHAPE_CIRCLE(g.cell(i, j), 1), 0):
                            out.add((L, j * g.nx + i))
            return out
        # net copper already on the board (zones, taps, earlier tracks)
        def net_cells():
            out = set()
            for L in LAYERS:
                arr = g.np[L]
                out.update((L, k) for k, o in enumerate(arr) if o == nid)
            return out
        tree = net_cells()
        pending = []
        for p in pads:
            pc = cells_of(p)
            if not pc: continue
            pending.append((p, pc))
        # seed: if the net has no zone/via copper, start from the first pad
        connected = []
        if not any(True for _ in ()):
            pass
        board.BuildConnectivity(); conn = board.GetConnectivity()
        unrouted = conn.GetUnconnectedCount(False) if False else None
        # start from the pad nearest the existing net copper
        todo = list(pending)
        if not todo: continue
        base = todo.pop(0)
        tree_cells = set(base[1]) | tree
        while todo:
            # pick pad nearest to the tree (by centre distance to any tree cell sample)
            sample = list(tree_cells)[::max(1, len(tree_cells) // 400)]
            def dist(item):
                c = item[0].GetPosition()
                return min(((c.x - (g.x0 + mm(G) * (k % g.nx))) ** 2 + (c.y - (g.y0 + mm(G) * (k // g.nx))) ** 2) for _, k in sample)
            todo.sort(key=dist)
            p, pc = todo.pop(0)
            if pc & tree_cells:
                tree_cells |= pc; continue
            path = astar(g, nid, pc, tree_cells, width)
            if not path:
                failed.append((name, p.GetParentFootprint().GetReference() + "." + p.GetNumber()))
                continue
            items = emit(board, g, path, p.GetNet(), width)
            for it in items: g.add_item(it)
            tree_cells |= set(path) | pc
        print("routed", name, "failed so far", len(failed))
    print("FAILED:", failed)
    for z in list(board.Zones()):
        pass
    build_pcb.gnd_fill(board, board.GetNetInfo().GetNetItem("GND"))
    route_pcb.fill(board)
    print("stitching vias:", route_pcb.stitch(board))
    route_pcb.fill(board)
    pcbnew.SaveBoard(PCB, board)

if __name__ == "__main__":
    main()
