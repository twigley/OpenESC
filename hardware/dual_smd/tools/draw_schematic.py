#!/usr/bin/env python3
"""Draw the dual-motor ESC schematic as a conventional wired KiCad 8 sheet.

The netlist intent lives in gen_schematic.PARTS. This file only decides where
things go and which wires are drawn. check_schematic.py then rebuilds the
connectivity from the drawn wires, KiCad-style, and compares it to PARTS.

Coordinates below are in grid units (1 u = 2.54 mm), screen axes (y down).
"""
import os, uuid
import gen_schematic as spec

U = 2.54
LIB = "OpenESC_dual"
NS = uuid.UUID("2b0b8f51-3f0e-4a77-9a55-5b1f2f7e9c01")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad", "dual_esc.kicad_sch")
PROJECT = "dual_esc"
def uid(*k): return str(uuid.uuid5(NS, "/".join(map(str, k))))
def mm(v): return f"{round(v * U, 4):g}"
def mmr(v): return f"{round(v, 4):g}"
FONT = "(effects (font (size 1.27 1.27)))"

# ------------------------------------------------------------ symbol library
# Pins: (number, name, type, x_u, y_u (lib, y up), angle, length_u, hidden)
SYM = {}
def box_symbol(name, ref, left, right, width_u, top_row=0, value=None, pin_len=2):
    """Rows in 'left'/'right' are (row, number, name, type); row 0 at top."""
    rows = [r for r, *_ in left + right]
    h0, h1 = min(rows) - 1, max(rows) + 1
    pins = []
    for row, num, nm, et in left:
        pins.append((num, nm, et, -width_u / 2 - pin_len, -row, 0, pin_len, False))
    for row, num, nm, et in right:
        pins.append((num, nm, et, width_u / 2 + pin_len, -row, 180, pin_len, False))
    gfx = [f"(rectangle (start {mm(-width_u/2)} {mm(-h0)}) (end {mm(width_u/2)} {mm(-h1)}) (stroke (width 0.254) (type default)) (fill (type background)))"]
    SYM[name] = dict(ref=ref, pins=pins, gfx=gfx, ref_at=(0, -h0 + 0.6), val_at=(0, -h1 - 0.6), power=False)

def two_pin(name, ref, vertical, gfx, pin_len_mm=2.54, half_u=2):
    if vertical:
        pins = [("1", "~", "passive", 0, half_u, 270, pin_len_mm / U, False),
                ("2", "~", "passive", 0, -half_u, 90, pin_len_mm / U, False)]
        ra, va = (1.2, 0.5), (1.2, -0.5)
    else:
        pins = [("1", "~", "passive", -half_u, 0, 0, pin_len_mm / U, False),
                ("2", "~", "passive", half_u, 0, 180, pin_len_mm / U, False)]
        ra, va = (0, 1.0), (0, -1.0)
    SYM[name] = dict(ref=ref, pins=pins, gfx=gfx, ref_at=ra, val_at=va, power=False, hpos=not vertical)

def pl(*pts, w=0.254, fill="none"):
    return "(polyline (pts " + " ".join(f"(xy {mmr(x)} {mmr(y)})" for x, y in pts) + f") (stroke (width {w}) (type default)) (fill (type {fill})))"

two_pin("R_V", "R", True, ["(rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))"])
two_pin("R_H", "R", False, ["(rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type none)))"])
two_pin("C_V", "C", True, [pl((-2.032, 0.508), (2.032, 0.508), w=0.508), pl((-2.032, -0.508), (2.032, -0.508), w=0.508)], 2.032, 1)
two_pin("C_H", "C", False, [pl((0.508, -2.032), (0.508, 2.032), w=0.508), pl((-0.508, -2.032), (-0.508, 2.032), w=0.508)], 2.032, 1)
two_pin("CP_V", "C", True, [pl((-2.032, 0.508), (2.032, 0.508), w=0.508),
                            "(arc (start -2.032 -1.016) (mid 0 -0.635) (end 2.032 -1.016) (stroke (width 0.508) (type default)) (fill (type none)))",
                            pl((-1.524, 1.524), (-0.508, 1.524)), pl((-1.016, 2.032), (-1.016, 1.016))], 2.032, 1)
