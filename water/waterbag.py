import logging
import mysql.connector
import time
import urllib

import water.jawsdb


def handle_get(path, wfile):
    db = jawsdb.JawsDB()
    rsp = ""

    parsed_url = urllib.parse.urlparse(path)
    parsed_params = urllib.parse.parse_qs(parsed_url.query)
    logging.info('waterbag.handle_get path: %s; urlparse:%s; parse_qs: %s' % (path, parsed_url, parsed_params))
    if parsed_url.path.endswith('height'):
        if 'insert_mm' in parsed_params:
            height_mm = int(parsed_params['insert_mm'][0])
            logging.info('insert %dmm height into db' % height_mm)
            insert_height(db, height_mm)
            logging.info('done')
            rsp += 'OK'
        else:
            rsp += "<pre>\n" + read_height(db) + "</pre>\n"

    if rsp == "":
        rsp = "UNKNOWN REQUEST"

    # db.close() done automatically
    wfile.write(bytes(rsp, 'utf-8'))


def insert_height(db, height_mm):
    db.insert('height', 'time, mm', '%s, %s', (time.time(), height_mm))


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

def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = jawsdb.JawsDB()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_height':
            insert_height(db, sys.argv[2] if len(sys.argv) >= 3 else 123)
        if sys.argv[1] == 'create_height':
            db.create("CREATE TABLE height (time INT UNSIGNED NOT NULL, mm INT, PRIMARY KEY (time));")
        if sys.argv[1] == 'delete_height':
            if len(sys.argv) == 3 and sys.argv[2] == 'really_do':
                db.delete_all('height')
            else:
                print("please confirm deletion of table including all data: %s delete_height really_do" % sys.argv[0])

    print(read_height(db))


if __name__ == "__main__":
    main()
