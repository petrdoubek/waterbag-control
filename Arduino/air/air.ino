/*
    Measuring air temperature and humidity (DHT sensor) and soil moisture, sending over WiFi to a server

    uses deep sleep, D0 and RST pins must be connected after the sketch is uploaded, otherwise it never wakes up
*/

#include <DHT.h>;

#define DHT_PIN  D7     // what pin we're connected to
#define DHTTYPE DHT22   // DHT 22  (AM2302)
DHT dht1(DHT_PIN, DHTTYPE); // Initialize DHT sensor for normal 16mhz Arduino
DHT dht2(D1, DHTTYPE);

#define SOIL_MEASURE_PIN A0     // soil moisture sensor (optional)
#define SOIL_VIN_PIN     D6     // soil voltage pin - turn it on only for measurement

// server resources, base URL of the server (like https://example.dom) is defined in secrets.h as SERVER
#define INSERT_PATH   "/environment?"

//#define USE_EEPROM  // optional, to be able to update configuration without flashing new software
#include "JsonConfig.h"
JsonConfig jcfg;

#define USE_DISPLAY // optional, use 4 digit TM1637 display for debugging
#define DIO_PIN          D3  // display - optional
#define CLK_PIN          D4  // display - optional
#include "Display4Digit.h"
Display4Digit disp4(CLK_PIN, DIO_PIN);

#include "secrets.h"
#include "WiFiClientHTTPS.h"
WiFiClientHTTPS wific(WIFI_SSID, WIFI_PASSWORD, SERVER, &disp4);

#include <MedianFilterLib.h>
#define WINDOW 9 // median filter window fixed, easier than configurable
MedianFilter<float> medianFilterTemp(WINDOW);
MedianFilter<int> medianFilterHumidity(WINDOW);
MedianFilter<int> medianFilterMoisture(WINDOW);

bool measured_temperature = false, measured_humidity = false, measured_moisture = false;


void init_config() {
  jcfg.val["CYCLE_SEND_S"] = 10;
  jcfg.val["WIFI_TIMEOUT_S"] = 10;
}


void setup() {
  Serial.begin(9600);
  Serial.setTimeout(2000);
  while(!Serial) {}
  
  dht1.begin();
  dht2.begin();
#ifdef SOIL_VIN_PIN
  pinMode(SOIL_VIN_PIN, OUTPUT);
#endif

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
  soilSensorSwitch(HIGH); // send current through the soil only for necessary time to save battery
  for (int i=0; i<WINDOW; i++) {
    Serial.printf("#%03d ", i);
    measure_dht(dht1);
    measure_soil();
    Serial.println();
    delay(2000); // DHT22 requires 2s interval between measurements
  }
  soilSensorSwitch(LOW);
  send_to_server();
  disp4.off();

  Serial.printf("Going into deep sleep for %ds\n", (long) jcfg.val["CYCLE_SEND_S"]);
  //ESP.deepSleep(1000000l * (long) jcfg.val["CYCLE_SEND_S"]);
  // there will be only one loop, the sketch restarts at setup after deep sleep
  delay(1000 * (long) jcfg.val["CYCLE_SEND_S"]);
}


void send_to_server() {
  if (measured_temperature || measured_moisture) {
    float filtered_temp = medianFilterTemp.GetFiltered();
    float filtered_humidity = medianFilterHumidity.GetFiltered();
    float filtered_moisture = medianFilterMoisture.GetFiltered();
    if (!insert_environment(filtered_temp, filtered_humidity, filtered_moisture)) {
      Serial.println("sending failed");
    }
    //load_command();  // check if server has any task (new config etc.)
  } else {
    Serial.println("sending skipped, nothing measured so far");
  }
}


void measure_dht(DHT dht) {
  int hum_pct = (int) dht.readHumidity();
  float temp_C = dht.readTemperature();

  Serial.printf("    Temp: %5.1fC", temp_C);
  if (temp_C >= -50.0 && temp_C <= 100.0) {
    medianFilterTemp.AddValue(temp_C);
    measured_temperature = true;
    disp4.showNumberDec((int) temp_C, false);
  } else {
    disp4.printDispErr("temperature out of range", 5);
  }

  Serial.printf("    Humidity: %3d%%", hum_pct);
  if (hum_pct >= 0 && hum_pct <= 100) {
    medianFilterHumidity.AddValue(hum_pct);
    measured_humidity = true;
  } else {
    disp4.printDispErr("humidity out of range", 6);
  }

  Serial.printf("    Dew point: %5.1fC", dew_point(temp_C, (float) hum_pct / 100.0));
}


void measure_soil() {
#ifdef SOIL_MEASURE_PIN
  int soil_resistance = analogRead(SOIL_MEASURE_PIN);

  Serial.printf("    Soil resistance: %4d", soil_resistance);
  if (soil_resistance > 0 && soil_resistance <= 1024) {
    medianFilterMoisture.AddValue(soil_resistance);
    measured_moisture = true;
  } else {
    disp4.printDispErr("soil resistance out of range", 7);
  }
#endif
}


void soilSensorSwitch(int value) {
#ifdef SOIL_VIN_PIN
  digitalWrite(SOIL_VIN_PIN, value);
#endif
}


bool insert_environment(float temp, int hum, int mois) {
  String ignored_response;
  return wific.get_url(String(INSERT_PATH)
           + (measured_temperature ? ("&insert_temperature=" + String(temp, 1)) : "")
           + (measured_humidity ? ("&insert_humidity=" + String(hum)) : "")
           + (measured_moisture ? ("&insert_moisture=" + String(mois)) : ""),
           ignored_response, true, (int) jcfg.val["WIFI_TIMEOUT_S"]);
}


/* calculate dew point [C] given temperature T [C] and humidity h [0-1] */
float dew_point(float T, float h) {
  float exp_term = (17.67 * T) / (243.5 + T);
  float ln_term = log(h * exp(exp_term));
  return (243.5 * ln_term) / (17.67 + ln_term);
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
