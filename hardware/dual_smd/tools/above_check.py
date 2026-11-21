#!/usr/bin/env python3
"""List top-side parts whose courtyard covers a bottom-side DRV8300 / MCU pin (and vice versa).
Run with KiCad's Python: tools/above_check.py"""
import sys, pcbnew
PCB = r"C:/Users/twig8/OpenESC/hardware/dual_smd/kicad/dual_esc.kicad_pcb"
b = pcbnew.LoadBoard(PCB)
chips = ("U101", "U102", "U201", "U202")
hits = {}
for ref in chips:
    fp = b.FindFootprintByReference(ref)
    side = fp.GetLayer()
    other = pcbnew.F_CrtYd if side == pcbnew.B_Cu else pcbnew.B_CrtYd
    for p in fp.Pads():
        c = p.GetPosition()
        for f in b.GetFootprints():
            if f.GetReference() == ref or f.GetLayer() == side: continue
            cy = f.GetCourtyard(other)
            if cy.OutlineCount() and cy.Contains(c):
                hits.setdefault(ref, set()).add(f.GetReference())
            else:
                for q in f.Pads():
                    if q.HitTest(c, pcbnew.FromMM(0.3)): hits.setdefault(ref, set()).add(f.GetReference())
for k, v in sorted(hits.items()): print(k, "under/over:", sorted(v))
print("clear" if not hits else "blocked")
