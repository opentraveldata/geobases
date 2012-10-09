#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is a general class *GeoBase* to manipulate geographical
data. It loads static csv files containing data about
airports or train stations, and then provides tools to browse it.


It relies on two other modules:

    - GeoUtils: to compute haversine distances between points
    - LevenshteinUtils: to calculate distances between strings. Indeed, we need
      a good tool to do it, in order to recognize things like station names
      in schedule files where we do not have the station id


Examples for airports::

    >>> geo_a = GeoBase(data='airports', verbose=False)
    >>> sorted(geo_a.findNearKey('ORY', 50)) # Orly, airports <= 50km
    [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
    >>> geo_a.get('CDG', 'city_code')
    'PAR'
    >>> geo_a.haversine('CDG', 'NCE')
    694.5162...


Examples for stations::

    >>> geo_t = GeoBase(data='stations', verbose=False)
    >>>
    >>> # Nice, stations <= 5km
    >>> [geo_t.get(k, 'name') for d, k in sorted(geo_t.findNearPoint((43.70, 7.26), 5))]
    ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch', 'Villefranche-sur-Mer', 'Nice-St-Augustin']
    >>>
    >>> geo_t.get('frpaz', 'name')
    'Paris-Austerlitz'
    >>> geo_t.haversine('frnic', 'frpaz')
    683.526...

From any point of reference:

    >>> geo = GeoBase(data='ori_por_multi')
    Import successful from ...
    Available info for things: ...
'''

from __future__ import with_statement

import heapq
import os
import yaml

from SysUtils         import localToFile

from .GeoUtils         import haversine
from .LevenshteinUtils import mod_leven, clean
from .GeoGridModule    import GeoGrid


class GeoBase(object):
    '''
    This is the main and only class. After __init__,
    a file is loaded in memory, and the user may use
    the instance to get information.
    '''

    PATH_CONF = localToFile(__file__, 'DataSources/Sources.yaml')

    BASES = yaml.load(open(PATH_CONF))


    @staticmethod
    def update():
        '''
        Launch update script on oripor data file.
        '''
        os.system('bash ' + localToFile(__file__, 'DataSources/Por/Ori/CheckOriPorUpdates.sh'))



    def __init__(self, data, source=None, headers=None, key_col=None, delimiter=None, verbose=True):
        '''Initialization

        :param data: the type of data wanted, 'airports', 'stations' \
            and 'mix' currently available. 'mix' will not load anything, \
            it is a way to get an empty object, which wille be fed later
        :param verbose: display informations or not during runtime

        :raises: ValueError, if data parameters is not recognized

        >>> geo_a = GeoBase(data='airports')
        Import successful from ...
        Available info for things: ...
        >>> geo_t = GeoBase(data='stations')
        Import successful from ...
        Available info for things: ...
        >>> geo_m = GeoBase(data='mix')
        Source was None, skipping loading...
        >>> geo_c = GeoBase(data='odd')
        Traceback (most recent call last):
        ValueError: Wrong data type. Not in ['airports', 'airports_csv', 'countries', 'stations', 'stations_nls', 'mix', 'feed']
        >>>
        >>> GeoBase(data='feed',
        ...         source=localToFile(__file__, 'DataSources/Airports/AirportsDotCsv/ORI_Simple_Airports_Database_Table.csv'),
        ...         headers=['code', 'ref_name', 'ref_name_2', 'name'],
        ...         key_col='code',
        ...         delimiter='^',
        ...         verbose=False).get('ORY')
        {'code': 'ORY', 'name': 'PARIS/FR:ORLY', 'ref_name_2': 'PARIS ORLY', 'ref_name': 'PARIS ORLY'}
        '''

        # Main structure in which everything will be loaded
        # Dictionary of dictionary
        self._things = {}
        self._ggrid  = None

        # A cache for the fuzzy searches
        self._cache_fuzzy = {}
        # An other cache if the algorithms are failing on a single
        # example, we first look in this cache
        self._bias_cache_fuzzy = {}

        # Parameters for data loading
        self._data      = data
        self._source    = source
        self._delimiter = delimiter
        self._key_col   = key_col
        self._headers   = headers
        self._verbose   = verbose


        if data in GeoBase.BASES:
            conf = GeoBase.BASES[data]

            if conf['local'] is True:
                self._source = localToFile(GeoBase.PATH_CONF, conf['source'])
            else:
                self._source = conf['source']

            self._key_col   = conf['key_col']
            self._delimiter = conf['delimiter']
            self._headers   = conf['headers']

        elif data == 'feed':
            # User input defining everything
            pass

        elif data == 'mix':
            # No loading, filling after by user input
            self._headers = [
                'code',
                'name',
                'lat',
                'lng'
            ]

        else:
            raise ValueError('Wrong data type. Not in %s' % GeoBase.BASES.keys())

        # Loading data
        self._loadFile()
        self.createGrid()



    def _loadFile(self):
        '''Load the file and feed the self._things.

        :param verbose: display informations or not during runtime
        :raises: IOError, if the source cannot be read
        :raises: ValueError, if duplicates are found in the source
        '''

        # Someone told me that this increases speed :)
        key_col = self._key_col
        lim     = self._delimiter
        headers = self._headers

        if self._source is None:
            if self._verbose:
                print 'Source was None, skipping loading...'
            return

        # It is possible to have a key_col which is a list
        # In this case we build the key as the concatenation between 
        # the different fields
        if isinstance(key_col, str):
            keyer = lambda row: row[headers.index(key_col)]

        elif isinstance(key_col, list):
            keyer = lambda row: lim.join(row[headers.index(k)] for k in key_col)
        else:
            raise ValueError("Inconsistent: key_col=%s, headers=%s" % (key_col, headers))


        with open(self._source) as f:

            for row in f:
                # Skip comments and empty lines
                if not row or row.startswith('#'):
                    continue

                # Stripping \t would cause bugs in tsv files
                row = row.strip(' \n\r').split(lim)
                key = keyer(row)

                # No duplicates ever
                if key in self._things:
                    if self._verbose:
                        print "/!\ %s already in base: %s" % (key, str(self._things[key]))

                #self._headers represents the meaning of each column.
                self._things[key] = {}

                for h, v in zip(headers, row):
                    if h is not None:
                        self._things[key][h] = v

            # We remove None headers, which are not-loaded-columns
            self._headers = [h for h in headers if h is not None]

        if self._verbose:
            print "Import successful from %s" % self._source
            print "Available info for things: %s" % self._headers



    def hasGeoSupport(self):
        '''
        Check if base has geocoding support.
        '''
        if 'lat' in self._headers and 'lng' in self._headers:
            return True

        return False



    def createGrid(self):
        '''
        Create the grid for geographical indexation after loading the data.
        '''

        if not self.hasGeoSupport():
            if self._verbose:
                print 'Not geocode support, skipping grid...'
            return

        self._ggrid = GeoGrid(radius=50, verbose=False)

        for key, lat_lng in self.iterLocations():

            if lat_lng is None:
                if self._verbose:
                    print 'No usable geocode for %s [%s,%s], skipping point...' % \
                            (key, self.get(key, 'lat'), self.get(key, 'lng'))
            else:
                self._ggrid.add(key, lat_lng, self._verbose)



    def get(self, key, field=None, default=None):
        '''
        Simple get on the database.
        This get function raise exception when input is not correct.

        :param key:   the key of the thing (like 'SFO')
        :param field: the field (like 'name' or 'lat')
        :raises:      KeyError, if the key is not in the base
        :returns:     the needed information

        >>> geo_a.get('CDG', 'city_code')
        'PAR'
        >>> geo_t.get('frnic', 'name')
        'Nice-Ville'
        >>> geo_t.get('frahah', 'name', default='default')
        'default'
        >>>
        >>> geo_t.get('frnic', 'not_a_field', default='default')
        Traceback (most recent call last):
        KeyError: "Field not_a_field not in ['code', 'lines', 'name', 'info', 'lat', 'lng', 'type']"
        >>> geo_t.get('frmoron', 'name')
        Traceback (most recent call last):
        KeyError: 'Thing not found: frmoron'
        '''

        try:
            if field is None:
                res = self._things[key]
            else:
                res = self._things[key][field]

        except KeyError:

            if key in self._things:
                raise KeyError("Field %s not in %s" % (field, self._headers))

            if default is not None:
                return default

            raise KeyError("Thing not found: %s" % str(key))

        else:
            return res



    def getLocation(self, key):
        '''
        Returns proper geocode.

        >>> geo_a.getLocation('AGN')
        (57.50..., -134.585...)
        '''
        try:
            loc = float(self.get(key, 'lat')), float(self.get(key, 'lng'))

        except ValueError:
            return None
        else:
            return loc



    def iterLocations(self):
        '''
        Returns all positions.

        :returns: a list of all (key, lat, lng) in the database

        >>> list(geo_a.iterLocations())
        [('AGN', (57.50..., -134.585...)), ('AGM', (65...
        '''
        return ( (key, self.getLocation(key)) for key in self._things )


    def getKeysWhere(self, field, value):
        '''
        Get iterator of all keys with particular
        field.
        For example, if you want to know all airports in Paris.

        :param field: the field to test
        :param value: the wanted value for the field
        :returns:     an iterator of matching keys

        >>> list(geo_a.getKeysWhere('city_code', 'PAR'))
        ['ORY', 'TNF', 'CDG', 'BVA']
        '''

        for key in self._things:

            if self.get(key, field) == value:

                yield key


    def __iter__(self):
        '''
        Returns iterator of all keys in the database.

        :returns: the list of all keys

        >>> list(a for a in geo_a)
        ['AGN', 'AGM', 'AGJ', 'AGH', ...
        '''
        return self._things.iterkeys()


    def __contains__(self, key):
        '''
        Test if a thing is in the base.

        :param key: the key of the thing to be tested
        :returns:   a boolean

        >>> 'AN' in geo_a
        False
        >>> 'AGN' in geo_a
        True
        '''
        if key in self._things:
            return True

        return False



    def keys(self):
        '''
        Returns a list of all keys in the database.

        :returns: the list of all keys

        >>> geo_a.keys()
        ['AGN', 'AGM', 'AGJ', 'AGH', ...
        '''
        return self._things.keys()


    def _build_distances(self, lat_lng_ref, keys):
        '''
        Compute the iterable of (dist, keys) of a reference
        lat_lng and a list of keys. Keys which have not valid
        geocodes will not appear in the results.

        >>> list(geo_a._build_distances((0,0), ['ORY', 'CDG']))
        [(5422.74..., 'ORY'), (5455.45..., 'CDG')]
        '''

        if lat_lng_ref is None:
            raise StopIteration

        for key in keys:

            lat_lng = self.getLocation(key)

            if lat_lng is not None:

                yield haversine(lat_lng_ref, lat_lng), key


    def findNearPoint(self, lat_lng, radius=50, from_keys=None, grid=True, double_check=True):
        '''
        Returns a list of nearby things from a point (given
        latidude and longitude), and a radius for the search.
        Note that the haversine function, which compute distance
        at the surface of a sphere, here returns kilometers,
        so the radius should be in kms.

        :param lat_lng: the lat_lng of the point
        :param radius:  the radius of the search (kilometers)
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance
        :returns:       an iterable of keys of things (like ['ORY', 'CDG'])

        >>> # Paris, airports <= 50km
        >>> [geo_a.get(k, 'name') for d, k in sorted(geo_a.findNearPoint((48.84, 2.367), 50))]
        ['Paris-Orly', 'Paris-Le Bourget', 'Toussus-le-Noble', 'Paris - Charles-de-Gaulle']
        >>>
        >>> # Nice, stations <= 5km
        >>> [geo_t.get(k, 'name') for d, k in sorted(geo_t.findNearPoint((43.70, 7.26), 5))]
        ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch', 'Villefranche-sur-Mer', 'Nice-St-Augustin']

        No grid mode.

        >>> # Paris, airports <= 50km
        >>> [geo_a.get(k, 'name') for d, k in sorted(geo_a.findNearPoint((48.84, 2.367), 50, grid=False))]
        ['Paris-Orly', 'Paris-Le Bourget', 'Toussus-le-Noble', 'Paris - Charles-de-Gaulle']
        >>> 
        >>> # Nice, stations <= 5km
        >>> [geo_t.get(k, 'name') for d, k in sorted(geo_t.findNearPoint((43.70, 7.26), 5, grid=False))]
        ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch', 'Villefranche-sur-Mer', 'Nice-St-Augustin']
        >>> 
        >>> # Paris, airports <= 50km with from_keys input list
        >>> sorted(geo_a.findNearPoint((48.84, 2.367), 50, from_keys=['ORY', 'CDG', 'BVE'], grid=False))
        [(12.76..., 'ORY'), (23.40..., 'CDG')]
        '''

        if from_keys is None:
            from_keys = iter(self)

        if grid:
            # Using grid, from_keys if just a post-filter
            from_keys = set(from_keys)

            for dist, thing in self._ggrid.findNearPoint(lat_lng, radius, double_check):

                if thing in from_keys:

                    yield (dist, thing)

        else:

            for dist, thing in self._build_distances(lat_lng, from_keys):

                if dist <= radius:

                    yield (dist, thing)




    def findNearKey(self, key, radius=50, from_keys=None, grid=True, double_check=True):
        '''
        Same as findNearPoint, except the point is given
        not by a lat/lng, but with its key, like ORY or SFO.
        We just look up in the base to retrieve lat/lng, and
        call findNearPoint.

        :param key:     the key of the point
        :param radius:  the radius of the search (kilometers)
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance
        :returns:       a list of keys of things (like ['ORY', 'CDG'])

        >>> sorted(geo_o.findNearKey('ORY', 10)) # Orly, por <= 10km
        [(0.0, 'ORY'), (1.82..., 'JDP'), (8.06..., 'XJY'), (9.95..., 'QFC')]
        >>> sorted(geo_a.findNearKey('ORY', 50)) # Orly, airports <= 50km
        [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
        >>> sorted(geo_t.findNearKey('frnic', 5)) # Nice station, stations <= 5km
        [(0.0, 'frnic'), (2.2..., 'fr4342'), (2.3..., 'fr5737'), (4.1..., 'fr4708'), (4.5..., 'fr6017')]

        No grid.

        >>> # Orly, airports <= 50km
        >>> sorted(geo_a.findNearKey('ORY', 50, grid=False))
        [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
        >>> 
        >>> # Nice station, stations <= 5km
        >>> sorted(geo_t.findNearKey('frnic', 5, grid=False))
        [(0.0, 'frnic'), (2.2..., 'fr4342'), (2.3..., 'fr5737'), (4.1..., 'fr4708'), (4.5..., 'fr6017')]
        >>> 
        >>> sorted(geo_a.findNearKey('ORY', 50, grid=False, from_keys=['ORY', 'CDG', 'SFO']))
        [(0.0, 'ORY'), (34.8..., 'CDG')]
        '''

        if from_keys is None:
            from_keys = iter(self)

        if grid:
            # Using grid, from_keys if just a post-filter
            from_keys = set(from_keys)

            for dist, thing in self._ggrid.findNearKey(key, radius, double_check):

                if thing in from_keys:

                    yield (dist, thing)

        else:

            for dist, thing in self.findNearPoint(self.getLocation(key), radius, from_keys, grid, double_check):

                yield (dist, thing)



    def findClosestFromPoint(self, lat_lng, N=1, from_keys=None, grid=True, double_check=True):
        '''
        Concept close to findNearPoint, but here we do not
        look for the things radius-close to a point,
        we look for the closest thing from this point, given by
        latitude/longitude.

        Note that a similar implementation is done in
        the LocalHelper, to find efficiently N closest point
        in a graph, from a point (using heaps).

        :param lat_lng:   the lat_lng of the point
        :param N:         the N closest results wanted
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform findClosestFromPoint. This is useful when we have names \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance
        :returns:   one key (like 'SFO'), or a list if approximate is not None

        >>> list(geo_a.findClosestFromPoint((43.70, 7.26))) # Nice
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), N=3)) # Nice
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=1)) # Nice
        [(0.56..., 'frnic')]
        >>>
        >>> #from datetime import datetime
        >>> #before = datetime.now()
        >>> #for _ in range(100): s = geo_a.findClosestFromPoint((43.70, 7.26), N=3)
        >>> #print datetime.now() - before

        No grid.

        >>> list(geo_o.findClosestFromPoint((43.70, 7.26), grid=False)) # Nice
        [(4.80..., 'III')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), grid=False)) # Nice
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), N=3, grid=False)) # Nice
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=1, grid=False)) # Nice
        [(0.56..., 'frnic')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=2, grid=False, from_keys=('frpaz', 'frply', 'frbve')))
        [(482.84..., 'frbve'), (683.89..., 'frpaz')]
        '''

        if from_keys is None:
            from_keys = iter(self)

        if grid:
            # Using grid, from_keys if just a post-filter
            from_keys = set(from_keys)

            for dist, thing in self._ggrid.findClosestFromPoint(lat_lng, N, double_check):

                if thing in from_keys:

                    yield (dist, thing)

        else:

            iterable = self._build_distances(lat_lng, from_keys)

            for dist, thing in heapq.nsmallest(N, iterable):

                yield (dist, thing)




    def fuzzyGet(self, fuzzy_value, field='name', approximate=None, from_keys=None):
        '''
        We get to the cool stuff.

        Fuzzy searches are retrieving an information
        on a thing when we do not know the code.
        We compare the value fuzzy_value which is supposed to be a field
        (e.g. a city or a name), to all things we have in the database,
        and we output the best match.
        Matching is performed using Levenshtein module, with a modified
        version of the Lenvenshtein ratio, adapted to the type of data.

        Example: we look up 'Marseille Saint Ch.' in our database
        and we find the corresponding code by comparing all station
        names with ''Marseille Saint Ch.''.

        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param approximate: if None, returns the best, if an int, returns a list of \
            n best matches
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform fuzzyGet. This is useful when we have geocodes \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :returns:           a couple with the best match and the distance found

        >>> geo_t.fuzzyGet('Marseille Charles', 'name')
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name')
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=3)
        [(0.78..., 'CDG'), (0.60..., 'HUX'), (0.57..., 'LBG')]

        Some corner cases. Here the first case raises en error, but in the second case,
        since we return lists, an empty list is returned.

        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=None, from_keys=[])
        Traceback (most recent call last):
        ValueError: Iterable was empty when performing max()
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=1, from_keys=[])
        []
        '''

        if from_keys is None:
            # iter(self), since __iter__ is defined is equivalent to
            # self._things.iterkeys()
            from_keys = iter(self)

        # All 'intelligence' is performed in the Levenshtein
        # module just here. All we do is minimize this distance
        iterable = ( (mod_leven(fuzzy_value, self.get(key, field)), key)
                     for key in from_keys )

        if approximate is None:
            try:
                res = max(iterable)
            except ValueError:
                # This exception is raised when
                # the iterable is empty
                raise ValueError('Iterable was empty when performing max()')
            else:
                return res

        return heapq.nlargest(approximate, iterable)



    def fuzzyGetAroundLatLng(self, lat_lng, radius, fuzzy_value, field='name', approximate=None, from_keys=None, grid=True, double_check=True):
        '''
        Same as fuzzyGet but with we search only within a radius
        from a geocode.

        :param lat_lng: the lat_lng of the point
        :param radius:  the radius of the search (kilometers)
        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param approximate: if None, returns the best, if an int, returns a list of \
            n best matches
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.

        >>> geo_a.fuzzyGet('Brussels', 'name', approximate=None)
        (0.61..., 'BQT')
        >>> geo_a.get('BQT', 'name')  # Brussels just matched on Brest!!
        'Brest'
        >>> geo_a.get('BRU', 'name') # We wanted BRU for 'Bruxelles'
        'Bruxelles National'
        >>> 
        >>> # Now a request limited to a circle of 20km around BRU gives BRU
        >>> geo_a.fuzzyGetAroundLatLng((50.9013890, 4.4844440), 20, 'Brussels', 'name')
        (0.46..., 'BRU')
        >>> 
        >>> # Now a request limited to some input keys
        >>> geo_a.fuzzyGetAroundLatLng((50.9013890, 4.4844440), 2000, 'Brussels', 'name', approximate=1, from_keys=['CDG', 'ORY'])
        [(0.33..., 'ORY')]
        '''

        if from_keys is None:
            from_keys = iter(self)

        nearest = ( key for dist, key in self.findNearPoint(lat_lng, radius, from_keys, grid, double_check) )

        return self.fuzzyGet(fuzzy_value, field, approximate, from_keys=nearest)


    def _fuzzyGetBiased(self, entry, verbose=True):
        '''
        Same as fuzzyGet but with bias system.
        '''

        if entry in self._bias_cache_fuzzy:
            # If the entry is stored is our bias
            # cache, we do not perform the fuzzy search
            # It avoids single failure on some rare examples
            if verbose:
                print 'Using bias: %s' % str(entry)

            return self._bias_cache_fuzzy[entry]

        # If not we process and store it in the cache
        return self.fuzzyGet(*entry)


    def fuzzyGetCached(self,
                        fuzzy_value,
                        field='name',
                        approximate=None,
                        verbose=True,
                        show_bad=(1, 1)):
        '''
        Same as fuzzyGet but with a caching and bias system.

        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param approximate: if None, returns the best, if an int, returns a list of \
            n best matches
        :param verbose:     display a certain range of similarity
        :param show_bad:    the range of similarity
        :returns:           the best match

        >>> geo_t.fuzzyGetCached('Marseille Saint Ch.', 'name')
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', show_bad=(0, 1))
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', approximate=2, show_bad=(0, 1))
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        [0.61]           paris+de+gaulle ->        bahias+de+huatulco (  HUX)
        [(0.78..., 'CDG'), (0.60..., 'HUX')]

        Some biasing:

        >>> geo_a.biasFuzzyCache('paris de gaulle', 'name', None, 'Biased result')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', approximate=None, show_bad=(0, 1)) # Cache there
        (0.78..., 'CDG')
        >>> geo_a.clearCache()
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', approximate=None)
        Using bias: ('paris+de+gaulle', 'name', None)
        'Biased result'
        '''

        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, approximate)

        if entry not in self._cache_fuzzy:

            match = self._fuzzyGetBiased(entry, verbose=verbose)

            self._cache_fuzzy[entry] = match

            # Debug purpose
            if verbose:
                self._debugFuzzy(match, fuzzy_value, field, approximate, show_bad)

        return self._cache_fuzzy[entry]



    def biasFuzzyCache(self, fuzzy_value, field, approximate, biased_result):
        '''
        If algorithms for fuzzy searches are failing on a single example,
        it is possible to use a first cache which will block
        the research and force the result.
        '''

        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, approximate)

        self._bias_cache_fuzzy[entry] = biased_result


    def clearCache(self):
        self._cache_fuzzy = {}

    def clearBiasCache(self):
        self._bias_cache_fuzzy = {}


    def _buildCacheKey(self, fuzzy_value, field, approximate):
        '''
        Key for the cache of fuzzyGet, based on parameters.

        >>> geo_a._buildCacheKey('paris de gaulle', 'name', approximate=None)
        ('paris+de+gaulle', 'name', None)
        >>> geo_a._buildCacheKey('Antibes SNCF 2', 'name', approximate=3)
        ('antibes', 'name', 3)
        '''
        return '+'.join(clean(fuzzy_value)), field, approximate


    def _debugFuzzy(self,
                    match,
                    fuzzy_value,
                    field,
                    approximate=None,
                    show_bad=(1, 1)):
        '''
        Some debugging.
        '''
        if approximate is None:
            matches = [ match ]
        else:
            matches = match

        for m in matches:

            if m[0] >= show_bad[0] and m[0] < show_bad[1]:

                print "[%.2f] %25s -> %25s (%5s)" % \
                    (m[0],
                     '+'.join(clean(fuzzy_value)),
                     '+'.join(clean(self.get(m[1], field))),
                     m[1])


    def haversine(self, key0, key1):
        '''
        Compute distance between two elements.
        This is just a wrapper between the original haversine
        function, but it is probably the most used feature :)

        :param key0: the first key
        :param key1: the second key
        :returns:    the distance (km)

        >>> geo_t.haversine('frnic', 'frpaz')
        683.526...
        '''

        return haversine(self.getLocation(key0), self.getLocation(key1))


    def set(self, key, field, value):
        '''
        Method to manually change a value in the base.

        :param key:   the key we want to change a value of
        :param field: the concerned field, like 'lat'
        :param value: the new value

        >>> geo_t.get('frnic', 'name')
        'Nice-Ville'
        >>> geo_t.set('frnic', 'name', 'Nice Gare SNCF')
        >>> geo_t.get('frnic', 'name')
        'Nice Gare SNCF'
        >>> geo_t.set('frnic', 'name', 'Nice-Ville') # Not to mess with other tests :)
        '''

        # If the key is not in the database,
        # we simply add it
        if key not in self._things:
            self._things[key] = {}

        self._things[key][field] = value

        # If the field was not referenced in the headers
        # we add it to the headers
        if field not in self._headers:
            self._headers.append(field)


    def setWithDict(self, key, dictionary):
        '''
        Same as set method, except we perform
        the input with a whole dictionary.

        :param key:         the key we want to change a value of
        :param dictionary:  the dict containing the new data

        >>> geo_m.keys()
        []
        >>> geo_m.setWithDict('frnic', {'code' : 'frnic', 'name': 'Nice'})
        >>> geo_m.keys()
        ['frnic']
        '''

        for field, val in dictionary.iteritems():
            self.set(key, field, val)


    def delete(self, key):
        '''
        Method to manually remove a value in the base.

        :param key:   the key we want to change a value of
        :param field: the concerned field, like 'lat'
        :returns:     None

        >>> data = geo_t.get('frxrn') # Output all data in one dict
        >>> geo_t.delete('frxrn')
        >>> geo_t.get('frxrn', 'name')
        Traceback (most recent call last):
        KeyError: 'Thing not found: frxrn'

        How to reverse the delete if data has been stored:

        >>> geo_t.setWithDict('frxrn', data)
        >>> geo_t.get('frxrn', 'name')
        'Redon'
        '''

        del self._things[key]





def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    extraglobs = {
        'geo_o': GeoBase(data='ori_por',  verbose=False),
        'geo_a': GeoBase(data='airports', verbose=False),
        'geo_t': GeoBase(data='stations', verbose=False),
        'geo_m': GeoBase(data='mix',      verbose=False)
    }

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE |
            doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()


