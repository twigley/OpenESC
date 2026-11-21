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
two_pin("L_H", "L", False, ["(arc (start -2.54 0) (mid -1.905 0.635) (end -1.27 0) (stroke (width 0.254) (type default)) (fill (type none)))",
                           "(arc (start -1.27 0) (mid -0.635 0.635) (end 0 0) (stroke (width 0.254) (type default)) (fill (type none)))",
                           "(arc (start 0 0) (mid 0.635 0.635) (end 1.27 0) (stroke (width 0.254) (type default)) (fill (type none)))",
                           "(arc (start 1.27 0) (mid 1.905 0.635) (end 2.54 0) (stroke (width 0.254) (type default)) (fill (type none)))"])
SYM["PAD"] = dict(ref="P", power=False, ref_at=(1.5, 1.0), val_at=(1.5, -1.0),
    pins=[("1", "1", "passive", -1, 0, 0, 1, False)],
    gfx=["(circle (center 0.508 0) (radius 0.508) (stroke (width 0.254) (type default)) (fill (type none)))"])

def nmos_gfx(dy):
    """N-MOSFET drawing centred at (0, dy) mm: gate lead from x = -5.08, drain up, source down."""
    g = lambda *p: pl(*[(x, y + dy) for x, y in p])
    return [g((-5.08, 0), (-1.778, 0)), g((-1.778, 1.905), (-1.778, -1.905)),
            g((-1.016, 1.905), (-1.016, 1.27)), g((-1.016, 0.381), (-1.016, -0.381)), g((-1.016, -1.27), (-1.016, -1.905)),
            g((-1.016, 1.588), (2.54, 1.588), (2.54, 2.54)), g((-1.016, -1.588), (2.54, -1.588), (2.54, -2.54)),
            g((-1.016, 0), (2.54, 0), (2.54, -1.588)),
            pl((-1.016, dy), (0, dy + 0.508), (0, dy - 0.508), (-1.016, dy), fill="outline"),
            f"(circle (center 0.508 {mmr(dy)}) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))"]
# AON7934 dual asymmetric half-bridge, drawn as its two MOSFETs.
# Q1 (high side): G1 = 1, D1 = 2,3,4,10; Q2 (low side): G2 = 8, S2 = 5,6,7; S1/D2 (switch node) = 9.
SYM["AON7934"] = dict(ref="Q", power=False, ref_at=(4.5, 3.0), val_at=(4.5, 2.0), pins=
    [("1", "G1", "input", -3, 2, 0, 1, False), ("8", "G2", "input", -3, -2, 0, 1, False),
     ("9", "S1/D2", "passive", 4, 0, 180, 3, False)] +
    [(n, "D1", "passive", 1, 5, 270, 1, n != "2") for n in ("2", "3", "4", "10")] +
    [(n, "S2", "passive", 1, -5, 90, 1, n != "5") for n in ("5", "6", "7")],
    gfx=nmos_gfx(5.08) + nmos_gfx(-5.08) + [pl((2.54, 10.16), (2.54, 7.62)), pl((2.54, -7.62), (2.54, -10.16))])
def power_sym(name, down):
    g = ([pl((0, 0), (0, -1.27), (1.27, -1.27), (0, -2.54), (-1.27, -1.27), (0, -1.27))] if down else
         [pl((0, 0), (0, 1.27)), pl((-0.762, 0.762), (0, 1.27), (0.762, 0.762))])
    SYM["PWR_" + name] = dict(ref="#PWR", power=True, net=name, pins=[("1", name, "power_in", 0, 0, 270 if down else 90, 0, True)],
                             gfx=g, ref_at=(0, -3 if down else 3), val_at=(0, -1.6 if down else 1.4))
for n, d in (("GND", True), ("VBAT", False), ("+5V", False), ("+3V3", False)):
    power_sym(n, d)
SYM["PWR_FLAG"] = dict(ref="#FLG", power=False, flag=True, ref_at=(0, 1.6), val_at=(0, 2.6),
    pins=[("1", "pwr", "power_out", 0, 0, 90, 0, False)],
    gfx=[pl((0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27))])

