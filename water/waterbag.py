import logging
import os
import mysql.connector
from mysql.connector import errorcode
import time
import urllib


def connect_db():
    db_config = dict(
        host="e7qyahb3d90mletd.chr7pe7iynqr.eu-west-1.rds.amazonaws.com",
        user="r4ciyc670gz7dvrk",
        passwd="mi2yo0or7qe982m5",
        database="kqmfr11rudkj9abl"
    )

    try:
        db = mysql.connector.connect(**db_config)
        logging.info("Database %s/%s connected" % (db_config['host'], db_config['database']))
        return db
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your database user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None


def handle_get(path, wfile):
    db = connect_db()
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

    db.close()
    wfile.write(bytes(rsp, 'utf-8'))


def insert_height(db, height_mm):
    cursor = db.cursor()
    cursor.execute("INSERT INTO height (time, mm) VALUES (%s, %s)", (time.time(), height_mm))
    db.commit()
    cursor.close()


def read_height(db):
    rsp = ""
    try:
        cursor = db.cursor()
        query = ("SELECT time, mm FROM height ORDER BY time desc")
        cursor.execute(query)
        for (timestamp, mm) in cursor:
            rsp += "  %s  %dmm\n" % (time.strftime("%x %X", time.localtime(timestamp)), mm)
        cursor.close()
    except mysql.connector.Error as err:
        rsp = err.msg
    return rsp


def create_table(db, table_def):
    cursor = db.cursor()
    try:
        print("Creating table: %s" % table_def)
        cursor.execute(table_def)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("  already exists.")
        else:
            print("  " + err.msg)
    else:
        print("  OK")
    cursor.close()


def delete_table(db, table):
    cursor = db.cursor()
    try:
        print("Deleting table: %s" % table)
        cursor.execute("DELETE FROM %s" % table)
        db.commit()
    except mysql.connector.Error as err:
        print("  " + err.msg)
    else:
        print("  OK")
    cursor.close()


def main():
    """if this module is run, connect to the database and print it out"""
    import sys
    db = connect_db()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'insert_height':
            insert_height(db, 123)
        if sys.argv[1] == 'create_height':
            create_table(db, "CREATE TABLE height (time INT UNSIGNED NOT NULL, mm INT, PRIMARY KEY (time));")
        if sys.argv[1] == 'delete_height':
            if len(sys.argv) == 3 and sys.argv[2] == 'really_do':
                delete_table(db, 'height')
            else:
                print("please confirm deletion of table including all data: %s delete_height really_do" % sys.argv[0])

    print(read_height(db))
    db.close()


if __name__ == "__main__":
    main()
