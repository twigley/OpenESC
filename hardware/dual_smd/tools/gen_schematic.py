#!/usr/bin/env python3
"""Generate the KiCad 8 schematic for the dual-motor SMD ESC.

Single source of truth for the netlist. Every pin gets a net label at its
connection point (no drawn wires), so connectivity is exactly what the
PARTS table says. Run:  python3 gen_schematic.py  -> ../kicad/dual_esc.kicad_sch
Also writes ../kicad/netlist.md for review.
"""
import os, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "kicad")
PROJECT = "dual_esc"
LIB = "OpenESC_dual"
NS = uuid.UUID("6d1f3a52-8c1e-4f0a-9b6e-0d2f2a7c11e5")

def uid(*k):  # deterministic UUIDs so regenerating gives clean diffs
    return str(uuid.uuid5(NS, "/".join(map(str, k))))

# ---------------------------------------------------------------- symbols
# pin spec: (number, name, electrical type, side L/R, hidden?) ; pins sharing
# (side, name) on a 'stack' symbol are drawn at one point.
SYMBOLS = {
 "DRV8300DPWR": dict(ref="U", stack=False, pins=[
   ("1","INHA","input","L"),("2","INHB","input","L"),("3","INHC","input","L"),
   ("4","INLA","input","L"),("5","INLB","input","L"),("6","INLC","input","L"),
   ("7","GVDD","passive","L"),("8","GND","passive","L"),
   ("20","BSTA","passive","R"),("19","GHA","output","R"),("18","SHA","passive","R"),
   ("17","BSTB","passive","R"),("16","GHB","output","R"),("15","SHB","passive","R"),
   ("14","BSTC","passive","R"),("13","GHC","output","R"),("12","SHC","passive","R"),
   ("11","GLA","output","R"),("10","GLB","output","R"),("9","GLC","output","R")]),
 # ATmega328P 32-pin TQFP / VQFN(MLF) pinout, pad 33 = exposed pad
 "ATmega328P-MU": dict(ref="U", stack=False, pins=[
   ("4","VCC","passive","L"),("6","VCC","passive","L"),("18","AVCC","passive","L"),
   ("20","AREF","passive","L"),("3","GND","passive","L"),("5","GND","passive","L"),
   ("21","GND","passive","L"),("33","EP","passive","L"),("29","PC6/~RESET","bidirectional","L"),
   ("7","PB6/XTAL1","bidirectional","L"),("8","PB7/XTAL2","bidirectional","L"),
   ("19","ADC6","input","L"),("22","ADC7","input","L"),
   ("12","PB0","bidirectional","R"),("13","PB1","bidirectional","R"),("14","PB2","bidirectional","R"),
   ("15","PB3/MOSI","bidirectional","R"),("16","PB4/MISO","bidirectional","R"),("17","PB5/SCK","bidirectional","R"),
   ("23","PC0","bidirectional","R"),("24","PC1","bidirectional","R"),("25","PC2","bidirectional","R"),
   ("26","PC3","bidirectional","R"),("27","PC4","bidirectional","R"),("28","PC5","bidirectional","R"),
   ("30","PD0/RXD","bidirectional","R"),("31","PD1/TXD","bidirectional","R"),("32","PD2","bidirectional","R"),
   ("1","PD3","bidirectional","R"),("2","PD4","bidirectional","R"),("9","PD5","bidirectional","R"),
   ("10","PD6","bidirectional","R"),("11","PD7","bidirectional","R")]),
 "LDO_SOT23": dict(ref="U", stack=False, pins=[
   ("@VIN","VIN","passive","L"),("@GND","GND","passive","L"),("@VOUT","VOUT","passive","R")]),
 "Resonator_3pin": dict(ref="Y", stack=False, pins=[
   ("1","1","passive","L"),("2","GND","passive","L"),("3","3","passive","R")]),
 # PG-TSDSON-8 FL / SuperSO8: 1-3 S, 4 G, 5-8 D (+ pad 9 = drain tab if footprint has it)
 "NMOS_8pin": dict(ref="Q", stack=True, pins=[
   ("4","G","input","L"),
   ("1","S","passive","R"),("2","S","passive","R"),("3","S","passive","R"),
   ("5","D","passive","R"),("6","D","passive","R"),("7","D","passive","R"),("8","D","passive","R")]),
 "R": dict(ref="R", stack=False, pins=[("1","~","passive","L"),("2","~","passive","R")]),
 "C": dict(ref="C", stack=False, pins=[("1","~","passive","L"),("2","~","passive","R")]),
 "CP": dict(ref="C", stack=False, pins=[("1","+","passive","L"),("2","-","passive","R")]),
 "Conn_1": dict(ref="P", stack=False, pins=[("1","1","passive","R")]),
 "Conn_2": dict(ref="P", stack=False, pins=[("1","1","passive","R"),("2","2","passive","R")]),
 "Conn_3": dict(ref="J", stack=False, pins=[(str(i),str(i),"passive","R") for i in (1,2,3)]),
 "Conn_6": dict(ref="J", stack=False, pins=[(str(i),str(i),"passive","R") for i in range(1,7)]),
}

