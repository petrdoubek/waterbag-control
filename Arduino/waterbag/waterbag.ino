/* 
 *  Home Rain Water Storage Monitoring and Control
 *
 * https://github.com/petrdoubek/waterbag-control
 *  
 *  Arduino-like NodeMCU ESP8266 unit measures water level using ultrasound sensor (SR04).
 *  It opens valve when a configured level is achieved (can as well be pump instead of valve).
 *  Optionally, it connects as HTTPS client to a server with database to store measurements
 *  and retrieve new configuration
 * 
 * - in fact distance from ceiling to waterbag top is measured, height is calculated as DIST_SENSOR_BOTTOM_MM - distance
 *   - DIST_SENSOR_BOTTOM_MM has to be calibrated based on installation, can be changed also by inserting command on server
 * - the server part must be deplayed at HOST and WiFi SSID and PASSWORD must be set to store and view the measurements
 *   - HTTPS is used without fingerprint or certificate, I'm using Heroku which does not allow HTTP
 * - tried also SRF05 sensor which should be more precise but it did not measure distance >= 700mm, may be faulty unit
 * - optional TM1637 4-digit display shows:
 *   - measured height (= DIST_SENSOR_BOTTOM_MM - measured distance)
 *   - wifi strength RSSI (negative number) when it is trying to send the measurement to server
 *   - OK result (spelled OH) or error code (ErNN where NN is two-digit error code)
 */

// pins, not all are mandatory
#define TRIGGER_PIN      D1  // ultrasound sensor
#define ECHO_PIN         D2  // ultrasound sensor
#define DIO_PIN          D3  // display - optional
#define CLK_PIN          D4  // display - optional
#define OVERFLOW_PIN     D5  // connected to relay that opens valve to release water somewhere
#define IRRIGATION_PIN   D6  // currently not used
#define LED_PIN          D7  // blink when measuring - optional

// server resources, base URL of the server (like https://example.dom) is defined in secrets.h as SERVER
#define INSERT_PATH   "/waterbag?insert_mm="
#define LOG_PATH      "/waterbag?insert_log="
#define COMMAND_PATH  "/waterbag/command"

#define USE_EEPROM  // optional, to be able to update configuration without flashing new software
#include "JsonConfig.h"
JsonConfig jcfg;

#define USE_DISPLAY // optional, use 4 digit TM1637 display for debugging
#include "Display4Digit.h"
Display4Digit disp4(CLK_PIN, DIO_PIN);

#include "secrets.h"
#include "WiFiClientHTTPS.h"
WiFiClientHTTPS wific(WIFI_SSID, WIFI_PASSWORD, SERVER, &disp4);

#include <NewPing.h>
NewPing sonar(TRIGGER_PIN, ECHO_PIN);

#include <MedianFilterLib.h>
MedianFilter<int> medianFilter(30);  // median filter window fixed to 30 measurements, easier than configurable

float last_sent_mm = 100000.0;
int till_measure_s, till_send_s, till_force_send_s;
bool measured = false, overflow_opened = false;


void init_config() {
  jcfg.val["DIST_SENSOR_BOTTOM_MM"] = 1674; // MUST BE CALIBRATED, DISTANCE THE SENSOR MEASURES WHEN STORAGE IS EMPTY
  jcfg.val["TRIGGER_OVERFLOW_MM"] = 600;    // MUST BE SET BASED ON WATERBAG OR TANK MAX LEVEL
  jcfg.val["N_PINGS"] = 19;
  jcfg.val["MIN_CHANGE_MM"] = 3;  // my SR04 unit seems to be quite precise (when combined with median filter), send even small changes
  jcfg.val["CYCLE_MEASURE_S"] = 4;
  jcfg.val["CYCLE_SEND_S"] = 30;  // sending rather often to test when first connected, set higher later
  jcfg.val["FORCE_SEND_S"] = 600; // dtto
  jcfg.val["WIFI_TIMEOUT_S"] = 30;
}


void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  pinMode(OVERFLOW_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(OVERFLOW_PIN, HIGH);  // the relay is activated by "grounded" pin, so HIGH means deactivated

  init_config();

  Serial.println();
  
  #ifdef USE_EEPROM
  Serial.println("loading config ...");
  if (!jcfg.loadEEPROM()) {
    Serial.println("loading failed, storing default to EEPROM");
    jcfg.saveEEPROM();
  }
  #endif
  Serial.print("using config: ");
  jcfg.printMe();

  reset_timers();
}


