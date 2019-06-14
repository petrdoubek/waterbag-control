#ifndef __JSONCONFIG_H__
#define __JSONCONFIG_H__

#include <ArduinoJson.h>
#include <EEPROM.h>

#define EEPROM_SIZE  512  // take first 512B of EEPROM

class JsonConfig {
  public:
    JsonConfig() {
      #ifdef USE_EEPROM
      EEPROM.begin(EEPROM_SIZE);
      #endif
    }

    void printMe() {
      char bytes[EEPROM_SIZE];
      if (serializeJson(val, bytes) == 0) { // returns number of bytes
        Serial.println("JSON serialization failed");
      }
      Serial.println(bytes);
    }

    bool loadJSON(const StaticJsonDocument<EEPROM_SIZE> &check_cfg) {
      if (true) { // TODO check that all parameters from cfg are present also in check_cfg
        val = check_cfg;
        return true;
      } else {
        Serial.println("configuration not valid, no update");
        return false;
      }
    }

    bool loadString(String bytes) {
      StaticJsonDocument<EEPROM_SIZE> check_cfg;
      if (deserializeJson(check_cfg, bytes) != DeserializationError::Ok) {
        Serial.println("JSON deserialization failed");
        return false;
      }
      return loadJSON(check_cfg);
    }

#ifdef USE_EEPROM
    bool loadEEPROM() {
      char bytes[EEPROM_SIZE];
      EEPROM.get(0, bytes);
      return loadString(bytes);
    }

    bool saveEEPROM() {
      char bytes[EEPROM_SIZE];
      if (serializeJson(val, bytes) == 0) { // returns number of bytes
        Serial.println("JSON serialization failed");
        return false;
      }
      EEPROM.put(0, bytes);
      EEPROM.commit();
      return true;
    }
#endif

    StaticJsonDocument<EEPROM_SIZE> val;
};

#endif
