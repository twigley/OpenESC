#!/usr/bin/env python3
"""Netlist for the dual-motor AM32 ESC (PARTS table).

Two independent channels, each an AT32F421K8U7 running the stock AM32 target
RR_ROBOT_DUAL_ESC_F421 (hardware groups AT_C + AT_045), a DRV8300DRGER gate
driver and three AON7934 dual asymmetric half-bridge MOSFETs. Shared 5 V buck
(BEC) and 3.3 V LDO. Bulk caps are mounted on the battery leads (off-board).

This file is the single source of truth for connectivity. draw_schematic.py
draws the KiCad sheet from it; check_schematic.py proves the drawing matches.
Running this file runs draw_schematic.py.

Datasheets checked (2026-11-21):
  AT32F421 DS v2.02 Figure 4 (QFN32 pinout; pins 16 = PB2 and 32 = PB8, so it
    is NOT identical to STM32F051K8U, whose 16/32 are VSS).  K8U7 = 5x5 mm,
    K8U7-4 = 4x4 mm 0.4 mm pitch (Table 49, EP 2.7 mm), same pinout; the 4x4
    part is used so the board fits 28 x 20 mm.
  DRV8300 SLVSFG5D Table 6-1 (RGE VQFN-24). MODE floating = GLx non-inverted;
    DT floating = 200 ns fixed dead time. GVDD 5-20 V, >= 10 uF.
  AON7934 Rev 1.1 + AOS PO-00136 (DFN3x3A_8L_EP2). 1 G1, 2-4 D1, 5-7 S2,
    8 G2, pad 9 = S1/D2 (switch node), pad 10 = D1.
  INA186 SBOS318B: A1 = 25 V/V; DCK (SC70-6) 1 REF, 2 GND, 3 VS, 4 IN+, 5 IN-, 6 OUT.
  TPS62933 SLUSEA4D: SOT583 1 RT, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST, 7 SS, 8 FB.
    5 V at 1.2 MHz (RT to GND): RTOP 31.3k (31.6k used), RBOT 10k, 2.2 uH,
    30 uF typical effective COUT (Table 10-2).
  TLV755P SBVS320D: DBV (SOT-23-5) 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

FP = dict(
 mcu="Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
 drv="Package_DFN_QFN:VQFN-24-1EP_4x4mm_P0.5mm_EP2.45x2.45mm",
 fet="OpenESC_dual:AOS_DFN3x3A-8L-EP2_3x3mm_P0.65mm",
 ina="Package_TO_SOT_SMD:SOT-363_SC-70-6",
 buck="Package_TO_SOT_SMD:SOT-583-8",
 ldo="Package_TO_SOT_SMD:SOT-23-5",
 ind="Inductor_SMD:L_Changjiang_FNR3015S",
 shunt="Resistor_SMD:R_1206_3216Metric",
 r0402="Resistor_SMD:R_0402_1005Metric",
 c0402="Capacitor_SMD:C_0402_1005Metric",
 c0603="Capacitor_SMD:C_0603_1608Metric",
 c0805="Capacitor_SMD:C_0805_2012Metric",
 bulk="Capacitor_SMD:CP_Elec_6.3x7.7",
 batt="OpenESC_dual:Pad_SMD_2.5x5.0mm",
 phase="OpenESC_dual:Pad_SMD_2.5x3.0mm",
 pad15="OpenESC_dual:Pad_SMD_1.5x1.5mm_Tight",
 pad10="OpenESC_dual:Pad_SMD_1.0x1.0mm_Tight",
)

PARTS = []      # (ref, symbol, value, footprint, {pin: net or None}, mpn)
OFF_BOARD = set()   # fitted, in the BOM, but not on the PCB (lead-mounted)
def add(ref, sym, val, fp, pins, mpn=""):
    PARTS.append((ref, sym, val, FP[fp], pins, mpn))

# --------------------------------------------------------------- per motor
# AM32 RR_ROBOT_DUAL_ESC_F421 = HARDWARE_GROUP_AT_C + AT_045:
#   A: INH PA10 (TMR1_CH3)  INL PB1 (CH3N)   BEMF PA0
#   B: INH PA9  (CH2)       INL PB0 (CH2N)   BEMF PA4
#   C: INH PA8  (CH1)       INL PA7 (CH1N)   BEMF PA5
#   neutral PA1 (comparator +), signal in PA2 (TMR15_CH1), telemetry PB6
#   (USART1_TX), Vbat sense PA3 (ADC3), current sense PA6 (ADC6).
MCU_PINS = {"1": "+3V3", "2": None, "3": None, "4": "NRST", "5": "+3V3",
            "6": "BEMF_A", "7": "NEUT", "8": "SIG", "9": "VSENSE", "10": "BEMF_B",
            "11": "BEMF_C", "12": "ISENSE", "13": "INLC", "14": "INLB", "15": "INLA",
            "16": None, "17": "+3V3", "18": "INHC", "19": "INHB", "20": "INHA",
            "21": None, "22": None, "23": "SWDIO", "24": "SWCLK", "25": None,
            "26": None, "27": None, "28": None, "29": "TLM", "30": None,
            "31": "BOOT0", "32": None, "33": "GND"}
GLOBAL = {"+3V3", "GND", "VBAT", "VSENSE", "+5V"}

def motor(m):
    b = 100 * m
    n = lambda s: s if s in GLOBAL or s is None else f"M{m}_{s}"
    U_MCU, U_DRV, U_INA = f"U{b+1}", f"U{b+2}", f"U{b+3}"
    add(U_MCU, "AT32F421K8U7", "AT32F421K8U7-4", "mcu", {k: n(v) for k, v in MCU_PINS.items()}, "AT32F421K8U7-4")
    drv = {"1": "INLA", "2": "INLB", "3": "INLC", "4": "VBAT", "5": None, "6": "GND", "7": None, "8": None,
           "9": "GLC", "10": "GLB", "11": "GLA", "12": "C", "13": "GHC", "14": "BSTC",
           "15": "B", "16": "GHB", "17": "BSTB", "18": "A", "19": "GHA", "20": "BSTA",
           "21": None, "22": "INHA", "23": "INHB", "24": "INHC", "25": "GND"}
    add(U_DRV, "DRV8300DRGE", "DRV8300DRGER", "drv", {k: n(v) for k, v in drv.items()}, "DRV8300DRGER")
    r = iter(range(b + 1, b + 99)); c = iter(range(b + 1, b + 99))
    R = lambda: f"R{next(r)}"; C = lambda: f"C{next(c)}"
    # MCU support
    add(C(), "C", "100nF", "c0402", {"1": "+3V3", "2": "GND"})          # VDD pin 1
    add(C(), "C", "100nF", "c0402", {"1": "+3V3", "2": "GND"})          # VDD pin 17
    add(C(), "C", "1uF", "c0402", {"1": "+3V3", "2": "GND"})            # VDDA pin 5
    add(C(), "C", "100nF", "c0402", {"1": n("NRST"), "2": "GND"})
    add(R(), "R", "10k", "r0402", {"1": "GND", "2": n("BOOT0")})
    add(R(), "R", "100R", "r0402", {"1": n("SIG"), "2": n("SIG_IN")})
    # gate driver support
    add(C(), "C", "10uF 16V", "c0603", {"1": "VBAT", "2": "GND"})       # GVDD
    add(C(), "C", "100nF", "c0402", {"1": "VBAT", "2": "GND"})
    for p in "ABC":
        add(C(), "C", "100nF 25V", "c0402", {"1": n("BST" + p), "2": n(p)})
    # power stage: one AON7934 per phase (Q1 high: D1/S1, Q2 low: D2/S2)
    for k, p in enumerate("ABC"):
        add(f"Q{b+k+1}", "AON7934", "AON7934", "fet",
            {"1": n("GH" + p), "2": "VBAT", "3": "VBAT", "4": "VBAT", "10": "VBAT",
             "9": n(p), "5": n("LS"), "6": n("LS"), "7": n("LS"), "8": n("GL" + p)}, "AON7934")
        add(R(), "R", "10k", "r0402", {"1": n("GL" + p), "2": "GND"})  # low-side gate pull-down (to GND: LS is GND + mV)
        add(C(), "C", "10uF 25V", "c0805", {"1": "VBAT", "2": "GND"})     # bus cap at each half-bridge
    # current sense: low-side shunt, INA186A1 (25 V/V) -> 12.5 mV/A
    add(f"R{b+50}", "R_SHUNT", "0R0005", "shunt", {"1": n("LS"), "2": "GND"}, "e.g. WSLP1206R0005 (verify)")
    add(U_INA, "INA186A1", "INA186A1", "ina",
        {"1": "GND", "2": "GND", "3": "+3V3", "4": n("LS"), "5": "GND", "6": n("IOUT")}, "INA186A1IDCKR")
    add(C(), "C", "100nF", "c0402", {"1": "+3V3", "2": "GND"})
    add(R(), "R", "1k", "r0402", {"1": n("IOUT"), "2": n("ISENSE")})
    add(C(), "C", "10nF", "c0402", {"1": n("ISENSE"), "2": "GND"})
    # BEMF dividers (10k / 4.7k = 0.32) and virtual neutral (3 x 10k / 1.5k)
    for p in "ABC":
        add(R(), "R", "10k", "r0402", {"1": n(p), "2": n("BEMF_" + p)})
        add(R(), "R", "4.7k", "r0402", {"1": n("BEMF_" + p), "2": "GND"})
    for p in "ABC":
        add(R(), "R", "10k", "r0402", {"1": n(p), "2": n("NEUT")})
    add(R(), "R", "1.5k", "r0402", {"1": n("NEUT"), "2": "GND"})
    # pads
    for k, p in enumerate("ABC"):
        add(f"P{b+k+1}", "PAD", f"M{m} {p}", "phase", {"1": n(p)})
    add(f"P{b+4}", "PAD", f"SIG{m}", "pad15", {"1": n("SIG_IN")})
    add(f"P{b+5}", "PAD", f"TLM{m}", "pad10", {"1": n("TLM")})
    add(f"P{b+6}", "PAD", f"SWDIO{m}", "pad10", {"1": n("SWDIO")})
    add(f"P{b+7}", "PAD", f"SWCLK{m}", "pad10", {"1": n("SWCLK")})
    add(f"P{b+8}", "PAD", f"NRST{m}", "pad10", {"1": n("NRST")})

for m in (1, 2):
    motor(m)

# --------------------------------------------------------------- shared
add("P1", "PAD", "BAT+", "batt", {"1": "VBAT"})
add("P2", "PAD", "BAT-", "batt", {"1": "GND"})
add("P3", "PAD", "GND", "pad15", {"1": "GND"})        # receiver / signal ground
add("P4", "PAD", "5V", "pad15", {"1": "+5V"})         # BEC out to receiver
add("P5", "PAD", "3V3", "pad10", {"1": "+3V3"})       # SWD supply sense
add("P6", "PAD", "GND", "pad10", {"1": "GND"})        # SWD ground
for i in range(1, 5):
    add(f"C{i}", "CP", "220uF 16V", "bulk", {"1": "VBAT", "2": "GND"}, "low-ESR polymer/electrolytic, on battery leads")
    OFF_BOARD.add(f"C{i}")
# Vbat sense divider, shared by both MCUs (100k / 10k, AM32 TARGET_VOLTAGE_DIVIDER 110)
add("R1", "R", "100k", "r0402", {"1": "VBAT", "2": "VSENSE"})
add("R2", "R", "10k", "r0402", {"1": "VSENSE", "2": "GND"})
# 5 V BEC: TPS62933 buck, 1.2 MHz (RT to GND) so a 3 x 3 mm 2.2 uH inductor fits
add("U1", "TPS62933", "TPS62933DRLR", "buck",
    {"1": "GND", "2": None, "3": "VBAT", "4": "GND", "5": "BEC_SW", "6": "BEC_BST", "7": "BEC_SS", "8": "BEC_FB"}, "TPS62933DRLR")
add("C5", "C", "10uF 25V", "c0805", {"1": "VBAT", "2": "GND"})
add("C6", "C", "100nF 25V", "c0402", {"1": "VBAT", "2": "GND"})
add("C7", "C", "100nF", "c0402", {"1": "BEC_BST", "2": "BEC_SW"})
add("C8", "C", "10nF", "c0402", {"1": "BEC_SS", "2": "GND"})
add("L1", "L", "2.2uH", "ind", {"1": "BEC_SW", "2": "+5V"}, "Changjiang FNR3015S2R2MT, 3x3 mm (verify Isat >= 2.5 A)")
add("R3", "R", "31.6k", "r0402", {"1": "+5V", "2": "BEC_FB"})
add("R4", "R", "10k", "r0402", {"1": "BEC_FB", "2": "GND"})
add("C9", "C", "22uF 10V", "c0603", {"1": "+5V", "2": "GND"})
add("C10", "C", "22uF 10V", "c0603", {"1": "+5V", "2": "GND"})
# 3.3 V for both MCUs: TLV75533 from 5 V
add("U2", "TLV75533PDBV", "TLV75533PDBVR", "ldo", {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}, "TLV75533PDBVR")
add("C11", "C", "1uF", "c0402", {"1": "+5V", "2": "GND"})
add("C12", "C", "1uF", "c0402", {"1": "+3V3", "2": "GND"})

NOTES = {
 "AT32F421K8U7-4": "AM32 target RR_ROBOT_DUAL_ESC_F421; 4x4 mm QFN32 (K8U7 = 5x5 mm, same pinout) chosen to fit 28 x 20 mm",
 "DRV8300DRGER": "D = internal bootstrap diodes; MODE and DT open (non-inverted INLx, 200 ns dead time); GVDD 5-20 V",
 "AON7934": "30 V dual asymmetric half-bridge, DFN 3x3A; RDS(on) at 4.5 V: 15.8 mOhm (Q1) / 11.6 mOhm (Q2) max",
 "INA186A1IDCKR": "25 V/V; 0.5 mOhm shunt gives 12.5 mV/A (AM32 MILLIVOLT_PER_AMP 12)",
 "TPS62933DRLR": "3.8-30 V in, 3 A; 1.2 MHz (RT to GND); 5 V BEC for the receiver",
 "TLV75533PDBVR": "3.3 V for both MCUs, from +5V",
}
def write_bom(path):
    import csv, collections
    groups = collections.OrderedDict()
    for ref, sym, val, fp, pins, mpn in PARTS:
        key = (val, fp, mpn, ref in OFF_BOARD)
        groups.setdefault(key, []).append(ref)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Refs", "Qty", "Value", "Part number", "Footprint", "Notes"])
        for (val, fp, mpn, off), refs in groups.items():
            note = NOTES.get(mpn, "")
            if off: note = "OFF-BOARD: solder across the battery leads within 20 mm of BAT+/BAT-. " + note
            w.writerow([" ".join(refs), len(refs), val, mpn or "generic", fp.split(":")[1], note.strip()])

if __name__ == "__main__":
    write_bom(os.path.join(HERE, "..", "BOM.csv"))
    import runpy
    runpy.run_path(os.path.join(HERE, "draw_schematic.py"), run_name="__main__")
