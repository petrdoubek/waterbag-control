/* Arduino measures waterbag height using ultrasound sensor (SRF04)
 * and connects as a client over HTTPS to an API to insert the measurement into database
 * 
 * - in fact distance from ceiling to waterbag top is measured, height is calculated as DIST_SENSOR_BOTTOM_MM - distance
 *   - DIST_SENSOR_BOTTOM_MM has to be calibrated based on installation
 *   - TODO use potentiometer to calibrate (show calculated height on display instead of distance to let user adjust)
 * - HTTPS is used without fingerprint or certificate, I'm using Heroku which does not allow HTTP
 * - tried also SRF05 sensor which should be more precise but it did not measure distance >= 700mm
 * - measurements (distance, not calculated waterbag height) are shown on TM1637 display
 * - TODO open sprinkler valve when waterbag height reaches maximum
 */

#define USING_AXTLS
#include <ESP8266WiFi.h>
#include <WiFiClientSecureAxTLS.h>  // force use of AxTLS (BearSSL is default) - found example with AxTLS which works for me
using namespace axTLS;

#include <NewPing.h>
#include "MedianFilterLib.h"

#include "waterbag_display.h"

const char *ssid = "a-router", *password = "D79EFFEC66";
const char *host = "pdou-voda.herokuapp.com";
#define INSERT_PATH "/height?insert_mm="

#define TRIGGER_PIN      D1
#define ECHO_PIN         D2
#define LED              D7
#define DIST_SENSOR_BOTTOM_MM  1660 // MUST BE CALIBRATED, DISTANCE THE SENSOR MEASURES WHEN STORAGE IS EMPTY
#define MAX_DETECT_CM  1000
#define N_PINGS           9
#define MIN_CHANGE_MM    10
#define CYCLE_MEASURE_S   2
#define CYCLE_SEND_S     30 // 60
#define FORCE_SEND_S    600 // 3600
#define AVG_WINDOW       30
#define CONNECT_ATTEMPTS  2
#define WIFI_TIMEOUT_S   15

NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DETECT_CM);
MedianFilter<int> medianFilter(AVG_WINDOW);

float last_sent_mm = 100000;
int till_measure_s = 1, till_send_s = CYCLE_SEND_S, till_force_send_s = FORCE_SEND_S;

void print_disp_err(String msg, int code) {
  Serial.println(msg);
  disp_err(code);
  delay(3000);
}

void setup() {
  Serial.begin(9600);
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);
  disp.setBrightness(8); // range 8-15
}

bool connect_wifi() {
  Serial.println("WiFi.begin ssid: " +String(ssid));
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  for (int i=0; i<WIFI_TIMEOUT_S; i++) {
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

void print_signal_strength() {
  Serial.print("signal strength (RSSI): " + String(WiFi.RSSI()) + " dBm\n");
  disp.showNumberDec(WiFi.RSSI(), false);
}
 
void loop() {
  if (till_measure_s <= 0) {
    measure();
    till_measure_s = CYCLE_MEASURE_S;
  }
  if (till_send_s <= 0) {
    int filtered_mm = medianFilter.GetFiltered();
    if (till_force_send_s <= 0 || abs(last_sent_mm - filtered_mm) >= MIN_CHANGE_MM) {
      if (insert_height(round(filtered_mm))) {
        last_sent_mm = filtered_mm;
        till_force_send_s = FORCE_SEND_S;
      } else {
        Serial.println("sending failed");
      }
    } else {
      Serial.println("sending skipped");
    }
    till_send_s = CYCLE_SEND_S;
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
  int dist_mm = (343 * (int) sonar.ping_median(N_PINGS, MAX_DETECT_CM)) / 2000;
  Serial.printf("measured distance %4dmm    ", dist_mm);
  digitalWrite(LED, LOW);
  medianFilter.AddValue(dist_mm);
  Serial.printf("median %4dmm\n", medianFilter.GetFiltered());
  disp.showNumberDec(dist_mm, false);
}


bool insert_height(int mm) {
  if (!connect_wifi()) return false;
  
  // Use WiFiClientSecure class to create TLS connection
//#pragma GCC diagnostic push
//#pragma GCC diagnostic ignored  "-Wdeprecated-declarations"
  WiFiClientSecure client;
//#pragma GCC diagnostic pop
  Serial.println("WiFiClientSecure.connect to " + String(host));

  bool sent = false;
  int attempts = 0;
  while (!sent && attempts<CONNECT_ATTEMPTS) {
    attempts++;

    if (!client.connect(host, 443)) {
      print_disp_err("WiFiClientSecure.connect failed", 3);
      delay(500);
      continue;
    }

    String url = INSERT_PATH + String(DIST_SENSOR_BOTTOM_MM - mm);
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
    String payload = client.readString();
  
    Serial.println("reply: ");
    Serial.println(payload);
    
    if (payload.startsWith("OK")) {
      WiFi.disconnect();
      disp.setSegments(disp_OK); delay(3000);
      return true;
    } else {
      print_disp_err("response not OK", 4);
    }
  }

  return false;
}
