import logging
import mysql.connector
import time

CHART_TEMPLATE = 'chart_environment.html'
INTERVAL_PAST_S = 3*24*3600


def handle_get(url, params, wfile):
    db = JawsDB()
    offset_ms, temperature_C, humidity_pct, moisture_res = 0, None, None, None
    rsp = ""

    logging.info('waterbag.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    interval_s = INTERVAL_PAST_S
    if 'days' in params and int(params['days'][0]) > 0:
        interval_s = int(params['days'][0]) * 24 * 3600
    if 'hours' in params and int(params['hours'][0]) > 0:
        interval_s = int(params['hours'][0]) * 3600

    if 'insert_temperature' in params:
        temperature_C = float(params['insert_temperature'][0])
    if 'insert_humidity' in params:
        humidity_pct = int(params['insert_humidity'][0])
    if 'insert_moisture' in params:
        moisture_res = int(params['insert_moisture'][0])
    if 'offset_ms' in params:
        offset_ms = int(params['offset_ms'][0])

    if temperature_C is not None or humidity_pct is not None or moisture_res is not None:
        insert_environment(db, offset_ms, temperature_C, humidity_pct, moisture_res)
        rsp += 'OK'
    elif url.path.endswith('table'):
        rsp += "<pre>" + table_environment(db) + "</pre>\n"
    elif url.path.endswith('chart') or url.path == '/environment':
        rsp += chart_environment(db, interval_s)
    else:
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def insert_environment(db, offset_ms, temperature_c, humidity_pct, moisture_res):
    time_ms = time.time() + offset_ms

    if temperature_c is not None:
        db.insert('temperature', 'time_ms, temperature_c', '%s, %s', (time_ms, temperature_c))
    if humidity_pct is not None:
        db.insert('humidity', 'time_ms, humidity_pct', '%s, %s', (time_ms, humidity_pct))
    if moisture_res is not None:
        db.insert('moisture', 'time_ms, moisture_res', '%s, %s', (time_ms, moisture_res))


def table_environment(db):
    """return list of temperature and humidity measurements in pre-tags"""
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT t.time_ms, temperature_c, humidity_pct, moisture_res"
                 "  FROM temperature t"
                 "  LEFT JOIN humidity h ON t.time_ms = h.time_ms"
                 "  LEFT JOIN moisture m ON t.time_ms = m.time_ms"
                 " ORDER BY time_ms desc")
        cursor.execute(query)

        for (time_ms, temperature_c, humidity_pct, moisture_res) in cursor:
            rsp += "\n%s  %s  %s  %s" % (time.strftime("%a %d.%m. %X", time.localtime(time_ms)),
                                          '%5.1fC' % temperature_c if temperature_c is not None else '  n/a ',
                                          '%3d%%' % humidity_pct if humidity_pct is not None else 'n/a ',
                                          '%3d%%' % moisture_to_pct(moisture_res) if moisture_res is not None else 'n/a ')

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
        moisture = [ (t, moisture_to_pct(m)) for (t, m) in read_timeseries(cursor, 'moisture', tm_from, tm_to) ]

        cursor.close()
        return (temperature, humidity, moisture)
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


def moisture_to_pct(resistance):
    return 100-(100*resistance/1024)


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_environment':
            insert_environment(db, 0, int(sys.argv[2]) if len(sys.argv) >= 3 else 22, int(sys.argv[3]) if len(sys.argv) >= 4 else 55)
        if sys.argv[1] == 'create_tables':
            db.create("CREATE TABLE temperature "
                      "(time_ms INT UNSIGNED NOT NULL, temperature_c FLOAT NOT NULL, "
                      "PRIMARY KEY (time_ms));")
            db.create("CREATE TABLE humidity "
                      "(time_ms INT UNSIGNED NOT NULL, humidity_pct INT NOT NULL, "
                      "PRIMARY KEY (time_ms));")
            db.create("CREATE TABLE moisture "
                      "(time_ms INT UNSIGNED NOT NULL, moisture_res INT NOT NULL, "
                      "PRIMARY KEY (time_ms));")
            return

    print(table_environment(db))


if __name__ == "__main__":
    from jawsdb import JawsDB, timeseries_csv
    main()
else:
    from .jawsdb import JawsDB, timeseries_csv
