import logging
import mysql.connector
from mysql.connector import errorcode
import os
import time


class JawsDB:

    def __init__(self):
        db_config = dict(
            host=os.environ['JAWSDB_HOST'],
            user=os.environ['JAWSDB_USER'],
            passwd=os.environ['JAWSDB_PASSWD'],
            database=os.environ['JAWSDB_DATABASE']
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
        """insert n-tuple or list of n-tuples"""
        if self.db is None:
            return False
        try:
            cursor = self.db.cursor()
            list_ntuples = args_ntuple if isinstance(args_ntuple, list) else [args_ntuple]
            for rec in list_ntuples:
                cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, attr_names_csv, attr_format_csv), rec)
            self.db.commit()
            cursor.close()
            return True
        except mysql.connector.Error as err:
            print("  " + err.msg)
            return False

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


def timeseries_csv(stored):
    stored_string = '[' + ','.join(["{t:%d,y:%d}" % (1000 * sec, l) for (sec, l) in stored]) + ']'
    return stored_string