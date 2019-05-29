#ifdef USE_DISPLAY
#include <TM1637Display.h>

#define CLK D4
#define DIO D3

TM1637Display disp(CLK, DIO);

// segments:
//   -      A
// |   |  F   B
//   -      G
// |   |  E   C
//   -      D
const uint8_t disp_E = SEG_A | SEG_F | SEG_G | SEG_E | SEG_D,
              disp_r = SEG_E | SEG_G;
const uint8_t disp_OK[] = {
  SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F,   // O
  SEG_B | SEG_C | SEG_E | SEG_F | SEG_G,           // K ~ H
  0,
  0  
};


void disp_err(int code) {
  uint8_t msg[4] = { disp_E, disp_r, 0, 0 };
  msg[2] = disp.encodeDigit((code / 10) % 10);
  msg[3] = disp.encodeDigit(code % 10);
  disp.setSegments(msg);
}
#endif


void print_disp_err(String msg, int code) {
  Serial.println(msg);
  #ifdef USE_DISPLAY
    disp_err(code);
    delay(3000); // delays all measuring and sending but it is worth it to see the error
  #endif
}