# N-channel MOSFET: G left, D top, S bottom. Pads 1-3 = S, 4 = G, 5-8 = D.
SYM["NMOS"] = dict(ref="Q", power=False, ref_at=(1.6, 1.0), val_at=(1.6, -1.0), pins=
    [("4", "G", "input", -2, 0, 0, 1, False)] +
    [(n, "D", "passive", 1, 2, 270, 1, n != "5") for n in "5678"] +
    [(n, "S", "passive", 1, -2, 90, 1, n != "1") for n in "123"], gfx=[
    pl((-2.54, 0), (-1.778, 0)), pl((-1.778, 1.905), (-1.778, -1.905)),
    pl((-1.016, 1.905), (-1.016, 1.27)), pl((-1.016, 0.381), (-1.016, -0.381)), pl((-1.016, -1.27), (-1.016, -1.905)),
    pl((-1.016, 1.588), (2.54, 1.588), (2.54, 2.54)), pl((-1.016, -1.588), (2.54, -1.588), (2.54, -2.54)),
    pl((-1.016, 0), (2.54, 0), (2.54, -1.588)),
    pl((-1.016, 0), (0, 0.508), (0, -0.508), (-1.016, 0), fill="outline"),
    "(circle (center 0.508 0) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))"])
SYM["PAD"] = dict(ref="P", power=False, ref_at=(1.5, 1.0), val_at=(1.5, -1.0),
    pins=[("1", "1", "passive", -1, 0, 0, 1, False)],
    gfx=["(circle (center 0.508 0) (radius 0.508) (stroke (width 0.254) (type default)) (fill (type none)))"])
SYM["RESONATOR"] = dict(ref="Y", power=False, ref_at=(1.5, 1.0), val_at=(1.5, -1.0), pins=[
    ("1", "1", "passive", 0, 2, 270, 1, False), ("3", "3", "passive", 0, -2, 90, 1, False),
    ("2", "GND", "passive", -2, 0, 0, 1, False)], gfx=[
    "(rectangle (start -1.016 0.762) (end 1.016 -0.762) (stroke (width 0.254) (type default)) (fill (type none)))",
    pl((-1.524, 1.27), (1.524, 1.27)), pl((-1.524, -1.27), (1.524, -1.27)),
    pl((0, 2.54), (0, 1.27)), pl((0, -2.54), (0, -1.27)), pl((-2.54, 0), (-1.016, 0))])
def power_sym(name, down):
    g = ([pl((0, 0), (0, -1.27), (1.27, -1.27), (0, -2.54), (-1.27, -1.27), (0, -1.27))] if down else
         [pl((0, 0), (0, 1.27)), pl((-0.762, 0.762), (0, 1.27), (0.762, 0.762))])
    SYM["PWR_" + name] = dict(ref="#PWR", power=True, net=name, pins=[("1", name, "power_in", 0, 0, 270 if down else 90, 0, True)],
                             gfx=g, ref_at=(0, -3 if down else 3), val_at=(0, -1.6 if down else 1.4))
for n, d in (("GND", True), ("VBAT", False), ("+5V", False)):
    power_sym(n, d)
# ERC power flag: an ordinary (non-global) symbol whose power_out pin marks the net it
# touches as driven. '#' reference keeps it off the BOM and the board.
SYM["PWR_FLAG"] = dict(ref="#FLG", power=False, flag=True, ref_at=(0, 1.6), val_at=(0, 2.6),
    pins=[("1", "pwr", "power_out", 0, 0, 90, 0, False)],
    gfx=[pl((0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27))])

# DRV8300DPWR: right-side rows line up with the three half-bridges drawn beside it.
PH_PITCH = 24
def drv_right():
    out = []
    pinmap = {"A": ("19", "20", "18", "11"), "B": ("16", "17", "15", "10"), "C": ("13", "14", "12", "9")}
    for k, p in enumerate("ABC"):
        gh, bst, sh, gl = pinmap[p]
        b = k * PH_PITCH
        out += [(b + 5, gh, "GH" + p, "output"), (b + 7, bst, "BST" + p, "passive"),
                (b + 9, sh, "SH" + p, "passive"), (b + 15, gl, "GL" + p, "output")]
    return out
