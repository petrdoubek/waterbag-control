"""Robot for purchasing loan participations on zonky.cz"""

import logging
import threading
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib

import water.waterbag
import water.openweather
import water.chart
import water.config
import water.environment
import water.dryingfan

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='%(funcName)-20s %(message)s')

CFG = None


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CFG

        logging.info('web server gets request: %s' % self.path)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        parsed_url = urllib.parse.urlparse(self.path)
        parsed_params = urllib.parse.parse_qs(parsed_url.query)

        if parsed_url.path.startswith('/waterbag'):
            water.waterbag.handle_get(parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/forecast'):
            water.openweather.handle_get(CFG, parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/chart') or parsed_url.path == '/':
            water.chart.handle_get(CFG, parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/config'):
            water.config.handle_get(CFG, parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/environment'):
            water.environment.handle_get(parsed_url, parsed_params, self.wfile)
        elif parsed_url.path.startswith('/dryingfan'):
            water.dryingfan.handle_get(parsed_url, parsed_params, self.wfile)
        else:
            self.wfile.write(bytes("UNKNOWN REQUEST", 'utf-8'))


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
    CFG = water.config.CONFIG

    thr_web = new_daemon(Web(CFG))
    thr_web.join()
    logging.info("threads joined, shutting down")


run_threads()
