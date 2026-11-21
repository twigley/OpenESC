# Dual-motor SMD ESC, AM32 version

Two independent 3-phase BLDC channels on one small board. Each channel has
its own Artery AT32F421 running the stock **AM32** firmware target
**`RR_ROBOT_DUAL_ESC_F421`** (hardware groups `AT_C` + `AT_045`), a TI
DRV8300 gate driver and three AOS AON7934 dual half-bridge MOSFETs. A shared
buck gives 5 V for the receiver (BEC), and an LDO gives 3.3 V for both MCUs.

**Status:** schematic drawn and checked (ERC clean); PCB placed at 28 x 20 mm,
routing: see [PCB status](#pcb-status). Not built. Part numbers marked
"verify" must be checked before ordering.

## Targets

| Item | Value |
|---|---|
| Battery | 2S Li-ion, 6.0 to 8.4 V |
| Current | about 10-12 A per motor, limit set in AM32 |
| Firmware | AM32, stock target `RR_ROBOT_DUAL_ESC_F421`, flashed on both MCUs; no `USE_INVERTED_*` |
| Board | 31 x 20 mm, 6-layer trial (L2 GND, L3/L4 signal, L5 VBAT), parts on both sides |
| Bulk caps | 4 x 220 uF 16 V on the battery leads (off-board, in the BOM) |

## Pin map (both channels, from AM32 `Inc/targets.h`)

| Function | AT32F421 pin (QFN32 no.) | Connects to |
|---|---|---|
| Phase A high / low | PA10 TMR1_CH3 (20) / PB1 TMR1_CH3N (15) | DRV8300 INHA (22) / INLA (1) |
| Phase B high / low | PA9 TMR1_CH2 (19) / PB0 TMR1_CH2N (14) | INHB (23) / INLB (2) |
| Phase C high / low | PA8 TMR1_CH1 (18) / PA7 TMR1_CH1N (13) | INHC (24) / INLC (3) |
| BEMF A / B / C | PA0 (6) / PA4 (10) / PA5 (11), comparator inverting inputs | 10k / 4.7k dividers from each phase |
| Neutral | PA1 (7), comparator non-inverting input | 3 x 10k from the phases, 1.5k to GND |
| Signal in | PA2 TMR15_CH1 (8) | 100 R to the SIG pad |
| Telemetry | PB6 USART1_TX (29) | TLM pad |
| Battery voltage | PA3 ADC3 (9) | 100k / 10k divider (shared by both MCUs) |
| Current | PA6 ADC6 (12) | INA186A1 via 1k / 10 nF |
| SWD | PA13 (23) / PA14 (24), NRST (4) | SWDIO / SWCLK / NRST pads, plus shared 3V3 / GND pads |
| BOOT0 | pin 31 | 10k to GND |

The pins were checked against the AT32F421 datasheet v2.02, Figure 4. The
AT32F421 QFN32 is **not** pin-identical to the STM32F051K8U: its pins 16 and
32 are PB2 and PB8, not VSS. Ground is the exposed pad only.

## Circuit notes

- **Gate driver:** DRV8300DRGER (VQFN-24), the D variant with internal
  bootstrap diodes. MODE is left open, so GLx follows INLx (non-inverted). DT
  is left open for the fixed 200 ns dead time, on top of AM32's DEAD_TIME 50.
  GVDD runs straight from VBAT (5-20 V) with 10 uF + 100 nF. Bootstrap caps
  are 100 nF 25 V. Source: TI SLVSFG5D Table 6-1 and section 9.2.2.
- **MOSFETs:** AON7934 has the high-side FET Q1 (D1 = VBAT) and the low-side
  FET Q2 (S2 = low-side source node) in one 3 x 3 mm package. The switch
  node is pad 9 (S1/D2). The footprint is made from AOS drawing PO-00136 rev
  C (DFN3x3A_8L_EP2) and is in `kicad/OpenESC_dual.pretty`. There are no
  gate series resistors, to save space. Each low-side gate has a 10k
  pull-down to GND. GND is the source potential plus the shunt's few mV.
- **Current sense:** each channel has one 0.5 mOhm low-side shunt from the
  three low-side sources to GND, feeding an INA186A1 (25 V/V). That gives
  12.5 mV/A against AM32's MILLIVOLT_PER_AMP 12, so readings are about 4 %
  high, trimmable in the configurator. REF is tied to GND (unidirectional).
- **BEMF:** 10k / 4.7k dividers (ratio 0.32, so 8.4 V gives 2.7 V). The
  virtual neutral is 3 x 10k with 1.5k to GND, the same ratio. There are no
  filter caps. The AM32 repository has firmware only, so there were no AM32
  reference values to compare against.
- **5 V BEC:** TPS62933 (3.8-30 V in, 3 A) at 1.2 MHz (RT to GND), with
  2.2 uH and 2 x 22 uF. The feedback divider is 31.6k / 10k for 5.0 V
  (TI SLUSEA4D Table 10-2). At 6.0 V in, the needed duty cycle is about 85 %,
  within the 98 % maximum.
- **3.3 V:** TLV75533PDBV from 5 V, with 1 uF in and out.
- **Heat:** RDS(on) at 4.5 V is 11.6-15.8 mOhm max per FET, and a 2S pack
  gives only 6-8 V of gate drive. At 12 A that is about 1.7-2.3 W in the
  conducting pair. Expect airflow to be needed above about 8 A continuous.

## Flashing AM32

1. With the battery disconnected, power the board from a 3.3 V SWD
   programmer through the 3V3 / GND pads. Connect SWDIO, SWCLK and NRST for
   the channel being flashed. Flash the AM32 bootloader built for the F421
   with its input on PA2 (from the AM32 bootloader releases; check the file
   name there) using an SWD probe that supports the AT32F421, such as
   Artery's AT-Link or an ST-Link with OpenOCD's AT32 support. Repeat for
   the second MCU.
2. Connect the battery and the signal wires. With the AM32 configurator
   (web or desktop), through a betaflight passthrough or a USB-serial
   one-wire adapter on each SIG pad, flash `RR_ROBOT_DUAL_ESC_F421` to each
   channel and set the current limit (10-12 A), motor direction and timing.
3. After that, firmware updates go over the signal wire. SWD is needed
   only once.

## PCB status

The PCB is **placed on 4 layers at 28 x 20 mm but not routed**.

**Stackup:** 1.6 mm, JLC04161H-7628 style, 2 oz outer / 0.5 oz inner. JLC
offers 2 oz outer copper on 4-layer boards; confirm when ordering.

| Layer | Use |
|---|---|
| L1 top | Power zones (phase nodes, low-side source buses, VBAT drain islands), signals |
| L2 | Solid GND plane |
| L3 | VBAT plane (x < 24 mm), GND beyond |
| L4 bottom | Gate drivers, MCUs, sense networks, signals |

**Placement:** all 117 on-board parts fit with no courtyard overlaps
(`kicad/render_top.png`, `kicad/render_bottom.png`,
`kicad/layer_L2_GND.png`, `kicad/layer_L3_VBAT.png`).

- **Gate drivers:** each DRV8300 is on the bottom, right under its motor's
  middle phase pad. That puts it within a few mm of all three AON7934 gates
  and phase nodes.
- **MCUs:** at the bottom right, no longer under the drivers.
- **BEMF filter caps:** 1 nF on each divided phase was added (C115-C117,
  C215-C217).
- **Gate series resistors:** don't fit, so they are still left out.

**0201:** 48 small-signal parts moved to 0201 (BEMF dividers, neutral
network, BEMF filter caps, gate pull-downs, BOOT0 / SIG / INA-output
resistors, MCU and INA 100 nF caps, NRST cap, ISENSE filter cap, Vbat
divider). The GVDD and bootstrap caps (25 V), the 1 uF caps and the bus and
bulk caps keep their larger sizes.

LCSC stock checked (2026-11-21):
- 100 nF 10 V X5R 0201: C284966
- 10 nF 25 V X7R 0201: C285010
- 1 nF 50 V X7R 0201: C301887
- 10k 0201 1 %: C6853700
- Other resistor values: the UNI-ROYAL 0201WMF ±1 % series covers 1 R-10 M
  (25 V), so they are in stock.

**Routing: not closed.**

- **31 x 20 mm, 4 layers:** Freerouting leaves 149 unrouted, `gridroute.py`
  about 86, `negroute.py` 67 overlapping nets.
- **6-layer trial at 31 x 20** (the committed board): L1 / L6 parts and
  power, L2 GND, L3 / L4 signal, L5 VBAT. `negroute.py` gets down to 53-55
  overlapping nets (plus 4 unroutable) and then plateaus.
- **Remaining conflicts:** fine-pitch escape round each DRV8300 and MCU.
  The most crowded spot is the driver pin row nearest the board edge, where
  several pins must escape through room for one track. Extra inner layers
  only help once each pin can drop to them, which needs via-in-pad / HDI
  vias (0.3 / 0.15 mm or smaller) at the 0.5 mm driver and 0.4 mm MCU pitch,
  or a placement with no pin row facing the edge.
- **JLC 6-layer, 2 oz outer:** available, but the minimum trace / space is
  then 0.16 mm. These rules use 0.13 mm, so 2 oz outer would need wider
  spacing at the QFN escapes (or 1 oz outer).

The committed board is the unrouted 6-layer placement.

## Files

- `tools/gen_schematic.py`: the netlist (`PARTS`), the single source of
  truth. Running it writes `BOM.csv` and redraws the schematic.
- `tools/draw_schematic.py`: draws `kicad/dual_esc.kicad_sch` as a wired,
  readable sheet. Labels are used only between blocks.
- `tools/check_schematic.py`: rebuilds connectivity from the drawn wires and
  fails unless it matches `PARTS`.
- `tools/gridroute.py`: grid maze router for the outer layers (power fanout, then signal nets).
- `tools/route_pcb.py`: power fanout, Freerouting run, keep-out removal, GND fill and stitching.
- `tools/build_pcb.py`: builds `kicad/dual_esc.kicad_pcb`. It places the parts,
  draws the power copper as zones, and links each footprint to its schematic
  symbol so the GUI's Update PCB keeps working. Run it with KiCad's Python.