DRV_LEFT = [(22, "1", "INHA", "input"), (23, "2", "INHB", "input"), (24, "3", "INHC", "input"),
            (26, "4", "INLA", "input"), (27, "5", "INLB", "input"), (28, "6", "INLC", "input"),
            (40, "7", "GVDD", "power_in"), (60, "8", "GND", "power_in")]
box_symbol("DRV8300DPWR", "U", DRV_LEFT, drv_right(), 8)

MCU_LEFT = [(0, "4", "VCC", "power_in"), (1, "6", "VCC", "power_in"), (2, "18", "AVCC", "power_in"),
            (4, "20", "AREF", "passive"), (9, "29", "PC6/~{RESET}", "input"),
            (12, "7", "PB6/XTAL1", "bidirectional"), (16, "8", "PB7/XTAL2", "bidirectional"),
            (19, "19", "ADC6", "input"), (20, "22", "ADC7", "input"),
            (23, "3", "GND", "power_in"), (24, "5", "GND", "power_in"), (25, "21", "GND", "power_in"), (26, "33", "EP", "power_in")]
MCU_RIGHT_ORDER = ["12", "13", "14", "15", "16", "17", None, "23", "24", "25", "26", "27", "28", None,
                   "30", "31", "32", "1", "2", "9", "10", "11"]
MCU_NAMES = {"12": "PB0", "13": "PB1", "14": "PB2", "15": "PB3/MOSI", "16": "PB4/MISO", "17": "PB5/SCK",
             "23": "PC0", "24": "PC1/ADC1", "25": "PC2/ADC2", "26": "PC3", "27": "PC4", "28": "PC5",
             "30": "PD0/RXD", "31": "PD1/TXD", "32": "PD2", "1": "PD3", "2": "PD4", "9": "PD5", "10": "PD6", "11": "PD7"}
MCU_RIGHT = [(i + 1, n, MCU_NAMES[n], "bidirectional") for i, n in enumerate(MCU_RIGHT_ORDER) if n]
box_symbol("ATmega328P-MU", "U", MCU_LEFT, MCU_RIGHT, 14)
box_symbol("MCP1703A-5002", "U", [(0, spec.LDO_PINS["VIN"], "VIN", "power_in"), (2, spec.LDO_PINS["GND"], "GND", "power_in")],
           [(0, spec.LDO_PINS["VOUT"], "VOUT", "power_out")], 6)
box_symbol("CONN6", "J", [], [(3*i - 2, str(i), str(i), "passive") for i in range(1, 7)], 4)
box_symbol("CONN3", "J", [], [(3*i - 2, str(i), str(i), "passive") for i in range(1, 4)], 4)
box_symbol("CONN2", "P", [], [(0, "1", "+", "passive"), (2, "2", "-", "passive")], 4)

# ------------------------------------------------------------- drawing state
inst = []      # (ref, symname, x, y, value, footprint, mpn)
wires = []     # ((x1,y1),(x2,y2))
labels = []    # (kind, name, x, y, side)  kind: label/global
ncs = []
texts = []
boxes = []
pwr_n = [0]
SPEC = {p[0]: p for p in spec.PARTS}

def place(ref, sym, x, y):
    _, _, val, fp, _, mpn = SPEC[ref]
    inst.append((ref, sym, x, y, val, fp, mpn))
flg_n = [0]
def flag(x, y):
    flg_n[0] += 1
    inst.append((f"#FLG{flg_n[0]:02d}", "PWR_FLAG", x, y, "PWR_FLAG", "", ""))
def pwr(name, x, y):
    pwr_n[0] += 1
    inst.append((f"#PWR{pwr_n[0]:03d}", "PWR_" + name, x, y, name, "", ""))
