# Rain Water Storage Automation

Monitoring water level in rain water storage (bag in my case, could be also tank) and triggering valve or pump when a configured level is reached.

The system has two parts:

- software for Arduino controller, in C/C++ used by Arduino IDE, this is mandatory, see Arduino directory
- server with database that stores and shows the measurements and can be used for manual control, in Python and MySQL, this optional

## Hardware

- NodeMCU ESP8266 board
- SR04 ultrasound distance sensor, powered by 5V from the board (3.3V might not work)
- relay to trigger valve or pump
- USB adapter to power the board
- power supply to power the valve or pump (if it is not the standard eletrical network voltage)
- optional LED to indicate when the sensor measures
- optional TM1637 display to show measurements and WiFi signal strength, useful at debugging stage

## Installation

Upload the software from `Arduino` directory to the controller using Arduino IDE.

To monitor and control the Arduino, run the server part somewhere in Internet. I am using Heroku, the free plan is sufficient (1000hrs per month and 5MB Jaws MySQL database). TODO how to trigger forecast update.

## Commands

Example of changing parameters in the Arduino controller by insert into `command` table in the SQL database. The change is not immediate, the controller checks for new setup after it sends the measurement. Server cannot push the configuration.

```
python water/waterbag.py insert_command '{"DIST_SENSOR_BOTTOM_MM":1674,"TRIGGER_OVERFLOW_MM":555,"MAX_DETECT_CM":300,"N_PINGS":9,"MIN_CHANGE_MM":3,"CYCLE_MEASURE_S":2,"CYCLE_SEND_S":60,"FORCE_SEND_S":600,"WIFI_TIMEOUT_S":30}'
```

