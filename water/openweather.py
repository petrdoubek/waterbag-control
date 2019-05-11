import json
import logging
import mysql.connector
import requests
import time

import water.jawsdb


INTERVAL_S = 3*3600;
URL = "http://api.openweathermap.org/data/2.5/forecast?q=pardubice,cz&mode=json&appid=13940fe7b67b11cff3cd0c2f8c0b526d"


def get_forecast():
    forecast = []
    rsp = requests.get(URL)
    if rsp.status_code == 200:
        jsn = rsp.json()
        if 'list' in jsn:
            for pt in jsn['list']:
                forecast.append((pt['dt'], pt['rain']['3h'] if ('rain' in pt and '3h' in pt['rain']) else 0.0))
    return forecast


def insert_forecasts(db, fcs):
    for fc in fcs:
        insert_forecast(db, fc[0], fc[0]+INTERVAL_S, fc[1])
        # TODO insert in one transaction


def insert_forecast(db, forecast_from, forecast_to, rain_mm):
    db.insert('forecast', 'valid_from, valid_to, forecast_from, forecast_to, rain_mm', '%s, %s, %s, %s, %s',
              (time.time(), time.time()+1e9, forecast_from, forecast_to, rain_mm))
    # TODO invalidate previous forecast


def read_forecast(db):
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT forecast_from, forecast_to, rain_mm FROM forecast"
                 " WHERE valid_to >= %d"
                 " ORDER BY forecast_from asc"
                 % time.time())
        cursor.execute(query)  # , time.time())
        for (forecast_from, forecast_to, rain_mm) in cursor:
            rsp += "  %s - %s  %.2fmm\n" % (jawsdb.strtime(forecast_from), jawsdb.strtime(forecast_to), rain_mm)
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = jawsdb.JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert':
            insert_forecast(db, time.time()+3*3600, time.time()+6*3600, sys.argv[2] if len(sys.argv) >= 3 else 1.23)
        if sys.argv[1] == 'create':
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

    insert_forecasts(db, get_forecast())
    print(read_forecast(db))


if __name__ == "__main__":
    main()



