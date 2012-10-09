#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is the main launcher for tests.
'''

import unittest
import doctest

import os
import sys

# PYTHON PATH MANAGEMENT
DIRNAME = os.path.dirname(__file__)
if DIRNAME == '':
    DIRNAME = '.'

DIRNAME = os.path.realpath(DIRNAME)
UPDIR   = os.path.split(DIRNAME)[0]

if UPDIR not in sys.path:
    sys.path.append(UPDIR)


import GeoBases.GeoBaseModule    as GeoM
import GeoBases.GeoGridModule    as GeoG
import GeoBases.GeoUtils         as GeoU
import GeoBases.LevenshteinUtils as GeoL


def test_suite():
    '''
    Create a test suite of all doctests.
    '''

    tests = unittest.TestSuite()

    # Standard options for DocTests
    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)


    globsGeo = {
        'geo_o'     : GeoM.GeoBase(data='ori_por',  verbose=False),
        'geo_a'     : GeoM.GeoBase(data='airports', verbose=False),
        'geo_t'     : GeoM.GeoBase(data='stations', verbose=False),
        'geo_m'     : GeoM.GeoBase(data='mix',      verbose=False)
    }


    tests.addTests(doctest.DocTestSuite(GeoM, optionflags=opt, extraglobs=globsGeo))
    tests.addTests(doctest.DocTestSuite(GeoG, optionflags=opt, extraglobs=globsGeo))
    tests.addTests(doctest.DocTestSuite(GeoU, optionflags=opt))
    tests.addTests(doctest.DocTestSuite(GeoL, optionflags=opt))


    return unittest.TestSuite(tests)


if __name__ == "__main__":

    # Verbosity is not available for some old unittest version
    #unittest.main(defaultTest='test_suite', verbosity=2)
    unittest.main(defaultTest='test_suite')

