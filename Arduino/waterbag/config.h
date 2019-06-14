#include <ArduinoJson.h>

#define EEPROM_SIZE  512
StaticJsonDocument<EEPROM_SIZE> cfg;


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
