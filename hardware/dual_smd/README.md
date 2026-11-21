# Dual-motor SMD ESC, AM32 version

Two independent 3-phase BLDC channels on one small board. Each channel has
its own Artery AT32F421 running the stock **AM32** firmware target
**`RR_ROBOT_DUAL_ESC_F421`** (hardware groups `AT_C` + `AT_045`), a TI
DRV8300 gate driver and three AOS AON7934 dual half-bridge MOSFETs. A shared
buck gives 5 V for the receiver (BEC), and an LDO gives 3.3 V for both MCUs.

**Status:** schematic drawn and checked (ERC clean). The PCB is **placed
but not routed**: 6 layers, 31 x 20 mm. It needs interactive routing in
KiCad (see [Routing notes](#routing-notes)). Not built. Part numbers marked
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

**Placed, not routed.** The board is 31 x 20 mm with 6 layers. All 129
on-board parts fit with no courtyard overlaps, and placement DRC is clean
(only unconnected items). Renders: `kicad/render_top.png`,
`kicad/render_bottom.png`.

### Stackup (1.6 mm, JLC 6-layer style)

| Layer | Use |
|---|---|
| L1 top (1 oz) | MOSFETs, phase / battery pads, shunts, gate resistors, BEC, LDO; power zones (phase nodes, low-side source buses, VBAT drain islands) |
| L2 | Solid GND plane |
| L3, L4 | Signal |
| L5 | VBAT plane (GND beyond x = 27.4 mm) |
| L6 bottom (1 oz) | Both DRV8300s, both MCUs, current-sense amps, BEMF networks, small passives |

**Outer copper is 1 oz.** JLC offers 2 oz outer on 6-layer boards, but then
the minimum trace / space is 0.16 mm, and the QFN escapes need 0.13 mm.
At 1 oz the outer power zones carry about half the current of 2 oz, so the
10-12 A phase and battery paths should be widened where possible,
solder-tinned, or reinforced with bus wire. The MOSFET drains also reach the
L5 VBAT plane through vias.

**Via-in-pad:** every DRV8300 and MCU signal pin has a filled via-in-pad,
0.3 mm diameter with a 0.15 mm hole, epoxy filled and capped. That is within
JLC's multilayer minimum of a 0.15 mm hole / 0.25 mm via, at a surcharge.
One JLC blog gives 0.20 mm as the minimum hole for via-in-pad, so confirm
before ordering. A 0.20 mm hole means 0.35-0.4 mm vias, which do not fit
side by side at the MCU's 0.4 mm pitch. The vias are staggered along the
pad length.

**Placement:**
- Both DRV8300s are in the bottom middle band, with only the low-side bus
  zones above them. Bootstrap caps sit between the drivers, GVDD caps beside
  them.
- The 4.7 R gate series resistors are on top, just under each gate pin.
- The BEMF networks, BEMF filter caps and gate pull-downs are on the bottom,
  under the phase pads.
- The MCUs are bottom right with nothing above their pins (checked with
  `tools/above_check.py`).
- The bus caps are under the phase pads. The LDO, BEC and SWD pads are top
  right.

**0201 parts:** 48 small-signal parts are 0201. LCSC stock was checked
2026-11-21:
- 100 nF 10 V: C284966
- 10 nF 25 V: C285010
- 1 nF 50 V: C301887
- 10k: C6853700
- Other resistor values: UNI-ROYAL 0201WMF ±1 % series

### Routing notes

Automated routing was tried and plateaued at about 55-65 conflicting nets
in every setup: Freerouting 2.5.0, and `tools/gridroute.py` / `negroute.py`
on 4 and 6 layers, with and without via-in-pad. Route it interactively in
KiCad:

1. Route the DRV8300 and MCU fanouts first. Drop each signal pin through
   its via-in-pad to L3 / L4, then run the six INH/INL lines per channel,
   the gate lines (driver -> 4.7 R on top -> FET gate) and the BST / SH
   lines on L3 / L4.
2. Keep each GHx / SHx pair together. Keep gate loops short.
3. Power stays in the L1 / L6 zones: phase nodes, low-side buses to the
   shunts, and VBAT drain islands with their vias to L5. Don't route
   signals through them on L1.
4. Run the BEMF / neutral / ISENSE lines to the MCU on L3 / L4. The shunt
   Kelvin lead (INA186 IN+) goes from the LS tap via.
5. Finish with the top / bottom GND fill and stitching vias to L2. GND /
   VBAT pads already have fanout vias where `tools/route_pcb.py` placed
   them.

## Files

- `tools/gen_schematic.py`: the netlist (`PARTS`), the single source of
  truth. Running it writes `BOM.csv` and redraws the schematic.
- `tools/draw_schematic.py`: draws `kicad/dual_esc.kicad_sch` as a wired,
  readable sheet. Labels are used only between blocks.
- `tools/check_schematic.py`: rebuilds connectivity from the drawn wires and
  fails unless it matches `PARTS`.
- `tools/above_check.py`: checks no part on the other side sits over a DRV8300 / MCU pin.
- `tools/negroute.py`: negotiated-congestion (rip-up) router experiment.
- `tools/gridroute.py`: grid maze router for the outer layers (power fanout, then signal nets).
- `tools/route_pcb.py`: power fanout, Freerouting run, keep-out removal, GND fill and stitching.
- `tools/build_pcb.py`: builds `kicad/dual_esc.kicad_pcb`. It places the parts,
  draws the power copper as zones, and links each footprint to its schematic
  symbol so the GUI's Update PCB keeps working. Run it with KiCad's Python.
