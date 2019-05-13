"""Robot for purchasing loan participations on zonky.cz"""

import logging
import threading
import os
import sys
import pprint
import concurrent.futures
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib

import water.waterbag
import water.openweather

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='%(funcName)-20s %(message)s')

CFG = None


class Config:
    def __init__(self):
        pass


def info_text(cfg):
    safe = dict(cfg.__dict__)
    safe['TOKEN'] = 'yes' if safe['TOKEN'] is not None else 'no'
    return "<p>I'm here. Your web server for zonky robot.\n<pre>\n%s\n</pre>\n"\
           % pprint.pformat(safe, depth=2, width=120)


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CFG

        logging.info('web server gets request: %s' % self.path)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        parsed_url = urllib.parse.urlparse(self.path)
        parsed_params = urllib.parse.parse_qs(parsed_url.query)

        if parsed_url.path.startswith('/height'):
            water.waterbag.handle_get(parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/forecast'):
            water.openweather.handle_get(parsed_url, parsed_params, self.wfile)
        else:
            self.wfile.write(bytes("UNKNOWN REQUEST", 'utf-8'))

    def handle_as_future(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            logging.info("submitting future")
            future = executor.submit(water.waterbag.handle_get, self.path, self.wfile)
            logging.info("waiting for result")
            future.result(timeout=10)
            logging.info("result returned")


class Web(threading.Thread):
    def __init__(self, cfg):
        threading.Thread.__init__(self)
        self.ip = '127.0.0.1' if 'USER' in os.environ else '0.0.0.0'
        self.port = int(os.environ.get('PORT', 5000))
        self.do_run = True
        self.cfg = cfg

    def run(self):
        logging.info('starting web server at %s:%d ...' % (self.ip, self.port))
        httpd = HTTPServer((self.ip, self.port), RequestHandler)
        logging.info('running web server ...')
        while self.do_run:
            httpd.handle_request()


def new_daemon(dmn):
    thr = dmn
    thr.setDaemon(True)
    thr.start()
    return dmn


def run_threads():
    global CFG
    CFG = Config()

    thr_web = new_daemon(Web(CFG))
    thr_web.join()
    logging.info("threads joined, shutting down")


run_threads()
