import logging
import math
import mysql.connector
import time


MAX_VOLUME_L = 3000
FLAT_WIDTH_MM = 2000  # width of flat waterbag, used for 'oval' volume approximation
MAX_HEIGHT_MM = 600
ROOF_AREA_M2 = 55
VOLUME_METHOD = 'oval'


def handle_get(url, params, wfile):
    db = JawsDB()
    rsp = ""

    logging.info('waterbag.handle_get urlparse:%s; parse_qs: %s' % (url, params))
    if 'insert_mm' in params:
        height_mm = int(params['insert_mm'][0])
        logging.info('insert %dmm height into db' % height_mm)
        insert_height(db, height_mm)
        logging.info('done')
        rsp += 'OK'
    elif 'insert_log' in params:
        msg = params['insert_log'][0]
        logging.info('insert log into db: %s' % msg)
        insert_log(db, msg)
        logging.info('done')
        rsp += 'OK'
    elif url.path.endswith('log'):
        rsp += "<pre>" + read_log(db) + "</pre>\n"
    elif url.path.endswith('command'):
        rsp += pop_command(db)
    else:
        rsp += "<pre>" + read_height(db) + "</pre>\n"

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def insert_height(db, height_mm):
    db.insert('height', 'time, mm', '%s, %s', (time.time(), height_mm))


def insert_log(db, msg):
    db.insert('log', 'time, msg', '%s, %s', (time.time(), msg))


def insert_command(db, cmd):
    db.insert('command', 'time, cmd, popped', '%s, %s, %s', (time.time(), cmd, 'N'))


def read_height(db):
    """return list of heights in pre-tags"""
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT time, mm FROM height ORDER BY time desc")
        cursor.execute(query)
        last = -1
        repeated = 0
        for (timestamp, mm) in cursor:
            if abs(mm-last) > 0:
                if repeated > 1:
                    rsp += "  (%dx)" % repeated
                rsp += "\n%s  %dmm" % (time.strftime("%a %d.%m. %X", time.localtime(timestamp)), mm)
                last = mm
                repeated = 1
            else:
                repeated += 1
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def read_log(db):
    """return list of heights in pre-tags"""
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT time, msg FROM log ORDER BY time desc")
        cursor.execute(query)
        for (timestamp, msg) in cursor:
            rsp += "\n%s  %s" % (time.strftime("%a %d.%m. %X", time.localtime(timestamp)), msg)
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def pop_command(db):
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = "SELECT time, cmd FROM command WHERE popped='N' ORDER BY time asc LIMIT 1"
        cursor.execute(query)

        for (timestamp, cmd) in cursor:
            rsp += cmd
            cursor.close()
            cursor2 = db.db.cursor()
            update = ("UPDATE command SET popped = 'Y' WHERE time = %d AND cmd = '%s' AND popped = 'N'"
                     % (timestamp, cmd))
            cursor2.execute(update)
            cursor2.close()
            db.db.commit()
            break  # only one command will be sent, client will ask for next one when ready

    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def waterbag_cut_mm2(height_mm, flat_width_mm):
    """approximate area of waterbag cut: assume constant circumference (2*flat_width)
    and shape of half-circle at either side (total one circle with r=height_mm/2 with rectangle between them"""
    r_mm = height_mm / 2
    return math.pi * pow(r_mm, 2) + height_mm * (flat_width_mm - math.pi * r_mm)


def volume_l(height_mm):
    """linear approximation will work for tanks with constant horizontal area
       oval is approximation for bag which gets rounder with increasing height"""
    if VOLUME_METHOD == 'linear':
        return height_mm * MAX_VOLUME_L / MAX_HEIGHT_MM
    elif VOLUME_METHOD == 'oval':
        return waterbag_cut_mm2(height_mm, FLAT_WIDTH_MM) * MAX_VOLUME_L / waterbag_cut_mm2(MAX_HEIGHT_MM, FLAT_WIDTH_MM)


def rain_l(rain_mm):
    """conversion from precipitation mm to liters of water harvested"""
    return rain_mm * ROOF_AREA_M2


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_height':
            insert_height(db, int(sys.argv[2]) if len(sys.argv) >= 3 else 123)
        if sys.argv[1] == 'read_log':
            print(read_log(db))
            return
        if sys.argv[1] == 'insert_log':
            insert_log(db, sys.argv[2] if len(sys.argv) >= 3 else "testing message")
            return
        if sys.argv[1] == 'pop_command':
            print(pop_command(db))
            return
        if sys.argv[1] == 'insert_command':
            insert_command(db, sys.argv[2] if len(sys.argv) >= 3 else "testing command")
            return
        if sys.argv[1] == 'create_height':
            db.create("CREATE TABLE height (time INT UNSIGNED NOT NULL, mm INT, PRIMARY KEY (time));")
            return
        if sys.argv[1] == 'create_log':
            db.create("CREATE TABLE log (time INT UNSIGNED NOT NULL, msg VARCHAR(1024));")
            return
        if sys.argv[1] == 'create_command':
            db.create("CREATE TABLE command (time INT UNSIGNED NOT NULL, cmd VARCHAR(1024), popped ENUM('Y','N'));")
            return
        if sys.argv[1] == 'delete_height':
            if len(sys.argv) == 3 and sys.argv[2] == 'really_do':
                db.delete_all('height')
            else:
                print("please confirm deletion of table including all data: %s delete_height really_do" % sys.argv[0])

    print(read_height(db))


if __name__ == "__main__":
    from jawsdb import JawsDB
    main()
else:
    from .jawsdb import JawsDB