void loop() {
  if (till_measure_s <= 0) {
    measure();
    till_measure_s = jcfg.val["CYCLE_MEASURE_S"];

    // open or close the overflow valve if needed
    if (measured) {
      int filtered_height_mm = medianFilter.GetFiltered();
      
      if (!overflow_opened && filtered_height_mm >= (int) jcfg.val["TRIGGER_OVERFLOW_MM"]) {
        digitalWrite(OVERFLOW_PIN, LOW);
        overflow_opened = true;
        insert_log("overflow_opened:" + String(filtered_height_mm) + "ge" + String((int) jcfg.val["TRIGGER_OVERFLOW_MM"]));
        
      } else if (overflow_opened && filtered_height_mm < (int) jcfg.val["TRIGGER_OVERFLOW_MM"]) {
        digitalWrite(OVERFLOW_PIN, HIGH);
        overflow_opened = false;
        insert_log("overflow_closed:" + String(filtered_height_mm) + "lt" + String((int) jcfg.val["TRIGGER_OVERFLOW_MM"]));  
      }
    }
    
  }
  
  if (till_send_s <= 0) {
    if (measured) {
      int filtered_mm = medianFilter.GetFiltered();
      if (till_force_send_s <= 0 || abs(last_sent_mm - filtered_mm) >= (int) jcfg.val["MIN_CHANGE_MM"]) {
        if (insert_height(round(filtered_mm))) {
          last_sent_mm = filtered_mm;
          till_force_send_s = jcfg.val["FORCE_SEND_S"];
        } else {
          Serial.println("sending failed");
        }
        load_command();  // check if server has any task (new config etc.)
      } else {
        Serial.printf("sending skipped, change < %dmm\n", (int) jcfg.val["MIN_CHANGE_MM"]);
      }
    } else {
      Serial.println("sending skipped, nothing measured so far");
    }
    till_send_s = jcfg.val["CYCLE_SEND_S"];
  }
  int skip_s = min(till_measure_s, till_send_s);
  till_measure_s -= skip_s;
  till_send_s -= skip_s;
  till_force_send_s -= skip_s;
  delay(1000*skip_s);
}


void reset_timers() {
  till_measure_s = 1;
  till_send_s = jcfg.val["CYCLE_SEND_S"];
  till_force_send_s = jcfg.val["FORCE_SEND_S"];
}


void measure() {
  /* try https://github.com/eliteio/Arduino_New_Ping it claims to use something more reliable than PulseIn
   * also there's ping_median(iterations) to get more robust result */
  digitalWrite(LED_PIN, HIGH);
  int dist_mm = 343 * (int) sonar.ping_median((int) jcfg.val["N_PINGS"]) / 2000;
  if (dist_mm > 0) {
    int height_mm = (int) jcfg.val["DIST_SENSOR_BOTTOM_MM"] - dist_mm;
    Serial.printf("measurement: const %dmm - distance %dmm = height %dmm    ", (int) jcfg.val["DIST_SENSOR_BOTTOM_MM"], dist_mm, height_mm);
    digitalWrite(LED_PIN, LOW);
    medianFilter.AddValue(height_mm);
    Serial.printf("median %4dmm\n", medianFilter.GetFiltered());
    #ifdef USE_DISPLAY
      disp4.showNumberDec(height_mm, false);
    #endif
    measured = true;
  } else {
    disp4.printDispErr("measurement failed: distance <= 0", 5);
  }
}


bool insert_height(int mm) {
  String ignored_response;
  return wific.get_url(INSERT_PATH + String(mm), ignored_response, true, (int) jcfg.val["WIFI_TIMEOUT_S"]);
}


bool insert_log(String msg) {
  String ignored_response;
  return wific.get_url(LOG_PATH + msg, ignored_response, false, (int) jcfg.val["WIFI_TIMEOUT_S"]);
}


bool load_command() {
  String cmd;
  if (!wific.get_url(COMMAND_PATH, cmd, false, (int) jcfg.val["WIFI_TIMEOUT_S"])) {
    return false;
  }
  if (cmd.startsWith("{")) {
    jcfg.loadString(cmd);
    Serial.print("config read from server: ");
    jcfg.printMe();
    #ifdef USE_EEPROM
    jcfg.saveEEPROM();
    #endif
    reset_timers();
  } else {
    Serial.println("UNKNOWN COMMAND: " + cmd);
  }
}
