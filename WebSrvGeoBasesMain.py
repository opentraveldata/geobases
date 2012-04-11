#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is an aggregator.
'''

from GeoBases.Webservice.Daemon import Daemon

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import sys


class MyDaemon(Daemon):

    def run(self):

        from GeoBases.Webservice.FlaskAppBuilder import app

        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(14003)
        IOLoop.instance().start()


def main():

    daemon = MyDaemon('/tmp/daemon-geob.pid')

    if len(sys.argv) != 2:
        print "Usage: %s {start|stop|restart|status}" % sys.argv[0]
        sys.exit(2)

    if 'start' == sys.argv[1]:
        daemon.start()

    elif 'stop' == sys.argv[1]:
        daemon.stop()

    elif 'restart' == sys.argv[1]:
        daemon.restart()

    elif 'status' == sys.argv[1]:
        daemon.status()

    else:
        print "Unknown command \"%s\"" % sys.argv[1]
        print "Usage: %s {start|stop|restart|status}" % sys.argv[0]
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":

    main()

