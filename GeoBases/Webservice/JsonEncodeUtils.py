#!/usr/bin/python
# -*- coding: utf-8 -*-


'''
This small module provides a way
to override flask current jsonify method.

    - not to mess with the order of the iterable
    - to be able to tune the decimal encoding

'''

from flask import Response

try:
    from simplejson import encoder, dumps
except ImportError:
    from json import encoder, dumps

# Two decimal character encoding
# This solution will not work with Python 2.7
# and its new json implementation
# Workarounds exist, but so far we have to move on
# and suppose we work under 2.6, and 2.7 is ok-ish.
encoder.FLOAT_REPR = lambda o: format(o, '.4f')
# Two effects: FIX the order problem of dumps regarding
# the Orderedict dumping
# AND seems to FIX the problem on Python 2.7 for decimal
encoder.c_make_encoder = None


def my_jsonify(data): 
    '''
    Custom jsonify function
    to support limit decimal encoding 
    and respect order of iterable.
    '''
    return Response(dumps(data), mimetype='application/json')


def _test():
    '''
    Launch doctests
    '''

    import doctest
    doctest.testmod()


if __name__ == '__main__':
    _test()



