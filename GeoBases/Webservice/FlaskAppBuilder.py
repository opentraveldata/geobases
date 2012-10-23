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
app.secret_key = '2334583067*&^&*(^4523094ys]LWX/,?RT'


VERBOSE = False

BASES = dict( 
    (base, GeoBase(data=base, verbose=VERBOSE)) 
    for base in GeoBase.BASES
) 

BASES_GEO_SUPPORT = set(k for k, g in BASES.items() if g.hasGeoSupport())



@app.route('/help', methods=['GET'])
@support_jsonp
def help():

    return jsonify({ 
        'bases'                 : BASES.keys(), 
        'methods'               : [
            '/help', 
            '/<base>/<key>',
            '/<base>/trepGet?value=',
            '/<base>/fuzzyGet?value=&N=&L=',
            '/<base>/findNearPoint?lat=&lng=&radius=',
            '/<base>/findClosestFromPoint?lat=&lng=&N='
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

    L = request.args.get('L', 0.80)
    L = 0.80 if not L else float(L)

    return my_jsonify({ 'root': list(BASES[base].fuzzyGet(request.args.get('value').encode('utf8'),
                                                          request.args.get('field', 'name'),
                                                          approximate=N,
                                                          min_match=L))})


@app.route('/<base>/trepGet', methods=['GET'])
@support_jsonp
def trepGet(base):

    if base not in BASES:
        return my_jsonify({'error' : 'Base not found'})

    if not BASES[base].hasTrepSupport():
        return my_jsonify({'error' : 'No opentrep support'})

    return my_jsonify({ 'root': list(BASES[base].trepGet(request.args.get('value').encode('utf8'))) })


@app.route('/<base>/findNearPoint', methods=['GET'])
@support_jsonp
def findNearPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    radius = request.args.get('radius', 50)
    radius = 50 if not radius else float(radius)

    return my_jsonify({ 'root' : sorted(BASES[base].findNearPoint((float(request.args.get('lat')), float(request.args.get('lng'))),
                                                                  radius))})


@app.route('/<base>/findClosestFromPoint', methods=['GET'])
@support_jsonp
def findClosestFromPoint(base):

    if base not in BASES_GEO_SUPPORT:
        return jsonify({'error' : 'Base does not support geocodes'})

    N = request.args.get('N', 10)
    N = 10 if not N else int(N)

    return my_jsonify({ 'root' : list(BASES[base].findClosestFromPoint((float(request.args.get('lat')), float(request.args.get('lng'))),
                                                                       N))})



def _test():
    '''
    Launch doctests
    '''
    import doctest
    doctest.testmod()



if __name__ == '__main__':

    _test()

    #app.run(host='0.0.0.0', debug=True, port=14003)

