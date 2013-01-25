#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is composed of several functions useful
for performing calculations on a sphere, such as distance or projections.
A part of them has been adapted from:
http://www.movable-type.co.uk/scripts/latlong.html

Functions frequently used by other modules:

- *haversine*: a function to compute the shortest path distance
  between two points on a sphere
- *prog_point*: a function to compute the localization of a point
  traveling on the shortest path between two points on a sphere,
  given a progression ratio (like 0%, 50% or 100%). This one uses
  a dichotomy, because so far I have an exact formula only for 50%
  (implemented in function *mid_point*)

Simple examples::

    >>> haversine((48.84, 2.367), (43.70, 7.26)) # Paris -> Nice
    683.85...
    >>> prog_point(48.84, 2.367, 35.5522, 139.7796, 0.001, accuracy=0.0001)
    (48.91..., 2.43...)
    >>> prog_point(48.84, 2.367, 35.5522, 139.7796, 1.0)
    (35.552..., 139.779...)

"""

from math import pi, cos, sin, acos, asin, tan, atan2, log, sqrt

# kms, mean radius
EARTH_RADIUS = 6371.0



def radian(a):
    """Degree to radian conversion.

    :param a: the input in degree
    :returns: the output in radian

    >>> radian(0)
    0.0
    >>> radian(180)
    3.14...
    """
    return float(a) / 180 * pi



def unradian(a):
    """Radian to degree conversion.

    :param a: the input in radian
    :returns: the output in degree

    >>> unradian(0)
    0.0
    >>> unradian(3.1415)
    179.9...
    """
    return float(a) * 180 / pi



def haversine(L0, L1):
    """
    As a matter of fact, it is easier for other
    libraries to just use two parameters.
    Exposing this function is more compliant with
    geohash signatures and getLocations() geobase function.

    :param L0: the LatLng tuple of the first point
    :param L1: the LatLng tuple of the second point
    :returns:    the distance in kilometers

    >>> haversine((48.84, 2.367), (43.70, 7.26)) # Paris -> Nice
    683.85...

    Case of unknown location.

    >>> haversine(None, (43.70, 7.26)) # returns None
    """
    if L0 is None or L1 is None:
        return None

    return haversine_precise(L0[0], L0[1], L1[0], L1[1])



def haversine_precise(lat0, lng0, lat1, lng1):
    """
    A function to compute the shortest path distance
    between two points on a sphere, using Haversine formula.

    :param lat0: the latitude of the first point
    :param lng0: the longitude of the first point
    :param lat1: the latitude of the second point
    :param lng1: the longitude of the second point
    :returns:    the distance in kilometers

    >>> haversine_precise(48.84, 2.367, 43.70, 7.26) # Paris -> Nice
    683.85...
    >>> haversine_precise(48.84, 2.367, 35.5522, 139.7796) # Paris -> Tokyo
    9730.22...
    """
    lat0 = radian(lat0)
    lat1 = radian(lat1)
    lng0 = radian(lng0)
    lng1 = radian(lng1)

    # Haversine
    return 2 * EARTH_RADIUS * asin(sqrt(
        sin(0.5 * (lat0 - lat1)) ** 2 +
        sin(0.5 * (lng0 - lng1)) ** 2 *
        cos(lat0) * cos(lat1)
    ))



def haversine_simple(lat0, lng0, lat1, lng1):
    """
    Another implementation of Haversine formula,
    but this one works well only for small amplitudes.

    :param lat0: the latitude of the first point
    :param lng0: the longitude of the first point
    :param lat1: the latitude of the second point
    :param lng1: the longitude of the second point
    :returns:    the distance in kilometers

    >>> haversine_simple(48.84, 2.367, 43.70, 7.26) # Paris -> Nice
    683.85...
    >>> haversine_simple(48.84, 2.367, 35.5522, 139.7796) # Paris -> Tokyo
    9730.22...
    """
    lat0 = radian(lat0)
    lat1 = radian(lat1)
    lng0 = radian(lng0)
    lng1 = radian(lng1)

    return EARTH_RADIUS * acos(
        sin(lat0) * sin(lat1) +
        cos(lat0) * cos(lat1) *
        cos(lng1 - lng0)
    )



def mid_point(lat0, lng0, lat1, lng1):
    """
    A function to compute the localization exactly in the middle of
    the shortest path between two points on a sphere.

    The given example provides the point between Paris and Tokyo.
    You can see the result at:
    http://maps.google.com/maps?f=q&hl=fr&ie=UTF8&ll=67.461,86.233&t=k&z=13
    It it somewhere in the North os Russia.

    :param lat0: the latitude of the first point
    :param lng0: the longitude of the first point
    :param lat1: the latitude of the second point
    :param lng1: the longitude of the second point
    :returns:    the position of the point in the middle

    >>> mid_point(48.84, 2.367, 35.5522, 139.7796) # Paris -> Tokyo
    (67.461..., 86.233...)
    """
    lat0 = radian(lat0)
    lat1 = radian(lat1)
    lng0 = radian(lng0)
    lng1 = radian(lng1)

    Bx = cos(lat1) * cos(lng1 - lng0)
    By = cos(lat1) * sin(lng1 - lng0)

    latm = atan2(
        sin(lat0) + sin(lat1),
        sqrt( (cos(lat0) + Bx)**2 + By**2)
    )

    lngm = lng0 + atan2(By, cos(lat0) + Bx)

    return unradian(latm), unradian(lngm)



def prog_point(lat0, lng0,
               lat1, lng1,
               progression=0.5,
               accuracy=0.005,
               verbose=False):
    """
    A function to compute the localization of a point
    traveling on the shortest path between two points on a sphere,
    given a progression ratio (like 0%, 50% or 100%).
    This one uses a dichotomy on mid_point.

    :param lat0:         the latitude of the first point
    :param lng0:         the longitude of the first point
    :param lat1:         the latitude of the second point
    :param lng1:         the longitude of the second point
    :param progression:  the progression of the traveler of the shortest path
    :param accuracy:     the accuracy of the dichotomy
    :param verbose:      display or not informations about the dichotomy
    :raises:             ValueError, if progression not in [0, 1]
    :returns:            the position of the progressing point

    >>> prog_point(48.84, 2.367, 35.5522, 139.7796, 0)
    (48.84..., 2.367...)
    >>> prog_point(48.84, 2.367, 35.5522, 139.7796,
    ...            progression=0.001,
    ...            accuracy=0.0001,
    ...            verbose=True)
    0.0000 < 0.0010 < 0.0020 in 10 steps
    (48.91..., 2.43...)
    >>> prog_point(48.84, 2.367, 35.5522, 139.7796, 0.5)
    (67.461..., 86.233...)
    >>> prog_point(48.84, 2.367, 35.5522, 139.7796, 1.0)
    (35.552..., 139.779...)
    """
    # We treat some obvious/moronic user input
    if progression > 1 or progression < 0:
        raise ValueError("Progression not in [0, 1]")

    if progression == 1:
        return lat1, lng1

    if progression == 0:
        return lat0, lng0

    i = 0
    progmin = 0
    progmax = 1

    while 1:
        # This is pretty much a standard dichotomy
        # We break when accuracy is sufficient
        i += 1

        latm, lngm = mid_point(lat0, lng0, lat1, lng1)

        progm = 0.5 * (progmin + progmax)

        if abs(progression - progm) <= accuracy:
            break

        if progression > progm:
            progmin = progm
            lat0, lng0 = latm, lngm

        else:
            progmax = progm
            lat1, lng1 = latm, lngm

    if verbose:
        print "%.4f < %.4f < %.4f in %s steps" % (progmin, progression, progmax, i)

    return latm, lngm



def mercator(lat, lng):
    """
    Returns Mercator projection

    :param lat: the latitude of the point
    :param lng: the longitude of the point
    :returns:   the projection

    >>> mercator(48.84, 2.367)
    (0.85..., 0.04...)
    """
    lat = radian(lat)
    lng = radian(lng)

    y = log(tan(0.25 * pi + 0.5 * lng))

    return lat, y



def _test():
    """
    When called directly, launching doctests.
    """
    import doctest
    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE)

    doctest.testmod(optionflags=opt)



if __name__ == '__main__':
    _test()

