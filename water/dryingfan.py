import logging
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
        temperature_out = float(params['insert_temperature_in'][0])
    if 'insert_humidity_in' in params:
        humidity_out = int(params['insert_humidity_in'][0])
    if 'offset_ms' in params:
        offset_ms = int(params['offset_ms'][0])

    if temperature_out is not None and humidity_out is not None and temperature_in is not None and humidity_in is not None:
        insert_environment(db, offset_ms, temperature_out, humidity_out, temperature_in, humidity_in)
        rsp += 'OK'
    elif url.path.endswith('table'):
        rsp += "<pre>" + table_environment(db) + "</pre>\n"
    elif url.path.endswith('chart') or url.path == '/dryingfan':
        rsp += chart_environment(db, interval_s)
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
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT time_ms, temperature_out, humidity_out, temperature_in, humidity_in"
                 "  FROM dryingfan"
                 " ORDER BY time_ms desc")
        cursor.execute(query)

        for (time_ms, temperature_out, humidity_out, temperature_in, humidity_in) in cursor:
            rsp += "\n%s  %s  %s  %s %s" % (time.strftime("%a %d.%m. %X", time.localtime(time_ms)),
                                          '%5.1fC' % temperature_out if temperature_out is not None else '  n/a ',
                                          '%3d%%' % humidity_out if humidity_out is not None else 'n/a ',
                                          '%5.1fC' % temperature_in if temperature_in is not None else '  n/a ',
                                          '%3d%%' % humidity_in if humidity_in is not None else 'n/a ')

        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def chart_environment(db, interval_s):
    tm_now = time.time()
    (temperature, humidity, moisture) = get_data(db, tm_now - interval_s, tm_now)
    with open(CHART_TEMPLATE, 'r') as template_file:
        return template_file.read()\
            .replace('%STATE%', '%dC %d%% soil moisture' % (temperature[-1][1], moisture[-1][1]))\
            .replace('%TEMPERATURE%', timeseries_csv(temperature)) \
            .replace('%HUMIDITY%', timeseries_csv(humidity)) \
            .replace('%MOISTURE%', timeseries_csv(moisture))


def get_data(db, tm_from, tm_to):
    """returns:
       - time series [{t,temperature}]
       - time series [{t,air humidity}]
       - time series [{t,soil moisture}]"""
    try:
        cursor = db.db.cursor()

        temperature = read_timeseries(cursor, 'temperature', tm_from, tm_to)
        humidity = read_timeseries(cursor, 'humidity', tm_from, tm_to)

        cursor.close()
        return (temperature, humidity)
    except mysql.connector.Error as err:
        return err.msg


def read_timeseries(cursor, table, tm_from, tm_to):
    timeseries = []
    cursor.execute("SELECT * FROM %s"
                   " WHERE time_ms BETWEEN %d and %d ORDER BY time_ms"
                   % (table, tm_from, tm_to))
    for (time_ms, value) in cursor:
        timeseries.append((time_ms, value))
    return timeseries



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