# DRV8300DRGE (VQFN-24). Right side: per phase k rows 24k+0 BST, +2 SH, +4 GH, +8 GL,
# lining up with the half-bridge drawn beside it (FET centre at row 24k + 6).
PH = 24
DRV_RIGHT = []
for k, (p, bst, sh, gh, gl) in enumerate((("A", "20", "18", "19", "11"), ("B", "17", "15", "16", "10"), ("C", "14", "12", "13", "9"))):
    b = PH * k
    DRV_RIGHT += [(b, bst, "BST" + p, "passive"), (b + 2, sh, "SH" + p, "passive"),
                  (b + 4, gh, "GH" + p, "output"), (b + 8, gl, "GL" + p, "output")]
DRV_LEFT = [(0, "22", "INHA", "input"), (1, "1", "INLA", "input"), (2, "23", "INHB", "input"),
            (3, "2", "INLB", "input"), (4, "24", "INHC", "input"), (5, "3", "INLC", "input"),
            (8, "4", "GVDD", "power_in"), (10, "5", "MODE", "input"), (11, "21", "DT", "input"),
            (12, "7", "NC", "passive"), (13, "8", "NC", "passive"), (15, "6", "GND", "power_in"), (16, "25", "EP", "power_in")]
box_symbol("DRV8300DRGE", "U", DRV_LEFT, DRV_RIGHT, 10)

# AT32F421K8U7 (QFN32). Right rows 0-5 line up with the driver inputs.
MCU_RIGHT = [(0, "20", "PA10/TMR1_CH3", "bidirectional"), (1, "15", "PB1/TMR1_CH3N", "bidirectional"),
             (2, "19", "PA9/TMR1_CH2", "bidirectional"), (3, "14", "PB0/TMR1_CH2N", "bidirectional"),
             (4, "18", "PA8/TMR1_CH1", "bidirectional"), (5, "13", "PA7/TMR1_CH1N", "bidirectional"),
             (7, "6", "PA0/CMP_INM6", "bidirectional"), (8, "10", "PA4/CMP_INM4", "bidirectional"),
             (9, "11", "PA5/CMP_INM5", "bidirectional"), (10, "7", "PA1/CMP_INP", "bidirectional"),
             (11, "12", "PA6/ADC6", "bidirectional"), (12, "9", "PA3/ADC3", "bidirectional"),
             (14, "8", "PA2/TMR15_CH1", "bidirectional"), (15, "29", "PB6/USART1_TX", "bidirectional"),
             (17, "23", "PA13/SWDIO", "bidirectional"), (18, "24", "PA14/SWCLK", "bidirectional")]
MCU_LEFT = [(0, "1", "VDD", "power_in"), (1, "17", "VDD", "power_in"), (2, "5", "VDDA", "power_in"),
            (4, "4", "NRST", "input"), (6, "31", "BOOT0", "input"),
            (8, "2", "PF0", "bidirectional"), (9, "3", "PF1", "bidirectional"), (10, "16", "PB2", "bidirectional"),
            (11, "21", "PA11", "bidirectional"), (12, "22", "PA12", "bidirectional"), (13, "25", "PA15", "bidirectional"),
            (14, "26", "PB3", "bidirectional"), (15, "27", "PB4", "bidirectional"), (16, "28", "PB5", "bidirectional"),
            (17, "30", "PB7", "bidirectional"), (18, "32", "PB8", "bidirectional"), (20, "33", "VSS/EP", "power_in")]
box_symbol("AT32F421K8U7", "U", MCU_LEFT, MCU_RIGHT, 16)
box_symbol("INA186A1", "U", [(0, "4", "IN+", "input"), (2, "5", "IN-", "input"), (4, "3", "VS", "power_in"),
                             (6, "2", "GND", "power_in"), (7, "1", "REF", "input")], [(0, "6", "OUT", "output")], 8)
box_symbol("TPS62933", "U", [(0, "3", "VIN", "power_in"), (2, "2", "EN", "input"), (4, "1", "RT", "input"), (6, "4", "GND", "power_in")],
           [(0, "6", "BST", "passive"), (2, "5", "SW", "output"), (4, "8", "FB", "input"), (6, "7", "SS", "passive")], 8)
box_symbol("TLV75533PDBV", "U", [(0, "1", "IN", "power_in"), (2, "3", "EN", "input"), (4, "2", "GND", "power_in")],
           [(0, "5", "OUT", "power_out"), (4, "4", "NC", "passive")], 8)

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
def glabel(name, x, y, side):
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
def nc(ref, num): ncs.append((ref, num))

