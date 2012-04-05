#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web

from SysUtils import addTopLevel, localToFile
addTopLevel(__file__, 1)

from GeoBaseModule import GeoBase

BASES = {
    'airports'     : GeoBase(data='airports'),
    'airports_csv' : GeoBase(data='airports_csv'),
    'stations'     : GeoBase(data='stations'),
    'stations_nls' : GeoBase(data='stations_nls'),
    'countries'    : GeoBase(data='countries')
}

BASES_WITH_GEOCODES = (
    'airports', 
    'airports_csv', 
    'stations'
)


class GetHandler(tornado.web.RequestHandler):

    def get(self, base, key):

        if base not in BASES:
            self.write("{'error' : 'Base not found'}")

        try:
            res = BASES[base].get(key)
        except:
            self.write("{'error' : 'Key not found'}")
        else:
            self.write(res)



if __name__ == "__main__":

    application = tornado.web.Application([
        (r"/(.*)/(.*)", GetHandler)
    ])

    application.listen(14003)
    tornado.ioloop.IOLoop.instance().start()