# ----------------------------------------------------------------- parts
FP = dict(
 tssop20="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
 qfn32="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm",
 sot23="Package_TO_SOT_SMD:SOT-23",
 reson="Crystal:Resonator_SMD_Murata_CSTxExxV-3Pin_3.0x1.1mm",
 fet="Package_TO_SOT_SMD:Infineon_PG-TSDSON-8_FL",   # ASSIGN/VERIFY in KiCad
 r0402="Resistor_SMD:R_0402_1005Metric",
 c0402="Capacitor_SMD:C_0402_1005Metric", c0603="Capacitor_SMD:C_0603_1608Metric",
 c0805="Capacitor_SMD:C_0805_2012Metric", c1206="Capacitor_SMD:C_1206_3216Metric",
 cp8="Capacitor_SMD:CP_Elec_8x10",
 pad4="TestPoint:TestPoint_Pad_4.0x4.0mm",
 jst3="Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
 hdr6="Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
 tc2030="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
)

PARTS = []   # (ref, symbol, value, footprint, {pin: net or None}, mpn)
def add(ref, sym, val, fp, pins, mpn=""):
    PARTS.append((ref, sym, val, FP[fp], pins, mpn))

# LDO pin numbers are filled from the verified datasheet table below
LDO_PINS = {"VIN": "3", "GND": "1", "VOUT": "2"}

PH = "ABC"
for m in (1, 2):
    U = f"U{m}"; base_q = 6*(m-1); base_r = 6*(m-1); base_cb = 3*(m-1)
    drv = {"7":"VBAT","8":"GND"}
    inh = {1:{"A":"M1_INHA","B":"M1_INHB","C":"M1_INHC"},2:{"A":"M2_INHA","B":"M2_INHB","C":"M2_INHC"}}[m]
    for i,p in enumerate(PH):
        drv[str(1+i)] = f"M{m}_INH{p}"
        drv[str(4+i)] = f"M{m}_INL{p}"
        bst, gh, sh = {"A":("20","19","18"),"B":("17","16","15"),"C":("14","13","12")}[p]
        gl = {"A":"11","B":"10","C":"9"}[p]
        node = f"M{m}_{p}"
        drv[bst] = f"M{m}_BST{p}"; drv[gh] = f"M{m}_GH{p}"; drv[sh] = node; drv[gl] = f"M{m}_GL{p}"
        qh, ql = f"Q{base_q+2*i+1}", f"Q{base_q+2*i+2}"
        add(qh,"NMOS_8pin","BSZ019N03LS","fet",{"4":f"M{m}_GH{p}_G",**{k:node for k in "123"},**{k:"VBAT" for k in "5678"}},"BSZ019N03LSATMA1")
        add(ql,"NMOS_8pin","BSZ019N03LS","fet",{"4":f"M{m}_GL{p}_G",**{k:"GND" for k in "123"},**{k:node for k in "5678"}},"BSZ019N03LSATMA1")
        add(f"R{base_r+2*i+1}","R","10R","r0402",{"1":f"M{m}_GH{p}","2":f"M{m}_GH{p}_G"})
        add(f"R{base_r+2*i+2}","R","10R","r0402",{"1":f"M{m}_GL{p}","2":f"M{m}_GL{p}_G"})
        add(f"R{12+base_r+2*i+1}","R","10k","r0402",{"1":f"M{m}_GH{p}_G","2":node})
        add(f"R{12+base_r+2*i+2}","R","10k","r0402",{"1":f"M{m}_GL{p}_G","2":"GND"})
        add(f"C{base_cb+i+1}","C","220nF 25V","c0603",{"1":f"M{m}_BST{p}","2":node})
        add(f"C{10+base_cb+i+1}","C","10uF 25V","c1206",{"1":"VBAT","2":"GND"})
        add(f"P{1+3*(m-1)+i+1}","Conn_1",f"M{m}_{p}","pad4",{"1":node})
    add(U,"DRV8300DPWR","DRV8300DPWR","tssop20",drv,"DRV8300DPWR")
    add(f"C{6+m}","C","10uF 25V","c0805",{"1":"VBAT","2":"GND"})
    add(f"C{8+m}","C","100nF 25V","c0402",{"1":"VBAT","2":"GND"})
    add(f"C{16+2*m-1}","CP","330uF 16V","cp8",{"1":"VBAT","2":"GND"})
    add(f"C{16+2*m}","CP","330uF 16V","cp8",{"1":"VBAT","2":"GND"})

