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
    >>> geo_a.distance('CDG', 'NCE')
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
    >>> geo_t.distance('frnic', 'frpaz')
    683.526...

From any point of reference:

    >>> geo = GeoBase(data='ori_por_multi')
    Import successful from ...
    Available fields for things: ...
'''

from __future__ import with_statement

import os
import os.path as op
import heapq
from itertools import izip_longest
import csv
import json
from shutil import copy

# Not in standard library
import yaml

from .GeoUtils         import haversine
from .LevenshteinUtils import mod_leven, clean
from .GeoGridModule    import GeoGrid


try:
    # This wrapper will raise an ImportError
    # if libopentrep cannot be found
    # or if OpenTrepWrapper was not installed
    from OpenTrepWrapper import main_trep

except ImportError as err:
    # Could not import
    HAS_TREP_SUPPORT = False
else:
    # No problem here
    HAS_TREP_SUPPORT = True

# Relative paths handling
local_path = lambda file_p, rel_p : op.join(op.realpath(op.dirname(file_p)), rel_p)


# We only export the main class
__all__ = ['GeoBase']


class GeoBase(object):
    '''
    This is the main and only class. After __init__,
    a file is loaded in memory, and the user may use
    the instance to get information.
    '''

    # Path to global configuration
    PATH_CONF = local_path(__file__, 'DataSources/Sources.yaml')

    # Loading configuration
    with open(PATH_CONF) as fl:
        BASES = yaml.load(fl)

    # Special fields for latitude and longitude recognition
    LAT_FIELD  = 'lat'
    LNG_FIELD  = 'lng'
    GEO_FIELDS = (LAT_FIELD, LNG_FIELD)

    # Loading indicator
    NB_LINES_STEP = 100000

    # Assets for map and tables
    ASSETS = {
        'map' : {
            'template' : {
                # source : v_target
                local_path(__file__, 'MapAssets/template.html') : '%s_map.html',
            },
            'static' : {
                # source : target
                local_path(__file__, 'MapAssets/blue_point.png')  : 'blue_point.png',
                local_path(__file__, 'MapAssets/blue_marker.png') : 'blue_marker.png'
            }
        },
        'table' : {
            'template' : {
                # source : v_target
                local_path(__file__, 'TablesAssets/template.html') : '%s_table.html',
            },
            'static' : {}
        }
    }


    @staticmethod
    def update():
        '''
        Launch update script on oripor data file.
        '''
        os.system('bash ' + local_path(__file__, 'DataSources/CheckDataUpdates.sh'))



    def __init__(self, data, **kwargs):
        '''Initialization

        :param data: the type of data wanted, 'airports', 'stations' \
            and 'feed' currently available. 'feed' will let you define your \
            own parameters.
        :param verbose: display informations or not during runtime

        :raises: ValueError, if data parameters is not recognized

        >>> geo_a = GeoBase(data='airports')
        Import successful from ...
        Available fields for things: ...
        >>> geo_t = GeoBase(data='stations')
        Import successful from ...
        Available fields for things: ...
        >>> geo_f = GeoBase(data='feed')
        Source was None, skipping loading...
        >>> geo_c = GeoBase(data='odd')
        Traceback (most recent call last):
        ValueError: Wrong data type. Not in ['airlines', ...]
        >>> 
        >>> fl = open(local_path(__file__, 'DataSources/Airports/AirportsDotCsv/ORI_Simple_Airports_Database_Table.csv'))
        >>> GeoBase(data='feed',
        ...         source=fl,
        ...         headers=['code', 'ref_name', 'ref_name_2', 'name'],
        ...         indexes='code',
        ...         delimiter='^',
        ...         verbose=False).get('ORY')
        {'code': 'ORY', 'name': 'PARIS/FR:ORLY', '__gar__': 'PAR^Y^^FR^EUROP^ITC2^FR052^2.35944^48.7253^3745^Y^A', '__dup__': [], '__key__': 'ORY', 'ref_name_2': 'PARIS ORLY', '__dad__': '', '__lno__': 6014, 'ref_name': 'PARIS ORLY'}
        >>> fl.close()
        >>> GeoBase(data='airports_csv',
        ...         headers=['iata_code', 'ref_name', 'ref_name_2', 'name'],
        ...         verbose=False).get('ORY')
        {'name': 'PARIS/FR:ORLY', 'iata_code': 'ORY', '__gar__': 'PAR^Y^^FR^EUROP^ITC2^FR052^2.35944^48.7253^3745^Y^A', '__dup__': [], '__key__': 'ORY', 'ref_name_2': 'PARIS ORLY', '__dad__': '', '__lno__': 6014, 'ref_name': 'PARIS ORLY'}
        '''

        # Main structure in which everything will be loaded
        # Dictionary of dictionary
        self._data   = data
        self._things = {}
        self._ggrid  = None

        # A cache for the fuzzy searches
        self._cache_fuzzy = {}
        # An other cache if the algorithms are failing on a single
        # example, we first look in this cache
        self._bias_cache_fuzzy = {}

        # This will be similar as _headers, but can be modified after loading
        # _headers is just for data loading
        self.fields = []

        # Defaults
        props = {
            'local'         : True,
            'source'        : None,
            'headers'       : [],
            'indexes'       : None,
            'delimiter'     : '^',
            'subdelimiters' : {},
            'quotechar'     : '"',
            'limit'         : None,
            'discard_dups'  : False,
            'verbose'       : True,
        }

        if data in GeoBase.BASES:
            conf = GeoBase.BASES[data]

            # File configuration overrides defaults
            for name in conf:
                if name in props:
                    props[name] = conf[name]
                else:
                    raise ValueError('Option "%s" for data "%s" not understood in file.' % (name, data))

        elif data == 'feed':
            # User input defining everything
            pass
        else:
            raise ValueError('Wrong data type. Not in %s' % sorted(GeoBase.BASES.keys()))

        # User input overrides default configuration
        # or file configuration
        for name in kwargs:
            if name in props:
                props[name] = kwargs[name]
            else:
                raise ValueError('Option "%s" not understood.' % name)

        if 'source' not in kwargs:
            # "local" is only used for sources from configuration
            # to have a relative path from the configuration file
            if props['source'] is not None and props['local'] is True:
                props['source'] = local_path(GeoBase.PATH_CONF, props['source'])

        # Final parameters affectation
        self._local         = props['local']
        self._source        = props['source']
        self._headers       = props['headers']
        self._indexes       = props['indexes']
        self._delimiter     = props['delimiter']
        self._subdelimiters = props['subdelimiters']
        self._quotechar     = props['quotechar']
        self._limit         = props['limit']
        self._discard_dups  = props['discard_dups']
        self._verbose       = props['verbose']

        # Loading data
        self._configSubDelimiters()

        if self._source is not None:
            if 'source' in kwargs:
                # As a keyword argument, source should be a file-like
                self._loadFile(self._source)
            else:
                # Here we read the source from the configuration file
                with open(self._source) as source_fl:
                    self._loadFile(source_fl)
        else:
            if self._verbose:
                print 'Source was None, skipping loading...'

        # Grid
        if self.hasGeoSupport():
            self.createGrid()
        else:
            if self._verbose:
                print 'No geocode support, skipping grid...'



    def _configSubDelimiters(self):
        '''Some precomputation on subdelimiters.
        '''
        for h in self._headers:
            # If not in conf, do not sub split
            if h not in self._subdelimiters:
                self._subdelimiters[h] = None

            # Handling sub delimiter not list-embedded
            if isinstance(self._subdelimiters[h], str):
                self._subdelimiters[h] = [self._subdelimiters[h]]



    @staticmethod
    def _configKeyer(indexes, headers):
        '''Define thw function that build a line key.
        '''
        # It is possible to have a indexes which is a list
        # In this case we build the key as the concatenation between
        # the different fields
        try:
            if isinstance(indexes, str):
                pos = (headers.index(indexes), )

            elif isinstance(indexes, list):
                pos = tuple(headers.index(k) for k in indexes)

            else:
                raise ValueError()

        except ValueError:
            raise ValueError("Inconsistent: indexes = %s with headers = %s" % \
                             (indexes, headers))
        else:
            keyer = lambda row, pos: '+'.join(row[p] for p in pos)

        return pos, keyer


    @staticmethod
    def _buildRowValues(row, headers, delimiter, subdelimiters, key, line_nb):
        '''Building all data associated to this row.
        '''
        # Erase everything, except duplicates counter
        data = {
            '__key__' : key,      # special field for key
            '__lno__' : line_nb,  # special field for line number
            '__gar__' : [],       # special field for garbage
            '__dup__' : [],       # special field for duplicates
            '__dad__' : '',       # special field for parent
        }

        # headers represents the meaning of each column.
        # Using izip_longest here will replace missing fields
        # with empty strings ''
        for h, v in izip_longest(headers, row, fillvalue=''):
            # if h is None, it means the conf file explicitely
            # specified not to load the column
            if h is None:
                continue
            # if h is an empty string, it means there was more
            # data than the headers said, we store it in the 
            # __gar__ special field
            if not h:
                data['__gar__'].append(v)
            else:
                if subdelimiters[h] is None:
                    data[h] = v
                else:
                    data['%s@raw' % h] = v
                    data[h] = recursive_split(v, subdelimiters[h])

        # Flattening the __gar__ list
        data['__gar__'] = delimiter.join(data['__gar__'])

        return data


    def _configReader(self, **csv_opt):
        '''Manually configure the reader, to bypass the limitations of csv.reader.

        '''
        delimiter = csv_opt['delimiter']
        #quotechar = csv_opt['quotechar']

        if len(delimiter) == 1:
            return lambda source_fl : csv.reader(source_fl, **csv_opt)

        if self._verbose:
            print '/!\ Delimiter "%s" was not 1-character.' % delimiter
            print '/!\ Fallback on custom reader, but quoting is disabled.'

        def _reader(source_fl):
            '''Custom reader supporting multiple characters split.
            '''
            for row in source_fl:
                yield row.rstrip('\r\n').split(delimiter)

        return _reader


    def _loadFile(self, source_fl):
        '''Load the file and feed the self._things.

        :param verbose: display informations or not during runtime
        :raises: IOError, if the source cannot be read
        :raises: ValueError, if duplicates are found in the source
        '''
        # We cache all variables used in the main loop
        headers       = self._headers
        delimiter     = self._delimiter
        subdelimiters = self._subdelimiters
        limit         = self._limit
        discard_dups  = self._discard_dups
        verbose       = self._verbose

        pos, keyer = self._configKeyer(self._indexes, headers)

        # csv reader options
        csv_opt = {
            'delimiter' : self._delimiter,
            'quotechar' : self._quotechar
        }

        _reader = self._configReader(**csv_opt)

        for line_nb, row in enumerate(_reader(source_fl), start=1):

            if verbose and line_nb % GeoBase.NB_LINES_STEP == 0:
                print '%-10s lines loaded so far' % line_nb

            if limit is not None and line_nb > limit:
                if verbose:
                    print 'Beyond limit %s for lines loaded, stopping.' % limit
                break

            # Skip comments and empty lines
            # Comments must *start* with #, otherwise they will not be stripped
            if not row or row[0].startswith('#'):
                continue

            key      = keyer(row, pos)
            row_data = self._buildRowValues(row, headers, delimiter, subdelimiters, key, line_nb)

            # No duplicates ever, we will erase all data after if it is
            if key not in self._things:
                self._things[key] = row_data

            else:
                if discard_dups is False:
                    # We compute a new key for the duplicate
                    d_key = '%s@%s' % (key, 1 + len(self._things[key]['__dup__']))

                    # We update the data with this info
                    row_data['__key__'] = d_key
                    row_data['__dup__'] = self._things[key]['__dup__']
                    row_data['__dad__'] = key

                    # We add the d_key as a new duplicate, and store the duplicate in the main _things
                    self._things[key]['__dup__'].append(d_key)
                    self._things[d_key] = row_data

                if verbose:
                    print "/!\ [lno %s] %s is duplicated #%s, first found lno %s" % \
                            (line_nb, key, len(self._things[key]['__dup__']), self._things[key]['__lno__'])


        # We remove None headers, which are not-loaded-columns
        self.fields = ['__key__', '__dup__', '__dad__', '__lno__']

        for h in headers:
            if subdelimiters[h] is not None:
                self.fields.append('%s@raw' % h)

            if h is not None:
                self.fields.append(h)

        self.fields.append('__gar__')


        if verbose:
            print "Import successful from %s" % self._source
            print "Available fields for things: %s" % self.fields



    def hasGeoSupport(self):
        '''
        Check if base has geocoding support.

        >>> geo_t.hasGeoSupport()
        True
        >>> geo_f.hasGeoSupport()
        False
        '''
        fields = set(self.fields)

        for required in GeoBase.GEO_FIELDS:
            if required not in fields:
                return False

        return True



    def createGrid(self):
        '''
        Create the grid for geographical indexation after loading the data.
        '''
        self._ggrid = GeoGrid(radius=50, verbose=False)

        for key in self:
            lat_lng = self.getLocation(key)

            if lat_lng is None:
                if self._verbose:
                    print 'No usable geocode for %s: ("%s","%s"), skipping point...' % \
                            (key, self.get(key, GeoBase.LAT_FIELD), self.get(key, GeoBase.LNG_FIELD))
            else:
                self._ggrid.add(key, lat_lng, self._verbose)



    def get(self, key, field=None, **kwargs):
        '''
        Simple get on the database.
        This get function raise exception when input is not correct.

        :param key:   the key of the thing (like 'SFO')
        :param field: the field (like 'name' or 'iata_code')
        :raises:      KeyError, if the key is not in the base
        :returns:     the needed information

        >>> geo_a.get('CDG', 'city_code')
        'PAR'
        >>> geo_t.get('frnic', 'name')
        'Nice-Ville'
        >>> geo_t.get('frnic')
        {'info': 'Desserte Voyageur-Infrastructure', 'code': 'frnic', ...}

        Cases of unknown key.

        >>> geo_t.get('frmoron', 'name', default='There')
        'There'
        >>> geo_t.get('frmoron', 'name')
        Traceback (most recent call last):
        KeyError: 'Thing not found: frmoron'
        >>> geo_t.get('frmoron', 'name', default=None)
        >>> geo_t.get('frmoron', default='There')
        'There'

        Cases of unknown field, this is a bug and always fail.

        >>> geo_t.get('frnic', 'not_a_field', default='There')
        Traceback (most recent call last):
        KeyError: "Field 'not_a_field' [for key 'frnic'] not in ['info', 'code', 'name', 'lines', '__gar__', '__dup__', '__key__', 'lat', 'lng', '__dad__', '__lno__']"
        '''

        if key not in self._things:
            # Unless default is set, we raise an Exception
            if 'default' in kwargs:
                return kwargs['default']

            raise KeyError("Thing not found: %s" % str(key))

        # Key is in geobase here
        if field is None:
            return self._things[key]

        try:
            res = self._things[key][field]
        except KeyError:
            raise KeyError("Field '%s' [for key '%s'] not in %s" % (field, key, self._things[key].keys()))
        else:
            return res



    def getLocation(self, key):
        '''
        Returns proper geocode.

        >>> geo_a.getLocation('AGN')
        (57.50..., -134.585...)
        '''
        try:
            loc = tuple(float(self.get(key, f)) for f in GeoBase.GEO_FIELDS)

        except ValueError:
            # Decode geocode, if error, returns None
            return None

        except KeyError:
            # Probably means that there is not geocode support
            # But could be that key is unkwown
            return None
        # Note that TypeError would mean that the input
        # type was not even a string, probably NoneType
        else:
            return loc



    def hasDuplicates(self, key):
        '''Tell if a key has duplicates.

        >>> geo_o.hasDuplicates('ORY')
        0
        >>> geo_o.hasDuplicates('THA')
        1
        '''
        return len(self._things[key]['__dup__'])



    def getDuplicates(self, key, field=None, default=None):
        '''Get all duplicates data, parent key included.

        >>> geo_o.getDuplicates('ORY', 'name')
        ['Paris-Orly']
        >>> geo_o.getDuplicates('THA', 'name')
        ['Tullahoma Regional Airport/William Northern Field', 'Tullahoma']
        >>> geo_o.getDuplicates('THA', '__key__')
        ['THA', 'THA@1']
        >>> geo_o.get('THA', '__dup__')
        ['THA@1']
        '''

        if key not in self._things:
            # Unless default is set, we raise an Exception
            if default is not None:
                return [default]

            raise KeyError("Thing not found: %s" % str(key))

        # Key is in geobase here
        if field is None:
            return [self._things[key]] + [self._things[d] for d in self._things[key]['__dup__']]

        try:
            res = [self._things[key][field]]
        except KeyError:
            raise KeyError("Field '%s' [for key '%s'] not in %s" % (field, key, self._things[key].keys()))
        else:
            return res + [self._things[d][field] for d in self._things[key]['__dup__']]



    def getKeysWhere(self, conditions, from_keys=None, reverse=False, force_str=False, mode='and'):
        '''
        Get iterator of all keys with particular
        field.
        For example, if you want to know all airports in Paris.

        :param conditions: a list of (field, value) conditions
        :param reverse:    we look keys where the field is *not* the particular value
        :param force_str:  for the str() method before every test
        :param mode:       either 'or' or 'and', how to handle several conditions
        :returns:          an iterator of matching keys

        >>> list(geo_a.getKeysWhere([('city_code', 'PAR')]))
        ['ORY', 'TNF', 'CDG', 'BVA']
        >>> list(geo_o.getKeysWhere([('comment', '')], reverse=True))
        []
        >>> list(geo_o.getKeysWhere([('__dup__', '[]')]))
        []
        >>> len(list(geo_o.getKeysWhere([('__dup__', [])])))
        10897
        >>> len(list(geo_o.getKeysWhere([('__dup__', '[]')], force_str=True)))
        10897
        >>> len(list(geo_o.getKeysWhere([('__dad__', '')], reverse=True))) # Counting duplicated keys
        512

        Testing several conditions.

        >>> c_1 = [('city_code'    , 'PAR')]
        >>> c_2 = [('location_type', 'H'  )]
        >>> len(list(geo_o.getKeysWhere(c_1)))
        17
        >>> len(list(geo_o.getKeysWhere(c_2)))
        59
        >>> len(list(geo_o.getKeysWhere(c_1 + c_2, mode='and')))
        2
        >>> len(list(geo_o.getKeysWhere(c_1 + c_2, mode='or')))
        74

        This works too \o/.

        >>> len(list(geo_o.getKeysWhere([('city_code', 'PAR'), ('city_code', 'BVE')], mode='and')))
        0
        >>> len(list(geo_o.getKeysWhere([('city_code', 'PAR'), ('city_code', 'BVE')], mode='or')))
        18
        '''

        if from_keys is None:
            from_keys = iter(self)

        # We set the lambda function now to avoid testing
        # force_str and reverse at each key later
        if not force_str and not reverse:
            pass_one = lambda a, b: a == b
        elif not force_str and reverse:
            pass_one = lambda a, b: a != b
        elif force_str and not reverse:
            pass_one = lambda a, b: str(a) == str(b)
        else:
            pass_one = lambda a, b: str(a) != str(b)

        # Handle and/or cases when multiple conditions
        if mode == 'and':
            pass_all = all
        elif mode == 'or':
            pass_all = any
        else:
            raise ValueError('"mode" argument must be in %s' % str(['and', 'or']))


        for key in from_keys:

            if pass_all(pass_one(self.get(key, f), v) for f, v in conditions):
                yield key


    def __str__(self):
        '''Stringification.

        >>> str(geo_t)
        '<GeoBases.GeoBaseModule.GeoBase(stations) object at 0x...>'
        '''
        return '<GeoBases.GeoBaseModule.GeoBase(%s) object at 0x...>' % self._data


    def __iter__(self):
        '''
        Returns iterator of all keys in the database.

        :returns: the iterator of all keys

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


    def __nonzero__(self):
        '''
        Testing GeoBase emptiness.

        :returns: a boolean

        >>> if not geo_o: print('empty')
        >>> if geo_o:     print('not empty')
        not empty

        This geo_f is actually empty.

        >>> if not geo_f: print('empty')
        empty
        >>> if geo_f:     print('not empty')
        '''

        if self._things:
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


    def _buildDistances(self, lat_lng_ref, keys):
        '''
        Compute the iterable of (dist, keys) of a reference
        lat_lng and a list of keys. Keys which have not valid
        geocodes will not appear in the results.

        >>> list(geo_a._buildDistances((0,0), ['ORY', 'CDG']))
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

            for dist, thing in self._buildDistances(lat_lng, from_keys):

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
        >>> # Corner case, from_keys empty is not used
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=2, from_keys=()))
        []
        >>> 
        >>> #from datetime import datetime
        >>> #before = datetime.now()
        >>> #for _ in range(100): s = geo_a.findClosestFromPoint((43.70, 7.26), N=3)
        >>> #print(datetime.now() - before)

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

            for dist, thing in self._ggrid.findClosestFromPoint(lat_lng, N, double_check, from_keys):

                yield (dist, thing)

        else:

            iterable = self._buildDistances(lat_lng, from_keys)

            for dist, thing in heapq.nsmallest(N, iterable):

                yield (dist, thing)


    def _buildRatios(self, fuzzy_value, field, keys, min_match=0):
        '''
        Compute the iterable of (dist, keys) of a reference
        fuzzy_value and a list of keys.

        >>> list(geo_a._buildRatios('marseille', 'name', ['ORY', 'MRS', 'CDG'], 0.80))
        [(0.9..., 'MRS')]
        '''

        for key in keys:

            r = mod_leven(fuzzy_value, self.get(key, field))

            if r >= min_match:

                yield r, key


    def fuzzyGet(self, fuzzy_value, field, approximate=None, min_match=0.75, from_keys=None):
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
        :param approximate: max number of results, None means all results
        :param min_match:   filter out matches under this threshold
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform fuzzyGet. This is useful when we have geocodes \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :returns:           a couple with the best match and the distance found

        >>> geo_t.fuzzyGet('Marseille Charles', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name')[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=3, min_match=0.55)
        [(0.78..., 'CDG'), (0.60..., 'HUX'), (0.57..., 'LBG')]
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=3, min_match=0.75)
        [(0.78..., 'CDG')]

        Some corner cases.

        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=None)[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', approximate=1, from_keys=[])
        []
        '''
        if from_keys is None:
            # iter(self), since __iter__ is defined is equivalent to
            # self._things.iterkeys()
            from_keys = iter(self)

        # All 'intelligence' is performed in the Levenshtein
        # module just here. All we do is minimize this distance
        iterable = self._buildRatios(fuzzy_value, field, from_keys, min_match)

        if approximate is None:
            return sorted(iterable, reverse=True)
        else:
            return heapq.nlargest(approximate, iterable)



    def fuzzyGetAroundLatLng(self, lat_lng, radius, fuzzy_value, field, approximate=None, min_match=0.75, from_keys=None, grid=True, double_check=True):
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

        >>> geo_a.fuzzyGet('Brussels', 'name', min_match=0.60)[0]
        (0.61..., 'BQT')
        >>> geo_a.get('BQT', 'name')  # Brussels just matched on Brest!!
        'Brest'
        >>> geo_a.get('BRU', 'name') # We wanted BRU for 'Bruxelles'
        'Bruxelles National'
        >>> 
        >>> # Now a request limited to a circle of 20km around BRU gives BRU
        >>> geo_a.fuzzyGetAroundLatLng((50.9013890, 4.4844440), 20, 'Brussels', 'name', min_match=0.40)[0]
        (0.46..., 'BRU')
        >>> 
        >>> # Now a request limited to some input keys
        >>> geo_a.fuzzyGetAroundLatLng((50.9013890, 4.4844440), 2000, 'Brussels', 'name', approximate=1, min_match=0.30, from_keys=['CDG', 'ORY'])
        [(0.33..., 'ORY')]
        '''
        if from_keys is None:
            from_keys = iter(self)

        nearest = ( key for dist, key in self.findNearPoint(lat_lng, radius, from_keys, grid, double_check) )

        return self.fuzzyGet(fuzzy_value, field, approximate, min_match, from_keys=nearest)


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
                       field,
                       approximate=None,
                       min_match=0.75,
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

        >>> geo_t.fuzzyGetCached('Marseille Saint Ch.', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', show_bad=(0, 1))[0]
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', min_match=0.60, approximate=2, show_bad=(0, 1))
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        [0.61]           paris+de+gaulle ->        bahias+de+huatulco (  HUX)
        [(0.78..., 'CDG'), (0.60..., 'HUX')]

        Some biasing:

        >>> geo_a.biasFuzzyCache('paris de gaulle', 'name', None, 0.75, [(0.5, 'Biased result')])
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', approximate=None, show_bad=(0, 1))[0] # Cache there
        (0.78..., 'CDG')
        >>> geo_a.clearCache()
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', approximate=None, min_match=0.75)
        Using bias: ('paris+de+gaulle', 'name', None, 0.75)
        [(0.5, 'Biased result')]
        '''
        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, approximate, min_match)

        if entry not in self._cache_fuzzy:

            match = self._fuzzyGetBiased(entry, verbose=verbose)

            self._cache_fuzzy[entry] = match

            # Debug purpose
            if verbose:
                self._debugFuzzy(match, fuzzy_value, field, show_bad)

        return self._cache_fuzzy[entry]



    def biasFuzzyCache(self, fuzzy_value, field, approximate, min_match, biased_result):
        '''
        If algorithms for fuzzy searches are failing on a single example,
        it is possible to use a first cache which will block
        the research and force the result.
        '''

        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, approximate, min_match)

        self._bias_cache_fuzzy[entry] = biased_result


    def clearCache(self):
        '''
        Clear cache for fuzzy searches.
        '''
        self._cache_fuzzy = {}

    def clearBiasCache(self):
        '''
        Clear biasing cache for fuzzy searches.
        '''
        self._bias_cache_fuzzy = {}


    @staticmethod
    def _buildCacheKey(fuzzy_value, field, approximate, min_match):
        '''
        Key for the cache of fuzzyGet, based on parameters.

        >>> geo_a._buildCacheKey('paris de gaulle', 'name', approximate=None, min_match=0)
        ('paris+de+gaulle', 'name', None, 0)
        >>> geo_a._buildCacheKey('Antibes SNCF 2', 'name', approximate=3, min_match=0)
        ('antibes', 'name', 3, 0)
        '''
        return '+'.join(clean(fuzzy_value)), field, approximate, min_match


    def _debugFuzzy(self, match, fuzzy_value, field, show_bad=(1, 1)):
        '''
        Some debugging.
        '''
        for m in match:

            if m[0] >= show_bad[0] and m[0] < show_bad[1]:

                print "[%.2f] %25s -> %25s (%5s)" % \
                    (m[0],
                     '+'.join(clean(fuzzy_value)),
                     '+'.join(clean(self.get(m[1], field))),
                     m[1])


    def distance(self, key0, key1):
        '''
        Compute distance between two elements.
        This is just a wrapper between the original haversine
        function, but it is probably the most used feature :)

        :param key0: the first key
        :param key1: the second key
        :returns:    the distance (km)

        >>> geo_t.distance('frnic', 'frpaz')
        683.526...
        '''

        return haversine(self.getLocation(key0), self.getLocation(key1))


    def set(self, key, field, value):
        '''
        Method to manually change a value in the base.

        :param key:   the key we want to change a value of
        :param field: the concerned field, like 'name'
        :param value: the new value

        >>> geo_t.get('frnic', 'name')
        'Nice-Ville'
        >>> geo_t.set('frnic', 'name', 'Nice Gare SNCF')
        >>> geo_t.get('frnic', 'name')
        'Nice Gare SNCF'
        >>> geo_t.set('frnic', 'name', 'Nice-Ville') # Not to mess with other tests :)

        We may even add new fields.

        >>> geo_t.set('frnic', 'new_field', 'some_value')
        >>> geo_t.get('frnic', 'new_field')
        'some_value'
        '''

        # If the key is not in the database,
        # we simply add it
        if key not in self._things:
            self._things[key] = {}

        self._things[key][field] = value

        # If the field was not referenced in the headers
        # we add it to the headers
        if field not in self.fields:
            self.fields.append(field)


    def setWithDict(self, key, dictionary):
        '''
        Same as set method, except we perform
        the input with a whole dictionary.

        :param key:         the key we want to change a value of
        :param dictionary:  the dict containing the new data

        >>> geo_f.keys()
        []
        >>> geo_f.setWithDict('frnic', {'code' : 'frnic', 'name': 'Nice'})
        >>> geo_f.keys()
        ['frnic']
        '''

        for field, val in dictionary.iteritems():
            self.set(key, field, val)


    def delete(self, key):
        '''
        Method to manually remove a value in the base.

        :param key:   the key we want to change a value of
        :param field: the concerned field, like 'name'
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


    @staticmethod
    def hasTrepSupport():
        '''
        Check if module has OpenTrep support.
        '''
        return HAS_TREP_SUPPORT


    @staticmethod
    def trepGet(fuzzy_value, trep_format='S', from_keys=None, verbose=False):
        '''
        OpenTrep integration.

        If not hasTrepSupport(), main_trep is not defined
        and trepGet will raise an exception if called.

        >>> if geo_t.hasTrepSupport():
        ...     print geo_t.trepGet('sna francisco los agneles') # doctest: +SKIP
        [(31.5192, 'SFO'), (46.284, 'LAX')]

        >>> if geo_t.hasTrepSupport():
        ...     print geo_t.trepGet('sna francisco', verbose=True) # doctest: +SKIP
         -> Raw result: SFO/31.5192
         -> Fmt result: ([(31.5192, 'SFO')], '')
        [(31.5192, 'SFO')]
        '''
        r = main_trep(searchString=fuzzy_value,
                      outputFormat=trep_format,
                      verbose=verbose)

        if trep_format == 'S':
            # Only this outputFormat is handled by upper layers
            if from_keys is None:
                return r[0]
            else:
                from_keys = set(from_keys)
                return [(k, e) for k, e in r[0] if e in from_keys]

        # For all other formats we return an empty
        # list to avoid failures
        return []


    def visualizeOnMap(self, output='example', label='__key__', from_keys=None, verbose=True):
        '''Creates map.

        Returns success code, number of templates realized.
        '''
        # We take the maximum verbosity between the local and global
        verbose = self._verbose or verbose

        if self.hasGeoSupport():
            geo_support = True
        else:
            geo_support = False

            if verbose:
                print '/!\ Could not find fields %s in headers %s.' % \
                        (' and '.join(GeoBase.GEO_FIELDS), self.fields)

        if label not in self.fields:
            if verbose:
                print '/!\ Label "%s" not in fields %s, could not visualize...' % \
                        (label, self.fields)
            return 0

        if from_keys is None:
            from_keys = iter(self)

        # Storing json data
        data = []

        for key in from_keys:

            lat_lng = self.getLocation(key)

            if lat_lng is None:
                lat_lng = '?', '?'

            elem = {
                '__key__' : key,
                '__lab__' : self.get(key, label),
                'lat'     : lat_lng[0],
                'lng'     : lat_lng[1]
            }

            for field in self.fields:
                # Keeping only important fields
                if not str(field).startswith('__') and \
                   not str(field).endswith('@raw') and \
                   field not in elem:

                    elem[field] = str(self.get(key, field))

            data.append(elem)

        # Dump the json geocodes
        json_name = '%s.json' % output

        with open(json_name, 'w') as out:
            out.write(json.dumps(data))

        if verbose:
            print 'Dumped %s' % json_name

        # Custom the template to connect to the json data
        tmp_template = []
        tmp_static   = []

        for name, assets in GeoBase.ASSETS.iteritems():

            # We do not render the map template  if not geocodes
            if name == 'map' and not geo_support:
                continue

            for template, v_target in assets['template'].iteritems():
                target = v_target % output

                with open(template) as temp:
                    with open(target, 'w') as out:

                        for row in temp:
                            row = row.replace('{{file_name}}', output)
                            row = row.replace('{{json_file}}', json_name)
                            out.write(row)

                tmp_template.append(target)
                if verbose:
                    print 'Dumped %s' % target

            for source, target in assets['static'].iteritems():

                copy(source, target)

                tmp_static.append(target)
                if verbose:
                    print 'Copied %s' % target

        if verbose:
            print '\n* Now you may use your browser to visualize:'
            print 'firefox %s &' % ' '.join(tmp_template)

            print '\n* If you want to clean the temporary files:'
            print 'rm %s %s' % (json_name, ' '.join(tmp_static + tmp_template))

        # This is the numbered of templates rendered
        return len(tmp_template)



def ext_split(value, split):
    '''Extended split function handling None and '' splitter.
    '''
    if split is None:
        return value
    if split == '':
        # Here we convert a string like 'CA' into ('C', 'A')
        return tuple(value)

    return tuple(value.split(split))


def recursive_split(value, splits):
    '''Recursive extended split.
    '''
    # Case where no subdelimiters
    if not splits:
        return value

    if len(splits) == 1:
        return ext_split(value, splits[0])

    if len(splits) == 2:
        return tuple(ext_split(v, splits[1]) for v in value.split(splits[0]))

    if len(splits) == 3:
        return tuple(
            tuple(ext_split(sv, splits[2]) for sv in ext_split(v, splits[1]))
            for v in value.split(splits[0])
        )

    raise ValueError('Sub delimiter "%s" not supported.' % str(splits))



def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    extraglobs = {
        'geo_o': GeoBase(data='ori_por',  verbose=False),
        'geo_a': GeoBase(data='airports', verbose=False),
        'geo_t': GeoBase(data='stations', verbose=False),
        'geo_f': GeoBase(data='feed',     verbose=False)
    }

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE)
            #doctest.REPORT_ONLY_FIRST_FAILURE)
            #doctest.IGNORE_EXCEPTION_DETAIL)

    doctest.testmod(extraglobs=extraglobs, optionflags=opt)



if __name__ == '__main__':
    _test()


