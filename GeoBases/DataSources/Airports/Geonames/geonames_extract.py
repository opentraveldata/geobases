#!/usr/bin/python
# -*- coding: utf-8 -*-


'''
This module is a tool to extract
airport informations from geonames replicates
on ORI databases.
'''

from __future__ import with_statement

import MySQLdb
import sys
import os


def nextToFile(path):

    return os.path.join(os.path.realpath(os.path.dirname(__file__)), path)



if __name__ == '__main__':

    ### Airports.csv utils
    CODE = 0
    CITY = 4

    airport_to_city = {}

    with open(nextToFile('../AirportsDotCsv/airports.csv')) as f:

        for line in f:
            line = line.strip().split(',')
            try:
                airport_to_city[line[CODE]] = line[CITY]
            except IndexError:
                pass

    ### countries.csv utils
    COUNTRY_NAME = 0
    COUNTRY_CODE = 1

    country_to_name = {}

    with open(nextToFile('../../Countries/list_countries.csv')) as f:

        for line in f:
            line = line.strip().split('^')

            country_to_name[line[COUNTRY_CODE][0:2]] = line[COUNTRY_NAME]


    # Open a connexion to the database
    db = MySQLdb.connect(
        host = 'nceoridb01.nce.amadeus.net',
        user = 'fpujol',
        passwd = 'fpujol',
        db = 'geo_geonames'
    )

    cursor = db.cursor()

    req = ''' SELECT alternatenames, asciiname, latitude, longitude, country
              FROM geoname
              WHERE fcode = 'AIRP' '''

    db.query(req)
    r = db.store_result()

    ### geonames table utils
    CODE    = 0
    NAME    = 1
    LAT     = 2
    LNG     = 3
    COUNTRY = 4

    with open('airports_from_geonames.csv', 'w') as out:

        row = r.fetch_row()

        while row:
            # Everything is in a tuple it is WEIRD
            row = row[0]

            for code in row[CODE].split(','):

                if (len(code) == 3 and code.isupper()):

                    out.write('^'.join([code,
                                        row[NAME],
                                        airport_to_city.get(code, ''),
                                        row[COUNTRY],
                                        country_to_name.get(row[COUNTRY], ''),
                                        str(row[LAT]),
                                        str(row[LNG])]))
                    out.write('\n')
                    break

            row = r.fetch_row()

    db.close()
