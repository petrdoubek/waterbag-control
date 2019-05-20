import logging
import mysql.connector
import time


MAX_VOLUME_L = 3000;
MAX_HEIGHT_MM = 600;
ROOF_AREA_M2 = 55;
#SENSOR_ABOVE_FLOOR_MM = 640;  # distance measured by sensor when the storage is empty

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
    else:
        rsp += "<pre>\n" + read_height(db) + "</pre>\n"

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    wfile.write(bytes(rsp, 'utf-8'))


def insert_height(db, height_mm):
    db.insert('height', 'time, mm', '%s, %s', (time.time(), height_mm)) #SENSOR_ABOVE_FLOOR_MM - height_mm))
    # TODO this logic should be in the sensor so that it can trigger sprinkler autonomously


def read_height(db):
    rsp = ""
    try:
        cursor = db.db.cursor()
        query = ("SELECT time, mm FROM height ORDER BY time desc")
        cursor.execute(query)
        for (timestamp, mm) in cursor:
            rsp += "  %s  %dmm\n" % (time.strftime("%x %X", time.localtime(timestamp)), mm)
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def volume_l(height_mm):
    """linear approximation, in reality the bag cut at low height resembles a rectangle and at high volume an ellipse;
       therefore the volume per mm is heigher at smaller height than at max height
       assumption is circumference is constant, that could be used for better approximation"""
    return height_mm * MAX_VOLUME_L / MAX_HEIGHT_MM;


def rain_l(rain_mm):
    """conversion from precipitation mm to liters of water harvested"""
    return rain_mm * ROOF_AREA_M2;


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_height':
            insert_height(db, int(sys.argv[2]) if len(sys.argv) >= 3 else 123)
        if sys.argv[1] == 'create_height':
            db.create("CREATE TABLE height (time INT UNSIGNED NOT NULL, mm INT, PRIMARY KEY (time));")
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
