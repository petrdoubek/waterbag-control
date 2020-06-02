import logging
import math
import mysql.connector
import time

CHART_TEMPLATE = 'chart_environment.html'
INTERVAL_PAST_S = 3*24*3600


def handle_get(url, params, wfile):
    db = JawsDB()
    offset_ms, temperature_out, humidity_out, temperature_in, humidity_in = 0, None, None, None, None
    rsp = ""

    logging.info('waterbag.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    interval_s = INTERVAL_PAST_S
    if 'days' in params and int(params['days'][0]) > 0:
        interval_s = int(params['days'][0]) * 24 * 3600
    if 'hours' in params and int(params['hours'][0]) > 0:
        interval_s = int(params['hours'][0]) * 3600

    if 'insert_temperature_out' in params:
        temperature_out = float(params['insert_temperature_out'][0])
    if 'insert_humidity_out' in params:
        humidity_out = int(params['insert_humidity_out'][0])
    if 'insert_temperature_in' in params:
        temperature_in = float(params['insert_temperature_in'][0])
    if 'insert_humidity_in' in params:
        humidity_in = int(params['insert_humidity_in'][0])
    if 'offset_ms' in params:
        offset_ms = int(params['offset_ms'][0])

    if temperature_out is not None or humidity_out is not None or temperature_in is not None or humidity_in is not None:
        insert_environment(db, offset_ms, temperature_out, humidity_out, temperature_in, humidity_in)
        rsp += 'OK'
    elif url.path.endswith('table'):
        rsp += "<pre>" + table_environment(db) + "</pre>\n"
    #elif url.path.endswith('chart') or url.path == '/dryingfan':
    #    rsp += chart_environment(db, interval_s)
    else:
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def insert_environment(db, offset_ms, temperature_out, humidity_out, temperature_in, humidity_in):
    time_ms = time.time() + offset_ms

    db.insert('dryingfan',
              'time_ms, temperature_out, humidity_out, temperature_in, humidity_in',
              '%s, %s, %s, %s, %s',
              (time_ms, temperature_out, humidity_out, temperature_in, humidity_in))


def table_environment(db):
    """return list of temperature and humidity measurements in pre-tags"""
    rsp =  "time                     outside      inside     [g/m3]"
    rsp =  "time                   temp   hum   temp   hum  out  in"
    try:
        cursor = db.db.cursor()
        query = ("SELECT time_ms, temperature_out, humidity_out, temperature_in, humidity_in"
                 "  FROM dryingfan"
                 " ORDER BY time_ms desc")
        cursor.execute(query)

        for (time_ms, temperature_out, humidity_out, temperature_in, humidity_in) in cursor:
            abs_out = abs_humidity(temperature_out, humidity_out)
            abs_in  = abs_humidity(temperature_in, humidity_in)
            rsp += "\n%s  %s  %s  %s %s %s %s %s" % (
                        time.strftime("%a %d.%m. %X", time.localtime(time_ms)),
                        '%5.1fC' % temperature_out if temperature_out is not None else '  n/a ',
                        '%3d%%' % humidity_out if humidity_out is not None else 'n/a ',
                        '%5.1fC' % temperature_in if temperature_in is not None else '  n/a ',
                        '%3d%%' % humidity_in if humidity_in is not None else 'n/a ',
                        '%3d' % abs_out if abs_out is not None else 'n/a',
                        '%3d' % abs_in if abs_in is not None else 'n/a',
                        'FAN' if abs_out is not None and abs_in is not None and (abs_out+0.5) <= abs_in else ''
            )

        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def abs_humidity(T, h):
    """calculate absolute humidity [g/m3] given temperature T [C] and relative humidity h [%]
       based on: https://www.easycalculation.com/weather/learn-relative-humidity-from-absolute.php"""
    if T is None or h is None:
        return None
    M = 18.0 # [g/mol]
    R = 0.0623665 # [ mmHg x m3 / C / mol ]
    TK = 273.15 + T # [K]
    ps = ( 0.61078 * 7.501 ) * math.exp ( (17.2694 * T) / (238.3 + T) ) # [mmHg]
    return h/100.0 * (M / (R * TK) * ps)


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'create_tables':
            db.create("CREATE TABLE dryingfan"
                      "(time_ms INT UNSIGNED NOT NULL, temperature_out FLOAT, humidity_out INT, temperature_in FLOAT, humidity_in INT,"
                      "PRIMARY KEY (time_ms));")
            return

    print(table_environment(db))


if __name__ == "__main__":
    from jawsdb import JawsDB, timeseries_csv
    main()
else:
    from .jawsdb import JawsDB, timeseries_csv
