# Dual-motor SMD ESC (design spec)

Two independent 3-phase BLDC bridges on one compact board, driven by one
on-board ATmega328P (the Nano's chip, so the Nano firmware runs unchanged).
Replaces the single-motor, through-hole v1.1 board for this use.

**Status:** schematic-level spec, BOM and firmware. Not yet drawn in KiCad and
not laid out or built. Part numbers marked "example" must be checked against
their datasheets before ordering.

## Targets

| Item | Value | Source |
|---|---|---|
| Battery | 2S LiPo, 7.4 V nominal (6.0 V empty to 8.4 V full) | Tom |
| Current | 20 A max per motor, 40 A total input | Tom |
| Motors | 2 x 3-phase BLDC, independent speed | Tom |
| Controller | ATmega328P on the board, no Nano (chosen 2026-11-20) | Tom |
| Size | As small as possible, surface mount. Estimate about 30 x 25 mm with 3.3 x 3.3 mm MOSFETs, or 35 x 30 mm with 5 x 6 mm | Tom |
| Use | Dual-motor fixed wing. Some airflow, 20 A as peaks, not continuous | Tom |
| MOSFET package | 3.3 x 3.3 mm (BSZ019N03LS), giving a board of about 30 x 25 mm | chosen from the use |
| Board size | 30 x 25 mm target. To fit, bulk caps went to 4 x 220 uF 16 V in 6.3 mm cans (was 330 uF 8 mm), and the serial header became bare 1.27 mm pads | Tom, 2026-11-20 |

## Why the IR2110 has to go

The v1.1 board uses IR2110 drivers, whose VCC must be at least 10 V. A 2S
pack gives 6.0 to 8.4 V, so it can't power them. The DRV8300 runs with
GVDD = 5 to 20 V (UVLO about 4.6 V rising), so it can be fed straight from
the battery with no boost or BEC. It replaces three IR2110s, three external
bootstrap diodes and the 5 V logic feed per motor with one TSSOP-20.
Source: TI DRV8300 datasheet SLVSFG5D, https://www.ti.com/lit/gpn/drv8300.

Low gate drive is the trade-off: the low side sees VBAT (6.0 to 8.4 V) and
the high side sees about VBAT - 0.85 V. The MOSFETs must therefore be
logic-level parts with RDS(on) specified at VGS = 4.5 V.

## Block diagram (per motor, n = 1, 2)

```
VBAT ──┬─────────────── GVDD (Un pin 7) + 10 uF + 100 nF to GND
       ├── bulk 2 x 330 uF + 3 x 10 uF ceramic
       ├── Q high A/B/C drain
MCU  ──► INHA/B/C, INLA/B/C (Un pins 1-6)
Un GHx ─ 10 R ─► Q high gate (10 k gate-source)    Q high source = phase x
Un SHx ──────────► phase x
Un BSTx ─ 220 nF ─► SHx
Un GLx ─ 10 R ─► Q low gate (10 k gate-source)     Q low drain = phase x, source = GND
```

## Netlist

### DRV8300DPWR pins (same on U1 and U2)

| Pin | Name | U1 (motor 1) net | U2 (motor 2) net |
|---|---|---|---|
| 1 | INHA | PB1 (D9) | PD5 (D5) |
| 2 | INHB | PB2 (D10) | PD6 (D6) |
| 3 | INHC | PB3 (D11) | PD7 (D7) |
| 4 | INLA | PD4 (D4) | PB0 (D8) |
| 5 | INLB | PD3 (D3) | PB4 (D12) |
| 6 | INLC | PD2 (D2) | PC3 (A3) |
| 7 | GVDD | VBAT | VBAT |
| 8 | GND | GND | GND |
| 9/10/11 | GLC/GLB/GLA | low-side gates C/B/A via 10 R | same |
| 12/15/18 | SHC/SHB/SHA | M1_C / M1_B / M1_A | M2_C / M2_B / M2_A |
| 13/16/19 | GHC/GHB/GHA | high-side gates C/B/A via 10 R | same |
| 14/17/20 | BSTC/BSTB/BSTA | 220 nF to SHC/SHB/SHA | same |

The DRV8300 inputs have 200 k pull-downs, so the gates stay off while the
MCU is in reset or its bootloader. If INHx and INLx are both high, the
driver turns that phase off (shoot-through protection). Its fixed ~200 ns
hardware dead time comes on top of the 2 us software dead time.

### MOSFETs

| Motor | Phase | High side (D=VBAT, S=phase) | Low side (D=phase, S=GND) |
|---|---|---|---|
| 1 | A | Q1 | Q2 |
| 1 | B | Q3 | Q4 |
| 1 | C | Q5 | Q6 |
| 2 | A | Q7 | Q8 |
| 2 | B | Q9 | Q10 |
| 2 | C | Q11 | Q12 |

### Microcontroller: ATmega328P-MU (QFN-32, 5 x 5 mm)

The pin numbers below are for the TQFP-32/QFN-32 pinout. **Check them
against the Microchip ATmega328P datasheet before capture.**

| Pin | Signal | Net |
|---|---|---|
| 4, 6 | VCC | +5V, 100 nF each |
| 18 | AVCC | +5V, 100 nF |
| 20 | AREF | 100 nF to GND |
| 3, 5, 21, exposed pad | GND | GND |
| 7, 8 | PB6/PB7 XTAL | 16 MHz resonator with built-in caps (keeps F_CPU = 16 MHz, so `micros()` timing is unchanged) |
| 29 | PC6 RESET | 10 k to +5V. 100 nF to serial-header DTR (auto-reset). ISP RST |
| 30, 31 | PD0 RXD, PD1 TXD | Serial header TX, RX (crossed) |
| 32, 1, 2 | PD2, PD3, PD4 | U1 INLC, INLB, INLA |
| 9, 10, 11 | PD5, PD6, PD7 | U2 INHA, INHB, INHC |
| 12 | PB0 | U2 INLA |
| 13, 14, 15 | PB1, PB2, PB3 | U1 INHA, INHB, INHC (PB3 = MOSI) |
| 16 | PB4 | U2 INLB (MISO) |
| 17 | PB5 | ISP SCK only (Arduino D13 LED pin, left off the gates) |
| 24, 25 | PC1, PC2 (A1, A2) | Speed inputs, motor 1 and motor 2 |
| 26 | PC3 (A3) | U2 INLC |

**Programming:**
- 6 bare pads at 1.27 mm pitch (GND, CTS/NC, 5V, RX, TX, DTR) for a USB-serial adapter;
  solder a header or wires on only when programming
  (FTDI or CH340 type) with the Optiboot/Nano bootloader. Uploads then work
  from the Arduino IDE as for a Nano.
- 2 x 3 ISP pads (MISO, 5V, SCK, MOSI, RST, GND), or Tag-Connect TC2030
  pads to save space. These are used once to burn the bootloader and fuses
  (16 MHz external).
- MOSI and MISO double as gate inputs, so **ISP with the battery
  disconnected**. With VBAT off, the DRV8300s are below their GVDD
  undervoltage lockout and keep every gate off.

**5 V supply:** a low-dropout regulator from VBAT, for example MCP1703A-5002
(SOT-23, 16 V max input; verify the datasheet). The MCU draws about 15 mA,
so the dropout is well under 1 V. That keeps 5 V down to about 6 V of
battery, which fixes the rail sag the Nano version had near empty. Use 1 uF
in and 1 uF out, or whatever the regulator's datasheet requires.

**Speed inputs J3/J4:** 3 pads each (5V, wiper, GND) for off-board pots.

## Layout guidance (needs KiCad)

- **Board size estimate:** about 30 x 25 mm with 3.3 x 3.3 mm MOSFETs, or
  35 x 30 mm with 5 x 6 mm. Both assume 2 layers, 2 oz copper, and parts on
  both sides. These are estimates, not routed results. Put the MOSFETs and
  bulk caps on top, and the MCU, DRV8300s, regulator and small passives on
  the bottom.
- **Heat:** the firmware drives the MOSFETs fully on (no PWM). At 20 A, the
  3.3 x 3.3 mm parts (about 2-3 mOhm) dissipate about 1.2 W each and need
  airflow. Use 5 x 6 mm parts if the board is enclosed.
- Put VBAT and GND as wide pours on both layers, stitched with vias. For 40 A
  input, keep the battery pads and the bus short, and plan to tin or add
  copper bus bars if the pours run hot.
- Place a 10 uF ceramic at each half-bridge, VBAT to GND, within a few mm of
  the high-side drain and the low-side source.
- Place the bootstrap and GVDD caps right at the DRV8300 pins (datasheet
  layout guidance).
- Keep each GHx/SHx pair routed together as a short pair.
- Use thermal vias under the MOSFET drain tabs.

## Not included (same as v1.1)

There's no current sensing, BEMF sensing, reverse-polarity protection or
fuse. The firmware is still open-loop.

## Firmware

`src/dual_open_loop_esc/dual_open_loop_esc.ino` (comments still use Nano/Arduino pin names, which map 1:1 to the ports above) runs both motors without
blocking. It uses the same 6-step sequence and the same 50 to 2000 us
step-delay mapping as v2.1, with pots on A1 and A2. It was tested in a host
simulation with stubbed AVR registers, which checked no high/low overlap, one
high and one low switch on at a time, and correct step rates. It has not
been compiled with avr-gcc or run on a Nano.

## KiCad files

- `kicad/dual_esc.kicad_sch` is a conventional wired schematic, laid out in
  the style of the v1.1 drawing. Each motor block has the DRV8300 driving
  three half-bridges drawn as high/low MOSFET pairs, with gate resistors,
  pull-downs, bootstrap caps, bus caps and phase pads, all wired, plus VBAT
  and GND power symbols. Global labels are used only between the MCU and the
  drivers. `tools/draw_schematic.py` draws the sheet, and `tools/gen_schematic.py`
  holds the intended netlist (`PARTS`).
- `tools/check_schematic.py` rebuilds connectivity from the drawn wires the
  way KiCad does: wire ends, pins or labels touching a wire connect; crossing
  wires don't. It fails unless the drawn nets match `PARTS` exactly.
- Pinouts checked against datasheets: ATmega328P 32-pin MLF (Atmel-8271IS
  Figure 1-1; the exposed pad is soldered to GND) and DRV8300 TSSOP-20 (TI
  SLVSFG5D Table 6-2). MCP1703 SOT-23A pins (1 GND, 2 VOUT, 3 VIN) come from
  a garbled extraction of DS22049F Table 3-1, so **confirm them in KiCad**.
  BSZ019N03LS (1-3 S, 4 G, 5-8 D) is the standard Infineon TSDSON-8 FL
  assignment, but **its datasheet was not readable here**.
- The MOSFET footprint name (`Infineon_PG-TSDSON-8_FL`) is a placeholder.
  Assign the real KiCad footprint before Update PCB.
