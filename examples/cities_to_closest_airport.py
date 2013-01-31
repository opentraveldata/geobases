#!/usr/bin/python
# -*- coding: utf-8 -*-

from GeoBases import GeoBase

def to_float(string):
    try:
        val = float(string)
    except:
        val = 0
    return val

def main():

    g = GeoBase('ori_por', verbose=False)

    conditions_city = [
        ('location_type', 'CA'),
        ('location_type', 'C')
    ]

    for _, city_key in g.getKeysWhere(conditions_city, mode='or'):

        # Associated por for the city
        tvl_list = g.get(city_key, 'tvl_por_list')

        # (page_rank, code)
        pr = [(to_float(g.get(k, 'page_rank')), k) for k in tvl_list]
        pr.sort(reverse=True)

        print '%s^%s' % (g.get(city_key, 'iata_code'),
                         '/'.join('%.2f:%s' % t for t in pr))

if __name__ == '__main__':
    main()
