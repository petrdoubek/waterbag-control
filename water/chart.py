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
    global INTERVAL_PAST_S, INTERVAL_FUTURE_S
    if 'days' in params and int(params['days'][0]) > 0:
        INTERVAL_PAST_S = int(params['days'][0]) * DAY_S
        INTERVAL_FUTURE_S = INTERVAL_PAST_S
    if 'hours' in params and int(params['hours'][0]) > 0:
        INTERVAL_PAST_S = int(params['hours'][0]) * 3600
        INTERVAL_FUTURE_S = INTERVAL_PAST_S

    rsp = html_chart(db)

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def li_parameters():
    """return list of parameters as a string, each parameter starting with <li> tag"""
    params = dict(roof_area_m2=ROOF_AREA_M2)
    return ''.join([ "<li>%s: %s\n" % (par,val) for par,val in params.items() ])


def get_volume(db, tm_from, tm_now, tm_to):
    try:
        cursor = db.db.cursor()

        query = ("SELECT time, mm FROM height"
                 " WHERE time BETWEEN %d and %d ORDER BY time" % (tm_from, tm_now))
        cursor.execute(query)
        stored = []
        for (sec, mm) in cursor:
            stored.append((sec, volume_l(mm)))
        stored_string = '[' + ','.join(["{t:%d,y:%d}" % (1000*sec, l) for (sec, l) in stored]) + ']'

        query = ("SELECT forecast_from, forecast_to, rain_mm FROM forecast"
                 " WHERE valid_to >= %d"
                 "   AND (forecast_from BETWEEN %d and %d"
                 "        OR forecast_to BETWEEN %d and %d)"
                 " ORDER BY forecast_from" % (tm_now, tm_now, tm_to, tm_now, tm_to))
        cursor.execute(query)
        forecast = [(stored[-1][0], stored[-1][1])]
        cumsum_l = stored[-1][1]
        for (from_s, to_s, mm) in cursor:
            cumsum_l += rain_l(mm)
            forecast.append((int((from_s + to_s)/2), cumsum_l))
        forecast_string = '[' + ','.join(["{t:%d,y:%d}" % (1000*sec, l) for (sec, l) in forecast]) + ']'

        cursor.close()
        return (stored_string, forecast_string)
    except mysql.connector.Error as err:
        return err.msg
        # TODO error handling!


def html_chart(db):
    tm_now = time.time()
    (stored, forecasted_rain) = get_volume(db, tm_now - INTERVAL_PAST_S, tm_now, tm_now + INTERVAL_FUTURE_S)
    with open(CHART_TEMPLATE, 'r') as template_file:
        return template_file.read()\
            .replace('%STORED%', stored)\
            .replace('%FORECASTED_RAIN%', forecasted_rain)\
            .replace('%MAX_L%', '%d' % round(1.5*MAX_VOLUME_L))\
            .replace('%PARAMETERS%', li_parameters())


def main():
    """if this module is run, connect to the database and print out the chart"""
    db = JawsDB()
    print(html_chart(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    from waterbag import volume_l, rain_l, MAX_VOLUME_L, ROOF_AREA_M2
    main()
else:
    from .jawsdb import JawsDB
    from .waterbag import volume_l, rain_l, MAX_VOLUME_L, ROOF_AREA_M2