def wire(*pts):
    for a, b in zip(pts, pts[1:]):
        assert a[0] == b[0] or a[1] == b[1], f"non-orthogonal wire {a}->{b}"
        wires.append((a, b))
def glabel(name, x, y, side):   # side: which way the label points ('L' text extends left)
    labels.append(("global_label", name, x, y, side))
def label(name, x, y, side="R"):
    labels.append(("label", name, x, y, side))
def text(s, x, y, size=2.5):
    texts.append((s, x, y, size))
def frame(title, x1, y1, x2, y2):
    boxes.append((x1, y1, x2, y2)); text(title, x1 + 1, y1 + 2, 2.5)

def pin_end(ref_or_inst, num):
    i = next(t for t in inst if t[0] == ref_or_inst)
    _, s, x, y = i[:4]
    p = next(p for p in SYM[s]["pins"] if p[0] == num)
    return (x + p[3], y - p[4])

# ------------------------------------------------------------- motor channel
def motor(m, OX, OY):
    U_ = f"U{m}"
    drv_cy = OY
    place(U_, "DRV8300DPWR", OX + 8, drv_cy)     # pin ends at OX+2 (left), OX+14 (right)
    L, R = OX + 2, OX + 14
    frame(f"MOTOR {m}: DRV8300 3-PHASE GATE DRIVER AND POWER STAGE", OX - 12, OY - 4, OX + 70, OY + 3 * PH_PITCH - 2)
    # inputs from MCU
    for row, num, nm, _ in DRV_LEFT[:6]:
        y = drv_cy + row
        wire((L, y), (L - 3, y)); glabel(f"M{m}_{nm}", L - 3, y, "L")
    # GVDD with local decoupling, GND
    yg = drv_cy + 40
    wire((L, yg), (L - 9, yg))
    for k, (cref, cx) in enumerate(((f"C{6+m}", L - 3), (f"C{8+m}", L - 6))):
        place(cref, "C_V", cx, yg + 1); pwr("GND", cx, yg + 2)
    pwr("VBAT", L - 9, yg)
    text("GVDD from battery (5-20 V)", L - 11, yg - 2, 1.27)
    y0 = drv_cy + 60
    wire((L, y0), (L - 2, y0), (L - 2, y0 + 1)); pwr("GND", L - 2, y0 + 1)

    qn = 6 * (m - 1)
    xb = R + 24
    for k, p in enumerate("ABC"):
        Y = drv_cy + k * PH_PITCH
        qh, ql = f"Q{qn + 2*k + 1}", f"Q{qn + 2*k + 2}"
        rgh, rgl = f"R{qn + 2*k + 1}", f"R{qn + 2*k + 2}"
        rph, rpl = f"R{12 + qn + 2*k + 1}", f"R{12 + qn + 2*k + 2}"
        cb = f"C{3*(m-1) + k + 1}"; cbus = f"C{10 + 3*(m-1) + k + 1}"; pad = f"P{1 + 3*(m-1) + k + 1}"
        # high side
        pwr("VBAT", xb + 1, Y + 1); wire((xb + 1, Y + 1), (xb + 1, Y + 3))
        place(qh, "NMOS", xb, Y + 5)
        place(rgh, "R_H", xb - 7, Y + 5); wire((xb - 5, Y + 5), (xb - 2, Y + 5))
        place(rph, "R_V", xb - 3, Y + 7)
        wire((xb - 3, Y + 9), (xb + 1, Y + 9))
        wire((xb + 1, Y + 7), (xb + 1, Y + 13))          # source(high) -> drain(low)
        wire((xb + 1, Y + 11), (xb + 5, Y + 11)); place(pad, "PAD", xb + 6, Y + 11)
        # low side
        place(ql, "NMOS", xb, Y + 15)
        place(rgl, "R_H", xb - 7, Y + 15); wire((xb - 5, Y + 15), (xb - 2, Y + 15))
        place(rpl, "R_V", xb - 3, Y + 17)
        wire((xb + 1, Y + 17), (xb + 1, Y + 20)); wire((xb - 3, Y + 19), (xb + 1, Y + 19)); pwr("GND", xb + 1, Y + 20)
        # bus decoupling next to the half-bridge
        cx = xb + 14
        pwr("VBAT", cx, Y + 7); wire((cx, Y + 7), (cx, Y + 9)); place(cbus, "C_V", cx, Y + 10)
        wire((cx, Y + 11), (cx, Y + 13)); pwr("GND", cx, Y + 13)
        # driver -> bridge
        dy = drv_cy + k * PH_PITCH  # driver rows for this phase are at dy+5/7/9/15
        wire((R, dy + 5), (xb - 9, Y + 5))
        wire((R, dy + 15), (xb - 9, Y + 15))
        wire((R, dy + 9), (xb - 3, Y + 9))
        wire((R, dy + 7), (R + 3, dy + 7)); place(cb, "C_V", R + 3, dy + 8)
    # bulk
    bx = xb + 22
    for j, cref in enumerate((f"C{16 + 2*m - 1}", f"C{16 + 2*m}")):
        x = bx + 5 * j
        pwr("VBAT", x, drv_cy + 7); wire((x, drv_cy + 7), (x, drv_cy + 9)); place(cref, "CP_V", x, drv_cy + 10)
        wire((x, drv_cy + 11), (x, drv_cy + 13)); pwr("GND", x, drv_cy + 13)
    text("Bulk", bx - 1, drv_cy + 5, 1.27)