mcu = {"4":"+5V","6":"+5V","18":"+5V","20":"AREF","3":"GND","5":"GND","21":"GND","33":"GND",
       "29":"~RESET","7":"XTAL1","8":"XTAL2","19":None,"22":None,
       "13":"M1_INHA","14":"M1_INHB","15":"M1_INHC",   # PB1 PB2 PB3/MOSI
       "2":"M1_INLA","1":"M1_INLB","32":"M1_INLC",     # PD4 PD3 PD2
       "9":"M2_INHA","10":"M2_INHB","11":"M2_INHC",    # PD5 PD6 PD7
       "12":"M2_INLA","16":"M2_INLB","26":"M2_INLC",   # PB0 PB4/MISO PC3
       "17":"SCK","24":"M1_SPD","25":"M2_SPD",         # PB5, PC1(A1), PC2(A2)
       "23":None,"27":None,"28":None,
       "30":"RXD","31":"TXD"}
add("U3","ATmega328P-MU","ATmega328P-MU","qfn32",mcu,"ATMEGA328P-MU")
add("Y1","Resonator_3pin","16MHz","reson",{"1":"XTAL1","2":"GND","3":"XTAL2"},"CSTNE16M0V53Z000R0")
add("U4","LDO_SOT23","MCP1703A-5002","sot23",{LDO_PINS["VIN"]:"VBAT",LDO_PINS["GND"]:"GND",LDO_PINS["VOUT"]:"+5V"},"MCP1703AT-5002E/CB")
add("C21","C","1uF 25V","c0603",{"1":"VBAT","2":"GND"})
add("C22","C","1uF 25V","c0603",{"1":"+5V","2":"GND"})
add("C23","C","100nF","c0402",{"1":"+5V","2":"GND"})
add("C24","C","100nF","c0402",{"1":"+5V","2":"GND"})
add("C25","C","100nF","c0402",{"1":"+5V","2":"GND"})
add("C26","C","100nF","c0402",{"1":"AREF","2":"GND"})
add("C27","C","10uF 10V","c0603",{"1":"+5V","2":"GND"})
add("C28","C","100nF","c0402",{"1":"DTR","2":"~RESET"})
add("R25","R","10k","r0402",{"1":"+5V","2":"~RESET"})
# FTDI / Pro Mini order: GND, CTS(GND), VCC, RXI, TXO, DTR
add("J1","Conn_6","Serial","hdr6",{"1":"GND","2":"GND","3":"+5V","4":"RXD","5":"TXD","6":"DTR"})
# AVR ISP 2x3: 1 MISO, 2 VCC, 3 SCK, 4 MOSI, 5 RST, 6 GND
add("J2","Conn_6","ISP","tc2030",{"1":"M2_INLB","2":"+5V","3":"SCK","4":"M1_INHC","5":"~RESET","6":"GND"})
add("J3","Conn_3","Speed M1","jst3",{"1":"+5V","2":"M1_SPD","3":"GND"})
add("J4","Conn_3","Speed M2","jst3",{"1":"+5V","2":"M2_SPD","3":"GND"})
add("P1","Conn_2","Battery","pad4",{"1":"VBAT","2":"GND"})

# ---------------------------------------------------------------- writer
G = 2.54
def fmt(v): return f"{round(v,4):g}"

