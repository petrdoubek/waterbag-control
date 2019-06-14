/*
 * Display4Digit.h - wrapper around TM1637Display, assumes 4-digit 7-segment display, adds functions:
 *
 * displaying functions are active when USE_DISPLAY is defined, otherwise only the print to Serial works
 */

#ifndef __PETRDOUBEK_DISPLAY_H__
#define __PETRDOUBEK_DISPLAY_H__

#ifdef USE_DISPLAY
#include <TM1637Display.h>
#endif

class Display4Digit {
  public:
    Display4Digit(int clk_pin, int dio_pin, int brightness = 8) {
      #ifdef USE_DISPLAY
      _disp = new TM1637Display(clk_pin, dio_pin);
      _disp->setBrightness(brightness); // range 8-15
      #endif
    }

    ~Display4Digit() {
      #ifdef USE_DISPLAY
      delete _disp;
      #endif
    }

    // display OK, spelled "OH"
    void dispOK() {
      #ifdef USE_DISPLAY
      uint8_t msg[4] = { _digit_O, _digit_H, 0, 0 };
      _disp->setSegments(msg);
      #endif
    }

    // display "ErNN" where NN is the code (0-99)
    void dispErr(int code) {
      #ifdef USE_DISPLAY
      uint8_t msg[4] = { _digit_E, _digit_r, 0, 0 };
      msg[2] = _disp->encodeDigit((code / 10) % 10);
      msg[3] = _disp->encodeDigit(code % 10);
      _disp->setSegments(msg);
      #endif
    }

    // shortcut to both print message to Serial and display the error code
    void printDispErr(String msg, int code) {
      Serial.println(msg);
      #ifdef USE_DISPLAY
      dispErr(code);
      delay(3000); // delays all other tasks but it is worth it to see the error
      #endif
    }

    void showNumberDec(int num, bool leading_zero) {
      #ifdef USE_DISPLAY
      _disp->showNumberDec(num, leading_zero);
      #endif
    }

  private:
    #ifdef USE_DISPLAY
    TM1637Display *_disp;

    // segments:
    //   -      A
    // |   |  F   B
    //   -      G
    // |   |  E   C
    //   -      D
    const uint8_t _digit_E = SEG_A | SEG_F | SEG_G | SEG_E | SEG_D,
                  _digit_H = SEG_B | SEG_C | SEG_E | SEG_F | SEG_G,
                  _digit_O = SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F,
                  _digit_r = SEG_E | SEG_G;
    #endif
};

#endif
