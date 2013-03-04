#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is grid implementation, in order
to provide geographical indexation features.

    >>> a = GeoGrid(radius=20)
    Setting grid precision to 4, avg radius to 20km
    >>> a.add('ORY', (48.72, 2.359))
    >>> a.add('CDG', (48.75, 2.361))
    >>> list(a._findInAdjacentCases(encode(48.72, 2.359, a.precision), N=2))
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
"""


from __future__ import with_statement

import itertools
import heapq
from geohash import encode, neighbors

from .GeoUtils import haversine


# Max recursion when iterating on frontiers
MAX_RECURSIVE_FRONTIER = 5000

# Thanks wikipedia
# hash length | lat bits | lng bits | lat error | lng error | km error
HASH_TO_ERROR = {
    1 : (2,  3,  23,       23,      2500),
    2 : (5,  5,  2.8,      5.6,     630),
    3 : (7,  8,  0.70,     0.7,     78),
    4 : (10, 10, 0.087,    0.18,    20),
    5 : (12, 13, 0.022,    0.022,   2.4),
    6 : (15, 15, 0.0027,   0.0055,  0.61),
    7 : (17, 18, 0.00068,  0.00068, 0.076),
    8 : (20, 20, 0.000085, 0.00017, 0.019)
}


class GeoGrid(object):
    """
    This is the main and only class.
    """
    def __init__(self, radius=None, precision=5, verbose=True):
        """Creates grid.

        :param radius:    the grid accuracy, in kilometers. If ``None``, \
                the ``precision`` parameter is used to define grid size
        :param precision: the hash length. This is only used if ``radius`` \
                is ``None``, otherwise this parameter (a hash length) is \
                computed from the radius
        :param verbose:   toggle verbosity
        :returns:         None
        """
        # True is considered an int but we do not want that
        if radius is True or \
           (radius is not None and not isinstance(radius, (float, int))):
            raise ValueError('radius should be float, int or None, was "%s"' % str(radius))

        if radius is not None:
            get_error = lambda x: (x[1][4] < radius,  abs(radius - x[1][4]))
            # Tricky, min of values only positive here
            precision = min(HASH_TO_ERROR.iteritems(), key=get_error)[0]

        self.radius    = radius
        self.precision = precision

        self._avg_radius = HASH_TO_ERROR[precision][4]

        # Double mapping
        self._keys = {}
        self._grid = {}

        if verbose:
            print 'Setting grid precision to %s, avg radius to %skm' % \
                    (precision, self._avg_radius)


    def _computeCaseId(self, lat_lng):
        """
        Computing the id the case for a (lat, lng).

        :param lat_lng: the lat_lng of the point (a tuple of (lat, lng))
        :returns:       the case_id
        """
        return encode(*lat_lng, precision=self.precision)



    def add(self, key, lat_lng, verbose=True):
        """
        Add a point to the grid.

        :param key:     the key to be added
        :param lat_lng: the lat_lng of the point (a tuple of (lat, lng))
        :param verbose: toggle verbosity
        :returns:       None
        """
        try:
            case_id = self._computeCaseId(lat_lng)

        except (TypeError, Exception):
            # TypeError for wrong type (NoneType, str)
            # Exception for invalid coordinates (raised by geohash module)
            if verbose:
                print 'Wrong coordinates %s for key %s, skipping point.' % \
                        (str(lat_lng), key)
            return

        self._keys[key] = {
            'case'    : case_id,
            'lat_lng' : lat_lng
        }

        if case_id not in self._grid:
            self._grid[case_id] = []

        self._grid[case_id].append(key)



    def _recursiveFrontier(self, case_id, N=1, stop=True):
        """
        Yield the successive frontiers from a case.
        A frontier is a set of case ids.
        """
        if stop is True:
            gen = xrange(N)
        else:
            gen = itertools.count()

        frontier = set([case_id])
        interior = frontier

        for i in gen:

            if i > MAX_RECURSIVE_FRONTIER:
                print '/!\ Recursion exceeded in recursiveFrontier'
                raise StopIteration

            yield frontier

            frontier = self._nextFrontier(frontier, interior)
            interior = interior | frontier


    @staticmethod
    def _nextFrontier(frontier, interior):
        """
        Compute next frontier from a frontier and a 
        matching interior.
        Interior is the set of case ids in the frontier.
        """
        return set([k for cid in frontier for k in neighbors(cid) if k not in interior])



    def _check_distance(self, candidate, ref_lat_lng, radius=None):
        """
        Filter from a iterator of candidates, the ones 
        who are within a radius if a ref_lat_lng.

        Yields the good ones.
        """
        if radius is not None:
            for can in candidate:
                dist = haversine(ref_lat_lng, self._keys[can]['lat_lng'])
                if dist <= radius:
                    yield (dist, can)
        else:
            for can in candidate:
                dist = haversine(ref_lat_lng, self._keys[can]['lat_lng'])
                yield (dist, can)


    def _allKeysInCases(self, cases):
        """
        Yields all keys in a iterable of case ids.
        """
        for case_id in cases:

            if case_id in self._grid:

                for key in self._grid[case_id]:
                    yield key


    def _findInAdjacentCases(self, case_id, N=1):
        """
        Find keys in adjacent cases from a case_id.
        Yields found keys.
        """
        for frontier in self._recursiveFrontier(case_id, N):

            for key in self._allKeysInCases(frontier):
                yield key


    def _findNearCase(self, case_id, radius=20):
        """
        Same as _findInAdjacentCases, but the limitation
        is given with a radius and not with a recursive limit
        in adjacency computation.
        """
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
        """
        Returns a list of nearby things from a point (given
        latidude and longitude), and a radius for the search.
        Note that the haversine function, which compute distance
        at the surface of a sphere, here returns kilometers,
        so the radius should be in kms.

        :param lat_lng:   the lat_lng of the point (a tuple ``(lat, lng)``)
        :param radius:    the radius of the search (kilometers)
        :param double_check: when using grid, perform an additional check on \
            results distance, this is useful because the grid is approximate, \
            so the results are only as accurate as the grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``
        """
        if lat_lng is None:
            # Case where the lat_lng was missing from base
            return iter([])

        candidate = self._findNearCase(case_id=self._computeCaseId(lat_lng),
                                       radius=radius)

        if double_check:
            return self._check_distance(candidate, lat_lng, radius)
        else:
            return ((0, can) for can in candidate)



    def findNearKey(self, key, radius=20, double_check=False):
        """
        Same as ``findNearPoint``, except the point is given
        not by a ``(lat, lng)``, but with its key, like ``'ORY'`` or ``'SFO'``.
        We just look up in the base to retrieve latitude and longitude, then
        call ``findNearPoint``.

        :param key:       the key of the thing (like ``'SFO'``)
        :param radius:    the radius of the search (kilometers)
        :param double_check: when using grid, perform an additional check on \
                results distance, this is useful because the grid is \
                approximate, so the results are only as accurate as the \
                grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``
        """
        if key not in self._keys:
            # Case where the key probably did not have a proper geocode
            # and as such was never indexed
            return iter([])

        candidate = self._findNearCase(case_id=self._keys[key]['case'],
                                       radius=radius)

        if double_check:
            return self._check_distance(candidate, self._keys[key]['lat_lng'], radius)
        else:
            return ((0, can) for can in candidate)



    def _findClosestFromCase(self, case_id, N=1, from_keys=None):
        """
        Find closest keys from a case.
        """
        found = set()

        for frontier in self._recursiveFrontier(case_id, stop=False):

            found = found | set(self._allKeysInCases(frontier))

            if from_keys is not None:
                # If from_keys is empty this will turn
                # into an infinite loop
                # stopped by MAX_RECURSIVE_FRONTIER
                # This should not happen since we treated that case
                # at the beginning
                found = found & from_keys

            # Heuristic
            # We have to compare the distance of the farthest found
            # against the distance really covered by the search
            #print frontier
            if len(found) >= N and len(frontier) > 1:
                break

        return found



    def findClosestFromPoint(self, lat_lng, N=1, double_check=False, from_keys=None):
        """
        Concept close to ``findNearPoint``, but here we do not
        look for the things radius-close to a point,
        we look for the closest thing from this point, given by
        latitude/longitude.

        :param lat_lng:   the lat_lng of the point (a tuple ``(lat, lng)``)
        :param N:         the N closest results wanted
        :param double_check: when using grid, perform an additional check on \
            results distance, this is useful because the grid is \
            approximate, so the results are only as accurate as the grid size
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform \
            ``findClosestFromPoint``. This is useful when we have names and \
            have to perform a matching based on name and location \
            (see ``fuzzyFindNearPoint``).
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``
        """
        if lat_lng is None:
            # Case where the lat_lng was missing from base
            return iter([])

        if from_keys is not None:
            # We convert to set before testing to nullity
            # because of empty iterators
            from_keys = set(from_keys)

            # If from_keys is empty, the result is obvious
            if not from_keys:
                return []

            # We cannot give what we do not have
            N = min(N, len(from_keys))

        # Some precaution for the number of wanted keys
        N = min(N, len(self._keys))

        # The case of the point is computed by _computeCaseId
        candidate = self._findClosestFromCase(case_id=self._computeCaseId(lat_lng),
                                              N=N,
                                              from_keys=from_keys)

        if double_check:
            return heapq.nsmallest(N, self._check_distance(candidate, lat_lng))
        else:
            return ((0, f) for f in candidate)


    def findClosestFromKey(self, key, N=1, double_check=False, from_keys=None):
        """
        Same as ``findClosestFromPoint``, except the point is given
        not by a ``(lat, lng)``, but with its key, like ``'ORY'`` or ``'SFO'``.
        We just look up in the base to retrieve latitude and longitude, then
        call ``findClosestFromPoint``.

        :param key:       the key of the thing (like ``'SFO'``)
        :param N:         the N closest results wanted
        :param double_check: when using grid, perform an additional check on \
                results distance, this is useful because the grid is \
                approximate, so the results are only as accurate as the \
                grid size
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform \
            ``findClosestFromKey``. This is useful when we have names and \
            have to perform a matching based on name and location \
            (see ``fuzzyFindNearPoint``).
        :returns:       an iterable of ``(distance, key)`` like \
        """
        if key not in self._keys:
            # Case where the key probably did not have a proper geocode
            # and as such was never indexed
            return iter([])

        if from_keys is not None:
            # We convert to set before testing to nullity
            # because of empty iterators
            from_keys = set(from_keys)

            # If from_keys is empty, the result is obvious
            if not from_keys:
                return []

            # We cannot give what we do not have
            N = min(N, len(from_keys))

        # Some precaution for the number of wanted keys
        N = min(N, len(self._keys))

        # The case of the point is just retrieved
        candidate = self._findClosestFromCase(case_id=self._keys[key]['case'],
                                              N=N,
                                              from_keys=from_keys)

        if double_check:
            return heapq.nsmallest(N, self._check_distance(candidate, self._keys[key]['lat_lng']))
        else:
            return ((0, f) for f in candidate)



def _test():
    """
    When called directly, launching doctests.
    """
    import doctest

    extraglobs = {}

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()

