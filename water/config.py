import json
import logging
import mysql.connector


def handle_get(url, params, wfile):
    db = JawsDB()
    rsp = ""

    logging.info('chart.handle_get urlparse:%s; parse_qs: %s' % (url, params))

    if any(value is not None for value in params.values()):
        rsp = "UPDATE OF PARAMETERS NOT IMPLEMENTED"
    else:
        rsp = table_parameters(db)

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def table_parameters(db):
    """return table of parameters as a string, including form to enter new parameters"""
    sensor_config_current, sensor_config_new = get_data(db)

    html = '<html>' \
           '<body style="font-family:arial;">' \
           '<form action="config">' \
           '<table cellpadding=2 border=1>' \
           '<tr><th>Parameter</th><th>Current value</th><th>Waiting value</th><th>Enter new value</th></tr>'

    params = { 'roof_area_m2': ROOF_AREA_M2, 'city': CITY, **sensor_config_current }

    for key, value in params.items():
        html += ('<tr><td>%s</td><td align=right>%s</td><td align=right>%s</td><td><input type="text" name="%s"></td></tr>' %
                 (key, value, getattr(sensor_config_new, key, ''), key)
                 )

    return html + '<tr><td></td><td></td><td></td><td align=center><input type="submit" value="Submit"></td></tr>' \
                  '</table>' \
                  '</form>' \
                  '</body>' \
                  '</html>'


def get_data(db):
    """returns:
       - current configuration of the sensor
       - new configuration not yet read by the sensor"""
    try:
        cursor = db.db.cursor()
        sensor_config_current, sensor_config_new = read_sensor_config(cursor)
        cursor.close()
        return (sensor_config_current, sensor_config_new)
    except mysql.connector.Error as err:
        return err.msg


def read_sensor_config(cursor):
    cfg_current, cfg_new = dict(), dict()

    cursor.execute("SELECT time, cmd FROM command "
                   " WHERE popped='Y'"
                   "   AND cmd LIKE '{%%}'"
                   " ORDER BY time desc LIMIT 1")
    for (cmd_ts, cmd) in cursor:
         cfg_current = json.loads(cmd)

    cursor.execute("SELECT time, cmd FROM command "
                   " WHERE popped='N'"
                   "   AND cmd LIKE '{%%}'"
                   " ORDER BY time desc LIMIT 1")
    for (cmd_ts, cmd) in cursor:
         cfg_new = json.loads(cmd)

    return cfg_current, cfg_new


def main():
    """if this module is run, connect to the database and print out the chart"""
    db = JawsDB()
    print(table_parameters(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    from waterbag import MAX_VOLUME_L, ROOF_AREA_M2
    from openweather import CITY
    main()
else:
    from .jawsdb import JawsDB
    from .waterbag import MAX_VOLUME_L, ROOF_AREA_M2
    from .openweather import CITY