# ------------------------------------------------------------- MCU
def mcu(MX, MY):
    place("U3", "ATmega328P-MU", MX, MY)
    L, R = MX - 9, MX + 9
    frame("MICROCONTROLLER ATmega328P (same chip as Arduino Nano)", MX - 40, MY - 6, MX + 32, MY + 32)
    r = lambda row: MY + row
    # supply pins
    for row in (0, 1, 2):
        wire((L, r(row)), (L - 3, r(row)))
    wire((L - 3, r(0)), (L - 3, r(2))); wire((L - 3, r(0)), (L - 3, r(-1))); pwr("+5V", L - 3, r(-1))
    # AREF
    wire((L, r(4)), (L - 2, r(4))); place("C26", "C_V", L - 2, r(5)); pwr("GND", L - 2, r(6))
    # reset
    wire((L, r(9)), (L - 12, r(9)))
    place("R25", "R_V", L - 5, r(7)); pwr("+5V", L - 5, r(5))
    place("C28", "C_H", L - 13, r(9)); wire((L - 14, r(9)), (L - 16, r(9))); label("DTR", L - 16, r(9), "L")
    label("~{RESET}", L - 8, r(9), "R")
    # resonator
    wire((L, r(12)), (L - 6, r(12))); wire((L, r(16)), (L - 6, r(16)))
    place("Y1", "RESONATOR", L - 6, r(14))
    wire((L - 8, r(14)), (L - 10, r(14)), (L - 10, r(15))); pwr("GND", L - 10, r(15))
    for row, num in ((19, "19"), (20, "22")):
        ncs.append(("U3", num))
    for row in (23, 24, 25, 26):
        wire((L, r(row)), (L - 2, r(row)))
    wire((L - 2, r(23)), (L - 2, r(27))); pwr("GND", L - 2, r(27))
    # decoupling, one per supply pin
    for j, c in enumerate(("C23", "C24", "C25", "C27")):
        x = MX - 36 + 4 * j
        pwr("+5V", x, r(19)); wire((x, r(19)), (x, r(20))); place(c, "C_V", x, r(21)); wire((x, r(22)), (x, r(23))); pwr("GND", x, r(23))
    text("Decoupling at U3 pins 4, 6, 18 and +5 V bulk", MX - 37, r(17), 1.27)
    # signal pins -> global labels
    nets = SPEC["U3"][4]
    for row, num, nm, _ in MCU_RIGHT:
        y = r(row); net = nets[num]
        if net is None:
            ncs.append(("U3", num)); continue
        wire((R, y), (R + 3, y))
        (glabel if net.startswith("M") else label)(net, R + 3, y, "R")

