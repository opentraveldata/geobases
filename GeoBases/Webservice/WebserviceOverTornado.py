#!/usr/bin/python
# -*- coding: utf-8 -*-

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from Webservice import app

if __name__ == '__main__':

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(14003)
    IOLoop.instance().start()

