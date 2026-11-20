# Dual-motor SMD ESC (design spec)

Two independent 3-phase BLDC bridges on one compact board, driven by one
Arduino Nano. Replaces the single-motor, through-hole v1.1 board for this use.

**Status:** schematic-level spec, BOM and firmware. Not yet drawn in KiCad and
not laid out or built. Part numbers marked "example" must be checked against
their datasheets before ordering.

## Targets

| Item | Value | Source |
|---|---|---|
| Battery | 2S LiPo, 7.4 V nominal (6.0 V empty to 8.4 V full) | Tom |
| Current | 20 A max per motor, 40 A total input | Tom |
| Motors | 2 x 3-phase BLDC, independent speed | Tom |
| Controller | 1 x Arduino Nano (plug-in) | Tom |
| Size | As small as possible, surface mount | Tom |

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
Nano ──► INHA/B/C, INLA/B/C (Un pins 1-6)
Un GHx ─ 10 R ─► Q high gate (10 k gate-source)    Q high source = phase x
Un SHx ──────────► phase x
Un BSTx ─ 220 nF ─► SHx
Un GLx ─ 10 R ─► Q low gate (10 k gate-source)     Q low drain = phase x, source = GND
```

## Netlist

### DRV8300DPWR pins (same on U1 and U2)

| Pin | Name | U1 (motor 1) net | U2 (motor 2) net |
|---|---|---|---|
| 1 | INHA | Nano D9 | Nano D5 |
| 2 | INHB | Nano D10 | Nano D6 |
| 3 | INHC | Nano D11 | Nano D7 |
| 4 | INLA | Nano D4 | Nano D8 |
| 5 | INLB | Nano D3 | Nano D12 |
| 6 | INLC | Nano D2 | Nano A3 |
| 7 | GVDD | VBAT | VBAT |
| 8 | GND | GND | GND |
| 9/10/11 | GLC/GLB/GLA | low-side gates C/B/A via 10 R | same |
| 12/15/18 | SHC/SHB/SHA | M1_C / M1_B / M1_A | M2_C / M2_B / M2_A |
| 13/16/19 | GHC/GHB/GHA | high-side gates C/B/A via 10 R | same |
| 14/17/20 | BSTC/BSTB/BSTA | 220 nF to SHC/SHB/SHA | same |

The DRV8300 inputs have 200 k pull-downs, so the gates stay off while the
Nano is unplugged or in its bootloader. If INHx and INLx are both high, the
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

### Nano connections

| Nano pin | Net |
|---|---|
| VIN | VBAT (see the power note below) |
| GND (both) | GND |
| 5V | J3 pin 1, J4 pin 1 (pot supply) |
| A1 | J3 pin 2 (motor 1 speed) |
| A2 | J4 pin 2 (motor 2 speed) |
| D2-D12, A3 | gate inputs, see the DRV8300 table |
| D0, D1, D13 | Not connected. D13 is avoided because the bootloader blinks the LED on it at reset. |

**Power note:** the Nano's VIN regulator wants about 7 V or more. Between
roughly 7.0 and 6.0 V (a 2S pack near empty), its 5 V rail will sag. The
DRV8300 logic threshold is VIH 2.0 V, so gate control keeps working, but the
pot readings scale with the sagging rail. If that matters, add a 5 V
low-dropout regulator, or power the Nano from a separate 5 V supply.

## Layout guidance (needs KiCad)

- **Board size estimate:** about 50 x 45 mm, 2 layers, 2 oz copper. This is an
  estimate, not a routed result. Put the Nano socket on the top side over the
  logic area. Each bridge's 6 MOSFETs go in a 3 x 2 grid (about 25 x 16 mm)
  with its DRV8300 beside it. The two bridges sit side by side.
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

`src/dual_open_loop_esc/dual_open_loop_esc.ino` runs both motors without
blocking. It uses the same 6-step sequence and the same 50 to 2000 us
step-delay mapping as v2.1, with pots on A1 and A2. It was tested in a host
simulation with stubbed AVR registers, which checked no high/low overlap, one
high and one low switch on at a time, and correct step rates. It has not
been compiled with avr-gcc or run on a Nano.
