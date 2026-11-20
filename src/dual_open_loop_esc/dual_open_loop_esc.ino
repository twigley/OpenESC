/*
  Dual open-loop BLDC ESC firmware (two motors, one Arduino Nano / ATmega328P)

  Based on src/open_loop_esc/open_loop_esc.ino v2.1 (same 6-step sequence,
  same 2 us software dead time), but non-blocking so the two motors can run
  at independent commutation rates.

  Target hardware: hardware/dual_smd/ (2x DRV8300D, 12x N-ch MOSFET, 2S LiPo).
  DRV8300 inputs are active high (INHx -> GHx, INLx -> GLx) and the driver
  itself blocks INHx = INLx = 1 on the same phase, so the pin semantics are
  the same as the IR2110 board.

  Pin map (motor 1 unchanged from v2.1):
    Motor 1  INHA D9  (PB1)   INHB D10 (PB2)   INHC D11 (PB3)
             INLA D4  (PD4)   INLB D3  (PD3)   INLC D2  (PD2)
             Speed pot A1
    Motor 2  INHA D5  (PD5)   INHB D6  (PD6)   INHC D7  (PD7)
             INLA D8  (PB0)   INLB D12 (PB4)   INLC A3  (PC3)
             Speed pot A2
  Left free on purpose: D0/D1 (USB serial), D13 (the bootloader blinks the
  LED on it at reset, which would pulse a gate input).

  Speed: each pot sets that motor's commutation step delay, 50..2000 us
  (same mapping as v2.1). Pots are read with a non-blocking ADC conversion
  so the ~110 us analogRead() does not stall the other motor.
*/

#include <avr/io.h>

#define DEAD_TIME_US 2
#define STEP_MIN_US  50
#define STEP_MAX_US  2000

struct Pin {
  volatile uint8_t *port;
  volatile uint8_t *ddr;
  uint8_t bit;
};

struct Motor {
  Pin hi[3];          // A, B, C high-side inputs
  Pin lo[3];          // A, B, C low-side inputs
  uint8_t adcChannel; // speed pot
  uint8_t step;       // 0..5
  uint16_t stepUs;    // current step duration
  uint32_t lastStep;  // micros() at last commutation
};

// 6-step table from v2.1: {high-side phase, low-side phase}, 0=A 1=B 2=C
static const uint8_t SEQ[6][2] = {
  {0, 1}, // A+ B-
  {0, 2}, // A+ C-
  {1, 2}, // B+ C-
  {1, 0}, // B+ A-
  {2, 0}, // C+ A-
  {2, 1}, // C+ B-
};

static Motor motors[2] = {
  { { {&PORTB, &DDRB, PORTB1}, {&PORTB, &DDRB, PORTB2}, {&PORTB, &DDRB, PORTB3} },
    { {&PORTD, &DDRD, PORTD4}, {&PORTD, &DDRD, PORTD3}, {&PORTD, &DDRD, PORTD2} },
    1, 0, STEP_MAX_US, 0 },
  { { {&PORTD, &DDRD, PORTD5}, {&PORTD, &DDRD, PORTD6}, {&PORTD, &DDRD, PORTD7} },
    { {&PORTB, &DDRB, PORTB0}, {&PORTB, &DDRB, PORTB4}, {&PORTC, &DDRC, PORTC3} },
    2, 0, STEP_MAX_US, 0 },
};

static inline void pinLow(const Pin &p)  { *p.port &= ~(1 << p.bit); }
static inline void pinHigh(const Pin &p) { *p.port |=  (1 << p.bit); }

// Switch motor m to step s: release everything not used by the new step,
// wait the dead time, then drive the new high/low pair.
static void applyStep(Motor &m, uint8_t s) {
  uint8_t h = SEQ[s][0], l = SEQ[s][1];
  for (uint8_t ph = 0; ph < 3; ph++) {
    if (ph != h) pinLow(m.hi[ph]);
    if (ph != l) pinLow(m.lo[ph]);
  }
  delayMicroseconds(DEAD_TIME_US);
  pinHigh(m.hi[h]);
  pinHigh(m.lo[l]);
}

// --- non-blocking ADC: alternate between the two pots ---
static uint8_t adcMotor = 0;

static void adcStart(uint8_t ch) {
  ADMUX = (1 << REFS0) | (ch & 0x07); // AVcc reference
  ADCSRA |= (1 << ADSC);
}

static void adcPoll() {
  if (ADCSRA & (1 << ADSC)) return;   // conversion still running
  uint16_t raw = ADC;
  motors[adcMotor].stepUs = map(raw, 0, 1023, STEP_MIN_US, STEP_MAX_US);
  adcMotor ^= 1;
  adcStart(motors[adcMotor].adcChannel);
}

void setup() {
  for (uint8_t i = 0; i < 2; i++) {
    for (uint8_t ph = 0; ph < 3; ph++) {
      pinLow(motors[i].hi[ph]);
      pinLow(motors[i].lo[ph]);
      *motors[i].hi[ph].ddr |= (1 << motors[i].hi[ph].bit);
      *motors[i].lo[ph].ddr |= (1 << motors[i].lo[ph].bit);
    }
  }
  // ADC on, prescaler 128 (125 kHz at 16 MHz)
  ADCSRA = (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
  adcStart(motors[0].adcChannel);

  uint32_t now = micros();
  for (uint8_t i = 0; i < 2; i++) {
    motors[i].lastStep = now;
    applyStep(motors[i], 0);
  }
}

void loop() {
  adcPoll();
  uint32_t now = micros();
  for (uint8_t i = 0; i < 2; i++) {
    Motor &m = motors[i];
    if ((uint32_t)(now - m.lastStep) >= m.stepUs) {
      m.lastStep += m.stepUs;          // keep cadence without drift
      if ((uint32_t)(now - m.lastStep) > STEP_MAX_US) m.lastStep = now; // resync after a stall
      m.step = (m.step + 1) % 6;
      applyStep(m, m.step);
    }
  }
}
