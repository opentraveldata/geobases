#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Webservice
'''

from JsonEncodeUtils import my_jsonify
from JsonPUtils import support_jsonp

from ..GeoBaseModule import GeoBase

from flask import Flask, request, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3ysdfsdR~XHH!jmN]LWX/,?RT'


VERBOSE = False

BASES = {
    'airports'     : GeoBase(data='airports',       verbose=VERBOSE),
    'airports_csv' : GeoBase(data='airports_csv',   verbose=VERBOSE),
    'stations'     : GeoBase(data='stations',       verbose=VERBOSE),
    'stations_nls' : GeoBase(data='stations_nls',   verbose=VERBOSE),
    'stations_uic' : GeoBase(data='stations_uic',   verbose=VERBOSE),
    'ori_por'      : GeoBase(data='ori_por',        verbose=VERBOSE),
    'countries'    : GeoBase(data='countries',      verbose=VERBOSE)
}

BASES_GEO_SUPPORT = set(k for k, g in BASES.items() if g.hasGeoSupport())



@app.route('/help', methods=['GET'])
@support_jsonp
def help():

    return jsonify({ 
        'bases'                 : BASES.keys(), 
        'methods'               : [
            '/help', 
            '/<base>/<key>',
            '/<base>/fuzzyGet?value=&N=',
            '/<base>/findNearPoint?lat=&lng=&radius=',
            '/<base>/findClosestFromPoint?lat=&lng=&N=',
            '/<base>/gridFindNearPoint?lat=&lng=&radius=',
            '/<base>/gridFindClosestFromPoint?lat=&lng=&N='
        ]
    })


@app.route('/<base>/<key>', methods=['GET'])
@support_jsonp
def get(base, key):

    if base not in BASES:
        return my_jsonify({'error' : 'Base not found'})

    try:
        res = BASES[base].get(key)
    except:
        return my_jsonify({'error' : 'Key not found'})
    else:
        return my_jsonify(res)


@app.route('/<base>/fuzzyGet', methods=['GET'])
@support_jsonp
def fuzzyGet(base):

    if base not in BASES:
        return my_jsonify({'error' : 'Base not found'})

    N = request.args.get('N', 10)
    N = 10 if not N else int(N)

    return my_jsonify({ 'root': BASES[base].fuzzyGet(request.args.get('value').encode('utf8'),
                                                     request.args.get('field', 'name'),
                                                     N)})


@app.route('/<base>/findNearPoint', methods=['GET'])
@support_jsonp
def findNearPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    radius = request.args.get('radius', 50)
    radius = 50 if not radius else float(radius)

    return my_jsonify({ 'root' : sorted(BASES[base].findNearPoint(float(request.args.get('lat')),
                                                                  float(request.args.get('lng')),
                                                                  radius))})


@app.route('/<base>/findClosestFromPoint', methods=['GET'])
@support_jsonp
def findClosestFromPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    N = request.args.get('N', 10)
    N = 10 if not N else int(N)

    return my_jsonify({ 'root' : BASES[base].findClosestFromPoint(float(request.args.get('lat')),
                                                                  float(request.args.get('lng')),
                                                                  N)})

@app.route('/<base>/gridFindNearPoint', methods=['GET'])
@support_jsonp
def gridFindNearPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    radius = request.args.get('radius', 50)
    radius = 50 if not radius else float(radius)

    return my_jsonify({ 'root' : sorted(BASES[base].gridFindNearPoint(float(request.args.get('lat')),
                                                                      float(request.args.get('lng')),
                                                                      radius))})


@app.route('/<base>/gridFindClosestFromPoint', methods=['GET'])
@support_jsonp
def gridFindClosestFromPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    N = request.args.get('N', 10)
    N = 10 if not N else int(N)

    return my_jsonify({ 'root' : BASES[base].gridFindClosestFromPoint(float(request.args.get('lat')),
                                                                      float(request.args.get('lng')),
                                                                      N)})


def _test():
    '''
    Launch doctests
    '''
    import doctest
    doctest.testmod()



if __name__ == '__main__':

    _test()

    #app.run(host='0.0.0.0', debug=True, port=14003)

