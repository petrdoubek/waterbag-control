/*
    Measuring air temperature and humidity, sending over WiFi to a server
*/

#include <DHT.h>;

#define DHT_PIN  D7     // what pin we're connected to
#define DHTTYPE DHT22   // DHT 22  (AM2302)
DHT dht(DHT_PIN, DHTTYPE); // Initialize DHT sensor for normal 16mhz Arduino

#define SOIL_PIN A0     // soil moisture sensor (optional)

// server resources, base URL of the server (like https://example.dom) is defined in secrets.h as SERVER
#define INSERT_PATH   "/air?insert_temperature="

//#define USE_EEPROM  // optional, to be able to update configuration without flashing new software
#include "JsonConfig.h"
JsonConfig jcfg;

//#define USE_DISPLAY // optional, use 4 digit TM1637 display for debugging
#define DIO_PIN          D3  // display - optional
#define CLK_PIN          D4  // display - optional
#include "Display4Digit.h"
Display4Digit disp4(CLK_PIN, DIO_PIN);

#include "secrets.h"
#include "WiFiClientHTTPS.h"
WiFiClientHTTPS wific(WIFI_SSID, WIFI_PASSWORD, SERVER, &disp4);

#include <MedianFilterLib.h>
#define WINDOW 30 // median filter window fixed to 30 measurements, easier than configurable
MedianFilter<float> medianFilterTemp(WINDOW);
MedianFilter<int> medianFilterHum(WINDOW);
MedianFilter<int> medianFilterSoil(WINDOW);

float last_sent_temp = 100000.0;
int till_measure_s, till_send_s, till_force_send_s;
bool measured = false;


void init_config() {
  jcfg.val["MIN_CHANGE_C"] = 1.0;
  jcfg.val["CYCLE_MEASURE_S"] = 3;
  jcfg.val["CYCLE_SEND_S"] = 60; //3600;
  jcfg.val["FORCE_SEND_S"] = 4 * 3600;
  jcfg.val["WIFI_TIMEOUT_S"] = 30;
}


void setup() {
  Serial.begin(9600);
  dht.begin();

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

  till_measure_s = 1;
  till_send_s = jcfg.val["CYCLE_SEND_S"];
  till_force_send_s = jcfg.val["FORCE_SEND_S"];
}


void loop() {
  if (till_measure_s <= 0) {
    measure();
    till_measure_s = jcfg.val["CYCLE_MEASURE_S"];
  }

  if (till_send_s <= 0) {
    if (measured) {
      float filtered_temp = medianFilterTemp.GetFiltered();
      float filtered_hum = medianFilterHum.GetFiltered();
      float filtered_mois = medianFilterSoil.GetFiltered();
      if (till_force_send_s <= 0
          || abs(last_sent_temp - filtered_temp) >= (float) jcfg.val["MIN_CHANGE_C"]) {
        if (insert_air(filtered_temp, filtered_hum, filtered_mois)) {
          last_sent_temp = filtered_temp;
          till_force_send_s = jcfg.val["FORCE_SEND_S"];
        } else {
          Serial.println("sending failed");
        }
        //load_command();  // check if server has any task (new config etc.)
      } else {
        Serial.printf("sending skipped, change < %.1fC\n", (float) jcfg.val["MIN_CHANGE_C"]);
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
  delay(1000 * skip_s);
}


void measure() {
  int hum_pct = (int) dht.readHumidity();
  float temp_C = dht.readTemperature();
#ifdef SOIL_PIN
  int soil_resistance = analogRead(SOIL_PIN);
  medianFilterSoil.AddValue(soil_resistance);
#endif

  //if (temp_C >= -50.0 && temp_C <= 100.0 && hum_pct >= 0 && hum_pct <= 100) {
  if (true) {
    Serial.printf("measurement: Humidity: %3d%%, Temp: %5.1fC", hum_pct, temp_C);
#ifdef SOIL_PIN
    Serial.printf(", Soil resistance: %4d", soil_resistance);
#endif
    Serial.println();
    medianFilterTemp.AddValue(temp_C);
    medianFilterHum.AddValue(hum_pct);
    Serial.printf("  median %3d%% %5.1fC", medianFilterHum.GetFiltered(), medianFilterTemp.GetFiltered());
#ifdef SOIL_PIN
    Serial.printf(" %4d", medianFilterSoil.GetFiltered());
#endif
    Serial.println();
#ifdef USE_DISPLAY
    disp4.showNumberDec((int) temp_C, false);
#endif
    measured = true;
  } else {
    disp4.printDispErr("measurement out of range", 5);
  }
}


bool insert_air(float temp, int hum, int mois) {
  String ignored_response;
  return wific.get_url(INSERT_PATH + String(temp, 1) + "&insert_humidity=" + String(hum)
#ifdef SOIL_PIN
                        + "&insert_moisture=" + String(mois)
#endif
                       ,
                       ignored_response, true, (int) jcfg.val["WIFI_TIMEOUT_S"]);
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
