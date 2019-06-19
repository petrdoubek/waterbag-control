import json
import logging
import mysql.connector

from .jawsdb import JawsDB
from .waterbag import insert_command

CONFIG = dict(
    max_height_mm = 600,    # maximum allowed waterbag height (or water level in water tank)
    max_volume_l = 3000,    # volume at max_height_mm
    flat_width_mm = 2000,   # width of flat waterbag, used for 'oval' volume approximation
    roof_area_m2 = 55,      # area from which rain water is collected, used in connection with precipitation forecast
    volume_method = 'oval', # approximation method
    city = 'pardubice,cz'
)

HTML_START = '<html><body style="font-family:arial;">'
HTML_END = '</body></html>'


def handle_get(cfg, url, params, wfile):
    db = JawsDB()
    rsp = ""

    logging.info('chart.handle_get urlparse:%s; parse_qs: %s' % (url, params))

    if any(value is not None for value in params.values()):
        rsp = update_config(cfg, db, params)
    else:
        rsp = html_table_config(cfg, db)

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def update_config(cfg, db, params):
    """update existing parameters with new values, insert new ones (assume they are sensor config, not server)
       TODO delete feature"""
    rsp = '<h1>Changed Parameters</h1>'
    global CONFIG
    sensor_config_current, _ = get_data(db)
    sensor_config_new = sensor_config_current.copy()
    sensor_changed, server_changed = False, False

    for key, value_list in params.items():
        value = value_list[0]
        if value != '':
            if key in CONFIG:
                CONFIG[key] = value
                server_changed = True
                rsp += '<li>server_config[%s] = %s\n' % (key, value)
            else:
                sensor_config_new[key] = value
                rsp += '<li>sensor_config[%s] = %s\n' % (key, value)
                sensor_changed = True

    if sensor_changed:
        cmd = json.dumps(sensor_config_new, separators=(',', ':'))
        rsp += '<p>Inserting sensor config:</p><pre>%s</pre><p>The config will be read next time the sensor connects.</p>' % cmd
        if insert_command(db, cmd):
            rsp += '<p>Insert OK</p>'
        else:
            rsp += '<p>Insert FAILED</p>'
    if server_changed:
        rsp += '<p><b>Server parameter(s) changed but they are not persisted in database.</b></p>\n'

    return HTML_START + rsp + '<p><a href="config">back to config</a></p>' + HTML_END


def html_table_config(cfg, db):
    """return table of parameters as a string, including form to enter new parameters"""
    sensor_config_current, sensor_config_new = get_data(db)

    html =  HTML_START + \
           '<form action="config">' \
           '<table cellpadding=2 border=1>' \
           '<tr><th>Parameter</th><th>Current value</th><th>Waiting value</th><th>Enter new value</th></tr>'

    params = { **cfg, **sensor_config_current }

    for key, value in params.items():
        html += ('<tr><td>%s</td><td align=right>%s</td><td align=right>%s</td><td><input type="text" name="%s"></td></tr>' %
                 (key, value, sensor_config_new.get(key, ''), key)
                 )

    return html + '<tr><td></td><td></td><td></td><td align=center><input type="submit" value="Submit"></td></tr>' \
                  '</table>' \
                  '</form>' + \
                  HTML_END


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