def sym_geom(name):
    s = SYMBOLS[name]; L=[]; R=[]; seenL={}; seenR={}
    for pin in s["pins"]:
        num,nm,et,side = pin
        if s["stack"]:
            seen = seenL if side=="L" else seenR
            if nm in seen: continue
            seen[nm]=1
        (L if side=="L" else R).append(pin)
    rows = max(len(L), len(R), 1)
    h = (rows+1)*G
    namelen = max([len(p[1]) for p in s["pins"]] + [1])
    w = max(4*G, round((namelen*1.27*2+4)/G)*G) if len(SYMBOLS[name]["pins"])>3 else 4*G
    pos = {}
    def place(lst, side):
        for i,p in enumerate(lst):
            y = h/2 - G - i*G
            x = -w/2 - G if side=="L" else w/2 + G
            y = round(y/G)*G if rows%2 else round((y-G/2)/G)*G+G/2*0
            pos[(side,p[1]) if s["stack"] else p[0]] = (x, y)
    place(L,"L"); place(R,"R")
    out = {}
    for num,nm,et,side in s["pins"]:
        out[num] = pos[(side,nm)] if s["stack"] else pos[num]
    return w, h, out

def lib_symbol(name):
    s = SYMBOLS[name]; w,h,pos = sym_geom(name)
    lines = [f'(symbol "{LIB}:{name}" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
      f'(property "Reference" "{s["ref"]}" (at 0 {fmt(h/2+1.27)} 0) (effects (font (size 1.27 1.27))))',
      f'(property "Value" "{name}" (at 0 {fmt(-h/2-1.27)} 0) (effects (font (size 1.27 1.27))))',
      '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
      '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
      '(property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
      f'(symbol "{name}_0_1" (rectangle (start {fmt(-w/2)} {fmt(h/2)}) (end {fmt(w/2)} {fmt(-h/2)}) (stroke (width 0.254) (type default)) (fill (type background))))',
      f'(symbol "{name}_1_1"']
    shown=set()
    for num,nm,et,side in s["pins"]:
        x,y = pos[num]; ang = 0 if side=="L" else 180
        key=(x,y); hide = " hide" if key in shown else ""; shown.add(key)
        lines.append(f'(pin {et} line (at {fmt(x)} {fmt(y)} {ang}) (length {G}){hide} (name "{nm}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    lines.append("))")
    return "\n".join(lines)

BLOCKS = [  # (title, origin x, origin y, width, height, refs)
 ("Battery input and 5 V supply",  20, 30, 230, 120, ["P1","C17","C18","C19","C20","U4","C21","C22","C27"]),
 ("Microcontroller and programming", 270, 30, 330, 250, ["U3","Y1","C23","C24","C25","C26","R25","C28","J1","J2","J3","J4"]),
 ("Motor 1 gate driver",            20, 170, 230, 190, ["U1","C7","C9","C1","C2","C3"]+[f"R{i}" for i in range(1,7)]+[f"R{i}" for i in range(13,19)]),
 ("Motor 1 power stage",            20, 380, 380, 190, [f"Q{i}" for i in range(1,7)]+["C11","C12","C13","P2","P3","P4"]),
 ("Motor 2 gate driver",           615, 30, 215, 250, ["U2","C8","C10","C4","C5","C6"]+[f"R{i}" for i in range(7,13)]+[f"R{i}" for i in range(19,25)]),
 ("Motor 2 power stage",           420, 380, 400, 190, [f"Q{i}" for i in range(7,13)]+["C14","C15","C16","P5","P6","P7"]),
]
STUB = 2*G      # visible wire from each pin to its net label
LABEL_ROOM = 22.86

def main():
    root = uid("root")
    SYMBOLS["LDO_SOT23"]["pins"] = [(LDO_PINS[n], n, et, sd) for (_, n, et, sd) in SYMBOLS["LDO_SOT23"]["pins"]]
    body = []; nets = {}
    byref = {p[0]: p for p in PARTS}
    placed = [r for blk in BLOCKS for r in blk[5]]
    assert sorted(placed) == sorted(byref), f"block assignment mismatch: {set(byref) ^ set(placed)}"
    snap = lambda v: round(v / G) * G
    for title, bx, by, bw, bh, refs in BLOCKS:
        body.append(f'(text "{title}" (exclude_from_sim no) (at {fmt(snap(bx))} {fmt(snap(by-5))} 0) (effects (font (size 3 3) (thickness 0.6) bold) (justify left bottom)) (uuid "{uid("title",title)}"))')
        body.append(f'(rectangle (start {fmt(snap(bx-5))} {fmt(snap(by-12))}) (end {fmt(snap(bx+bw))} {fmt(snap(by+bh))}) (stroke (width 0.3) (type dash)) (fill (type none)) (uuid "{uid("box",title)}"))')
        col_x = bx; y = by; col_w = 0
        for ref in refs:
            _, sym, val, fp, pins, mpn = byref[ref]
            w, h, pos = sym_geom(sym)
            span = w + 2*(G + STUB + LABEL_ROOM)
            if y + h + 8 > by + bh:
                col_x += col_w + 6; y = by; col_w = 0
            cx = snap(col_x + span/2); cy = snap(y + h/2 + 3*G)
            col_w = max(col_w, span); y = cy + h/2 + 4*G
            props = [("Reference",ref,(cx, cy-h/2-1.27),False),("Value",val,(cx, cy+h/2+1.27),False),
                     ("Footprint",fp,(cx,cy),True),("Datasheet","",(cx,cy),True),("Description","",(cx,cy),True)]
            if mpn: props.append(("MPN",mpn,(cx,cy),True))
            pl = [f'(symbol (lib_id "{LIB}:{sym}") (at {fmt(cx)} {fmt(cy)} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid("sym",ref)}")']
            for k,v,(px,py),hid in props:
                pl.append(f'(property "{k}" "{v}" (at {fmt(px)} {fmt(py)} 0) (effects (font (size 1.27 1.27)){" hide" if hid else ""}))')
            for num,_,_,_ in SYMBOLS[sym]["pins"]:
                pl.append(f'(pin "{num}" (uuid "{uid("pin",ref,num)}"))')
            pl.append(f'(instances (project "{PROJECT}" (path "/{root}" (reference "{ref}") (unit 1)))))')
            body.append("\n".join(pl))
            done=set()
            for num,nm,et,side in SYMBOLS[sym]["pins"]:
                px,py = pos[num]; ax, ay = cx+px, cy-py
                net = pins.get(num, "__MISSING__")
                assert net != "__MISSING__", f"{ref} pin {num} has no net entry"
                nets.setdefault(net, []).append(f"{ref}.{num}")
                if (ax,ay) in done: continue
                done.add((ax,ay))
                if net is None:
                    body.append(f'(no_connect (at {fmt(ax)} {fmt(ay)}) (uuid "{uid("nc",ref,num)}"))')
                    continue
                ex = ax - STUB if side == "L" else ax + STUB
                body.append(f'(wire (pts (xy {fmt(ax)} {fmt(ay)}) (xy {fmt(ex)} {fmt(ay)})) (stroke (width 0) (type default)) (uuid "{uid("w",ref,num)}"))')
                ang, just = (180,"right") if side=="L" else (0,"left")
                body.append(f'(label "{net}" (at {fmt(ex)} {fmt(ay)} {ang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{uid("lbl",ref,num)}"))')
            extra = set(pins) - {p[0] for p in SYMBOLS[sym]["pins"]}
            assert not extra, f"{ref}: nets on unknown pins {extra}"
    used = sorted({p[1] for p in PARTS})
    sch = [f'(kicad_sch (version 20231120) (generator "eeschema") (generator_version "8.0") (uuid "{root}") (paper "A1")',
           '(title_block (title "OpenESC dual-motor SMD ESC") (rev "0.1") (comment 1 "Generated by hardware/dual_smd/tools/gen_schematic.py - edit the script, not this file"))',
           "(lib_symbols", *[lib_symbol(s) for s in used], ")", *body,
           '(sheet_instances (path "/" (page "1"))))']
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, f"{PROJECT}.kicad_sch"),"w").write("\n".join(sch)+"\n")
    with open(os.path.join(OUT,"netlist.md"),"w") as f:
        f.write("# Generated netlist (from gen_schematic.py)\n\n| Net | Pins |\n|---|---|\n")
        for n in sorted(nets, key=lambda n:(n is None, str(n))):
            f.write(f"| {n if n else '(no connect)'} | {' '.join(sorted(nets[n]))} |\n")
    return nets

if __name__ == "__main__":
    nets = main()
    singles = [n for n,p in nets.items() if n and len(p) < 2]
    print(f"parts={len(PARTS)} nets={len([n for n in nets if n])} single-pin nets={singles}")