def cap_to_gnd(ref, x, y_top, top_net=None, sym="C_V"):
    """Vertical cap with its top pin at (x, y_top) and GND below."""
    place(ref, sym, x, y_top + 1); pwr("GND", x, y_top + 2)
    if top_net: pwr(top_net, x, y_top)

# ------------------------------------------------------------- one motor channel
def motor(m, OX, OY):
    b = 100 * m
    N = lambda s: f"M{m}_{s}"
    MX = OX + 44                       # MCU centre; pins end at MX -/+ 10
    L, R = MX - 10, MX + 10
    Dxl = R + 24                       # driver left pin ends
    DX = Dxl + 7; Dxr = Dxl + 14       # driver centre / right pin ends
    Qx = Dxr + 12                      # half-bridge symbol x
    frame(f"MOTOR {m}: AT32F421 (AM32 RR_ROBOT_DUAL_ESC_F421), DRV8300 DRIVER, AON7934 HALF-BRIDGES",
          OX, OY - 12, Qx + 66, OY + 80)
    place(f"U{b+1}", "AT32F421K8U7", MX, OY)
    place(f"U{b+2}", "DRV8300DRGE", DX, OY)
    # MCU -> driver: six straight wires (rows 0-5)
    for row in range(6):
        wire((R, OY + row), (Dxl, OY + row))
    # MCU supply and decoupling (one cap per supply pin)
    for row in (0, 1, 2):
        wire((L, OY + row), (L - 3, OY + row))
    wire((L - 3, OY), (L - 3, OY + 2)); wire((L - 3, OY), (L - 3, OY - 2)); pwr("+3V3", L - 3, OY - 2)
    for j, (c, note) in enumerate(((f"C{b+1}", "pin 1"), (f"C{b+2}", "pin 17"), (f"C{b+3}", "VDDA"))):
        x = OX + 4 + 5 * j
        cap_to_gnd(c, x, OY + 1, "+3V3")
    text("Decoupling at VDD 1, VDD 17, VDDA", OX + 2, OY - 3, 1.27)
    # NRST: 100 nF to GND + SWD pad; BOOT0: 10k to GND
    wire((L, OY + 4), (L - 14, OY + 4))
    cap_to_gnd(f"C{b+4}", L - 6, OY + 4)
    place(f"P{b+8}", "PAD", L - 13, OY + 4)            # pad pin end at L-14
    place(f"R{b+1}", "R_H", L - 2, OY + 6)             # right pin at L (BOOT0), left at L-4
    wire((L - 4, OY + 6), (L - 4, OY + 7)); pwr("GND", L - 4, OY + 7)
    for row, num, *_ in MCU_LEFT:
        if 8 <= row <= 18: nc(f"U{b+1}", num)
    wire((L, OY + 20), (L - 2, OY + 20), (L - 2, OY + 21)); pwr("GND", L - 2, OY + 21)
    # MCU right: sense inputs by label, signal / telemetry / SWD to pads
    for row, net in ((7, "BEMF_A"), (8, "BEMF_B"), (9, "BEMF_C"), (10, "NEUT"), (11, "ISENSE")):
        wire((R, OY + row), (R + 3, OY + row)); label(N(net), R + 3, OY + row)
    wire((R, OY + 12), (R + 3, OY + 12)); label("VSENSE", R + 3, OY + 12)
    place(f"R{b+2}", "R_H", R + 4, OY + 14)            # 100R: pins R+2 / R+6
    wire((R, OY + 14), (R + 2, OY + 14)); wire((R + 6, OY + 14), (R + 8, OY + 14))
    place(f"P{b+4}", "PAD", R + 9, OY + 14)
    for row, pad, what in ((15, f"P{b+5}", f"TLM{m} (telemetry out)"), (17, f"P{b+6}", f"SWDIO{m}"), (18, f"P{b+7}", f"SWCLK{m}")):
        wire((R, OY + row), (R + 8, OY + row)); place(pad, "PAD", R + 9, OY + row)
    text("NRST / SWD pads: flash AM32 bootloader once", L - 30, OY + 9, 1.27)
    # driver supply: GVDD from VBAT with 10 uF + 100 nF; MODE, DT, NC open; GND
    yg = OY + 8
    wire((Dxl, yg), (Dxl - 11, yg))
    cap_to_gnd(f"C{b+5}", Dxl - 3, yg); cap_to_gnd(f"C{b+6}", Dxl - 8, yg)
    pwr("VBAT", Dxl - 11, yg)
    for num in ("5", "21", "7", "8"): nc(f"U{b+2}", num)
    text("MODE open: GLx = INLx; DT open: 200 ns", Dxl - 12, OY + 21, 1.27)
    wire((Dxl, OY + 15), (Dxl - 2, OY + 15), (Dxl - 2, OY + 16)); wire((Dxl, OY + 16), (Dxl - 2, OY + 16))
    wire((Dxl - 2, OY + 16), (Dxl - 2, OY + 17)); pwr("GND", Dxl - 2, OY + 17)
    # half-bridges
    LS = Qx + 10                       # low-side source rail
    for k, p in enumerate("ABC"):
        Y = OY + PH * k + 6
        q = f"Q{b+k+1}"
        place(q, "AON7934", Qx, Y)
        # bootstrap cap BST -> SH, SH loop to the switch node
        wire((Dxr, Y - 6), (Dxr + 3, Y - 6)); place(f"C{b+7+k}", "C_V", Dxr + 3, Y - 5)
        wire((Dxr, Y - 4), (Qx - 6, Y - 4), (Qx - 6, Y - 9), (Qx + 7, Y - 9), (Qx + 7, Y))
        wire((Qx + 4, Y), (Qx + 7, Y), (Qx + 16, Y))
        label(N(p), Qx + 11, Y)
        place(f"P{b+k+1}", "PAD", Qx + 17, Y)
        # gates (no series resistor: space; DRV8300 drive strength sets the edges)
        wire((Dxr, Y - 2), (Qx - 3, Y - 2))
        wire((Dxr, Y + 2), (Qx - 3, Y + 2))
        place(f"R{b+3+k}", "R_V", Qx - 5, Y + 4); pwr("GND", Qx - 5, Y + 6)   # 10k GL pull-down
        # drain to VBAT, source to the LS rail
        wire((Qx + 1, Y - 5), (Qx + 1, Y - 6), (Qx + 3, Y - 6)); pwr("VBAT", Qx + 3, Y - 6)
        wire((Qx + 1, Y + 5), (Qx + 1, Y + 7), (LS, Y + 7))
        # bus cap at the half-bridge
        cap_to_gnd(f"C{b+10+k}", Qx + 27, Y - 4, "VBAT")
    yA, yC = OY + 6 + 7, OY + 2 * PH + 6 + 7
    # current sense: LS rail -> 0.5 mOhm shunt -> GND, INA186A1 (25 V/V) -> RC -> PA6
    ys = yC + 4
    wire((LS, yA), (LS, ys))
    place(f"R{b+50}", "R_V", LS, ys + 2); pwr("GND", LS, ys + 4)
    text("Shunt 0.5 mOhm x 25 V/V = 12.5 mV/A (AM32 MILLIVOLT_PER_AMP 12)", LS - 4, ys + 12, 1.27)
    IX = LS + 14
    place(f"U{b+3}", "INA186A1", IX, ys)
    wire((LS, ys), (IX - 6, ys))                       # IN+ (Kelvin to the shunt top)
    wire((IX - 6, ys + 2), (IX - 11, ys + 2), (IX - 11, ys + 3)); pwr("GND", IX - 11, ys + 3)   # IN- (shunt GND end)
    wire((IX - 6, ys + 4), (IX - 9, ys + 4)); pwr("+3V3", IX - 9, ys + 4)
    cap_to_gnd(f"C{b+13}", IX - 9, ys + 4)
    wire((IX - 6, ys + 6), (IX - 7, ys + 6), (IX - 7, ys + 7)); wire((IX - 6, ys + 7), (IX - 7, ys + 7))
    wire((IX - 7, ys + 7), (IX - 7, ys + 8)); pwr("GND", IX - 7, ys + 8)
    place(f"R{b+6}", "R_H", IX + 8, ys)                # pins IX+6 / IX+10
    wire((IX + 10, ys), (IX + 14, ys)); label(N("ISENSE"), IX + 14, ys)
    cap_to_gnd(f"C{b+14}", IX + 12, ys)
    # BEMF dividers and virtual neutral
    BX = Qx + 36
    text("BEMF dividers 10k / 4.7k (8.4 V -> 2.7 V) + 1 nF, virtual neutral 3 x 10k / 1.5k", BX - 2, OY - 6, 1.27)
    for k, (p, rt, rb) in enumerate((("A", 7, 8), ("B", 9, 10), ("C", 11, 12))):
        y = OY + 6 * k
        label(N(p), BX, y, "L"); wire((BX, y), (BX + 2, y))
        place(f"R{b+rt}", "R_H", BX + 4, y)            # pins BX+2 / BX+6
        wire((BX + 6, y), (BX + 14, y)); label(N("BEMF_" + p), BX + 14, y)
        place(f"R{b+rb}", "R_V", BX + 9, y + 2); pwr("GND", BX + 9, y + 4)
        cap_to_gnd(f"C{b+15+k}", BX + 12, y)            # 1 nF BEMF filter
    yN = OY + 22
    for k, p in enumerate("ABC"):
        y = yN + 3 * k
        label(N(p), BX, y, "L"); wire((BX, y), (BX + 2, y))
        place(f"R{b+13+k}", "R_H", BX + 4, y)
        wire((BX + 6, y), (BX + 9, y))
    wire((BX + 9, yN), (BX + 9, yN + 6)); wire((BX + 9, yN + 6), (BX + 14, yN + 6)); label(N("NEUT"), BX + 14, yN + 6)
    place(f"R{b+16}", "R_V", BX + 9, yN + 8); pwr("GND", BX + 9, yN + 10)

