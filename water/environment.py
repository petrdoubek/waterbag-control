import logging
import mysql.connector
import time


def handle_get(url, params, wfile):
    db = JawsDB()
    offset_ms, temperature_C, humidity_pct, moisture_res = 0, None, None, None
    rsp = ""

    logging.info('waterbag.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    if 'insert_temperature' in params:
        temperature_C = float(params['insert_temperature'][0])
    if 'insert_humidity' in params:
        humidity_pct = int(params['insert_humidity'][0])
    if 'insert_moisture' in params:
        moisture_res = int(params['insert_humidity'][0])
    if 'offset_ms' in params:
        offset_ms = int(params['offset_ms'][0])

    if len(params) == 0:
        rsp += "<pre>" + read_environment(db) + "</pre>\n"
    elif temperature_C is not None or humidity_pct is not None or moisture_res is not None:
        insert_environment(db, offset_ms, temperature_C, humidity_pct, moisture_res)
        rsp += 'OK'

    if rsp == "":
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


def read_environment(db):
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
                                          '%4d' % moisture_res if moisture_res is not None else ' n/a')

        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_environment':
            insert_environment(db, 0, int(sys.argv[2]) if len(sys.argv) >= 3 else 22, int(sys.argv[3]) if len(sys.argv) >= 4 else 55)
        if sys.argv[1] == 'create_environment':
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

    print(read_environment(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    main()
else:
    from .jawsdb import JawsDB
