#define USING_AXTLS
#include <ESP8266WiFi.h>
#include <WiFiClientSecureAxTLS.h>  // force use of AxTLS (BearSSL is default) - found example with AxTLS which works for me
using namespace axTLS;

#include "secrets.h"
const char *ssid = WIFI_SSID, *password = WIFI_PASSWORD, *host = SERVER;
#define INSERT_PATH   "/waterbag?insert_mm="
#define LOG_PATH      "/waterbag?insert_log="
#define COMMAND_PATH  "/waterbag/command"


void print_signal_strength() {
  Serial.print("signal strength (RSSI): " + String(WiFi.RSSI()) + " dBm\n");
  #ifdef USE_DISPLAY
    disp.showNumberDec(WiFi.RSSI(), false);
  #endif
}


bool connect_wifi(int timeout) {
  Serial.println("WiFi.begin ssid: " +String(ssid));
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  for (int i=0; i < timeout; i++) {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("WiFi.begin OK. IP address: ");
      Serial.println(WiFi.localIP());
      print_signal_strength();
      return true;
    }
    delay(1000);
  }
  print_disp_err("WiFi.begin failed", 1);
  return false;
}


bool get_url(String url, String &response, bool check_ok, int timeout) {
  if (!connect_wifi(timeout)) return false;

  WiFiClientSecure client;
  Serial.println("WiFiClientSecure.connect to " + String(host));

  if (!client.connect(host, 443)) {
    print_disp_err("WiFiClientSecure.connect failed", 3);
    return false;
  }

  Serial.print("requesting URL: " + String(url) + " ... ");

  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + host + "\r\n" +
               "User-Agent: WaterbagHeightSensorESP8266\r\n" +
               "Connection: close\r\n\r\n");

  Serial.println("request sent");
  while (client.connected()) {
    String line = client.readStringUntil('\n');
    if (line == "\r") {
      Serial.println("headers received");
      break;
    }
  }
  response = client.readString();

  Serial.println("reply: ");
  Serial.println(response);

  if (!check_ok) return true;
  if (response.startsWith("OK")) {
    WiFi.disconnect();
    #ifdef USE_DISPLAY
      disp.setSegments(disp_OK);
      delay(3000);
    #endif
    return true;
  } else {
    print_disp_err("response not OK", 4);
  }

  return false;
}
