# Rain Water Storage Automation

Monitoring water level in rain water tank (in my case [bag or bladder by Citerneo](https://www.citerneo.eu/rainwater), could be also tank, cistern, barrel) and triggering valve or pump when a configured level is reached.

![screenshot of water level chart](docs/images/screenshot-waterbag-control-server-chart.png?raw=true)

Why do I need it? My waterbag is in basement below terrain level and overflow outlet is below terrain level. The bag would burst if I let the pressure build that high. The sewer drain is also not low enough to ensure recommended maximum height of the bag is not exceeded. So I automatically pump out water when the maximum height is reached and sewer drain serves only as a fallback.

The system has two parts:

- software for Arduino controller, in C/C++ used by Arduino IDE, this is mandatory, see [Arduino directory](https://github.com/petrdoubek/waterbag-control/tree/master/Arduino)
- server with MySQL database that stores and shows the measurements and can be used for manual control, in Python, this optional

## Hardware

- [NodeMCU ESP8266 board](https://www.nodemcu.com/index_en.html) with integrated WiFi
- SR04 ultrasound distance sensor, powered by 5V from the board (3.3V might not work)
- [relay board](https://www.aliexpress.com/w/wholesale-2-channel-5V-relay.html) to trigger valve or pump - in my case [Orbit 1in Jar Top 24V valve](https://www.orbitonline.com/products/sprinkler-systems/valves/plastic-valves/automatic-jar-top/1-male-threaded-in-line-jar-top-sprinkler-control-valve-218)
- USB adapter to power the board
- power supply to power the valve or pump (if it is not the standard electrical network voltage)
- optional LED to indicate when the sensor measures
- optional TM1637 display to show measurements and WiFi signal strength, useful at debugging stage

## Sensor Installation

1. Install driver for ESP8266 (look for guide for your OS), install [Arduino IDE](https://www.arduino.cc/en/Main/Software), add your board (Tools->Board->Board Manager), connect the board via USB and test it (File->Examples).
1. Copy directory `Arduino/waterbag` to your `Arduino` directory and header files directory `Arduino/petrdoubek` to your `Arduino/libraries` (or copy the header files to directory `Arduino/waterbag` as well).
1. Adjust parameters in `init_config()` for your needs, set `WIFI_SSID, WIFI_PASSWORD, SERVER` (to dummy values if you do not plan to use the server part).
1. Compile, upload to the board, watch Tools->Serial Monitor, you should see that the board initialized with your configuration and fails to measure because of missing sensor.
1. Connect the distance sensor and optionally LED and/or display to the defined pins, tune the measurement using `DIST_SENSOR_BOTTOM_MM` to get correct water height. If you already have server part running, you can change setup remotely without uploading and restarting.
1. Connect the relay, test that it works by artificially lowering `TRIGGER_OVERFLOW_MM` just below the current height. Again with running server the parameter can be changed remotely.

## Server Installation

To monitor and control the Arduino (via configuration changes), run the server part somewhere where your sensor can connect. I am using [Heroku](https://www.heroku.com/), the free plan is sufficient (1000hrs per month and 5MB [JawsDB MySQL database](https://elements.heroku.com/addons/jawsdb) as add-on).

1. Define database access variables:

```
JAWSDB_DATABASE
JAWSDB_HOST
JAWSDB_PASSWD
JAWSDB_URL
JAWSDB_USER
```

1. Run `python server.py`, if using Heroku this is defined in `Procfile` and you test locally by `heroku local`
1. Main page is at `chart`, e.g. `https://localhost:5000/chart` if testing locally.

To display the forecasted precipitation, I am using [OpenWeatherMap 5day/3hour forecast API](https://openweathermap.org/forecast5). The service is free, you need to register to get an API key, which the server expects in `OPENWEATHER_APPID` variable. Forecast update is triggered by a GET call to `forecast/update` resource, e.g. using `curl` call in [Heroku scheduler](https://elements.heroku.com/addons/scheduler) add-on.

## Remote Control

The configuration of sensor can be changed from server by inserting a new configuration into `command` table in the SQL database. The change is not immediate, the controller checks for new setup after it sends the measurement. This is cost optimization to save free hours on Heroku - if this is not a concern for you, configure shorter `FORCE_SEND_S` period. Server cannot push the configuration.

Either use the `config` page on web server, or command line interface, e.g.:

```
python water/waterbag.py insert_command '{"DIST_SENSOR_BOTTOM_MM":1674,"TRIGGER_OVERFLOW_MM":600,"MAX_DETECT_CM":300,"N_PINGS":9,"MIN_CHANGE_MM":3,"CYCLE_MEASURE_S":2,"CYCLE_SEND_S":60,"FORCE_SEND_S":7200,"WIFI_TIMEOUT_S":30}'
```
