import logging
import mysql.connector
import time

from .jawsdb import JawsDB, timeseries_csv
from .waterbag import volume_l, rain_l

CHART_TEMPLATE = 'chart.html'
DAY_S = 24*3600
INTERVAL_PAST_S = 3*DAY_S
INTERVAL_FUTURE_S = 3*DAY_S


def handle_get(cfg, url, params, wfile):
    db = JawsDB()

    logging.info('chart.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    global INTERVAL_PAST_S, INTERVAL_FUTURE_S
    if 'days' in params and int(params['days'][0]) > 0:
        INTERVAL_PAST_S = int(params['days'][0]) * DAY_S
        INTERVAL_FUTURE_S = INTERVAL_PAST_S
    if 'hours' in params and int(params['hours'][0]) > 0:
        INTERVAL_PAST_S = int(params['hours'][0]) * 3600
        INTERVAL_FUTURE_S = INTERVAL_PAST_S

    rsp = html_chart(cfg, db)

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def html_chart(cfg, db):
    tm_now = time.time()
    (stored, forecasted_rain, overflow, now_l, overflow_s, total_open_s) = \
        get_data(cfg, db, tm_now - INTERVAL_PAST_S, tm_now, tm_now + INTERVAL_FUTURE_S)
    with open(CHART_TEMPLATE, 'r') as template_file:
        return template_file.read()\
            .replace('%STATE%', '%dl %s' % (now_l, ('OPENED %ds' % overflow_s) if overflow_s>=0 else ''))\
            .replace('%STORED%', stored) \
            .replace('%OVERFLOW%', overflow) \
            .replace('%FORECASTED_RAIN%', forecasted_rain)\
            .replace('%MAX_L%', '%d' % round(1.25 * float(cfg['max_volume_l'])))\
            .replace('%TOTAL_OVERFLOW_S%', '%d' % total_open_s)


def get_data(cfg, db, tm_from, tm_now, tm_to):
    """returns:
       - time series [{t,stored}] printed as string
       - time series [{t,forecast}] printed as string
       - time series [{t,0 or CONST * max_volume based on overflow closed/opened}] printed as a string
       - current volume
       - how many seconds is overflow opened (or -1 if closed)
       - how long was the overflow opened in seconds over the time between tm_from and tm_now"""
    try:
        cursor = db.db.cursor()

        stored = read_stored(cfg, cursor, tm_from, tm_to)

        if stored is None or len(stored) < 1:
            stored, forecast, overflow = [{tm_now-INTERVAL_PAST_S,0}, {tm_now,0}], [], []
            last_stored_l, total_open_s = 0, 0
        else:
            last_stored_ts, last_stored_l = stored[-1]
            forecast = read_forecast(cfg, cursor, last_stored_ts, last_stored_l, tm_now, tm_to)
            overflow, total_open_s = read_overflow(cfg, cursor, last_stored_ts, tm_from, tm_to)

        cursor.close()
        return (timeseries_csv(stored), timeseries_csv(forecast), timeseries_csv(overflow),
                last_stored_l,
                tm_now - overflow[-1][0] if len(overflow) > 0 and overflow[-1][1]>0 else -1,
                total_open_s)
    except mysql.connector.Error as err:
        return err.msg


def read_stored(cfg, cursor, tm_from, tm_to):
    stored = []
    cursor.execute("SELECT time, mm FROM height"
                   " WHERE time BETWEEN %d and %d ORDER BY time"
                   % (tm_from, tm_to))
    for (sec, mm) in cursor:
        stored.append((sec, volume_l(cfg, mm)))
    return stored


def read_forecast(cfg, cursor, last_stored_ts, last_stored_l, tm_now, tm_to):
    cursor.execute("SELECT forecast_from, forecast_to, rain_mm FROM forecast"
                   " WHERE valid_to >= %d"
                   "   AND (forecast_from BETWEEN %d and %d"
                   "        OR forecast_to BETWEEN %d and %d)"
                   " ORDER BY forecast_from"
                   % (tm_now, tm_now, tm_to, tm_now, tm_to))
    forecast = [(last_stored_ts, last_stored_l)]
    cumsum_l = last_stored_l
    for (from_s, to_s, mm) in cursor:
        cumsum_l += rain_l(cfg, mm)
        forecast.append((int((from_s + to_s) / 2), cumsum_l))
    if len(forecast) >= 2 and forecast[1][0] < last_stored_ts:
        forecast[1] = (last_stored_ts, forecast[1][1])  # do not go back in time with first forecast
        # TODO forecast only proportionate part of rain?
    return forecast


def read_overflow(cfg, cursor, last_stored_ts, tm_from, tm_to):
    total_open_s = 0
    overflow = []
    cursor.execute("SELECT time, msg FROM log"
                   " WHERE time BETWEEN %d and %d"
                   "   AND msg LIKE 'overflow_%%'"
                   " ORDER BY time"
                   % (tm_from, tm_to))
    for (log_ts, msg) in cursor:
        if msg.startswith('overflow_opened'):  # going up
            overflow.append((log_ts, 0))
            overflow.append((log_ts, float(cfg['max_volume_l'] / 6)))
        if msg.startswith('overflow_closed'):  # going down
            if len(overflow) > 0:
                total_open_s += log_ts - overflow[-1][0]
            overflow.append((log_ts, float(cfg['max_volume_l'] / 6)))
            overflow.append((log_ts, 0))
    if len(overflow) > 0:
        overflow.append((last_stored_ts, overflow[-1][1]))
    return overflow, total_open_s
