import json
import logging
import mysql.connector
import os
import requests
import time

INTERVAL_S = 3*3600
APPID = os.environ['OPENWEATHER_APPID']
URL = "http://api.openweathermap.org/data/2.5/forecast?q=%s&mode=json&appid=%s"


def handle_get(cfg, url, params, wfile):
    db = JawsDB()
    rsp = ""

    logging.info('openweather.handle_get urlparse:%s; parse_qs: %s' % (url, params))

    if url.path.endswith('/html'):
        rsp += "<pre>\n" + read_forecast(db, time.time()) + "</pre>\n"
    if url.path.endswith('/update'):
        insert_forecasts(db, get_forecast(cfg))
        rsp += "UPDATE OK"

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def get_forecast(cfg):
    """retrieve 5day/3hr forecasts, return list of tuples (timestamp of 3hr period start, precipitation forecast in mm)"""
    forecast = []
    rsp = requests.get(URL % (cfg['city'], APPID))
    if rsp.status_code == 200:
        jsn = rsp.json()
        if 'list' in jsn:
            for pt in jsn['list']:
                forecast.append((pt['dt'], pt['rain']['3h'] if ('rain' in pt and '3h' in pt['rain']) else 0.0))
    return forecast


def insert_forecasts(db, fcs):
    """insert forecasts into database with current timestamp as valid-from, invalidate the old ones"""
    now = time.time()
    invalidate_old(db, fcs, now)
    db.insert('forecast', 'valid_from, valid_to, forecast_from, forecast_to, rain_mm', '%s, %s, %s, %s, %s',
              [(now, now + 1e9, fc[0], fc[0]+INTERVAL_S, fc[1]) for fc in fcs])


def invalidate_old(db, fcs, now):
    """invalidate forecasts that are replaced by fcs"""
    try:
        for fc in fcs:
            cursor = db.db.cursor()
            query = ("UPDATE forecast SET valid_to = %d"
                     " WHERE forecast_from = %d"
                     "   AND valid_to >= %d"
                     % (now-1, fc[0], now))
            cursor.execute(query)
            cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg


def read_forecast(db, start_timestamp):
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT valid_from, forecast_from, forecast_to, rain_mm FROM forecast"
                 " WHERE valid_to >= %d"
                 "   AND forecast_to >= %d"
                 " ORDER BY forecast_from asc"
                 % (time.time(), start_timestamp))
        cursor.execute(query)  # , time.time())
        for (valid_from, forecast_from, forecast_to, rain_mm) in cursor:
            rsp += "%s:    %s - %s  %.2fmm\n" % (time.strftime("%d.%m. %H:%m", time.localtime(valid_from)),
                                                time.strftime("%a %d.%m. %H:%m", time.localtime(forecast_from)),
                                                time.strftime("%H:%m", time.localtime(forecast_to)),
                                                rain_mm)
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def rain_soon_mm(db, start_timestamp, end_timestamp):
    rain_soon_mm = 0
    try:
        cursor = db.db.cursor()
        query = ("SELECT SUM(rain_mm) FROM forecast"
                 " WHERE valid_to >= %d"
                 "   AND forecast_to >= %d"
                 "   AND forecast_from <= %d"
                 " ORDER BY forecast_from asc"
                 % (time.time(), start_timestamp, end_timestamp))
        cursor.execute(query)
        for (rain_mm) in cursor:
            rain_soon_mm = rain_mm
            break
        cursor.close()
    except mysql.connector.Error as err:
        return 0
    return rain_soon_mm


def main():
    """if this module is run, connect to the database and print it out + accept some command line arguments to test methods"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert':
            insert_forecasts(db, [(time.time(), sys.argv[2] if len(sys.argv) >= 3 else 1.23)])
        if sys.argv[1] == 'create_tables':
            db.create("CREATE TABLE forecast ("
                      " valid_from     INT UNSIGNED NOT NULL,"
                      " valid_to       INT UNSIGNED NOT NULL,"
                      " forecast_from  INT UNSIGNED NOT NULL,"
                      " forecast_to    INT UNSIGNED NOT NULL,"
                      " rain_mm        FLOAT,"
                      "PRIMARY KEY (valid_from, forecast_from));")
        if sys.argv[1] == 'delete':
            if len(sys.argv) == 3 and sys.argv[2] == 'really_do':
                db.delete_all('forecast')
            else:
                print("please confirm deletion of table including all data: %s delete_height really_do" % sys.argv[0])

    print(read_forecast(db, time.time()))


if __name__ == "__main__":
    from jawsdb import JawsDB, strtime
    main()
else:
    from .jawsdb import JawsDB, strtime