def conn_pins(ref, X, Y, nets_by_pin, glob=()):
    """Connector at (X, Y); pin i at y = Y + 3i - 2. Power nets get a symbol, others a label."""
    place(ref, "CONN6" if len(nets_by_pin) == 6 else "CONN3", X, Y); jx = X + 4
    items = sorted(nets_by_pin.items())
    for idx, (i, net) in enumerate(items):
        y = Y + 3 * i - 2
        nxt = items[idx + 1][1] if idx + 1 < len(items) else None
        if net == "GND":
            wire((jx, y), (jx + 2, y))
            if nxt == "GND": wire((jx + 2, y), (jx + 2, y + 3))
            else: pwr("GND", jx + 2, y)
        elif net == "+5V":
            wire((jx, y), (jx + 10, y)); pwr("+5V", jx + 10, y)
        else:
            wire((jx, y), (jx + 5, y)); (glabel if net in glob else label)(net, jx + 5, y, "R")

def programming(X, Y):
    frame("PROGRAMMING", X - 2, Y - 4, X + 40, Y + 23)
    text("J1 USB-serial (FTDI order)", X - 1, Y - 1, 1.27)
    conn_pins("J1", X, Y + 2, {1: "GND", 2: "GND", 3: "+5V", 4: "RXD", 5: "TXD", 6: "DTR"})
    text("J2 ISP (TC2030), battery OFF", X + 19, Y - 1, 1.27)
    conn_pins("J2", X + 20, Y + 2, {1: "M2_INLB", 2: "+5V", 3: "SCK", 4: "M1_INHC", 5: "~{RESET}", 6: "GND"},
              glob=("M2_INLB", "M1_INHC"))
    text("MISO = M2_INLB, MOSI = M1_INHC", X + 19, Y + 22, 1.27)

def supply(X, Y):
    frame("BATTERY INPUT (2S) AND 5 V SUPPLY", X - 2, Y - 4, X + 62, Y + 10)
    place("P1", "CONN2", X, Y + 1)                  # pins at (X+4, Y+1) and (X+4, Y+3)
    yv, yg = Y + 1, Y + 3
    pwr("VBAT", X + 6, yv - 0); pwr("GND", X + 6, yg + 4)
    caps = ["C21"]
    xend = X + 8 + 5 * len(caps)
    wire((X + 4, yv), (xend, yv)); wire((X + 4, yg), (xend, yg))
    wire((X + 6, yg), (X + 6, yg + 4))
    for j, c in enumerate(caps):
        place(c, "C_V", X + 9 + 5 * j, yv + 1)
    flag(X + 7, yv); flag(X + 7, yg)      # battery is the source of VBAT and GND (ERC)
    # LDO: VIN row 0, GND row 2 line up with the rails
    place("U4", "MCP1703A-5002", xend + 5, yv)       # VIN at xend+0, VOUT at xend+10
    vo = xend + 10
    wire((vo, yv), (vo + 12, yv))
    for j, c in enumerate(("C22", "C27")):
        x = vo + 3 + 5 * j
        place(c, "C_V", x, yv + 1); wire((x, yv + 2), (x, yv + 3)); pwr("GND", x, yv + 3)
    pwr("+5V", vo + 12, yv)
    text("C21 = LDO input cap; bulk caps sit at each bridge", X + 8, Y - 1, 1.27)

def pots(X, Y):
    frame("SPEED INPUTS (potentiometers)", X - 2, Y - 4, X + 40, Y + 11)
    conn_pins("J3", X, Y, {1: "+5V", 2: "M1_SPD", 3: "GND"}, glob=("M1_SPD",))
    conn_pins("J4", X + 20, Y, {1: "+5V", 2: "M2_SPD", 3: "GND"}, glob=("M2_SPD",))

motor(1, 16, 8)
motor(2, 100, 8)
mcu(215, 14)
programming(178, 58)
supply(16, 92)
pots(178, 90)

# ------------------------------------------------------------- post-process
def endpoints():
    pts = set()
    for a, b in wires: pts |= {a, b}
    for ref, s, x, y, *_ in inst:
        for p in SYM[s]["pins"]: pts.add((x + p[3], y - p[4]))
    for _, _, x, y, _ in labels: pts.add((x, y))
    return pts
