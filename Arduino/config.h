#include <ArduinoJson.h>

#define EEPROM_SIZE  512
StaticJsonDocument<EEPROM_SIZE> cfg;

void init_config(StaticJsonDocument<EEPROM_SIZE> &cfg) {
  cfg["DIST_SENSOR_BOTTOM_MM"] = 1660; // MUST BE CALIBRATED, DISTANCE THE SENSOR MEASURES WHEN STORAGE IS EMPTY
  cfg["TRIGGER_OVERFLOW_MM"] = 600;    // MUST BE SET BASED ON WATERBAG OR TANK MAX LEVEL
  cfg["MAX_DETECT_CM"] = 1000;
  cfg["N_PINGS"] = 19;
  cfg["MIN_CHANGE_MM"] = 3;  // my SRF04 unit seems to be quite precise (when combined with median filter), send even small changes
  cfg["CYCLE_MEASURE_S"] = 4;
  cfg["CYCLE_SEND_S"] = 30;  // sending rather often to test when first connected, set higher later
  cfg["FORCE_SEND_S"] = 600; // dtto
  cfg["AVG_WINDOW"] = 30;    // TODO currently not used it would mean dynamic allocation of the medianFilter
  cfg["WIFI_TIMEOUT_S"] = 30;
}

void print_config(StaticJsonDocument<EEPROM_SIZE> &cfg) {
  char bytes[EEPROM_SIZE];
  if (serializeJson(cfg, bytes) == 0) { // returns number of bytes
    Serial.println("JSON serialization failed");
  }
  Serial.println(bytes);  
}

void config_from_string(String bytes) {
  StaticJsonDocument<EEPROM_SIZE> check_cfg;
  if (deserializeJson(check_cfg, bytes) != DeserializationError::Ok) {
    Serial.println("JSON deserialization failed");
    return;
  }
  if (true) { // TODO check that all parameters from cfg are present also in check_cfg
    cfg = check_cfg;
  } else {
    Serial.println("configuration not valid, no update");       
  }  
}

#ifdef USE_EEPROM
#include <EEPROM.h>

void eeprom_init() {
  EEPROM.begin(EEPROM_SIZE);
}


void read_config(StaticJsonDocument<EEPROM_SIZE> &cfg) {
  char bytes[EEPROM_SIZE];
  EEPROM.get(0, bytes);
  StaticJsonDocument<EEPROM_SIZE> check_cfg;
  if (deserializeJson(check_cfg, bytes) != DeserializationError::Ok) {
    Serial.println("JSON deserialization failed");
    return;
  }
  if (true) { // TODO check that all parameters from cfg are present also in check_cfg
    cfg = check_cfg;
  } else {
    Serial.println("configuration not valid, no update");       
  }
}


void store_config(StaticJsonDocument<EEPROM_SIZE> &cfg) {
  char bytes[EEPROM_SIZE];
  if (serializeJson(cfg, bytes) == 0) { // returns number of bytes
    Serial.println("JSON serialization failed");
  }
  EEPROM.put(0, bytes);
  EEPROM.commit();
}

#endif
