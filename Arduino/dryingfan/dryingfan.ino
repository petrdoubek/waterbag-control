/*
    Controller for a fan that is drying a room (e.g. cellar) by outside air
    The fan should run only if the air outside is drier than the air inside
    Temperature must be taken into account, I see two options:
    - run only if dew point outside < temperature inside
    - run only if absolute humidity outside < absolute humidity inside

    Two DHT sensors are used, measurements are sent over WiFi to a server
*/

#include <DHT.h>;

DHT OutsideDHT(D2, DHT22);
DHT InsideDHT(D1, DHT22);

// server resources, base URL of the server (like https://example.dom) is defined in secrets.h as SERVER
#define INSERT_PATH   "/dryingfan?"

//#define USE_EEPROM  // optional, to be able to update configuration without flashing new software
#include "JsonConfig.h"
JsonConfig jcfg;

#define LED_PIN          D7

#define USE_DISPLAY // optional, use 4 digit TM1637 display for debugging
#define DIO_PIN          D3  // display - optional
#define CLK_PIN          D4  // display - optional
#include "Display4Digit.h"
Display4Digit disp4(CLK_PIN, DIO_PIN);

#include "secrets.h"
#include "WiFiClientHTTPS.h"
WiFiClientHTTPS wific(WIFI_SSID, WIFI_PASSWORD, SERVER, &disp4);

#include <MedianFilterLib.h>
#define WINDOW 9 // median filter window size is fixed, easier than configurable
MedianFilter<float> OutsideTemperature(WINDOW);
MedianFilter<int> OutsideHumidity(WINDOW);
MedianFilter<float> InsideTemperature(WINDOW);
MedianFilter<int> InsideHumidity(WINDOW);

bool valid_temp_out = false, valid_hum_out = false;
bool valid_temp_in = false, valid_hum_in = false;


void init_config() {
  jcfg.val["CYCLE_SEND_S"] = 10;
  jcfg.val["WIFI_TIMEOUT_S"] = 10;
}


void setup() {
  Serial.begin(9600);
  Serial.setTimeout(2000);
  while(!Serial) {}

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  OutsideDHT.begin();
  InsideDHT.begin();
  
  init_config();

  Serial.println();

#ifdef USE_EEPROM
  Serial.println("loading config ...");
  if (jcfg.loadEEPROM()) {
    Serial.println("loading failed, storing default to EEPROM");
    jcfg.saveEEPROM();
  }
#endif
  Serial.print("using config: ");
  jcfg.printMe();
}


void loop() {
  for (int i=0; i<WINDOW; i++) {
    digitalWrite(LED_PIN, HIGH);
    Serial.printf("#%03d Out: ", i);
    measure_dht(OutsideDHT, OutsideTemperature, OutsideHumidity, valid_temp_out, valid_hum_out);
    Serial.printf("   In: ");
    measure_dht(InsideDHT, InsideTemperature, InsideHumidity, valid_temp_in, valid_hum_in);
    Serial.println();
    digitalWrite(LED_PIN, LOW);
    delay(2000); // DHT22 requires 2s interval between measurements
  }
  send_to_server();
  disp4.off();

  Serial.printf("Sleep for %ds\n", (long) jcfg.val["CYCLE_SEND_S"]);
  delay(1000 * (long) jcfg.val["CYCLE_SEND_S"]);
}


void measure_dht(DHT dht,
                 MedianFilter<float> &Temperature,
                 MedianFilter<int> &Humidity,
                 bool &valid_temp,
                 bool &valid_hum)
{
  int hum_pct = (int) dht.readHumidity();
  float temp_C = dht.readTemperature();

  Serial.printf("    Temp:%3.0fC", temp_C);
  if (temp_C >= -50.0 && temp_C <= 100.0) {
    Temperature.AddValue(temp_C);
    valid_temp = true;
    disp4.showNumberDec((int) temp_C, false);
  } else {
    disp4.printDispErr(" (out of range)", 5);
  }

  Serial.printf("    RelHum:%3d%%", hum_pct);
  if (hum_pct >= 0 && hum_pct <= 100) {
    Humidity.AddValue(hum_pct);
    valid_hum = true;
  } else {
    disp4.printDispErr(" (out of range)", 6);
  }

  Serial.printf("    DewPt: %2.0fC", dew_point(temp_C, (float) hum_pct / 100.0));
  Serial.printf("    AbsHum: %3.0fg/m3", abs_humidity(temp_C, (float) hum_pct / 100.0));
}


void send_to_server() {
  if (valid_temp_out || valid_hum_out || valid_temp_in || valid_hum_in) {
    String ignored_response;
    bool rsp = wific.get_url(String(INSERT_PATH)
           + (valid_temp_out ? ("insert_temperature_out=" + String(OutsideTemperature.GetFiltered(), 1)) : "")
           + (valid_hum_out ? ("&insert_humidity_out=" + String(OutsideHumidity.GetFiltered())) : "")
           + (valid_temp_in ? ("&insert_temperature_in=" + String(InsideTemperature.GetFiltered(), 1)) : "")
           + (valid_hum_in ? ("&insert_humidity_in=" + String(InsideHumidity.GetFiltered())) : ""),
           ignored_response, true, (int) jcfg.val["WIFI_TIMEOUT_S"]);
    if (!rsp) {
      Serial.println("sending failed");
    }
    //load_command();  // check if server has any task (new config etc.)
  } else {
    Serial.println("sending skipped, nothing measured so far");
  }
}


/* calculate dew point [C] given temperature T [C] and humidity h [0-1] */
float dew_point(float T, float h) {
  float exp_term = (17.67 * T) / (243.5 + T);
  float ln_term = log(h * exp(exp_term));
  return (243.5 * ln_term) / (17.67 + ln_term);
}


/* calculate absolute humidity [g/m3] given temperature T [C] and relative humidity h [0-1]
   based on: https://www.easycalculation.com/weather/learn-relative-humidity-from-absolute.php */
float abs_humidity(float T, float h) {
  float M = 18.0; // [g/mol]
  float R = 0.0623665; // [ mmHg x m3 / C / mol ]
  float TK = 273.15 + T; // [K]
  float ps = ( 0.61078 * 7.501 ) * exp ( (17.2694 * T) / (238.3 + T) ); // [mmHg]
  return h * (M / (R * TK) * ps);
}

/*
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
  } else {
    Serial.println("UNKNOWN COMMAND: " + cmd);
  }
  }*/
