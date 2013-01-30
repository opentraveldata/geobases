#!/usr/bin/python
# -*- coding: utf-8 -*-

from GeoBases import GeoBase

def main():
    '''
    '''
    g = GeoBase('ori_por', verbose=False)

    conditions_city = [
        ('location_type', 'CA'),
        ('location_type', 'C')
    ]

    conditions_airport_1 = [
        ('location_type', 'CA'),
        ('is_geonames',   'Y')
    ]
    conditions_airport_2 = [
        ('location_type', 'A'),
        ('is_geonames',   'Y')
    ]

    airports = list(g.getKeysWhere(conditions_airport_1, mode='and')) + \
               list(g.getKeysWhere(conditions_airport_2, mode='and'))

    for city_key in g.getKeysWhere(conditions_city, mode='or'):

        res = list(g.findClosestFromKey(city_key, from_keys=airports))

        if not res:
            # If geocoding problem for example
            continue

        dist, closest = res[0]

        print '%s^%s^%s' % (g.get(city_key, 'iata_code', default=''),
                            g.get(closest,  'iata_code', default=''),
                            dist)

if __name__ == '__main__':
    main()
