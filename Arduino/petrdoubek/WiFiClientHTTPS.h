/*
 * WiFiClientHTTPS.h - wrapper around WiFiClientSecure, using HTTPS GET without certificate or fingerprint
 */

#ifndef __WIFICLIENTHTTPS_H__
#define __WIFICLIENTHTTPS_H__

#define USING_AXTLS
#include <ESP8266WiFi.h>
#include <WiFiClientSecureAxTLS.h>  // force use of AxTLS (BearSSL is default) - found example with AxTLS which works for me
using namespace axTLS;

class WiFiClientHTTPS {
  public:
    WiFiClientHTTPS(const char *ssid, const char *password, const char *host, Display4Digit *disp) {
      strcpy(_ssid, ssid);
      strcpy(_password, password);
      strcpy(_host, host);
      _disp = disp;
    }

    bool get_url(String url, String &response, bool check_ok, int timeout) {
      if (!connect_wifi(timeout)) return false;
    
      WiFiClientSecure client;
      Serial.println("WiFiClientSecure.connect to " + String(_host));
    
      if (!client.connect(_host, 443)) {
        _disp->printDispErr("WiFiClientSecure.connect failed", 3);
        return false;
      }
    
      Serial.print("requesting URL: " + String(url) + " ... ");
    
      client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                   "Host: " + _host + "\r\n" +
                   "User-Agent: ESP8266\r\n" +
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
        _disp->dispOK();
        delay(3000);
        return true;
      } else {
        _disp->printDispErr("response not OK", 4);
      }
    
      return false;
    }

  protected:
    void print_signal_strength() {
      Serial.print("signal strength (RSSI): " + String(WiFi.RSSI()) + " dBm\n");
      _disp->showNumberDec(WiFi.RSSI(), false);
    }

    bool connect_wifi(int timeout) {
      Serial.println("WiFi.begin ssid: " +String(_ssid));
      WiFi.mode(WIFI_STA);
      WiFi.begin(_ssid, _password);
      for (int i=0; i < timeout; i++) {
        if (WiFi.status() == WL_CONNECTED) {
          Serial.print("WiFi.begin OK. IP address: ");
          Serial.println(WiFi.localIP());
          print_signal_strength();
          return true;
        }
        delay(1000);
      }
      _disp->printDispErr("WiFi.begin failed", 1);
      return false;
    }
  
  private:
    char *_ssid, *_password, *_host;
    Display4Digit *_disp;
};

#endif