# ------------------------------------------------------------- shared supply
def supply(X, Y):
    frame("BATTERY (2S Li-ion 6.0-8.4 V), 5 V BEC, 3.3 V LDO, Vbat SENSE", X - 2, Y - 6, X + 110, Y + 50)
    # battery pads, flags
    place("P1", "PAD", X + 1, Y); place("P2", "PAD", X + 1, Y + 4)
    wire((X, Y), (X - 1, Y)); pwr("VBAT", X - 1, Y)
    wire((X, Y + 4), (X - 1, Y + 4), (X - 1, Y + 5)); pwr("GND", X - 1, Y + 5)
    text("BAT+ / BAT- pads", X + 3, Y + 2, 1.27)
    pwr("VBAT", X + 8, Y + 8); wire((X + 8, Y + 8), (X + 8, Y + 9)); flag(X + 8, Y + 9)
    pwr("GND", X + 12, Y + 10); wire((X + 12, Y + 10), (X + 12, Y + 9)); flag(X + 12, Y + 9)
    # bulk caps on the battery leads
    for i in range(4):
        cap_to_gnd(f"C{i+1}", X + 18 + 5 * i, Y + 1, "VBAT", "CP_V")
    text("C1-C4 220 uF: mounted on the battery leads, within 20 mm of P1/P2 (not on the PCB)", X + 14, Y - 2, 1.27)
    # Vbat divider -> VSENSE (both MCUs PA3)
    pwr("VBAT", X + 84, Y + 2)
    place("R1", "R_V", X + 84, Y + 4)
    wire((X + 84, Y + 6), (X + 88, Y + 6)); label("VSENSE", X + 88, Y + 6)
    place("R2", "R_V", X + 84, Y + 8); pwr("GND", X + 84, Y + 10)
    text("Vbat sense 100k / 10k (AM32 TARGET_VOLTAGE_DIVIDER 110)", X + 76, Y - 1, 1.27)
    # buck: TPS62933 1.2 MHz -> +5V
    BX, BY = X + 20, Y + 22
    place("U1", "TPS62933", BX, BY)                    # left pins end BX-6, right BX+6
    wire((BX - 6, BY), (BX - 14, BY)); pwr("VBAT", BX - 14, BY)
    cap_to_gnd("C5", BX - 9, BY); cap_to_gnd("C6", BX - 12, BY)
    nc("U1", "2")
    wire((BX - 6, BY + 4), (BX - 8, BY + 4), (BX - 8, BY + 6)); wire((BX - 6, BY + 6), (BX - 8, BY + 6))
    wire((BX - 8, BY + 6), (BX - 8, BY + 7)); pwr("GND", BX - 8, BY + 7)
    text("RT to GND: 1.2 MHz; EN open: on", BX - 16, BY + 10, 1.27)
    wire((BX + 6, BY), (BX + 9, BY)); place("C7", "C_V", BX + 9, BY + 1)       # BST cap to SW
    wire((BX + 6, BY + 2), (BX + 9, BY + 2), (BX + 12, BY + 2))
    place("L1", "L_H", BX + 14, BY + 2)                # pins BX+12 / BX+16
    wire((BX + 16, BY + 2), (BX + 30, BY + 2)); pwr("+5V", BX + 30, BY + 2)
    cap_to_gnd("C9", BX + 24, BY + 2); cap_to_gnd("C10", BX + 27, BY + 2)
    place("R3", "R_V", BX + 19, BY + 4)                # top pin BX+19,BY+2 on +5V; bottom BY+6
    wire((BX + 6, BY + 4), (BX + 17, BY + 4), (BX + 17, BY + 6), (BX + 19, BY + 6))
    place("R4", "R_V", BX + 19, BY + 8); pwr("GND", BX + 19, BY + 10)
    wire((BX + 6, BY + 6), (BX + 7, BY + 6), (BX + 7, BY + 9)); place("C8", "C_V", BX + 7, BY + 10); pwr("GND", BX + 7, BY + 11)
    pwr("+5V", BX + 33, BY + 1); wire((BX + 33, BY + 1), (BX + 33, BY + 2)); flag(BX + 33, BY + 2)
    text("5 V BEC", BX + 22, BY - 4, 1.27)
    # pads for the receiver
    place("P4", "PAD", BX + 37, BY + 6); wire((BX + 36, BY + 6), (BX + 34, BY + 6)); pwr("+5V", BX + 34, BY + 6)
    place("P3", "PAD", BX + 37, BY + 9); wire((BX + 36, BY + 9), (BX + 34, BY + 9), (BX + 34, BY + 10)); pwr("GND", BX + 34, BY + 10)
    text("5V / GND to receiver", BX + 39, BY + 7, 1.27)
    # LDO: TLV75533 +5V -> +3V3
    LX, LY = X + 80, Y + 22
    place("U2", "TLV75533PDBV", LX, LY)
    wire((LX - 6, LY), (LX - 10, LY)); pwr("+5V", LX - 10, LY)
    wire((LX - 6, LY + 2), (LX - 8, LY + 2), (LX - 8, LY))
    cap_to_gnd("C11", LX - 12, LY, "+5V")
    wire((LX - 6, LY + 4), (LX - 7, LY + 4), (LX - 7, LY + 5)); pwr("GND", LX - 7, LY + 5)
    nc("U2", "4")
    wire((LX + 6, LY), (LX + 12, LY)); pwr("+3V3", LX + 12, LY)
    cap_to_gnd("C12", LX + 9, LY)
    # SWD supply / ground pads
    place("P5", "PAD", LX + 17, LY + 8); wire((LX + 16, LY + 8), (LX + 14, LY + 8)); pwr("+3V3", LX + 14, LY + 8)
    place("P6", "PAD", LX + 17, LY + 11); wire((LX + 16, LY + 11), (LX + 14, LY + 11), (LX + 14, LY + 12)); pwr("GND", LX + 14, LY + 12)
    text("SWD 3V3 / GND", LX + 19, LY + 9, 1.27)

motor(1, 6, 26)
motor(2, 6, 124)
supply(210, 26)

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
    hide_names = name in ("R_V", "R_H", "C_V", "C_H", "CP_V", "L_H", "AON7934", "PAD", "PWR_FLAG") or s["power"]
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
         '(title_block (title "OpenESC dual-motor AM32 ESC") (date "2026-11-21") (rev "0.3") '
         '(comment 1 "2S Li-ion, 2 x (AT32F421 + DRV8300 + 3 x AON7934), AM32 RR_ROBOT_DUAL_ESC_F421") '
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
        just = " (justify left)" if not pw and s not in ("AT32F421K8U7", "DRV8300DRGE", "INA186A1", "TPS62933", "TLV75533PDBV") else ""
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
