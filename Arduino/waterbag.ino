/* Home Rain Water Storage Monitoring and Control
 *  Arduino-like NodeMCU ESP8266 unit measures water level using ultrasound sensor (SR04).
 *  It opens valve when a configured level is achieved (can as well be pump instead of valve).
 *  Optionally connects as HTTPS client to an internet server with database to store measurements
 *  and retrieve new configuration
 * 
 * - in fact distance from ceiling to waterbag top is measured, height is calculated as DIST_SENSOR_BOTTOM_MM - distance
 *   - DIST_SENSOR_BOTTOM_MM has to be calibrated based on installation, can be changed also by inserting command on server
 *   - TODO store parameters to EEPROM
 * - the server part must be deplayed at HOST and WiFi SSID and PASSWORD must be set to store and view the measurements
 *   - HTTPS is used without fingerprint or certificate, I'm using Heroku which does not allow HTTP
 * - tried also SRF05 sensor which should be more precise but it did not measure distance >= 700mm, may be faulty unit
 * - optional TM1637 4-digit display shows:
 *   - measured height (= DIST_SENSOR_BOTTOM_MM - measured distance)
 *   - wifi strength RSSI (negative number) when it is trying to send the measurement to server
 *   - OK result (spelled OH) or error code (ErNN where NN is two-digit error code)
 */

#include <NewPing.h>
#include <MedianFilterLib.h>

#define USE_DISPLAY
#include "display.h"

#include "wifi.h"

#define USE_EEPROM  // optional, to be able to update configuration without flashing new software
#include "config.h"

#define TRIGGER_PIN      D1  // ultrasound sensor
#define ECHO_PIN         D2  // ultrasound sensor
#define OVERFLOW_PIN     D5  // connected to relay that opens valve to release water somewhere
#define IRRIGATION_PIN   D6  // currently not used
#define LED              D7  // blink when measuring - nice to have

NewPing sonar(TRIGGER_PIN, ECHO_PIN, (int) cfg["MAX_DETECT_CM"]);
MedianFilter<int> medianFilter(30);  // TODO cfg["AVG_WINDOW"] - then it must be pointer and it has to be recreated when setup changes

float last_sent_mm = 100000.0;
int till_measure_s, till_send_s, till_force_send_s;
bool overflow_opened = false;


void setup() {
  Serial.begin(9600);
  pinMode(LED, OUTPUT);
  pinMode(OVERFLOW_PIN, OUTPUT);
  digitalWrite(LED, LOW);
  digitalWrite(OVERFLOW_PIN, HIGH);  // the relay is activated by "grounded" pin, so HIGH means deactivated

  init_config(cfg);
  till_measure_s = 1;
  till_send_s = cfg["CYCLE_SEND_S"];
  till_force_send_s = cfg["FORCE_SEND_S"];

  Serial.println();
  #ifdef USE_DISPLAY
    disp.setBrightness(8); // range 8-15
  #endif
  #ifdef USE_EEPROM
    Serial.println("loading config ...");
    read_config(cfg);
    store_config(cfg);
  #endif
  print_config(cfg);
}


void loop() {
  if (till_measure_s <= 0) {
    measure();
    till_measure_s = cfg["CYCLE_MEASURE_S"];
    
    // open or close the overflow valve if needed
    int filtered_height_mm = medianFilter.GetFiltered();
    Serial.println("opened? "+ String(overflow_opened));
    
    if (!overflow_opened && filtered_height_mm >= (int) cfg["TRIGGER_OVERFLOW_MM"]) {
      digitalWrite(OVERFLOW_PIN, LOW);
      overflow_opened = true;
      insert_log("overflow_opened:" + String(filtered_height_mm) + "ge" + String((int) cfg["TRIGGER_OVERFLOW_MM"]));
      
    } else if (overflow_opened && filtered_height_mm < (int) cfg["TRIGGER_OVERFLOW_MM"]) {
      digitalWrite(OVERFLOW_PIN, HIGH);
      overflow_opened = false;
      insert_log("overflow_closed:" + String(filtered_height_mm) + "lt" + String((int) cfg["TRIGGER_OVERFLOW_MM"]));  
    }
    
  }
  if (till_send_s <= 0) {
    int filtered_mm = medianFilter.GetFiltered();
    if (till_force_send_s <= 0 || abs(last_sent_mm - filtered_mm) >= (int) cfg["MIN_CHANGE_MM"]) {
      if (insert_height(round(filtered_mm))) {
        last_sent_mm = filtered_mm;
        till_force_send_s = cfg["FORCE_SEND_S"];
      } else {
        Serial.println("sending failed");
      }
      load_command();  // check if server has any task (new config etc.)
    } else {
      Serial.println("sending skipped");
    }
    till_send_s = cfg["CYCLE_SEND_S"];
  }
  int skip_s = min(till_measure_s, till_send_s);
  till_measure_s -= skip_s;
  till_send_s -= skip_s;
  till_force_send_s -= skip_s;
  delay(1000*skip_s);
}

void measure() {
  /* try https://github.com/eliteio/Arduino_New_Ping it claims to use something more reliable than PulseIn
   * also there's ping_median(iterations) to get more robust result */
  digitalWrite(LED, HIGH);
  int dist_mm = (343 * (int) sonar.ping_median((int) cfg["N_PINGS"], (int) cfg["MAX_DETECT_CM"])) / 2000;
  int height_mm = (int) cfg["DIST_SENSOR_BOTTOM_MM"] - dist_mm;
  Serial.printf("measurement: const %dmm - distance %dmm = height %dmm    ", (int) cfg["DIST_SENSOR_BOTTOM_MM"], dist_mm, height_mm);
  digitalWrite(LED, LOW);
  medianFilter.AddValue(height_mm);
  Serial.printf("median %4dmm\n", medianFilter.GetFiltered());
  #ifdef USE_DISPLAY
    disp.showNumberDec(height_mm, false);
  #endif
}


bool insert_height(int mm) {
  String ignored_response;
  return get_url(INSERT_PATH + String(mm), ignored_response, true, (int) cfg["WIFI_TIMEOUT_S"]);
}


bool insert_log(String msg) {
  String ignored_response;
  return get_url(LOG_PATH + msg, ignored_response, false, (int) cfg["WIFI_TIMEOUT_S"]);
}


bool load_command() {
  String cmd;
  if (!get_url(COMMAND_PATH, cmd, false, (int) cfg["WIFI_TIMEOUT_S"])) {
    return false;
  }
  if (cmd.startsWith("{")) {
    config_from_string(cmd);
    Serial.println("config read from server:");
    print_config(cfg);
    #ifdef USE_EEPROM
      store_config(cfg);
    #endif
  } else {
    Serial.println("UNKNOWN COMMAND: " + cmd);
  }
}
