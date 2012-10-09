#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is grid implementation, in order
to provide geographical indexation features.

    >>> a = GeoGrid(radius=20)
    Setting grid precision to 4, avg radius to 20km
    >>> a.add('ORY', (48.72, 2.359))
    >>> a.add('CDG', (48.75, 2.361))
    >>> list(a._findInAdjacentCases(encode(48.72, 2.359, a._precision), N=2))
    ['ORY', 'CDG']
    >>> a._keys['ORY']
    {'case': 'u09t', 'lat_lng': (48.7..., 2.359)}
    >>> neighbors('t0db')
    ['t0d8', 't0e0', 't06z', 't06x', 't07p', 't0dc', 't0d9', 't0e1']
    >>> list(a._recursiveFrontier('t0dbr', N=2))
    [set(['t0dbr']), set(['t0e08', 't0e00', 't0dbn', 't0e02', 't0dbq', 't0dbp', 't0dbw', 't0dbx'])]
    >>> list(a._recursiveFrontier('t0dbr', N=1))
    [set(['t0dbr'])]
    >>> sum(len(f) for f in a._recursiveFrontier('t0dbr', N=2))
    9
    >>> sum(len(f) for f in a._recursiveFrontier('t0dbr', N=3))
    25
    >>> sum(len(f) for f in a._recursiveFrontier('t0dbr', N=4))
    49
    >>> sum(len(f) for f in a._recursiveFrontier('t0dbr', N=5))
    81
    >>> list(a.findNearKey('ORY', 20))
    [(0, 'ORY'), (0, 'CDG')]
    >>> list(a.findNearKey('ORY', 20, double_check=True))
    [(0.0, 'ORY'), (3.33..., 'CDG')]
    >>> list(a.findClosestFromPoint((48.75, 2.361), N=2, double_check=True))
    [(0.0, 'CDG'), (3.33..., 'ORY')]
'''


from __future__ import with_statement

import itertools
from geohash import encode, neighbors

from .GeoUtils import haversine


# Max recursion when iterating on frontiers
RECURSIVE_FRONTIER_LIMIT = 5000


class GeoGrid(object):
    '''
    This is the main and only class.
    '''

    def __init__(self, precision=5, radius=None, verbose=True):

        # Thanks wikipedia
        # hash length | lat bits | lng bits | lat error | lng error | km error
        precision_to_errors = {
            1 : (2,  3,  23,       23,      2500),
            2 : (5,  5,  2.8,      5.6,     630),
            3 : (7,  8,  0.70,     0.7,     78),
            4 : (10, 10, 0.087,    0.18,    20),
            5 : (12, 13, 0.022,    0.022,   2.4),
            6 : (15, 15, 0.0027,   0.0055,  0.61),
            7 : (17, 18, 0.00068,  0.00068, 0.076),
            8 : (20, 20, 0.000085, 0.00017, 0.019)
        }

        if radius is not None:

            # Tricky, min of values only positive here
            precision = min(precision_to_errors.iteritems(),
                            key=lambda x: (x[1][4] < radius,  abs(radius - x[1][4])))[0]

        self._precision  = precision
        self._avg_radius = precision_to_errors[precision][4]

        # Double mapping
        self._keys = {}
        self._grid = {}

        if verbose:
            print 'Setting grid precision to %s, avg radius to %skm' % (precision, self._avg_radius)


    def _computeCaseId(self, lat_lng):

        return encode(*lat_lng, precision=self._precision)



    def add(self, key, lat_lng, verbose=True):

        try:
            case_id = self._computeCaseId(lat_lng)
        except:
            if verbose:
                print 'Wrong coordinates %s for key %s, skipping point.' % (str(lat_lng), key)
            return

        self._keys[key] = {
            'case'    : case_id,
            'lat_lng' : lat_lng
        }

        if case_id not in self._grid:
            self._grid[case_id] = []

        self._grid[case_id].append(key)



    def _recursiveFrontier(self, case_id, N=1, stop=True):

        if stop is True:
            gen = xrange(N)
        else:
            gen = itertools.count()

        frontier = set([case_id])
        interior = frontier

        for i in gen:

            if i > RECURSIVE_FRONTIER_LIMIT:
                print '/!\ Recursion exceeded in recursiveFrontier'
                raise StopIteration

            yield frontier

            frontier = self._nextFrontier(frontier, interior)
            interior = interior | frontier



    def _nextFrontier(self, frontier, interior):

        return  set([k for id in frontier for k in neighbors(id) if k not in interior])



    def _check_distance(self, candidate, ref_lat_lng, radius):

        for can in candidate:

            dist = haversine(ref_lat_lng, self._keys[can]['lat_lng'])

            if dist <= radius:
                yield (dist, can)


    def _allKeysInCases(self, cases):

        for case_id in cases:

            if case_id in self._grid:

                for key in self._grid[case_id]:
                    yield key


    def _findInAdjacentCases(self, case_id, N=1):

        for frontier in self._recursiveFrontier(case_id, N):

            for key in self._allKeysInCases(frontier):
                yield key


    def _findNearCase(self, case_id, radius=20):

        # Do your homework :D
        # A more accurate formula would be with
        # self._avg_radius = min(r1, r2) where r1 are r2 are
        # the size of one case
        if float(radius) == self._avg_radius:
            N = 2
        else:
            N = int(float(radius) / self._avg_radius) + 2

        return self._findInAdjacentCases(case_id, N)



    def findNearPoint(self, lat_lng, radius=20, double_check=False):

        candidate = self._findNearCase(self._computeCaseId(lat_lng), radius)

        if double_check:
            return self._check_distance(candidate, lat_lng, radius)
        else:
            return ((0, can) for can in candidate)



    def findNearKey(self, key, radius=20, double_check=False):

        candidate = self._findNearCase(self._keys[key]['case'], radius)

        if double_check:
            return self._check_distance(candidate, self._keys[key]['lat_lng'], radius)
        else:
            return ((0, can) for can in candidate)



    def findClosestFromPoint(self, lat_lng, N=1, double_check=False, from_keys=None):

        if from_keys is not None:
            from_keys = set(from_keys)

        # Some precaution for the number of wanted keys
        N = min(N, len(self._keys))

        # The case of the point
        case_id = self._computeCaseId(lat_lng)

        found = set()

        for frontier in self._recursiveFrontier(case_id, stop=False):

            found = found | set(self._allKeysInCases(frontier))

            if from_keys:
                # If from_keys is empty we avoid
                # this step, otherwise infinite loop
                found = found & from_keys

            # Heuristic
            # We have to compare the distance of the farthest found
            # against the distance really covered by the search
            #print frontier
            if len(found) >= N and len(frontier) > 1:
                break

        if double_check:
            return sorted(self._check_distance(found, lat_lng, radius=float('inf')))[:N]
        else:
            return ((0, f) for f in found)




def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    extraglobs = {}

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()



