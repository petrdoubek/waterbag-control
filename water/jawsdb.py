import logging
import mysql.connector
from mysql.connector import errorcode
import time


class JawsDB:

    def __init__(self):
        db_config = dict(
            host="e7qyahb3d90mletd.chr7pe7iynqr.eu-west-1.rds.amazonaws.com",
            user="r4ciyc670gz7dvrk",
            passwd="mi2yo0or7qe982m5",
            database="kqmfr11rudkj9abl"
        )

        try:
            self.db = mysql.connector.connect(**db_config)
            logging.info("Database %s/%s connected" % (db_config['host'], db_config['database']))
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your database user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
            self.db = None

    def __del__(self):
        if self.db is not None:
            print("Closing database")
            self.db.close()

    def create(self, table_def):
        cursor = self.db.cursor()
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

    def insert(self, table, attr_names_csv, attr_format_csv, args_ntuple):
        if self.db is None:
            return False
        cursor = self.db.cursor()
        cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, attr_names_csv, attr_format_csv), args_ntuple)
        self.db.commit()
        cursor.close()
        return True

    def delete_all(self, table):
        cursor = self.db.cursor()
        try:
            print("Deleting table: %s" % table)
            cursor.execute("DELETE FROM %s" % table)
            self.db.commit()
        except mysql.connector.Error as err:
            print("  " + err.msg)
        else:
            print("  OK")
        cursor.close()


def strtime(tm):
    return time.strftime("%x %X", time.localtime(tm))
