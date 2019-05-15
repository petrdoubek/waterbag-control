import logging
import mysql.connector
import time


CHART_TEMPLATE = 'chart.html'
DAY_S = 24*3600
INTERVAL_PAST_S = 14*DAY_S
INTERVAL_FUTURE_S = 5*DAY_S


def handle_get(url, params, wfile):
    db = JawsDB()
    rsp = ""

    logging.info('chart.handle_get urlparse:%s; parse_qs: %s' % (url, params))

    rsp = html_chart(db)

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def get_volume(db, tm_from, tm_now, tm_to):
    try:
        cursor = db.db.cursor()

        query = ("SELECT time, mm FROM height"
                 " WHERE time BETWEEN %d and %d ORDER BY time" % (tm_from, tm_now))
        cursor.execute(query)
        stored = []
        for (timestamp, mm) in cursor:
            stored.append((timestamp, volume_l(mm)))
        stored_string = '[' + ','.join(["{t:%d,y:%d}" % (timestamp, l) for (timestamp, l) in stored]) + ']'

        query = ("SELECT forecast_from, rain_mm FROM forecast"
                 " WHERE valid_to >= %d"
                 "   AND (forecast_from BETWEEN %d and %d"
                 "        OR forecast_to BETWEEN %d and %d)"
                 " ORDER BY forecast_from" % (tm_now, tm_now, tm_to, tm_now, tm_to))
        cursor.execute(query)
        forecast = [];
        cumsum_l = stored[-1][1]
        for (timestamp, mm) in cursor:
            cumsum_l += rain_l(mm)
            forecast.append((timestamp, cumsum_l))
        forecast_string = '[' + ','.join(["{t:%d,y:%d}" % (timestamp, l) for (timestamp, l) in forecast]) + ']'

        cursor.close()
        return (stored_string, forecast_string)
    except mysql.connector.Error as err:
        return err.msg
        # TODO error handling!


def get_rain_forecast(db, tm_from, tm_to):
    try:
        cursor = db.db.cursor()
        query = ("SELECT forecast_from, rain_mm FROM forecast"
                 " WHERE valid_to >= %d"
                 "   AND (forecast_from BETWEEN %d and %d"
                 "        OR forecast_to BETWEEN %d and %d)"
                 " ORDER BY forecast_from" % (tm_from, tm_from, tm_to, tm_from, tm_to))
        cursor.execute(query)
        forecast = [];
        cumsum_l = 0
        for (timestamp, mm) in cursor:
            cumsum_l += rain_l(mm)
            forecast.append((timestamp, cumsum_l))
        rsp = '[' + ','.join(["{t:%d,y:%d}" % (timestamp, l) for (timestamp, l) in forecast]) + ']'
        cursor.close()
        return rsp
    except mysql.connector.Error as err:
        return err.msg
        # TODO error handling!


def html_chart(db):
    tm_now = time.time()
    (stored, forecasted_rain) = get_volume(db, tm_now - INTERVAL_PAST_S, tm_now, tm_now + INTERVAL_FUTURE_S)
    with open(CHART_TEMPLATE, 'r') as template_file:
        return template_file.read()\
            .replace('%STORED%', stored)\
            .replace('%FORECASTED_RAIN%', forecasted_rain)


def main():
    """if this module is run, connect to the database and print out the chart"""
    db = JawsDB()
    print(html_chart(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    from waterbag import volume_l, rain_l
    main()
else:
    from .jawsdb import JawsDB
    from .waterbag import volume_l, rain_l
