#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is a general class *GeoBase* to manipulate geographical
data. It loads static csv files containing data about
airports or train stations, and then provides tools to browse it.

It relies on three other modules:

- *GeoUtils*: to compute haversine distances between points
- *LevenshteinUtils*: to calculate distances between strings. Indeed, we need
  a good tool to do it, in order to recognize things like station names
  in schedule files where we do not have the station id
- *GeoGridModule*: to handle geographical indexation

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

    >>> geo = GeoBase(data='ori_por_multi') # we have a few duplicates even with (iata, loc_type) key
    /!\ [lno ...] RDU+CA is duplicated #1, first found lno ...
    /!\ [lno ...] RDU+CA is duplicated #2, first found lno ...
    /!\ [lno ...] RDU+CA is duplicated #3, first found lno ...
    Import successful from ...
    Available fields for things: ...
"""

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
def relative(rel_path, root_file=__file__):
    """Handle relative paths.
    """
    return op.join(op.realpath(op.dirname(root_file)), rel_path)


# Path to global configuration
PATH_CONF = relative('DataSources/Sources.yaml')

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
            relative('MapAssets/template.html') : '%s_map.html',
        },
        'static' : {
            # source : target
            relative('MapAssets/map.js')            : 'map.js',
            relative('MapAssets/point.png')         : 'point.png',
            relative('MapAssets/marker.png')        : 'marker.png',
            relative('MapAssets/red_point.png')     : 'red_point.png',
            relative('MapAssets/red_marker.png')    : 'red_marker.png',
            relative('MapAssets/orange_point.png')  : 'orange_point.png',
            relative('MapAssets/orange_marker.png') : 'orange_marker.png',
            relative('MapAssets/yellow_point.png')  : 'yellow_point.png',
            relative('MapAssets/yellow_marker.png') : 'yellow_marker.png',
            relative('MapAssets/green_point.png')   : 'green_point.png',
            relative('MapAssets/green_marker.png')  : 'green_marker.png',
            relative('MapAssets/cyan_point.png')    : 'cyan_point.png',
            relative('MapAssets/cyan_marker.png')   : 'cyan_marker.png',
            relative('MapAssets/blue_point.png')    : 'blue_point.png',
            relative('MapAssets/blue_marker.png')   : 'blue_marker.png',
            relative('MapAssets/purple_point.png')  : 'purple_point.png',
            relative('MapAssets/purple_marker.png') : 'purple_marker.png',
            relative('MapAssets/black_point.png')   : 'black_point.png',
            relative('MapAssets/black_marker.png')  : 'black_marker.png',
        }
    },
    'table' : {
        'template' : {
            # source : v_target
            relative('TablesAssets/template.html') : '%s_table.html',
        },
        'static' : {
            # source : target
            relative('TablesAssets/table.js') : 'table.js',
        }
    }
}



# We only export the main class
__all__ = ['GeoBase', 'BASES']


class GeoBase(object):
    """
    This is the main and only class. After __init__,
    a file is loaded in memory, and the user may use
    the instance to get information.
    """

    @staticmethod
    def update(force=False):
        """Launch update script on data files.
        """
        script_path  = relative('DataSources/CheckDataUpdates.sh')
        force_option = '-f' if force else ''

        os.system('bash %s %s' % (script_path, force_option))


    def __init__(self, data, **kwargs):
        """Initialization

        The ``kwargs`` parameters given when creating the object may be:

        - local         : ``True`` by default, is the source local or not
        - source        : ``None`` by default, file-like to the source
        - headers       : ``[]`` by default, list of fields in the data
        - indexes       : ``None`` by default, list of fields defining the key for a line
        - delimiter     : ``'^'`` by default, delimiter for each field,
        - subdelimiters : ``{}`` by default, a ``{ 'field' : 'delimiter' }`` dict to define subdelimiters
        - quotechar     : ``'"'`` by default, this is the string defined for quoting
        - limit         : ``None`` by default, put an int if you want to load only the first lines
        - discard_dups  : ``False`` by default, boolean to discard key duplicates of handle them
        - verbose       : ``True`` by default, toggle verbosity

        :param data: the type of data wanted, 'airports', 'stations', and many more available. \
            'feed' will create an empty instance.
        :param kwargs: additional parameters
        :raises:  ValueError, if data parameters is not recognized
        :returns: None

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
        >>> fl = open(relative('DataSources/Airports/GeoNames/airports_geonames_only_clean.csv'))
        >>> GeoBase(data='feed',
        ...         source=fl,
        ...         headers=['iata_code', 'name', 'city'],
        ...         indexes='iata_code',
        ...         delimiter='^',
        ...         verbose=False).get('ORY')
        {'city': 'PAR', 'name': 'Paris-Orly', 'iata_code': 'ORY', '__gar__': 'FR^France^48.7252780^2.3594440', '__par__': [], '__dup__': [], '__key__': 'ORY', '__lno__': 798}
        >>> fl.close()
        >>> GeoBase(data='airports',
        ...         headers=['iata_code', 'name', 'city'],
        ...         verbose=False).get('ORY')
        {'city': 'PAR', 'name': 'Paris-Orly', 'iata_code': 'ORY', '__gar__': 'FR^France^48.7252780^2.3594440', '__par__': [], '__dup__': [], '__key__': 'ORY', '__lno__': 798}
        """
        # Main structure in which everything will be loaded
        # Dictionary of dictionary
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
        self.data   = data

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

        if data in BASES:
            conf = BASES[data]

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
            raise ValueError('Wrong data type. Not in %s' % sorted(BASES.keys()))

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
                props['source'] = relative(props['source'], root_file=PATH_CONF)

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

            # We add those default fields if user adds data with self.set
            self.fields = ['__key__', '__dup__', '__par__', '__lno__', '__gar__']


        # Grid
        if self.hasGeoSupport():
            self.createGrid()
        else:
            if self._verbose:
                print 'No geocode support, skipping grid...'



    def _configSubDelimiters(self):
        """Some precomputation on subdelimiters.
        """
        for h in self._headers:
            # If not in conf, do not sub split
            if h not in self._subdelimiters:
                self._subdelimiters[h] = None

            # Handling sub delimiter not list-embedded
            if isinstance(self._subdelimiters[h], str):
                self._subdelimiters[h] = [self._subdelimiters[h]]



    @staticmethod
    def _configKeyer(indexes, headers):
        """Define the function that build a line key.
        """
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
            raise ValueError("Inconsistent: headers = %s with indexes = %s" % \
                             (headers, indexes))
        else:
            keyer = lambda row, pos: '+'.join(row[p] for p in pos)

        return pos, keyer


    @staticmethod
    def _buildRowValues(row, headers, delimiter, subdelimiters, key, line_nb):
        """Building all data associated to this row.
        """
        # Erase everything, except duplicates counter
        data = {
            '__key__' : key,      # special field for key
            '__lno__' : line_nb,  # special field for line number
            '__gar__' : [],       # special field for garbage
            '__dup__' : [],       # special field for duplicates
            '__par__' : [],       # special field for parent
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
        """Manually configure the reader, to bypass the limitations of csv.reader.
        """
        #quotechar = csv_opt['quotechar']
        delimiter = csv_opt['delimiter']

        if len(delimiter) == 1:
            return lambda source_fl : csv.reader(source_fl, **csv_opt)

        if self._verbose:
            print '/!\ Delimiter "%s" was not 1-character.' % delimiter
            print '/!\ Fallback on custom reader, but quoting is disabled.'

        def _reader(source_fl):
            """Custom reader supporting multiple characters split.
            """
            for row in source_fl:
                yield row.rstrip('\r\n').split(delimiter)

        return _reader


    def _loadFile(self, source_fl):
        """Load the file and feed the self._things.

        :param verbose: display informations or not during runtime
        :raises: IOError, if the source cannot be read
        :raises: ValueError, if duplicates are found in the source
        """
        # We cache all variables used in the main loop
        headers       = self._headers
        indexes       = self._indexes
        delimiter     = self._delimiter
        subdelimiters = self._subdelimiters
        quotechar     = self._quotechar
        limit         = self._limit
        discard_dups  = self._discard_dups
        verbose       = self._verbose

        pos, keyer = self._configKeyer(indexes, headers)

        # csv reader options
        csv_opt = {
            'delimiter' : delimiter,
            'quotechar' : quotechar
        }

        _reader = self._configReader(**csv_opt)

        for line_nb, row in enumerate(_reader(source_fl), start=1):

            if verbose and line_nb % NB_LINES_STEP == 0:
                print '%-10s lines loaded so far' % line_nb

            if limit is not None and line_nb > limit:
                if verbose:
                    print 'Beyond limit %s for lines loaded, stopping.' % limit
                break

            # Skip comments and empty lines
            # Comments must *start* with #, otherwise they will not be stripped
            if not row or row[0].startswith('#'):
                continue

            try:
                key = keyer(row, pos)
            except IndexError:
                if verbose:
                    print '/!\ Could not compute key with headers %s, indexes %s for line %s: %s' % \
                            (headers, indexes, line_nb, row)
                continue

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
                    row_data['__par__'] = [key]

                    # We add the d_key as a new duplicate, and store the duplicate in the main _things
                    self._things[key]['__dup__'].append(d_key)
                    self._things[d_key] = row_data

                    if verbose:
                        print "/!\ [lno %s] %s is duplicated #%s, first found lno %s: creation of %s..." % \
                                (line_nb, key, len(self._things[key]['__dup__']), self._things[key]['__lno__'], d_key)
                else:
                    if verbose:
                        print "/!\ [lno %s] %s is duplicated, first found lno %s: dropping line..." % \
                                (line_nb, key, self._things[key]['__lno__'])


        # We remove None headers, which are not-loaded-columns
        self.fields = ['__key__', '__dup__', '__par__', '__lno__']

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
        """Check if data type has geocoding support.

        :returns: boolean for geocoding support

        >>> geo_t.hasGeoSupport()
        True
        >>> geo_f.hasGeoSupport()
        False
        """
        fields = set(self.fields)

        for required in GEO_FIELDS:
            if required not in fields:
                return False

        return True



    def createGrid(self):
        """Create the grid for geographical indexation after loading the data.
        """
        self._ggrid = GeoGrid(radius=50, verbose=False)

        for key in self:
            lat_lng = self.getLocation(key)

            if lat_lng is None:
                if self._verbose:
                    print 'No usable geocode for %s: ("%s","%s"), skipping point...' % \
                            (key, self.get(key, LAT_FIELD), self.get(key, LNG_FIELD))
            else:
                self._ggrid.add(key, lat_lng, self._verbose)



    def get(self, key, field=None, **kwargs):
        """Simple get on the base.

        This get function raises an exception when input is not correct.

        :param key:     the key of the thing (like 'SFO')
        :param field:   the field (like 'name' or 'iata_code')
        :param default: if key is missing, returns default if given
        :raises:        KeyError, if the key is not in the base
        :returns:       the needed information

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
        KeyError: "Field 'not_a_field' [for key 'frnic'] not in ['info', 'code', 'name', 'lines@raw', 'lines', '__gar__', '__par__', '__dup__', '__key__', 'lat', 'lng', '__lno__']"
        """
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
        """Returns geocode as (float, float) or None.

        :param key:     the key of the thing (like 'SFO')
        :returns:       the location, a tuple of floats (lat, lng), or None

        >>> geo_a.getLocation('AGN')
        (57.50..., -134.585...)
        """
        try:
            loc = tuple(float(self.get(key, f)) for f in GEO_FIELDS)

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



    def hasParents(self, key):
        """Tell if a key has parents.

        :param key:     the key of the thing (like 'SFO')
        :returns:       the number of parents

        >>> geo_o.hasParents('MRS')
        0
        >>> geo_o.hasParents('MRS@1')
        1
        >>> geo_o.hasParents('PAR')
        0
        """
        return len(self._things[key]['__par__'])


    def hasDuplicates(self, key):
        """Tell if a key has duplicates.

        :param key:     the key of the thing (like 'SFO')
        :returns:       the number of duplicates

        >>> geo_o.hasDuplicates('MRS')
        1
        >>> geo_o.hasDuplicates('MRS@1')
        1
        >>> geo_o.hasDuplicates('PAR')
        0
        """
        return len(self._things[key]['__dup__'])



    def getAllDuplicates(self, key, field=None, **kwargs):
        """Get all duplicates data, parent key included.

        :param key:     the key of the thing (like 'SFO')
        :param field:   the field (like 'name' or 'iata_code')
        :returns:       the list of values for the given field iterated \
                on all duplicates for the key, including the key itself

        >>> geo_o.getAllDuplicates('ORY', 'name')
        ['Paris-Orly']
        >>> geo_o.getAllDuplicates('THA', 'name')
        ['Tullahoma Regional Airport/William Northern Field', 'Tullahoma']
        >>> geo_o.getAllDuplicates('THA', '__key__')
        ['THA', 'THA@1']
        >>> geo_o.getAllDuplicates('THA@1', '__key__')
        ['THA@1', 'THA']
        >>> geo_o.get('THA', '__dup__')
        ['THA@1']
        """
        if key not in self._things:
            # Unless default is set, we raise an Exception
            if 'default' in kwargs:
                return kwargs['default']

            raise KeyError("Thing not found: %s" % str(key))

        # Building the list of all duplicates
        keys = [key]
        for k in self._things[key]['__dup__'] + self._things[key]['__par__']:
            if k not in keys:
                keys.append(k)

        # Key is in geobase here
        if field is None:
            return [self._things[k] for k in keys]

        try:
            res = [self._things[k][field] for k in keys]
        except KeyError:
            raise KeyError("Field '%s' [for key '%s'] not in %s" % \
                           (field, key, self._things[key].keys()))
        else:
            return res



    def getKeysWhere(self, conditions, from_keys=None, reverse=False, force_str=False, mode='and'):
        """Get iterator of all keys with particular field.

        For example, if you want to know all airports in Paris.

        :param conditions: a list of (field, value) conditions
        :param reverse:    we look keys where the field is *not* the particular value. \
                Note that this negation is done at the lower level, before combining \
                conditions. So if you have two conditions with mode='and', expect \
                results matching not condition 1 *and* not condition 2.
        :param force_str:  for the str() method before every test
        :param mode:       either 'or' or 'and', how to handle several conditions
        :param from_keys:  if given, we will look for results from this iterable of keys
        :returns:          an iterable of (v, key) where v is the number of matched \
                condition

        >>> list(geo_a.getKeysWhere([('city_code', 'PAR')]))
        [(1, 'ORY'), (1, 'TNF'), (1, 'CDG'), (1, 'BVA')]
        >>> list(geo_o.getKeysWhere([('comment', '')], reverse=True))
        []
        >>> list(geo_o.getKeysWhere([('__dup__', '[]')]))
        []
        >>> len(list(geo_o.getKeysWhere([('__dup__', [])])))
        7024
        >>> len(list(geo_o.getKeysWhere([('__dup__', '[]')], force_str=True)))
        7024
        >>> len(list(geo_o.getKeysWhere([('__par__', [])], reverse=True))) # Counting duplicated keys
        4431

        Testing several conditions.

        >>> c_1 = [('city_code'    , 'PAR')]
        >>> c_2 = [('location_type', 'H'  )]
        >>> len(list(geo_o.getKeysWhere(c_1)))
        18
        >>> len(list(geo_o.getKeysWhere(c_2)))
        91
        >>> len(list(geo_o.getKeysWhere(c_1 + c_2, mode='and')))
        2
        >>> len(list(geo_o.getKeysWhere(c_1 + c_2, mode='or')))
        107

        This works too \o/.

        >>> len(list(geo_o.getKeysWhere([('city_code', 'PAR'), ('city_code', 'BVE')], mode='and')))
        0
        >>> len(list(geo_o.getKeysWhere([('city_code', 'PAR'), ('city_code', 'BVE')], mode='or')))
        20
        """
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
            raise ValueError('"mode" argument must be in %s, was %s' % (str(['and', 'or']), mode))


        for key in from_keys:
            try:
                matches = [pass_one(self.get(key, f), v) for f, v in conditions]
                if pass_all(matches):
                    yield sum(matches), key
            except KeyError:
                # This means from_keys parameters contained unknown keys
                if self._verbose:
                    print 'Key %-10s raised KeyError in getKeysWhere, moving on...' % key


    def __str__(self):
        """Stringification.

        >>> str(geo_t)
        '<GeoBases.GeoBaseModule.GeoBase(stations) object at 0x...>'
        """
        return '<GeoBases.GeoBaseModule.GeoBase(%s) object at 0x...>' % self.data


    def __iter__(self):
        """Returns iterator of all keys in the base.

        :returns: the iterator of all keys

        >>> list(a for a in geo_a)
        ['AGN', 'AGM', 'AGJ', 'AGH', ...
        """
        return self._things.iterkeys()


    def __contains__(self, key):
        """Test if a thing is in the base.

        :param key: the key of the thing to be tested
        :returns:   a boolean

        >>> 'AN' in geo_a
        False
        >>> 'AGN' in geo_a
        True
        """
        if key in self._things:
            return True

        return False


    def __nonzero__(self):
        """Testing emptiness of structure.

        :returns: a boolean

        >>> if not geo_o: print('empty')
        >>> if geo_o:     print('not empty')
        not empty

        This geo_f is actually empty.

        >>> if not geo_f: print('empty')
        empty
        >>> if geo_f:     print('not empty')
        """
        if self._things:
            return True

        return False


    def keys(self):
        """Returns a list of all keys in the base.

        :returns: the list of all keys

        >>> geo_a.keys()
        ['AGN', 'AGM', 'AGJ', 'AGH', ...
        """
        return self._things.keys()


    def _buildDistances(self, lat_lng_ref, keys):
        """
        Compute the iterable of (dist, keys) of a reference
        lat_lng and a list of keys. Keys which have not valid
        geocodes will not appear in the results.

        >>> list(geo_a._buildDistances((0,0), ['ORY', 'CDG']))
        [(5422.74..., 'ORY'), (5455.45..., 'CDG')]
        """
        if lat_lng_ref is None:
            raise StopIteration

        for key in keys:

            lat_lng = self.getLocation(key)

            if lat_lng is not None:

                yield haversine(lat_lng_ref, lat_lng), key


    def findNearPoint(self, lat_lng, radius=50, from_keys=None, grid=True, double_check=True):
        """
        Returns a list of nearby things from a point (given
        latidude and longitude), and a radius for the search.
        Note that the haversine function, which compute distance
        at the surface of a sphere, here returns kilometers,
        so the radius should be in kms.

        :param lat_lng: the lat_lng of the point (a tuple of (lat, lng))
        :param radius:  the radius of the search (kilometers)
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance, \
            this is useful because the grid is approximate, so the results are only as accurate \
            as the grid size
        :returns:       an iterable of (distance, key) like [(3.2, 'SFO'), (4.5, 'LAX')]

        >>> # Paris, airports <= 50km
        >>> [geo_a.get(k, 'name') for d, k in sorted(geo_a.findNearPoint((48.84, 2.367), 50))]
        ['Paris-Orly', 'Paris-Le Bourget', 'Toussus-le-Noble', 'Paris - Charles-de-Gaulle']
        >>>
        >>> # Nice, stations <= 5km
        >>> [geo_t.get(k, 'name') for d, k in sorted(geo_t.findNearPoint((43.70, 7.26), 5))]
        ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch', 'Villefranche-sur-Mer', 'Nice-St-Augustin']
        >>>
        >>> # Wrong geocode
        >>> sorted(geo_t.findNearPoint(None, 5))
        []

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
        """
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
        """
        Same as findNearPoint, except the point is given
        not by a lat/lng, but with its key, like ORY or SFO.
        We just look up in the base to retrieve lat/lng, and
        call findNearPoint.

        :param key:     the key of the thing (like 'SFO')
        :param radius:  the radius of the search (kilometers)
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance, \
            this is useful because the grid is approximate, so the results are only as accurate \
            as the grid size
        :returns:       an iterable of (distance, key) like [(3.2, 'SFO'), (4.5, 'LAX')]

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
        """
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
        """
        Concept close to findNearPoint, but here we do not
        look for the things radius-close to a point,
        we look for the closest thing from this point, given by
        latitude/longitude.

        :param lat_lng:   the lat_lng of the point (a tuple of (lat, lng))
        :param N:         the N closest results wanted
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform findClosestFromPoint. This is useful when we have names \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance, \
            this is useful because the grid is approximate, so the results are only as accurate \
            as the grid size
        :returns:       an iterable of (distance, key) like [(3.2, 'SFO'), (4.5, 'LAX')]

        >>> list(geo_a.findClosestFromPoint((43.70, 7.26))) # Nice
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), N=3)) # Nice
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=1)) # Nice
        [(0.56..., 'frnic')]
        >>> # Corner case, from_keys empty is not used
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=2, from_keys=()))
        []
        >>> list(geo_t.findClosestFromPoint(None, N=2))
        []
        >>> #from datetime import datetime
        >>> #before = datetime.now()
        >>> #for _ in range(100): s = geo_a.findClosestFromPoint((43.70, 7.26), N=3)
        >>> #print(datetime.now() - before)

        No grid.

        >>> list(geo_o.findClosestFromPoint((43.70, 7.26), grid=False)) # Nice
        [(0.60..., 'NCE@1')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), grid=False)) # Nice
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint((43.70, 7.26), N=3, grid=False)) # Nice
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=1, grid=False)) # Nice
        [(0.56..., 'frnic')]
        >>> list(geo_t.findClosestFromPoint((43.70, 7.26), N=2, grid=False, from_keys=('frpaz', 'frply', 'frbve')))
        [(482.84..., 'frbve'), (683.89..., 'frpaz')]
        """
        if from_keys is None:
            from_keys = iter(self)

        if grid:
            for dist, thing in self._ggrid.findClosestFromPoint(lat_lng, N, double_check, from_keys):
                yield (dist, thing)

        else:
            iterable = self._buildDistances(lat_lng, from_keys)

            for dist, thing in heapq.nsmallest(N, iterable):
                yield (dist, thing)



    def findClosestFromKey(self, key, N=1, from_keys=None, grid=True, double_check=True):
        """
        Same as findClosestFromPoint, except the point is given
        not by a lat/lng, but with its key, like ORY or SFO.
        We just look up in the base to retrieve lat/lng, and
        call findClosestFromPoint.

        :param key:       the key of the thing (like 'SFO')
        :param N:         the N closest results wanted
        :param from_keys: if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform findClosestFromPoint. This is useful when we have names \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance, \
            this is useful because the grid is approximate, so the results are only as accurate \
            as the grid size
        :returns:       an iterable of (distance, key) like [(3.2, 'SFO'), (4.5, 'LAX')]

        >>> list(geo_a.findClosestFromKey('ORY')) # Orly
        [(0.0, 'ORY')]
        >>> list(geo_a.findClosestFromKey('ORY', N=3))
        [(0.0, 'ORY'), (18.80..., 'TNF'), (27.80..., 'LBG')]
        >>> # Corner case, from_keys empty is not used
        >>> list(geo_t.findClosestFromKey('ORY', N=2, from_keys=()))
        []
        >>> list(geo_t.findClosestFromKey(None, N=2))
        []
        >>> #from datetime import datetime
        >>> #before = datetime.now()
        >>> #for _ in range(100): s = geo_a.findClosestFromKey('NCE', N=3)
        >>> #print(datetime.now() - before)

        No grid.

        >>> list(geo_o.findClosestFromKey('ORY', grid=False)) # Nice
        [(0.0, 'ORY')]
        >>> list(geo_a.findClosestFromKey('ORY', N=3, grid=False)) # Nice
        [(0.0, 'ORY'), (18.80..., 'TNF'), (27.80..., 'LBG')]
        >>> list(geo_t.findClosestFromKey('frnic', N=1, grid=False)) # Nice
        [(0.0, 'frnic')]
        >>> list(geo_t.findClosestFromKey('frnic', N=2, grid=False, from_keys=('frpaz', 'frply', 'frbve')))
        [(482.79..., 'frbve'), (683.52..., 'frpaz')]
        """
        if from_keys is None:
            from_keys = iter(self)

        if grid:
            for dist, thing in self._ggrid.findClosestFromKey(key, N, double_check, from_keys):
                yield (dist, thing)

        else:
            for dist, thing in self.findClosestFromPoint(self.getLocation(key), N, from_keys, grid, double_check):
                yield (dist, thing)


    def _buildRatios(self, fuzzy_value, field, keys, min_match=0):
        """
        Compute the iterable of (dist, keys) of a reference
        fuzzy_value and a list of keys.

        >>> list(geo_a._buildRatios('marseille', 'name', ['ORY', 'MRS', 'CDG'], 0.80))
        [(0.9..., 'MRS')]
        """
        for key in keys:

            r = mod_leven(fuzzy_value, self.get(key, field))

            if r >= min_match:
                yield r, key


    def fuzzyGet(self, fuzzy_value, field, max_results=None, min_match=0.75, from_keys=None):
        """
        Fuzzy searches are retrieving an information
        on a thing when we do not know the code.
        We compare the value fuzzy_value which is supposed to be a field
        (e.g. a city or a name), to all things we have in the base,
        and we output the best match.
        Matching is performed using Levenshtein module, with a modified
        version of the Lenvenshtein ratio, adapted to the type of data.

        Example: we look up 'Marseille Saint Ch.' in our base
        and we find the corresponding code by comparing all station
        names with ''Marseille Saint Ch.''.

        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param max_results: max number of results, None means all results
        :param min_match:   filter out matches under this threshold
        :param from_keys:   if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform fuzzyGet. This is useful when we have geocodes \
            and have to perform a matching based on name and location (see fuzzyGetAroundLatLng).
        :returns:           an iterable of (distance, key) like [(0.97, 'SFO'), (0.55, 'LAX')]

        >>> geo_t.fuzzyGet('Marseille Charles', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name')[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', max_results=3, min_match=0.55)
        [(0.78..., 'CDG'), (0.60..., 'HUX'), (0.57..., 'LBG')]
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', max_results=3, min_match=0.75)
        [(0.78..., 'CDG')]

        Some corner cases.

        >>> geo_a.fuzzyGet('paris de gaulle', 'name', max_results=None)[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGet('paris de gaulle', 'name', max_results=1, from_keys=[])
        []
        """
        if from_keys is None:
            # iter(self), since __iter__ is defined is equivalent to
            # self._things.iterkeys()
            from_keys = iter(self)

        # All 'intelligence' is performed in the Levenshtein
        # module just here. All we do is minimize this distance
        iterable = self._buildRatios(fuzzy_value, field, from_keys, min_match)

        if max_results is None:
            return sorted(iterable, reverse=True)
        else:
            return heapq.nlargest(max_results, iterable)



    def fuzzyGetAroundLatLng(self, lat_lng, radius, fuzzy_value, field, max_results=None, min_match=0.75, from_keys=None, grid=True, double_check=True):
        """
        Same as fuzzyGet but with we search only within a radius
        from a geocode.

        :param lat_lng:     the lat_lng of the point (a tuple of (lat, lng))
        :param radius:      the radius of the search (kilometers)
        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param max_results: if None, returns all, if an int, only returns the first ones
        :param min_match:   filter out matches under this threshold
        :param from_keys:   if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param grid:        boolean, use grid or not
        :param double_check: when using grid, perform an additional check on results distance, \
            this is useful because the grid is approximate, so the results are only as accurate \
            as the grid size
        :returns:           an iterable of (distance, key) like [(0.97, 'SFO'), (0.55, 'LAX')]

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
        >>> geo_a.fuzzyGetAroundLatLng((50.9013890, 4.4844440), 2000, 'Brussels', 'name', max_results=1, min_match=0.30, from_keys=['CDG', 'ORY'])
        [(0.33..., 'ORY')]
        """
        if from_keys is None:
            from_keys = iter(self)

        nearest = ( key for dist, key in self.findNearPoint(lat_lng, radius, from_keys, grid, double_check) )

        return self.fuzzyGet(fuzzy_value, field, max_results, min_match, from_keys=nearest)


    def _fuzzyGetBiased(self, entry, verbose=True):
        """
        Same as fuzzyGet but with bias system.
        """
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
                       max_results=None,
                       min_match=0.75,
                       verbose=True,
                       show_bad=(1, 1)):
        """
        Same as fuzzyGet but with a caching and bias system.

        :param fuzzy_value: the value, like 'Marseille'
        :param field:       the field we look into, like 'name'
        :param max_results: if None, returns all, if an int, only returns the first ones
        :param min_match:   filter out matches under this threshold
        :param verbose:     display information on a certain range of similarity
        :param show_bad:    the range of similarity
        :returns:           an iterable of (distance, key) like [(0.97, 'SFO'), (0.55, 'LAX')]

        >>> geo_t.fuzzyGetCached('Marseille Saint Ch.', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', show_bad=(0, 1))[0]
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        (0.78..., 'CDG')
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', min_match=0.60, max_results=2, show_bad=(0, 1))
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        [0.61]           paris+de+gaulle ->        bahias+de+huatulco (  HUX)
        [(0.78..., 'CDG'), (0.60..., 'HUX')]

        Some biasing:

        >>> geo_a.biasFuzzyCache('paris de gaulle', 'name', None, 0.75, [(0.5, 'Biased result')])
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', max_results=None, show_bad=(0, 1))[0] # Cache there
        (0.78..., 'CDG')
        >>> geo_a.clearCache()
        >>> geo_a.fuzzyGetCached('paris de gaulle', 'name', max_results=None, min_match=0.75)
        Using bias: ('paris+de+gaulle', 'name', None, 0.75)
        [(0.5, 'Biased result')]
        """
        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, max_results, min_match)

        if entry not in self._cache_fuzzy:

            match = self._fuzzyGetBiased(entry, verbose=verbose)

            self._cache_fuzzy[entry] = match

            # Debug purpose
            if verbose:
                self._debugFuzzy(match, fuzzy_value, field, show_bad)

        return self._cache_fuzzy[entry]



    def biasFuzzyCache(self, fuzzy_value, field, max_results, min_match, biased_result):
        """
        If algorithms for fuzzy searches are failing on a single example,
        it is possible to use a first cache which will block
        the research and force the result.

        :param fuzzy_value:   the value, like 'Marseille'
        :param field:         the field we look into, like 'name'
        :param max_results:   if None, returns all, if an int, only returns the first ones
        :param min_match:     filter out matches under this threshold
        :param biased_result: the expected result
        :returns:             None

        """
        # Cleaning is for keeping only useful data
        entry = self._buildCacheKey(fuzzy_value, field, max_results, min_match)

        self._bias_cache_fuzzy[entry] = biased_result


    def clearCache(self):
        """Clear cache for fuzzy searches.
        """
        self._cache_fuzzy = {}


    def clearBiasCache(self):
        """Clear biasing cache for fuzzy searches.
        """
        self._bias_cache_fuzzy = {}


    @staticmethod
    def _buildCacheKey(fuzzy_value, field, max_results, min_match):
        """Key for the cache of fuzzyGet, based on parameters.

        >>> geo_a._buildCacheKey('paris de gaulle', 'name', max_results=None, min_match=0)
        ('paris+de+gaulle', 'name', None, 0)
        >>> geo_a._buildCacheKey('Antibes SNCF 2', 'name', max_results=3, min_match=0)
        ('antibes', 'name', 3, 0)
        """
        return '+'.join(clean(fuzzy_value)), field, max_results, min_match


    def _debugFuzzy(self, match, fuzzy_value, field, show_bad=(1, 1)):
        """Some debugging.
        """
        for m in match:

            if m[0] >= show_bad[0] and m[0] < show_bad[1]:

                print "[%.2f] %25s -> %25s (%5s)" % \
                    (m[0],
                     '+'.join(clean(fuzzy_value)),
                     '+'.join(clean(self.get(m[1], field))),
                     m[1])


    def distance(self, key0, key1):
        """Compute distance between two elements.

        This is just a wrapper between the original haversine
        function, but it is probably the most used feature :)

        :param key0: the first key
        :param key1: the second key
        :returns:    the distance (km)

        >>> geo_t.distance('frnic', 'frpaz')
        683.526...
        """
        return haversine(self.getLocation(key0), self.getLocation(key1))


    def set(self, key, field, value):
        """Method to manually change a value in the base.

        :param key:   the key we want to change a value of
        :param field: the concerned field, like 'name'
        :param value: the new value
        :returns:     None

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
        """
        # If the key is not in the base,
        # we simply add it
        if key not in self._things:
            self._things[key] = {
                '__key__' : key,      # special field for key
                '__lno__' : 0,        # special field for line number
                '__gar__' : [],       # special field for garbage
                '__dup__' : [],       # special field for duplicates
                '__par__' : [],       # special field for parent
            }

        self._things[key][field] = value

        # If the field was not referenced in the headers
        # we add it to the headers
        if field not in self.fields:
            self.fields.append(field)


    def setWithDict(self, key, dictionary):
        """
        Same as set method, except we perform
        the input with a whole dictionary.

        :param key:         the key we want to change a value of
        :param dictionary:  the dict containing the new data
        :returns:           None

        >>> geo_f.keys()
        []
        >>> geo_f.setWithDict('frnic', {'code' : 'frnic', 'name': 'Nice'})
        >>> geo_f.keys()
        ['frnic']
        """
        for field, val in dictionary.iteritems():
            self.set(key, field, val)


    def delete(self, key):
        """Method to manually remove a value in the base.

        :param key:   the key we want to delete
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
        """
        del self._things[key]


    @staticmethod
    def hasTrepSupport():
        """Check if module has OpenTrep support.
        """
        return HAS_TREP_SUPPORT


    @staticmethod
    def trepGet(fuzzy_value, trep_format='S', from_keys=None, verbose=False):
        """OpenTrep integration.

        If not hasTrepSupport(), main_trep is not defined
        and trepGet will raise an exception if called.

        :param fuzzy_value:   the fuzzy value
        :param trep_format:   the format given to OpenTrep
        :param from_keys:     if None, it takes all keys in consideration, else takes from_keys \
            iterable of keys to perform search.
        :param verbose:       toggle verbosity
        :returns:             an iterable of (distance, key) like [(0.97, 'SFO'), (0.55, 'LAX')]

        >>> if geo_t.hasTrepSupport():
        ...     print geo_t.trepGet('sna francisco los agneles') # doctest: +SKIP
        [(31.5192, 'SFO'), (46.284, 'LAX')]

        >>> if geo_t.hasTrepSupport():
        ...     print geo_t.trepGet('sna francisco', verbose=True) # doctest: +SKIP
         -> Raw result: SFO/31.5192
         -> Fmt result: ([(31.5192, 'SFO')], '')
        [(31.5192, 'SFO')]
        """
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


    def visualize(self,
                  output='example',
                  label='__key__',
                  point_size=None,
                  point_color=None,
                  icon_type='auto',
                  from_keys=None,
                  catalog=None,
                  add_lines=None,
                  link_duplicates=True,
                  verbose=True):
        """Creates map and other visualizations.

        :param output:          set the name of the rendered files
        :param label:           set the field which will appear as map icons title
        :param point_size:      set the field defining the map icons circle size
        :param point_color:     set the field defining the map icons colors
        :icon_type:             set the global icon size, either 'B', 'S' or 'auto'
        :from_keys:             only display this iterable of keys if not None
        :param catalog:         optional color catalog to have specific colors for certain field values
        :param add_lines:       optional list of (key1, key2, ..., keyN) to draw additional lines
        :param link_duplicates: boolean toggling lines between duplicated keys feature
        :param verbose:         toggle verbosity
        :returns:               (list of templates successfully rendered, total number of templates available).
        """
        # We take the maximum verbosity between the local and global
        verbose = self._verbose or verbose

        if self.hasGeoSupport():
            geo_support = True
        else:
            geo_support = False

            if verbose:
                print '\n/!\ Could not find fields %s in headers %s.' % \
                        (' and '.join(GEO_FIELDS), self.fields)

        # Label is the field which labels the points
        if label not in self.fields:
            raise ValueError('label "%s" not in fields %s.' % (label, self.fields))

        if point_size is not None and point_size not in self.fields:
            raise ValueError('point_size "%s" not in fields %s.' % (point_size, self.fields))

        if point_color is not None and point_color not in self.fields:
            raise ValueError('point_color "%s" not in fields %s.' % (point_color, self.fields))

        # Optional function which gives points size
        if point_size is None:
            get_size = lambda key: 0
        else:
            get_size = lambda key: self.get(key, point_size)

        # Optional function which gives points size
        if point_color is None:
            get_category = lambda key: None
        else:
            get_category = lambda key: self.get(key, point_color)

        # from_keys lets you have a set of keys to visualize
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
                '__siz__' : get_size(key),
                '__cat__' : get_category(key),
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

        # Icon type
        if icon_type is None:
            base_icon = ''
        elif icon_type == 'auto':
            base_icon = 'marker.png' if len(data) < 100 else 'point.png'
        elif icon_type == 'S':
            base_icon = 'point.png'
        elif icon_type == 'B':
            base_icon = 'marker.png'
        else:
            allowed = ('auto', 'S', 'B', None)
            raise ValueError('icon_type "%s" not in %s.' % (icon_type, allowed))

        # Additional lines
        if add_lines is None:
            add_lines = []

        if link_duplicates:
            # We add to add_lines all list of duplicates
            # We keep a set of already processed "master" keys to avoid
            # putting several identical lists in the json
            done_keys = set()

            for elem in data:
                key = elem['__key__']

                if not self.hasParents(key):
                    mkey = set([key])
                else:
                    mkey = set(self.get(key, '__par__'))

                if self.hasDuplicates(key) and not mkey.issubset(done_keys):
                    # mkey have some keys which are not in done_keys
                    add_lines.append(self.getAllDuplicates(key, '__key__'))
                    done_keys = done_keys | mkey

            if verbose:
                print '* Added lines for duplicates linking, total %s' % len(add_lines)

        # Count the categories for coloring
        categories = {}

        for elem in data:
            if icon_type is None:
                # Here we are in no-icon mode, categories
                # will be based on the entries who will have a circle
                try:
                    c = float(elem['__siz__'])
                except ValueError:
                    c = 0
            else:
                c = 1

            cat = elem['__cat__']
            if cat not in categories:
                categories[cat] = 0
            if c > 0:
                categories[cat] += c

        # Color repartition given biggest categories
        colors  = ('red', 'orange', 'yellow', 'green', 'cyan', 'purple')
        col_num = 0

        if not categories:
            step = 1
        else:
            # c > 0 makes sure we do not create a category
            # for stuff that will not be displayed
            nb_non_empty_cat = len([c for c in categories.values() if c > 0])

            if nb_non_empty_cat > 0:
                step = max(1, len(colors) / nb_non_empty_cat)
            else:
                # All categories may be empty if not icons + not circles
                step = 1

        for cat, vol in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            categories[cat] = {
                'volume' : vol
            }
            if cat is None:
                # None is also the default category, when point_color is None
                categories[cat]['color'] = 'blue'

            elif col_num < len(colors):
                # We affect the next color available
                categories[cat]['color'] = colors[col_num]
                col_num += step
            else:
                # After all colors are used, remaining categories are black
                categories[cat]['color'] = 'black'

            if verbose:
                if icon_type is not None:
                    field_vol = 'volume'
                elif point_size is not None:
                    field_vol = point_size
                else:
                    field_vol = '(not used)'

                print '> Affecting category %-8s to color %-7s | %s %s' % \
                        (cat, categories[cat]['color'], field_vol, vol)


        # catalog is a user defined color scheme
        if catalog is None:
            # Default diff-friendly catalog
            catalog = {
                ' ' : 'blue',
                '+' : 'green',
                'Y' : 'green',
                '-' : 'red',
                'N' : 'red',
            }

        for cat in catalog:
            if cat in categories:

                old_color = categories[cat]['color']
                new_color = catalog[cat]
                categories[cat]['color'] = new_color

                if verbose:
                    print '> Overrides category %-8s to color %-7s (from %-7s)' % \
                            (cat, new_color, old_color)

                # We test other categories to avoid duplicates in coloring
                for ocat in categories:
                    if ocat == cat:
                        continue
                    ocat_color = categories[ocat]['color']

                    if ocat_color == new_color:
                        categories[ocat]['color'] = old_color

                        if verbose:
                            print '> Switching category %-8s to color %-7s (from %-7s)' % \
                                    (ocat, old_color, ocat_color)


        # Finally, we write the colors as an element attribute
        for elem in data:
            elem['__col__'] = categories[elem['__cat__']]['color']


        # Gathering data for lines
        data_lines = []

        for line in add_lines:
            data_line = []

            for l_key in line:
                lat_lng = self.getLocation(l_key)

                if lat_lng is None:
                    lat_lng = '?', '?'

                data_line.append({
                    '__key__' : l_key,
                    '__lab__' : self.get(l_key, label),
                    'lat'     : lat_lng[0],
                    'lng'     : lat_lng[1],
                })

            data_lines.append(data_line)


        # Dump the json geocodes
        json_name = '%s.json' % output

        with open(json_name, 'w') as out:
            out.write(json.dumps({
                'meta'       : {
                    'label'           : label,
                    'point_size'      : point_size,
                    'point_color'     : point_color,
                    'icon_type'       : icon_type,
                    'base_icon'       : base_icon,
                    'link_duplicates' : link_duplicates,
                },
                'points'     : data,
                'lines'      : data_lines,
                'categories' : sorted(categories.items(),
                                      key=lambda x: x[1]['volume'],
                                      reverse=True)
            }))

        tmp_template = []
        tmp_static   = [json_name]

        for name, assets in ASSETS.iteritems():
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

            for source, target in assets['static'].iteritems():
                copy(source, target)
                tmp_static.append(target)

        if verbose:
            print
            print '* Now you may use your browser to visualize:'
            print ' '.join(tmp_template)
            print
            print '* If you want to clean the temporary files:'
            print 'rm %s' % ' '.join(tmp_static + tmp_template)
            print

        # This is the numbered of templates rendered
        return tmp_template, sum(len(a['template']) for a in ASSETS.values())



def ext_split(value, split):
    """Extended split function handling None and '' splitter.

    :param value:  the value to be split
    :param split:  the splitter
    :returns:      the split value

    >>> ext_split('', ',')
    ()
    >>> ext_split('PAR', 'A')
    ('P', 'R')
    >>> ext_split('PAR', '')
    ('P', 'A', 'R')
    >>> ext_split('PAR', None)
    'PAR'
    """
    if split is None:
        return value
    if split == '':
        # Here we convert a string like 'CA' into ('C', 'A')
        return tuple(value)

    # Python split function has ''.split(';') -> ['']
    # But in this case we prefer having [] as a result
    if not value:
        return ()

    return tuple(value.split(split))


def recursive_split(value, splits):
    """Recursive extended split.

    :param value:  the value to be split
    :param splits: the list of splitters
    :returns:      the split value

    >>> recursive_split('PAR^Paris/Parys', ['^', '/'])
    (('PAR',), ('Paris', 'Parys'))
    """
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
    """When called directly, launching doctests.
    """
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


