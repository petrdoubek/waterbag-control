import logging
import mysql.connector
import time


def handle_get(url, params, wfile):
    db = JawsDB()
    offset_ms, temperature_C, humidity_pct = 0, None, None
    rsp = ""

    logging.info('waterbag.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    if 'insert_temperature' in params:
        temperature_C = float(params['insert_temperature'][0])
    if 'insert_humidity' in params:
        humidity_pct = int(params['insert_humidity'][0])
    if 'offset_ms' in params:
        offset_ms = int(params['offset_ms'][0])

    if len(params) == 0:
        rsp += "<pre>" + read_air(db) + "</pre>\n"
    elif temperature_C is not None or humidity_pct is not None:
        logging.info('insert temperature and/or humidity into db')
        insert_air(db, offset_ms, temperature_C, humidity_pct)
        logging.info('done')
        rsp += 'OK'

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def insert_air(db, offset_ms, temperature_c, humidity_pct):
    time_ms = time.time() + offset_ms

    if temperature_c is None and humidity_pct is not None:
        db.insert('air', 'time_ms, humidity_pct', '%s, %s', (time_ms, humidity_pct))
    elif temperature_c is not None and humidity_pct is None:
        db.insert('air', 'time_ms, temperature_c', '%s, %s', (time_ms, temperature_c))
    else:
        db.insert('air', 'time_ms, temperature_c, humidity_pct', '%s, %s, %s', (time_ms, temperature_c, humidity_pct))


def read_air(db):
    """return list of temperature and humidity measurements in pre-tags"""
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT time_ms, temperature_c, humidity_pct FROM air ORDER BY time_ms desc")
        cursor.execute(query)

        for (time_ms, temperature_c, humidity_pct) in cursor:
            rsp += "\n%s  %s  %s" % (time.strftime("%a %d.%m. %X", time.localtime(time_ms)),
                                          '%5.1fC' % temperature_c if temperature_c is not None else '  n/a ',
                                          '%3d%%' % humidity_pct if humidity_pct is not None else 'n/a ')

        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_air':
            insert_air(db, 0, int(sys.argv[2]) if len(sys.argv) >= 3 else 22, int(sys.argv[3]) if len(sys.argv) >= 4 else 55)
        if sys.argv[1] == 'create_air':
            db.create("CREATE TABLE air "
                      "(time_ms INT UNSIGNED NOT NULL, temperature_c FLOAT, humidity_pct INT, "
                      "PRIMARY KEY (time_ms));")
            return
        if sys.argv[1] == 'delete_air':
            if len(sys.argv) == 3 and sys.argv[2] == 'really_do':
                db.delete_all('air')
            else:
                print("please confirm deletion of table including all data: %s delete_air really_do" % sys.argv[0])

    print(read_air(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    main()
else:
    from .jawsdb import JawsDB