def on_seg(p, a, b):
    if a[0] == b[0] == p[0]: return min(a[1], b[1]) < p[1] < max(a[1], b[1])
    if a[1] == b[1] == p[1]: return min(a[0], b[0]) < p[0] < max(a[0], b[0])
    return False
def split_wires():
    global wires
    pts = endpoints(); changed = True
    while changed:
        changed = False; out = []
        for a, b in wires:
            hit = next((p for p in pts if on_seg(p, a, b)), None)
            if hit: out += [(a, hit), (hit, b)]; changed = True
            else: out.append((a, b))
        wires = out
split_wires()
deg = {}
for a, b in wires:
    for p in (a, b): deg[p] = deg.get(p, 0) + 1
pin_pts = {}
for ref, s, x, y, *_ in inst:
    for p in SYM[s]["pins"]: pin_pts[(x + p[3], y - p[4])] = 1
junctions = [p for p, d in deg.items() if d + pin_pts.get(p, 0) >= 3]

# ------------------------------------------------------------- writer
def lib_symbol(name, prefix=LIB + ":"):
    s = SYM[name]
    hide_names = name in ("R_V", "R_H", "C_V", "C_H", "CP_V", "NMOS", "PAD", "RESONATOR", "PWR_FLAG") or s["power"]
    head = f'(symbol "{prefix}{name}"' + (" (power)" if s["power"] else "")
    if hide_names: head += " (pin_numbers hide)"
    head += f' (pin_names (offset {"0" if s["power"] else "1.016"}){" hide" if hide_names else ""})'
    nob = s["power"] or s.get("flag")
    head += f' (exclude_from_sim no) (in_bom {"no" if nob else "yes"}) (on_board {"no" if s.get("flag") else "yes"})'
    hide = " hide" if s["power"] else ""
    val = s.get("net", name)
    L = [head,
         f'(property "Reference" "{s["ref"]}" (at {mm(s["ref_at"][0])} {mm(s["ref_at"][1])} 0) (effects (font (size 1.27 1.27)){hide}))',
         f'(property "Value" "{val}" (at {mm(s["val_at"][0])} {mm(s["val_at"][1])} 0) {FONT})',
         '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '(property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'(symbol "{name}_0_1" ' + " ".join(s["gfx"]) + ")", f'(symbol "{name}_1_1"']
    for num, nm, et, x, y, ang, ln, hid in s["pins"]:
        L.append(f'(pin {et} line (at {mm(x)} {mm(y)} {ang}) (length {mm(ln)}){" hide" if hid else ""} '
                 f'(name "{nm}" {FONT}) (number "{num}" {FONT}))')
    L.append("))")
    return "\n".join(L)

def write():
    root = uid("root")
    o = [f'(kicad_sch (version 20231120) (generator "eeschema") (generator_version "8.0") (uuid "{root}") (paper "A1")',
         '(title_block (title "OpenESC dual-motor SMD ESC") (date "2026-11-20") (rev "0.2") '
         '(comment 1 "2S LiPo, 20 A peak per motor, ATmega328P + 2x DRV8300D") '
         '(comment 2 "Drawn by hardware/dual_smd/tools/draw_schematic.py; netlist in gen_schematic.py"))',
         "(lib_symbols", *[lib_symbol(n) for n in sorted({i[1] for i in inst})], ")"]
    for x, y in junctions:
        o.append(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid("j", x, y)}"))')
    for ref, num in ncs:
        x, y = pin_end(ref, num)
        o.append(f'(no_connect (at {mm(x)} {mm(y)}) (uuid "{uid("nc", ref, num)}"))')
    for a, b in wires:
        o.append(f'(wire (pts (xy {mm(a[0])} {mm(a[1])}) (xy {mm(b[0])} {mm(b[1])})) (stroke (width 0) (type default)) (uuid "{uid("w", a, b)}"))')
    for kind, name, x, y, side in labels:
        ang, just = (180, "right") if side == "L" else (0, "left")
        if kind == "global_label":
            o.append(f'(global_label "{name}" (shape bidirectional) (at {mm(x)} {mm(y)} {ang}) (fields_autoplaced yes) '
                     f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid("gl", name, x, y)}") '
                     f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {mm(x)} {mm(y)} 0) (effects (font (size 1.27 1.27)) (justify {just}) hide)))')
        else:
            o.append(f'(label "{name}" (at {mm(x)} {mm(y)} {ang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{uid("l", name, x, y)}"))')
    for s, x, y, size in texts:
        o.append(f'(text "{s}" (exclude_from_sim no) (at {mm(x)} {mm(y)} 0) (effects (font (size {size} {size}) bold) (justify left bottom)) (uuid "{uid("t", s, x, y)}"))')
    for x1, y1, x2, y2 in boxes:
        o.append(f'(rectangle (start {mm(x1)} {mm(y1)}) (end {mm(x2)} {mm(y2)}) (stroke (width 0.254) (type dash)) (fill (type none)) (uuid "{uid("b", x1, y1)}"))')
    for ref, s, x, y, val, fp, mpn in inst:
        S = SYM[s]; pw = S["power"] or S.get("flag", False)
        rx, ry = S["ref_at"]; vx, vy = S["val_at"]
        props = [("Reference", ref, x + rx, y - ry, pw), ("Value", val, x + vx, y - vy, False),
                 ("Footprint", fp, x, y, True), ("Datasheet", "", x, y, True), ("Description", "", x, y, True)]
        if mpn: props.append(("MPN", mpn, x, y, True))
        just = " (justify left)" if not pw and s not in ("ATmega328P-MU", "DRV8300DPWR", "MCP1703A-5002", "CONN6", "CONN3", "CONN2") else ""
        L = [f'(symbol (lib_id "{LIB}:{s}") (at {mm(x)} {mm(y)} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if pw else "yes"}) (on_board {"no" if S.get("flag") else "yes"}) (dnp no) (uuid "{uid("s", ref)}")']
        for k, v, px, py, hid in props:
            j = just if k in ("Reference", "Value") else ""
            L.append(f'(property "{k}" "{v}" (at {mm(px)} {mm(py)} 0) (effects (font (size 1.27 1.27)){j}{" hide" if hid else ""}))')
        for p in S["pins"]:
            L.append(f'(pin "{p[0]}" (uuid "{uid("p", ref, p[0])}"))')
        L.append(f'(instances (project "{PROJECT}" (path "/{root}" (reference "{ref}") (unit 1)))))')
        o.append("\n".join(L))
    o.append('(sheet_instances (path "/" (page "1"))))')
    open(OUT, "w").write("\n".join(o) + "\n")
    # Project symbol library holding the same symbols, plus the project lib tables,
    # so KiCad resolves OpenESC_dual:* and the local footprint library.
    kd = os.path.dirname(OUT)
    with open(os.path.join(kd, f"{LIB}.kicad_sym"), "w") as f:
        f.write('(kicad_symbol_lib (version 20231120) (generator "draw_schematic") (generator_version "8.0")\n')
        f.write("\n".join(lib_symbol(n, prefix="") for n in sorted(SYM)) + "\n)\n")
    with open(os.path.join(kd, "sym-lib-table"), "w") as f:
        f.write(f'(sym_lib_table\n  (version 7)\n  (lib (name "{LIB}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB}.kicad_sym") (options "") (descr "Generated by draw_schematic.py"))\n)\n')
    with open(os.path.join(kd, "fp-lib-table"), "w") as f:
        f.write(f'(fp_lib_table\n  (version 7)\n  (lib (name "{LIB}") (type "KiCad") (uri "${{KIPRJMOD}}/{LIB}.pretty") (options "") (descr "Project footprints"))\n)\n')

if __name__ == "__main__":
    placed = {i[0] for i in inst if not i[0].startswith("#")}
    missing = set(SPEC) - placed
    assert not missing, f"parts in spec but not drawn: {sorted(missing)}"
    write()
    print(f"symbols={len(inst)} wires={len(wires)} junctions={len(junctions)} labels={len(labels)}")
