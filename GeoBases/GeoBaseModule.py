#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module defines a class *GeoBase* to manipulate geographical
data (or not). It loads static files containing data, then provides
tools to play with it.

It relies on four other modules:

- *GeoUtils*: to compute haversine distances between points
- *LevenshteinUtils*: to calculate distances between strings. Indeed, we need
  a good tool to do it, in order to recognize things like station names
  in schedule files where we do not have the station id
- *GeoGridModule*: to handle geographical indexation
- *SourcesManagerModule*: to handle data sources

Examples for airports::

    >>> geo_a = GeoBase(data='airports', verbose=False)
    >>> sorted(geo_a.findNearKey('ORY', 50)) # Orly, airports <= 50km
    [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
    >>> geo_a.get('CDG', 'city_code')
    'PAR'
    >>> geo_a.distance('CDG', 'NCE')
    694.516...


Examples for stations::

    >>> geo_t = GeoBase(data='stations', verbose=False)
    >>>
    >>> # Nice, stations <= 5km
    >>> point = (43.70, 7.26)
    >>> [geo_t.get(k, 'name') for d, k in sorted(geo_t.findNearPoint(point, 3))]
    ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch']
    >>>
    >>> geo_t.get('frpaz', 'name')
    'Paris-Austerlitz'
    >>> geo_t.distance('frnic', 'frpaz')
    683.526...

From any point of reference, we have a few duplicates
even with ``('iata_code', 'location_type')`` key:

    >>> geo = GeoBase(data='ori_por', key_fields=['iata_code', 'location_type'])
    In skipped zone, dropping line 1: "iata_code...".
    /!\ [lno ...] CRK+C is duplicated #1, first found lno ...: creation of ...
    /!\ [lno ...] EAP+C is duplicated #1, first found lno ...: creation of ...
    /!\ [lno ...] OSF+C is duplicated #1, first found lno ...: creation of ...
    /!\ [lno ...] RDU+C is duplicated #1, first found lno ...: creation of ...
    Import successful from ...
    Available fields for things: ...
"""

from __future__ import with_statement

import os.path as op
import heapq
from itertools import izip_longest, count, product
import csv

from .SourcesManagerModule import SourcesManager, is_remote, is_archive
from .GeoUtils             import haversine
from .LevenshteinUtils     import mod_leven, clean
from .GeoGridModule        import GeoGrid
from .VisualMixinModule    import VisualMixin

# Not in standard library
from fuzzy import DMetaphone, nysiis
dmeta = DMetaphone()

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


# The sources manager
S_MANAGER = SourcesManager()

# Special fields for latitude and longitude recognition
LAT_FIELD  = 'lat'
LNG_FIELD  = 'lng'
GEO_FIELDS = (LAT_FIELD, LNG_FIELD)

# Default grid size
GRID_RADIUS = 50 # kms

# Default min match for fuzzy searches
MIN_MATCH  = 0.75
RADIUS     = 50
NB_CLOSEST = 1

# Loading indicator
NB_LINES_STEP = 100000

# Defaults
DEFAULTS = {
    'source'        : None,  # not for configuration file, use path
    'paths'         : None,
    'headers'       : [],
    'key_fields'    : None,
    'indices'       : [],
    'delimiter'     : '^',
    'subdelimiters' : {},
    'join'          : [],
    'quotechar'     : '"',
    'limit'         : None,
    'skip'          : None,
    'discard_dups'  : False,
    'verbose'       : True,
}


# We only export the main class
__all__ = ['GeoBase', 'DEFAULTS']


class GeoBase(VisualMixin):
    """
    This is the main and only class. After __init__,
    a file is loaded in memory, and the user may use
    the instance to get information.
    """
    def __init__(self, data, **kwargs):
        """Initialization

        The ``kwargs`` parameters given when creating the object may be:

        - source        : ``None`` by default, file-like to the source
        - paths         : ``None`` by default, path or list of paths to \
                the source. This will only be used if source is ``None``.
        - headers       : ``[]`` by default, list of fields in the data
        - key_fields    : ``None`` by default, list of fields defining the \
                key for a line, ``None`` means line numbers will be used \
                to generate keys
        - indices       : ``[]`` by default, an iterable of additional \
                indexed fields
        - delimiter     : ``'^'`` by default, delimiter for each field,
        - subdelimiters : ``{}`` by default, a ``{ 'field' : 'delimiter' }`` \
                dict to define subdelimiters
        - join          : ``[]`` by default, list of dict defining join \
                clauses. A join clause is a dict \
                ``{ 'fields' : fields, 'with' : [base, fields]}``, for example \
                ``{ 'fields' : 'country_code', 'with' : ['countries', 'code']}``
        - quotechar     : ``'"'`` by default, this is the string defined for \
                quoting
        - limit         : ``None`` by default, put an int if you want to \
                load only the first lines
        - skip          : ``None`` by default, put an int if you want to \
                skip the first lines during loading
        - discard_dups  : ``False`` by default, boolean to discard key \
                duplicates or handle them
        - verbose       : ``True`` by default, toggle verbosity

        :param data: the type of data, ``'airports'``, ``'stations'``, \
                and many more available. ``'feed'`` will create an empty \
                instance.
        :param kwargs: additional parameters
        :raises:  ``ValueError``, if data parameters is not recognized
        :returns: ``None``

        >>> geo_a = GeoBase(data='airports')
        Import successful from ...
        Available fields for things: ...
        >>> geo_t = GeoBase(data='stations')
        Import successful from ...
        Available fields for things: ...
        >>> geo_f = GeoBase(data='feed')
        No source specified, skipping loading...
        Available fields for things: ...
        No geocode support, skipping grid...
        >>> geo_c = GeoBase(data='odd')
        Traceback (most recent call last):
        ValueError: Wrong data type "odd". Not in ['aircraft', ...]

        Import some custom data.

        >>> p = 'DataSources/Airports/GeoNames/airports_geonames_only_clean.csv'
        >>> fl = open(op.join(op.realpath(op.dirname(__file__)), p))
        >>> GeoBase(data='feed',
        ...         source=fl,
        ...         headers=['iata_code', 'name', 'city'],
        ...         key_fields='iata_code',
        ...         delimiter='^',
        ...         verbose=False).get('ORY', 'name')
        'Paris-Orly'
        >>> fl.close()
        >>> GeoBase(data='airports',
        ...         headers=['iata_code', 'cname', 'city'],
        ...         join=[],
        ...         verbose=False).get('ORY', 'cname')
        'Paris-Orly'
        """
        # Main structure in which everything will be loaded
        # Dictionary of dictionary
        self._things  = {}
        self._indexed = {}
        self._ggrid   = None

        # Other bases for join clauses
        self._ext_bases = {}

        # A cache for the fuzzy searches
        self._fuzzy_cache = {}
        # An other cache if the algorithms are failing on a single
        # example, we first look in this cache
        self._fuzzy_bias_cache = {}

        # This will be similar as _headers, but can be modified after loading
        # _headers is just for data loading
        self.fields = []
        self.data   = data
        self.loaded = None # loaded stuff information, depends on sources and paths

        # To store skipped lines, in case we dump
        self._skipped = {}

        # Defaults
        props = {}
        for k, v in DEFAULTS.iteritems():
            props[k] = v

        # paths read from the configuration file are by default
        # relative to the sources dir, if paths are read
        # as a keyword argument, the default is there are absolute paths
        if 'paths' in kwargs:
            default_is_relative = False
        else:
            default_is_relative = True

        allowed_conf = set(props.keys()) - set(['source'])
        allowed_args = set(props.keys())

        if self.data not in S_MANAGER:
            raise ValueError('Wrong data type "%s". Not in %s' % \
                             (self.data, sorted(S_MANAGER)))

        # The configuration may be empty
        conf = S_MANAGER.get(self.data)
        if conf is None:
            conf = {}

        # File configuration overrides defaults
        for option in conf:
            if option in allowed_conf:
                props[option] = conf[option]
            else:
                raise ValueError('Option "%s" for data "%s" not understood in file.' % \
                                 (option, self.data))

        # User input overrides default configuration or file configuration
        for option in kwargs:
            if option in allowed_args:
                props[option] = kwargs[option]
            else:
                raise ValueError('Option "%s" not understood in arguments.' % option)

        # If None, put the default instead
        for k, v in props.iteritems():
            if v is None:
                props[k] = DEFAULTS[k]

        # Final parameters affectation
        self._source        = props['source']
        self._headers       = props['headers']
        self._key_fields    = props['key_fields']
        self._indices       = props['indices']
        self._delimiter     = props['delimiter']
        self._subdelimiters = props['subdelimiters']
        self._join          = props['join']
        self._quotechar     = props['quotechar']
        self._limit         = props['limit']
        self._skip          = props['skip']
        self._discard_dups  = props['discard_dups']
        self._verbose       = props['verbose']
        self._paths         = props['paths']

        # Tweaks on types, fail on wrong values
        self._checkProperties(default_is_relative)

        # Loading data
        if self._source is not None:
            # As a keyword argument, source should be a file-like
            self._load(self._source, self._verbose)
            self.loaded = self._source

        elif self._paths:
            # Here we read the source from the configuration file
            for path in self._paths:
                file_ = S_MANAGER.handle_path(path, self.data, self._verbose)

                if file_ is None:
                    continue

                try:
                    with open(file_) as source_fl:
                        self._load(source_fl, self._verbose)
                except IOError:
                    if self._verbose:
                        print '/!\ Failed to open "%s", failing over...' % file_
                else:
                    self.loaded = file_
                    break
            else:
                # Here the loop did not break, meaning nothing was loaded
                # We will go here even if self._paths was []
                raise IOError('Nothing was loaded from: %s' % \
                              ''.join('\n(*) %s' % p['file'] for p in self._paths))


        if self._verbose:
            if isinstance(self.loaded, str):
                print "Import successful from %s" % self.loaded
            elif self.loaded is not None:
                print "Import successful from *file-like*"
            else:
                print 'No source specified, skipping loading...'

            print "Available fields for things: %s" % self.fields

        # Grid
        if self.hasGeoSupport():
            self.addGrid(radius=GRID_RADIUS, verbose=self._verbose)
        else:
            if self._verbose:
                print 'No geocode support, skipping grid...'


        # Indices
        for fields in self._indices:
            self.addIndex(fields, verbose=self._verbose)

        # Join handling
        for fields, join_data in self._join.iteritems():
            self._loadExtBase(fields, join_data)


    @staticmethod
    def _convertFieldToRaw(field):
        """Convert field name to raw version.
        """
        return '%s@raw' % field


    def _isFieldDelimited(self, field):
        """Check if a given field is split.
        """
        if field in self._subdelimiters:
            return True
        return False


    @staticmethod
    def _isFieldRaw(field):
        """Check if a given field is a raw version of a split one.
        """
        if str(field).endswith('@raw'):
            return True
        return False


    @staticmethod
    def _isFieldSpecial(field):
        """Check if a given field is special.
        """
        if str(field).startswith('__'):
            return True
        return False


    @classmethod
    def _isFieldNormal(cls, field):
        """Check if a given field is "normal", meaning neither special or raw.
        """
        if cls._isFieldRaw(field):
            return False

        if cls._isFieldSpecial(field):
            return False

        return True


    def _checkProperties(self, default_is_relative):
        """Some check on parameters.
        """
        # Tuplification
        self._headers = tuplify(self._headers)

        if self._key_fields is not None:
            self._key_fields = tuplify(self._key_fields)

        for i, v in enumerate(self._indices):
            self._indices[i] = tuplify(v)
        self._indices = tuplify(self._indices)

        # We remove the None values
        for h in self._subdelimiters.keys():
            if self._subdelimiters[h] is None:
                del self._subdelimiters[h]
            else:
                self._subdelimiters[h] = tuplify(self._subdelimiters[h])

        # Paths conversion to dict
        self._paths = S_MANAGER.convert_paths_format(self._paths,
                                                     default_is_relative)

        # Some headers are not accepted
        for h in self._headers:
            if not self._isFieldNormal(h):
                raise ValueError('Illegal header name "%s", __/@raw detected.' % h)


        # We remove None, convert to dict, tuplify keys *and* values
        new_join = {}

        for i, v in enumerate(self._join):
            if v is not None:
                new_join[tuplify(v['fields'])] = tuplify(v['with'])

        self._join = new_join



    def _loadExtBase(self, fields, join_data):
        """External bases for join fields handling.
        """
        for f in fields:
            if f not in self.fields:
                raise ValueError('Wrong field "%s". Not in %s' % (f, self.fields))

        if len(join_data) == 0:
            raise ValueError('Empty join_data for fields "%s" (was "%s").' % \
                            (fields, join_data))
        elif len(join_data) == 1:
            # Here if the user did not specify the field
            # of the join on the external base, we assume
            # it has the same name
            # join_data <=> join_base [, join_fields]
            join_base, join_fields = join_data[0], fields
        else:
            join_base, join_fields = join_data[0], tuplify(join_data[1])

        # Creation of external bases
        self._join[fields] = join_base, join_fields

        # When joining on multiple fields, you have to provide
        # the same number of fields for current base to external
        if len(fields) != len(join_fields):
            raise ValueError('"%s" should be the same length has "%s" as join fields.' % \
                            (fields, join_fields))

        if join_base not in S_MANAGER:
            raise ValueError('Wrong join data type "%s". Not in %s' % \
                             (join_base, sorted(S_MANAGER)))

        if join_base in self._ext_bases:
            if self._verbose:
                print '(Join) skipped [already done] load for external base "%s" [with %s] for join on %s' % \
                        (join_base, join_fields, fields)
        else:
            # To avoid recursion, we force the join to be empty
            if join_base == self.data:
                self._ext_bases[join_base] = self

                if self._verbose:
                    print '(Join) auto-referenced base "%s" [with %s] for join on %s' % \
                            (join_base, join_fields, fields)
            else:
                self._ext_bases[join_base] = GeoBase(join_base,
                                                     join=[],
                                                     verbose=False)

                if self._verbose:
                    print '(Join) loaded external base "%s" [with %s] for join on %s' % \
                            (join_base, join_fields, fields)

        ext_b = self._ext_bases[join_base]

        for f in join_fields:
            if f not in ext_b.fields:
                raise ValueError('Wrong join field "%s". Not in %s' % (f, ext_b.fields))

        # We index the field to optimize further findWith
        ext_b.addIndex(join_fields, verbose=self._verbose)



    def hasIndex(self, fields=None):
        """Tells if an iterable of fields is indexed.

        Default value is ``None`` for fields, this will test the
        presence of any index.

        :param fields:  the iterable of fields
        :returns:       a boolean

        >>> geo_o.hasIndex('iata_code')
        True
        >>> geo_o.hasIndex(('iata_code', 'asciiname'))
        False
        >>> geo_o.hasIndex()
        True
        """
        if fields is None:
            return not not self._indexed

        return tuplify(fields) in self._indexed



    def addIndex(self, fields, force=False, verbose=True):
        """Add an index on an iterable of fields.

        :param fields:  the iterable of fields
        :param force:   ``False`` by default, force index update \
                if it already exists
        :param verbose: toggle verbosity

        >>> geo_o.addIndex('iata_code', force=True, verbose=True)
        /!\ Index on ('iata_code',) already built, overriding...
        Built index for fields ('iata_code',)

        Index on multiple fields.

        >>> geo_o.addIndex(('icao_code', 'location_type'), verbose=True)
        Built index for fields ('icao_code', 'location_type')

        Do not force.

        >>> geo_o.addIndex('iata_code', force=False, verbose=True)
        /!\ Index on ('iata_code',) already built, exiting...
        """
        if not fields:
            if verbose:
                print '/!\ Fields %s were empty, index not added' % str(fields)
            return

        fields = tuplify(fields)

        if self.hasIndex(fields):
            if not force:
                if verbose:
                    print '/!\ Index on %s already built, exiting...' % str(fields)
                return

            elif verbose:
                print '/!\ Index on %s already built, overriding...' % str(fields)

        self._indexed[fields] = self._buildIndex(fields, verbose)



    def dropIndex(self, fields=None, verbose=True):
        """Drop an index on an iterable of fields.

        If fields is not given all indexes are dropped.

        :param fields:  the iterable of fields, if ``None``,
            all indexes will be dropped

        >>> geo_o.hasIndex(('icao_code', 'location_type'))
        True
        >>> geo_o.dropIndex(('icao_code', 'location_type'))
        >>> geo_o.hasIndex(('icao_code', 'location_type'))
        False
        """
        if fields is None:
            for fs in self._indexed:
                del self._indexed[tuplify(fs)]
        else:
            if self.hasIndex(fields):
                del self._indexed[tuplify(fields)]
            else:
                if verbose:
                    print 'No index to drop on "%s".' % str(fields)



    def updateIndex(self, fields=None, verbose=True):
        """Update index on fields.

        If fields is not given all indexes are updated.

        :param fields:  the iterable of fields, if ``None``,
            all indexes will be updated
        :param verbose: toggle verbosity

        Here is an example, we drop the index then make a query.

        >>> geo_o.dropIndex('iata_code')
        >>> list(geo_o.findWith([('iata_code', 'NCE')])) # not indexed
        [(1, 'NCE'), (1, 'NCE@1')]

        Now we index and make the same query.

        >>> geo_o.addIndex('iata_code')
        Built index for fields ('iata_code',)
        >>> list(geo_o.findWith([('iata_code', 'NCE')])) # indexed
        [(1, 'NCE'), (1, 'NCE@1')]

        Now we add a new key to the data.

        >>> geo_o.set('NEW_KEY_2', **{
        ...     'iata_code' : 'NCE',
        ... })

        If we run the query again, the result is wrong when
        using the index, because it is not up-to-date.

        >>> list(geo_o.findWith([('iata_code', 'NCE')])) # indexed
        [(1, 'NCE'), (1, 'NCE@1')]
        >>> list(geo_o.findWith([('iata_code', 'NCE')], index=False))
        [(1, 'NCE'), (1, 'NEW_KEY_2'), (1, 'NCE@1')]

        Now we update the index, then the query works.

        >>> geo_o.updateIndex('iata_code')
        Built index for fields ('iata_code',)
        >>> list(geo_o.findWith([('iata_code', 'NCE')])) # indexed, up to date
        [(1, 'NCE'), (1, 'NEW_KEY_2'), (1, 'NCE@1')]
        >>> geo_o.delete('NEW_KEY_2') # avoid messing other tests

        Note that ``updateIndex`` will not create indexes if it does not exist.

        >>> geo_f.updateIndex('iata_code')
        No index to update on "iata_code".
        """
        if fields is None:
            for fs in self._indexed:
                self.dropIndex(fs, verbose=verbose)
                self.addIndex(fs, verbose=verbose)
        else:
            if self.hasIndex(fields):
                self.dropIndex(fields, verbose=verbose)
                self.addIndex(fields, verbose=verbose)
            else:
                if verbose:
                    print 'No index to update on "%s".' % str(fields)



    def _buildIndex(self, fields, verbose=True):
        """Build index given an iterable of fields

        :param fields:  the iterable of fields
        :param verbose: toggle verbosity
        :returns:       the dictionary of { values : list of matching keys }

        >>> geo_o._buildIndex('iata_code', verbose=False)['MRS']
        ['MRS', 'MRS@1']
        >>> geo_o._buildIndex(('iata_code',), verbose=False)[('MRS',)]
        ['MRS', 'MRS@1']
        >>> geo_o._buildIndex(['iata_code', 'country_code'])[('MRS', 'FR')]
        Built index for fields ['iata_code', 'country_code']
        ['MRS', 'MRS@1']
        """
        if isinstance(fields, str):
            compute_val = lambda k: self.get(k, fields)

        elif isinstance(fields, (list, tuple, set)):
            compute_val = lambda k: tuple(self.get(k, f) for f in fields)

        else:
            raise ValueError('Wrong fields "%s" for index' % str(fields))

        # Mapping for every possible value to matching keys
        index = {}

        for key in self:

            try:
                val = compute_val(key)
            except KeyError:
                # Here we have some fields that failed
                # This can happen if incomplete key information
                # has been supplied after loading
                if verbose:
                    print '/!\ Could not compute values for key "%s" and fields %s' % \
                            (key, str(fields))
                continue

            if val not in index:
                index[val] = []

            index[val].append(key)

        if verbose:
            print 'Built index for fields %s' % str(fields)

        return index


    @staticmethod
    def _buildKeyer(key_fields, headers, verbose=True):
        """Define the function that build a line key.
        """
        # If key_fields is None we index with the line number
        if key_fields is None:
            if verbose:
                print '/!\ key_fields was None, keys will be created from line numbers.'

            return lambda row, lno: str(lno)

        # It is possible to have a key_fields which is a list
        # In this case we build the key as the concatenation between
        # the different fields
        try:
            pos = tuple(headers.index(k) for k in key_fields)

        except ValueError:
            raise ValueError("Inconsistent: headers = %s with key_fields = %s" % \
                             (headers, key_fields))
        else:
            keyer = lambda row, lno: '+'.join(row[p] for p in pos)

        return keyer


    @staticmethod
    def _emptyData(key, lno):
        """Generate empty data for a key.
        """
        return {
            '__key__' : key,  # special field for key
            '__dup__' : [],   # special field for duplicates
            '__par__' : [],   # special field for parent
            '__lno__' : lno,  # special field for line number
            '__gar__' : [],   # special field for garbage
        }


    def _buildRowData(self, row, headers, subdelimiters, key, lno):
        """Building all data associated to this row.
        """
        # Erase everything, except duplicates counter
        data = self._emptyData(key, lno=lno)

        # headers represents the meaning of each column.
        # Using izip_longest here will replace missing fields
        # with empty strings ''
        for h, v in izip_longest(headers, row, fillvalue=None):
            # if h is None, it means either:
            # 1) the conf file explicitely specified not to load the column
            # 2) there was more data than the headers said
            # Either way, we store it in the __gar__ special field
            if h is None:
                data['__gar__'].append(v)
            else:
                if self._isFieldDelimited(h):
                    data[self._convertFieldToRaw(h)] = v
                    data[h] = recursive_split(v, subdelimiters[h])
                else:
                    data[h] = v

        return data


    @staticmethod
    def _buildReader(verbose, **csv_opt):
        """Manually configure the reader, to bypass the limitations of csv.reader.
        """
        #quotechar = csv_opt['quotechar']
        delimiter = csv_opt['delimiter']


        if len(delimiter) == 1:
            return lambda source_fl : csv.reader(source_fl, **csv_opt)

        if len(delimiter) == 0:
            if verbose:
                print '/!\ Delimiter was empty.'
                print '/!\ Fallback on splitting-every-char, but quoting is disabled.'

            def _reader(source_fl):
                """Custom reader splitting every char.
                """
                for row in source_fl:
                    yield list(row.rstrip('\r\n'))

            return _reader

        if verbose:
            print '/!\ Delimiter "%s" was not 1-character.' % delimiter
            print '/!\ Fallback on custom reader, but quoting is disabled.'

        def _m_reader(source_fl):
            """Custom reader supporting multiple characters split.
            """
            for row in source_fl:
                yield row.rstrip('\r\n').split(delimiter)

        return _m_reader


    def _buildDuplicatedKey(self, key, nb_dups):
        """
        When the key is already in base and we do not want to discard the row,
        we have to compute a new key for this row.
        We iterate until we find an available key
        """
        for n in count(nb_dups):
            dup_key = '%s@%s' % (key, n)

            if dup_key not in self:
                return dup_key


    @staticmethod
    def _buildLnoEvents(skip, limit, verbose):
        """
        Build lambda functions handling events
        related to the line number count.
        """
        # Limit handling
        if skip is None:
            in_skipped_zone = lambda n : False
        else:
            in_skipped_zone = lambda n : n <= skip

        if limit is None:
            is_over_limit = lambda n : False
        else:
            is_over_limit = lambda n : n > limit

        # Verbose counter
        if verbose:
            show_load_info = lambda n : n % NB_LINES_STEP == 0
        else:
            show_load_info = lambda n : False

        return in_skipped_zone, is_over_limit, show_load_info


    def _load(self, source_fl, verbose=True):
        """Load the file and feed the main structure.

        :param source_fl: file-like input
        :param verbose:   toggle verbosity during data loading
        """
        # We cache all variables used in the main loop
        headers       = self._headers
        key_fields    = self._key_fields
        delimiter     = self._delimiter
        subdelimiters = self._subdelimiters
        quotechar     = self._quotechar
        limit         = self._limit
        skip          = self._skip
        discard_dups  = self._discard_dups

        keyer = self._buildKeyer(key_fields, headers, verbose)

        # Line number events
        in_skipped_zone, is_over_limit, show_load_info = self._buildLnoEvents(skip, limit, verbose)

        # Resetting skipped lines
        self._skipped = {}

        # csv reader options
        csv_opt = {
            'delimiter' : delimiter,
            'quotechar' : quotechar
        }

        _reader = self._buildReader(verbose, **csv_opt)

        for lno, row in enumerate(_reader(source_fl), start=1):

            if show_load_info(lno):
                print '%-10s lines loaded so far' % lno

            # Skip comments and empty lines
            # Comments must *start* with #, otherwise they will not be stripped
            if not row or row[0].startswith('#'):
                # Storing that
                self._skipped[lno] = row
                continue

            if in_skipped_zone(lno):
                if verbose:
                    print 'In skipped zone, dropping line %s: "%s...".' % \
                            (lno, row[0])
                # Storing that
                self._skipped[lno] = row
                continue

            if is_over_limit(lno):
                if verbose:
                    print 'Over limit %s for loaded lines, stopping.' % limit
                break

            try:
                key = keyer(row, lno)
            except IndexError:
                if verbose:
                    print '/!\ Could not compute key with headers %s, key_fields %s for line %s: %s' % \
                            (headers, key_fields, lno, row)
                # Storing that
                self._skipped[lno] = row
                continue

            data = self._buildRowData(row, headers, subdelimiters, key, lno)

            # No duplicates ever, we will erase all data after if it is
            if key not in self:
                self._resetData(key, data)

            else:
                if discard_dups is False:
                    # We compute a new key for the duplicate
                    nb_dups = 1 + len(self.get(key, '__dup__'))
                    dup_key = self._buildDuplicatedKey(key, nb_dups)

                    # We update the data with this info
                    data['__key__'] = dup_key
                    data['__dup__'] = self.get(key, '__dup__')
                    data['__par__'] = [key]

                    # We add the dup_key as a new duplicate,
                    # store the duplicate in the main structure
                    self.get(key, '__dup__').append(dup_key)
                    self._resetData(dup_key, data)

                    if verbose:
                        print "/!\ [lno %s] %s is duplicated #%s, first found lno %s: creation of %s..." % \
                                (lno, key, nb_dups, self.get(key, '__lno__'), dup_key)
                else:
                    if verbose:
                        print "/!\ [lno %s] %s is duplicated, first found lno %s: dropping line..." % \
                                (lno, key, self.get(key, '__lno__'))


        # We remove None headers, which are not-loaded-columns
        # We do not use the field synchronisation method to gain speed
        # and to preserve a consistent order of first (from headers)
        self.fields = ['__key__', '__dup__', '__par__', '__lno__']

        for h in headers:
            if self._isFieldDelimited(h):
                self.fields.append(self._convertFieldToRaw(h))
            if h is not None:
                self.fields.append(h)

        self.fields.append('__gar__')


    def save(self, path=None, safe=False, headers=None, verbose=True):
        """Save the data structure in the initial loaded file.

        :param path: ``None`` as default. If no argument is given for this \
                parameter, we will try to save to the default path defined \
                in the configuration file. Otherwise we will try to save in \
                the path given.
        :param safe: default is ``False``. If ``safe`` is ``False``, the data \
                is dumped in the initial loaded file. If ``True``, a \
                ``filename.new`` will be created to dump the data.
        :param headers: the headers of data which will be dumped. Leave default \
                to use headers defined in configuration. Otherwise, this must be \
                a list of fields.
        :param verbose: toggle verbosity
        :returns: ``None``
        """
        if path is None:
            paths = self._paths
        else:
            paths = [{ 'file' : path, 'local' : False }]

        if not paths:
            print '/!\ No path to save to!'
            return

        if headers is None:
            if self._headers:
                headers = self._headers
            else:
                print '/!\ Headers were not specified, and no headers in configuration.'
                return

        # Here we read the source from the configuration file
        for path in paths:
            if is_remote(path):
                if verbose:
                    print '/!\ Remote paths are not supported for saving (was %s).' % \
                            path['file']
                continue

            if is_archive(path):
                if verbose:
                    print '/!\ Archives are not supported for saving (was %s).' % \
                            path['file']
                continue

            file_ = S_MANAGER.handle_path(path, self.data, verbose)

            if file_ is None:
                continue

            try:
                if op.isfile(file_):
                    # File already exist!
                    if safe:
                        file_ = '%s.new' % file_

                with open(file_ , 'w') as out_fl:
                    self._dump(out_fl, headers)
            except IOError:
                if verbose:
                    print '/!\ Failed to open "%s", failing over...' % file_
            else:
                break
        else:
            # Here the loop did not break, meaning nothing was loaded
            # We will go here even if paths was []
            print '/!\ Nothing was save in: %s' % \
                    ''.join('\n(*) %s' % p['file'] for p in paths)
            return

        if verbose:
            print 'Saved to "%s".' % file_


    def _dump(self, out_fl, headers):
        """Dump the data structure in the file-like.
        """
        # Caching
        subdelimiters = self._subdelimiters
        delimiter = self._delimiter

        # We first try to sort the keys by line numbers first
        sorted_keys = sorted([(self.get(k, '__lno__'), k) for k in self] + \
                             [(lno, None) for lno in self._skipped])

        for lno, key in sorted_keys:
            if lno in self._skipped:
                out_fl.write(delimiter.join(self._skipped[lno]) + '\n')

            # Can happen for keys from _skipped
            if key not in self:
                continue

            line = []
            for h in headers:
                try:
                    if h is None:
                        # May happen for not-loaded-columns
                        line.append('')
                    elif self._isFieldDelimited(h):
                        line.append(recursive_join(self.get(key, h), subdelimiters[h]))
                    else:
                        line.append(str(self.get(key, h)))
                except KeyError:
                    # If key has no field "h", happens for incomplete data
                    line.append('')

            out_fl.write(delimiter.join(line) + '\n')



    def hasGeoSupport(self, key=None):
        """Check if data type has geocoding support.

        If a key parameter is given, check the geocode support
        of this specific key.

        :param key: if key parameter is not ``None``,
            we check the geocode support for this specific key,
            not for the general data with ``fields`` attribute
        :returns:   boolean for geocoding support

        >>> geo_t.hasGeoSupport()
        True
        >>> geo_f.hasGeoSupport()
        False

        For a specific key.

        >>> geo_o.hasGeoSupport('ORY')
        True
        >>> geo_o.set('EMPTY')
        >>> geo_o.hasGeoSupport('EMPTY')
        False
        >>> geo_o.delete('EMPTY') # avoid messing other tests
        """
        if key is None:
            fields = set(self.fields)
        else:
            fields = set(self.get(key).keys())

        for required in GEO_FIELDS:
            if required not in fields:
                return False

        return True



    def hasGrid(self):
        """Tells if an iterable of fields is indexed.

        :param fields:  the iterable of fields
        :returns:       a boolean

        >>> geo_t.hasGrid()
        True
        >>> geo_t.dropGrid()
        >>> geo_t.hasGrid()
        False
        >>> geo_t.addGrid()
        """
        return self._ggrid is not None



    def addGrid(self, radius=GRID_RADIUS, precision=5, force=False, verbose=True):
        """Create the grid for geographical indexation.

        This operation is automatically performed an initialization if there
        is geocode support in headers.

        :param radius:    the grid accuracy, in kilometers
                the ``precision`` parameter is used to define grid size
        :param precision: the hash length. This is only used if ``radius`` \
                is ``None``, otherwise this parameter (a hash length) is \
                computed from the radius
        :param force:   ``False`` by default, force grid update \
                if it already exists
        :param verbose:   toggle verbosity
        :returns:         ``None``

        >>> geo_o.addGrid(radius=50, force=True, verbose=True)
        /!\ Grid already built, overriding...
        """
        if self.hasGrid():
            if not force:
                if verbose:
                    print '/!\ Grid already built, exiting...'
                return

            elif verbose:
                print '/!\ Grid already built, overriding...'

        self._ggrid = GeoGrid(precision=precision, radius=radius, verbose=False)

        for key in self:
            lat_lng = self.getLocation(key)

            if lat_lng is None:
                if verbose:
                    if self.hasGeoSupport(key):
                        print 'No usable geocode for %s: ("%s","%s"), skipping point...' % \
                                (key, self.get(key, LAT_FIELD), self.get(key, LNG_FIELD))
                    else:
                        # We could not even display the lat/lng
                        # This can happen if incomplete key information
                        # has been supplied after loading
                        print 'No geocode support for %s: "%s", skipping point...' % \
                                (key, self.get(key))
            else:
                self._ggrid.add(key, lat_lng, verbose)



    def dropGrid(self, verbose=True):
        """Delete grid.

        :returns: ``None``

        >>> geo_t.dropGrid()
        >>> geo_t.hasGrid()
        False

        Attempt to use the grid, failure.

        >>> sorted(geo_t.findNearKey('frbve', grid=False))[0:3]
        [(0.0, 'frbve'), (7.63..., 'fr2698'), (9.07..., 'fr3065')]
        >>> sorted(geo_t.findNearKey('frbve'))[0:3]
        Traceback (most recent call last):
        ValueError: Attempting to use grid, but grid is None

        Adding the grid again.

        >>> geo_t.addGrid(radius=50, verbose=True)
        >>> sorted(geo_t.findNearKey('frbve'))[0:3]
        [(0.0, 'frbve'), (7.63..., 'fr2698'), (9.07..., 'fr3065')]
        """
        if self.hasGrid():
            self._ggrid = None
        else:
            if verbose:
                print 'No grid to drop.'



    def updateGrid(self, verbose=True):
        """Update the grid for geographical indexation.

        :param radius:    the grid accuracy, in kilometers
                the ``precision`` parameter is used to define grid size
        :param precision: the hash length. This is only used if ``radius`` \
                is ``None``, otherwise this parameter (a hash length) is \
                computed from the radius
        :param verbose:   toggle verbosity
        :returns:         ``None``

        We use the grid for a query.

        >>> sorted(geo_t.findNearKey('frbve'))[0:3]
        [(0.0, 'frbve'), (7.63..., 'fr2698'), (9.07..., 'fr3065')]

        Now we add a new key to the data.

        >>> geo_t.set('NEW_KEY_3', **{
        ...     'lat' : '45.152',
        ...     'lng' : '1.528',
        ... })

        If we run the query again, the result is wrong when
        using the grid, because it is not up-to-date.

        >>> sorted(geo_t.findNearKey('frbve'))[0:3]
        [(0.0, 'frbve'), (7.63..., 'fr2698'), (9.07..., 'fr3065')]
        >>> sorted(geo_t.findNearKey('frbve', grid=False))[0:3]
        [(0.0, 'frbve'), (0.07..., 'NEW_KEY_3'), (7.63..., 'fr2698')]

        Now we update the grid, then the query works.

        >>> geo_t.updateGrid()
        >>> sorted(geo_t.findNearKey('frbve'))[0:3]
        [(0.0, 'frbve'), (0.07..., 'NEW_KEY_3'), (7.63..., 'fr2698')]
        >>> geo_t.delete('NEW_KEY_3') # avoid messing other tests

        Note that ``updateGrid`` will not create the grid if it does not exist.

        >>> geo_f.updateGrid()
        No grid to update.
        """
        if self.hasGrid():
            radius    = self._ggrid.radius
            precision = self._ggrid.precision

            self.dropGrid(verbose=verbose)
            self.addGrid(radius=radius, precision=precision, verbose=verbose)

        else:
            if verbose:
                print 'No grid to update.'



    def get(self, key, field=None, **kwargs):
        """Simple get on the base.

        Get data on ``key`` for ``field`` information. For example
        you can get data on ``CDG`` for its ``city_code_list``.
        You can use the ``None`` as ``field`` value to get all information
        in a dictionary.
        You can give an additional keyword argument
        ``default``, to avoid ``KeyError`` on the ``key`` parameter.

        :param key:     the key of the element (like ``'SFO'``)
        :param field:   the field (like ``'name'`` or ``'iata_code'``)
        :param kwargs:  other named arguments, use 'default' to avoid \
                ``KeyError`` on ``key`` (not ``KeyError`` on ``field``). \
                Use 'ext_field' to field data from join base.
        :raises:        ``KeyError`` if the key is not in the base
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
        KeyError: "Field 'not_a_field' [for key 'frnic'] not in ['__dup__', ...
        """
        if key not in self:
            # Unless default is set, we raise an Exception
            if 'default' in kwargs:
                return kwargs['default']

            raise KeyError("Thing not found: %s" % str(key))

        if 'ext_field' in kwargs:
            return self._joinGet(key, field, kwargs['ext_field'])

        # Key is in geobase here
        if field is None:
            return self._things[key]

        try:
            res = self._things[key][field]
        except KeyError:
            raise KeyError("Field '%s' [for key '%s'] not in %s" % \
                           (field, key, sorted(self._things[key])))
        else:
            return res


    def getJoinBase(self, fields, verbose=True):
        """Get joined base from the fields who have join.

        :param fields:  the iterable of fields
        :param verbose: boolean, toggle verbosity
        :returns:       a GeoBase object or ``None`` if fields are not joined

        >>> geo_o.getJoinBase('iata_code')
        Fields "('iata_code',)" do not have join, cannot retrieve external base.
        >>> geo_o.getJoinBase('country_code') # doctest: +SKIP
        <GeoBases.GeoBaseModule.GeoBase object at 0x...>
        """
        fields = tuplify(fields)

        if not self.hasJoin(fields):
            if verbose:
                print 'Fields "%s" do not have join, cannot retrieve external base.' % str(fields)
            return

        # This is the data type of the joined base
        join_base = self._join[fields][0]

        return self._ext_bases[join_base]


    def hasJoin(self, fields=None):
        """Tells if an iterable of fields has join information.

        Default value is ``None`` for fields, this will test the
        presence of any join information.

        :param fields:  the iterable of fields
        :returns:       a boolean

        >>> geo_o.hasJoin('iata_code')
        False
        >>> geo_o.hasJoin('tvl_por_list')
        True
        >>> geo_o.hasJoin()
        True
        """
        if fields is None:
            return not not self._join

        return tuplify(fields) in self._join



    def _joinGet(self, key, fields=None, ext_field=None):
        """Get that performs join with external bases.

        :param key:     the key of the element (like ``'SFO'``)
        :param fields:  the iterable of fields (like ``'name'`` or \
                ``'iata_code'``)
        :param ext_field:  the external field we want in the external \
                base
        :raises:        ``KeyError`` if the key is not in the base
        :raises:        ``ValueError`` if ``fields`` has no join information
        :returns:       the needed information

        >>> geo_o._joinGet('CDG', 'country_code', '__key__')
        ('FR',)
        >>> geo_o._joinGet('CDG', 'country_code', 'name')
        ('France',)
        >>> geo_o._joinGet('CDG', 'name')
        Traceback (most recent call last):
        ValueError: Fields "('name',)" has no join information, available: ...
        """
        # We only work with tuple of fields for joining
        fields = tuplify(fields)

        if not self.hasJoin(fields):
            raise ValueError('Fields "%s" has no join information, available: %s' % \
                             (str(fields), self._join.keys()))

        join_base, join_fields = self._join[fields]
        ext_b = self._ext_bases[join_base]

        values = tuple(self.get(key, f) for f in fields)

        if ext_field == '__loc__':
            ext_get = ext_b.getLocation
        else:
            ext_get = lambda k : ext_b.get(k, ext_field)

        if any(self._isFieldDelimited(f) for f in fields):
            # This is the cartesian product of all possible combinations
            # of sub-delimited values
            # *iter_over_subdel* is here to create the lists from values which are
            # not embedded in a container, before given it to *product*
            comb = product(*(iter_over_subdel(v, deep=False) for v in values))

            return tuple(tuple(ext_get(k) for _, k in
                               ext_b.findWith(zip(join_fields, c)))
                         for c in comb)
        else:
            return tuple(ext_get(k) for _, k in
                         ext_b.findWith(zip(join_fields, values)))



    def getLocation(self, key, **kwargs):
        """Returns geocode as (float, float) or None.

        :param key:     the key of the element (like ``'SFO'``)
        :param kwargs:  other named arguments, use 'default' to avoid \
                ``KeyError`` on ``key`` (not ``None`` on wrong value).
        :returns:       the location, a tuple of floats like ``(lat, lng)``, or \
                ``None`` if any problem happened during execution

        >>> geo_o.getLocation('AGN')
        (57.5..., -134...)

        Behavior on unkwown key.

        >>> geo_o.getLocation('UNKNOWN')
        Traceback (most recent call last):
        KeyError: 'Thing not found: UNKNOWN'
        >>> geo_o.getLocation('UNKNOWN', default=(0, 0))
        (0, 0)
        """
        if key not in self:
            # Unless default is set, we raise an Exception
            if 'default' in kwargs:
                return kwargs['default']

            raise KeyError("Thing not found: %s" % str(key))

        try:
            loc = tuple(float(self.get(key, f)) for f in GEO_FIELDS)

        except (ValueError, TypeError, KeyError):
            # Decode geocode, if error, returns None
            # TypeError : input type is not a string, probably None
            # ValueError: could not convert to float
            # KeyError  : could not find lat or lng 'fields'
            return
        else:
            return loc



    def hasParents(self, key):
        """Tell if a key has parents.

        :param key:     the key of the element (like ``'SFO'``)
        :returns:       the number of parents

        >>> geo_o.hasParents('MRS')
        0
        >>> geo_o.hasParents('MRS@1')
        1
        >>> geo_o.hasParents('PAR')
        0
        """
        return len(self.get(key, '__par__'))


    def hasDuplicates(self, key):
        """Tell if a key has duplicates.

        :param key:     the key of the element (like ``'SFO'``)
        :returns:       the number of duplicates

        >>> geo_o.hasDuplicates('MRS')
        1
        >>> geo_o.hasDuplicates('MRS@1')
        1
        >>> geo_o.hasDuplicates('PAR')
        0
        """
        return len(self.get(key, '__dup__'))



    def getFromAllDuplicates(self, key, field=None, **kwargs):
        """Get all duplicates data, parent key included.

        :param key:     the key of the element (like ``'SFO'``)
        :param field:   the field (like ``'name'`` or ``'iata_code'``)
        :param kwargs:  other named arguments, use 'default' to avoid \
                key failure
        :returns:       the list of values for the given field iterated \
                on all duplicates for the key, including the key itself

        >>> for n in geo_o.getFromAllDuplicates('ORY', 'name'):
        ...     print(n)
        Paris Orly Airport
        >>> geo_o.getFromAllDuplicates('THA', 'name')
        ['Tullahoma Regional Airport/William Northern Field', 'Tullahoma']

        One parent, one duplicate example.

        >>> geo_o.get('THA@1', '__par__')
        ['THA']
        >>> geo_o.get('THA', '__dup__')
        ['THA@1']

        Use getFromAllDuplicates on master or duplicates gives the same
        results.

        >>> geo_o.getFromAllDuplicates('THA', '__key__')
        ['THA', 'THA@1']
        >>> geo_o.getFromAllDuplicates('THA@1', '__key__')
        ['THA@1', 'THA']

        Corner cases are handled in the same way as ``get`` method.

        >>> geo_o.getFromAllDuplicates('nnnnnnoooo', default='that')
        'that'
        >>> it = geo_o.getFromAllDuplicates('THA', field=None)
        >>> [e['__key__'] for e in it]
        ['THA', 'THA@1']
        """
        if key not in self:
            # Unless default is set, we raise an Exception
            if 'default' in kwargs:
                return kwargs['default']

            raise KeyError("Thing not found: %s" % str(key))

        # Building the list of all duplicates
        keys = [key]
        for k in self.get(key, '__dup__') + self.get(key, '__par__'):
            if k not in keys:
                keys.append(k)

        # Key is in geobase here
        if field is None:
            return [self.get(k) for k in keys]

        try:
            res = [self.get(k, field) for k in keys]
        except KeyError:
            raise KeyError("Field '%s' [for key '%s'] not in %s" % \
                           (field, key, self.get(key).keys()))
        else:
            return res



    def _findWithUsingOneIndex(self, fields, values):
        """Perform findWith using one index.
        """
        if values not in self._indexed[fields]:
            # No key matched these values for the fields
            raise StopIteration

        m = len(fields)

        for key in self._indexed[fields][values]:
            yield m, key



    def _checkIndexUsability(self, conditions, mode):
        """Check if indexes are usable for a given iterable of fields.
        """
        fields = tuple(f for f, _ in conditions)

        if self.hasIndex(fields) and mode == 'and':
            return True

        if all(self.hasIndex(f) for f in fields):
            return True

        return False



    def _findWithUsingSeveralIndex(self, conditions, mode, verbose=False):
        """Perform findWith using several indexes.
        """
        # In case conditions is an iterator
        conditions = list(conditions)

        fields = tuple(f for f, _ in conditions)
        values = tuple(v for _, v in conditions)

        if self.hasIndex(fields) and mode == 'and':
            if verbose:
                print '["%s" mode] Using index for %s: value(s) %s' % \
                        (mode, str(fields), str(values))

            # Here we use directly the multiple index to have the matching keys
            for m, key in self._findWithUsingOneIndex(fields, values):
                yield m, key


        elif all(self.hasIndex(f) for f in fields):
            if verbose:
                print '["%s" mode] Using index for %s: value(s) %s' % \
                        (mode,
                         ' and '.join(str((f,)) for f in set(fields)),
                         '; '.join(str((v,)) for v in values))

            if mode == 'or':
                # Here we use each index to check the condition on one field
                # and we return the keys matching *any* condition
                candidates = set.union(*[
                    set(k for _, k in self._findWithUsingOneIndex((f,), (v,)))
                    for f, v in conditions
                ])

                for key in candidates:
                    m = sum(self.get(key, f) == v for f, v in conditions)
                    yield m, key

            elif mode == 'and':
                # Here we use each index to check the condition on one field
                # and we keep only the keys matching *all* conditions
                candidates = set.intersection(*[
                    set(k for _, k in self._findWithUsingOneIndex((f,), (v,)))
                    for f, v in conditions
                ])

                m = len(fields)
                for key in candidates:
                    yield m, key



    def findWith(self, conditions, from_keys=None, reverse=False, mode='and', index=True, verbose=False):
        """Get iterator of all keys with particular field.

        For example, if you want to know all airports in Paris.

        :param conditions: a list of ``('field', 'value')`` conditions
        :param reverse:    we look keys where the field is *not* the \
                particular value. Note that this negation is done at \
                the lower level, before combining conditions. So if you \
                have two conditions with ``mode='and'``, expect \
                results matching not condition 1 *and* not condition 2.
        :param mode:       either ``'or'`` or ``'and'``, how to handle \
                several conditions
        :param from_keys:  if given, we will look for results from this \
                iterable of keys
        :param index:      boolean to disable index when searching
        :param verbose:    toggle verbosity during search
        :returns:          an iterable of ``(v, key)`` where ``v`` is the \
                number of matched conditions

        >>> list(geo_a.findWith([('city_code', 'PAR')]))
        [(1, 'ORY'), (1, 'TNF'), (1, 'CDG'), (1, 'BVA')]
        >>> len(list(geo_o.findWith([('comment', '')], reverse=True))) # doctest: +SKIP
        212
        >>> len(list(geo_o.findWith([('__dup__', [])]))) # doctest: +SKIP
        6264
        >>> # Counting duplicated keys
        >>> len(list(geo_o.findWith([('__par__', [])], reverse=True))) # doctest: +SKIP
        5377

        Testing indexes.

        >>> list(geo_o.findWith([('iata_code', 'MRS')], mode='and', verbose=True))
        ["and" mode] Using index for ('iata_code',): value(s) ('MRS',)
        [(1, 'MRS'), (1, 'MRS@1')]
        >>> geo_o.addIndex('iata_code', force=True)
        /!\ Index on ('iata_code',) already built, overriding...
        Built index for fields ('iata_code',)
        >>> geo_o.addIndex('location_type')
        Built index for fields ('location_type',)

        Now querying with simple indexes (dropping multiple index if it exists).

        >>> geo_o.dropIndex(('iata_code', 'location_type'), verbose=False)
        >>> list(geo_o.findWith([('iata_code', 'NCE'), ('location_type', ('A',))],
        ...                     mode='and',
        ...                     verbose=True))
        ["and" mode] Using index for ('iata_code',) and ('location_type',): value(s) ('NCE',); (('A',),)
        [(2, 'NCE')]

        Multiple index.

        >>> geo_o.addIndex(('iata_code', 'location_type'), verbose=False)
        >>> list(geo_o.findWith([('iata_code', 'NCE'), ('location_type', ('A',))],
        ...                     mode='and',
        ...                     verbose=True))
        ["and" mode] Using index for ('iata_code', 'location_type'): value(s) ('NCE', ('A',))
        [(2, 'NCE')]

        Mode "or" with index.

        >>> geo_o.addIndex('city_code_list')
        Built index for fields ('city_code_list',)
        >>> list(geo_o.findWith([('iata_code', 'NCE'), ('city_code_list', ('NCE',))],
        ...                     mode='or',
        ...                     verbose=True))
        ["or" mode] Using index for ('iata_code',) and ('city_code_list',): value(s) ('NCE',); (('NCE',),)
        [(2, 'NCE@1'), (2, 'NCE')]
        >>> list(geo_o.findWith([('iata_code', 'NCE'), ('city_code_list', ('NCE',))],
        ...                     mode='or',
        ...                     index=False,
        ...                     verbose=True))
        [(2, 'NCE'), (2, 'NCE@1')]

        Testing several conditions.

        >>> c_1 = [('city_code_list', ('PAR',))]
        >>> c_2 = [('location_type', ('H',))]
        >>> len(list(geo_o.findWith(c_1)))
        17
        >>> len(list(geo_o.findWith(c_2))) # doctest: +SKIP
        100
        >>> len(list(geo_o.findWith(c_1 + c_2, mode='and'))) # doctest: +SKIP
        2
        >>> len(list(geo_o.findWith(c_1 + c_2, mode='or'))) # doctest: +SKIP
        111
        """
        if from_keys is None:
            iter_keys = iter(self)
            is_in_keys = lambda k: k in self
        else:
            from_keys = set(from_keys)
            iter_keys = iter(from_keys)
            is_in_keys = lambda k: k in from_keys

        # In case conditions is an iterator
        conditions = list(conditions)

        # We check here the fields in conditions
        # because KeyError are catched next
        for field, _ in conditions:
            if field not in self.fields:
                raise ValueError('Conditions %s include unknown field "%s"' % \
                                 (conditions, field))

        # If we have only one condition, mode does not matter
        if len(conditions) == 1 and mode == 'or':
            mode = 'and'

        # If indexed
        if index and not reverse:
            # If this condition is not met, we do not raise StopIteration,
            # we will proceed with non-indexed code after
            if self._checkIndexUsability(conditions, mode):
                for m, key in self._findWithUsingSeveralIndex(conditions,
                                                              mode=mode,
                                                              verbose=verbose):
                    if is_in_keys(key):
                        yield m, key
                raise StopIteration


        # We set the lambda function now to avoid testing
        # reverse at each key later
        if reverse:
            pass_one = lambda a, b: a != b
        else:
            pass_one = lambda a, b: a == b

        # Handle and/or cases when multiple conditions
        if mode == 'and':
            pass_all = all
        elif mode == 'or':
            pass_all = any
        else:
            raise ValueError('"mode" argument must be in %s, was %s' % \
                             (str(['and', 'or']), mode))

        for key in iter_keys:
            if key not in self:
                # This means from_keys parameters contained unknown keys
                if verbose:
                    print 'Key %-10s and conditions %s failed in findWith, moving on...' % \
                            (key, conditions)
                continue

            matches = [pass_one(self.get(key, f), v) for f, v in conditions]
            if pass_all(matches):
                yield sum(matches), key



    def __iter__(self):
        """Returns iterator of all keys in the base.

        :returns: the iterator of all keys

        >>> list(a for a in geo_a)
        ['AGN', 'AGM', 'AGJ', 'AGH', ...
        """
        return self._things.iterkeys()


    def __contains__(self, key):
        """Test if a thing is in the base.

        :param key: the key of the element to be tested
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


    def distance(self, key0, key1):
        """Compute distance between two elements.

        This is just a wrapper between the original haversine
        function, but it is probably one of the most used feature :)

        :param key0: the first key
        :param key1: the second key
        :returns:    the distance (km)

        >>> geo_t.distance('frnic', 'frpaz')
        683.526...
        """
        return haversine(self.getLocation(key0), self.getLocation(key1))


    def _buildDistances(self, lat_lng_ref, keys):
        """
        Compute the iterable of ``(dist, keys)`` of a reference
        ``lat_lng`` and a list of keys. Keys which have not valid
        geocodes will not appear in the results.

        >>> list(geo_a._buildDistances((0, 0), ['ORY', 'CDG']))
        [(5422.74..., 'ORY'), (5455.45..., 'CDG')]
        """
        if lat_lng_ref is None:
            raise StopIteration

        for key in keys:
            # Do not fail on unknown keys
            if key not in self:
                continue

            lat_lng = self.getLocation(key)

            if lat_lng is not None:
                yield haversine(lat_lng_ref, lat_lng), key


    def findNearPoint(self, lat_lng, radius=RADIUS, from_keys=None, grid=True, double_check=True):
        """
        Returns a list of nearby things from a point (given
        latidude and longitude), and a radius for the search.
        Note that the haversine function, which compute distance
        at the surface of a sphere, here returns kilometers,
        so the radius should be in kms.

        :param lat_lng:   the lat_lng of the point (a tuple ``(lat, lng)``)
        :param radius:    the radius of the search (kilometers)
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform search.
        :param grid:      boolean, use grid or not
        :param double_check: when using grid, perform an additional check on \
            results distance, this is useful because the grid is approximate, \
            so the results are only as accurate as the grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``

        >>> # Paris, airports <= 20km
        >>> [geo_a.get(k, 'name') for d, k in
        ...  sorted(geo_a.findNearPoint((48.84, 2.367), 20))]
        ['Paris-Orly', 'Paris-Le Bourget']
        >>>
        >>> # Nice, stations <= 3km
        >>> [geo_t.get(k, 'name') for d, k in
        ...  sorted(geo_t.findNearPoint((43.70, 7.26), 3))]
        ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch']
        >>>
        >>> # Wrong geocode
        >>> sorted(geo_t.findNearPoint(None, 5))
        []

        No grid mode.

        >>> # Paris, airports <= 20km
        >>> [geo_a.get(k, 'name') for d, k in
        ...  sorted(geo_a.findNearPoint((48.84, 2.367), 20, grid=False))]
        ['Paris-Orly', 'Paris-Le Bourget']
        >>> 
        >>> # Nice, stations <= 3km
        >>> [geo_t.get(k, 'name') for d, k in
        ...  sorted(geo_t.findNearPoint((43.70, 7.26), 3, grid=False))]
        ['Nice-Ville', 'Nice-Riquier', 'Nice-St-Roch']
        >>> 
        >>> # Paris, airports <= 50km with from_keys input list
        >>> sorted(geo_a.findNearPoint((48.84, 2.367), 50,
        ...                            from_keys=['ORY', 'CDG', 'BVE'],
        ...                            grid=False))
        [(12.76..., 'ORY'), (23.40..., 'CDG')]
        """
        if from_keys is None:
            iter_keys = iter(self)
            is_in_keys = lambda k: k in self
        else:
            from_keys = set(from_keys)
            iter_keys = iter(from_keys)
            is_in_keys = lambda k: k in from_keys

        if grid and not self.hasGrid():
            raise ValueError('Attempting to use grid, but grid is None')

        if grid:
            # Using grid, from_keys is just used as post-filter
            for dist, key in self._ggrid.findNearPoint(lat_lng=lat_lng,
                                                       radius=radius,
                                                       double_check=double_check):
                if is_in_keys(key):
                    yield dist, key

        else:
            for dist, key in self._buildDistances(lat_lng, iter_keys):
                if dist <= radius:
                    yield dist, key



    def findNearKey(self, key, radius=RADIUS, from_keys=None, grid=True, double_check=True):
        """
        Same as ``findNearPoint``, except the point is given
        not by a ``(lat, lng)``, but with its key, like ``'ORY'`` or ``'SFO'``.
        We just look up in the base to retrieve latitude and longitude, then
        call ``findNearPoint``.

        :param key:       the key of the element (like ``'SFO'``)
        :param radius:    the radius of the search (kilometers)
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform search.
        :param grid:      boolean, use grid or not
        :param double_check: when using grid, perform an additional check on \
                results distance, this is useful because the grid is \
                approximate, so the results are only as accurate as the \
                grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``

        >>> sorted(geo_o.findNearKey('ORY', 10)) # Orly, por <= 10km
        [(0.0, 'ORY'), (6.94..., 'XJY'), (9.96..., 'QFC')]
        >>> sorted(geo_a.findNearKey('ORY', 50)) # Orly, airports <= 50km
        [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
        >>> sorted(geo_t.findNearKey('frnic', 3)) # Nice station, stations <= 3km
        [(0.0, 'frnic'), (2.2..., 'fr4342'), (2.3..., 'fr5737')]

        No grid.

        >>> # Orly, airports <= 50km
        >>> sorted(geo_a.findNearKey('ORY', 50, grid=False))
        [(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
        >>> 
        >>> # Nice station, stations <= 3km
        >>> sorted(geo_t.findNearKey('frnic', 3, grid=False))
        [(0.0, 'frnic'), (2.2..., 'fr4342'), (2.3..., 'fr5737')]
        >>> 
        >>> keys = ['ORY', 'CDG', 'SFO']
        >>> sorted(geo_a.findNearKey('ORY', 50, grid=False, from_keys=keys))
        [(0.0, 'ORY'), (34.8..., 'CDG')]
        """
        if from_keys is None:
            iter_keys = iter(self)
            is_in_keys = lambda k: k in self
        else:
            from_keys = set(from_keys)
            iter_keys = iter(from_keys)
            is_in_keys = lambda k: k in from_keys

        if grid and not self.hasGrid():
            raise ValueError('Attempting to use grid, but grid is None')

        if key not in self:
            raise StopIteration

        if grid:
            # Using grid, from_keys is just used as post-filter
            for dist, key in self._ggrid.findNearKey(key=key,
                                                     radius=radius,
                                                     double_check=double_check):
                if is_in_keys(key):
                    yield dist, key

        else:
            for dist, key in self.findNearPoint(lat_lng=self.getLocation(key),
                                                radius=radius,
                                                from_keys=iter_keys,
                                                grid=grid,
                                                double_check=double_check):
                yield dist, key



    def findClosestFromPoint(self, lat_lng, N=NB_CLOSEST, from_keys=None, grid=True, double_check=True):
        """
        Concept close to ``findNearPoint``, but here we do not
        look for the things radius-close to a point,
        we look for the closest thing from this point, given by
        latitude/longitude.

        :param lat_lng:   the lat_lng of the point (a tuple ``(lat, lng)``)
        :param N:         the N closest results wanted
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform \
            ``findClosestFromPoint``. This is useful when we have names and \
            have to perform a matching based on name and location \
            (see ``fuzzyFindNearPoint``).
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on \
            results distance, this is useful because the grid is \
            approximate, so the results are only as accurate as the grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``

        >>> point = (43.70, 7.26) # Nice
        >>> list(geo_a.findClosestFromPoint(point))
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint(point, N=3))
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint(point, N=1))
        [(0.56..., 'frnic')]
        >>> # Corner case, from_keys empty is not used
        >>> list(geo_t.findClosestFromPoint(point, N=2, from_keys=()))
        []
        >>> list(geo_t.findClosestFromPoint(None, N=2))
        []

        No grid.

        >>> list(geo_o.findClosestFromPoint(point, grid=False))
        [(0.60..., 'NCE@1')]
        >>> list(geo_a.findClosestFromPoint(point, grid=False))
        [(5.82..., 'NCE')]
        >>> list(geo_a.findClosestFromPoint(point, N=3, grid=False))
        [(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
        >>> list(geo_t.findClosestFromPoint(point, N=1, grid=False))
        [(0.56..., 'frnic')]

        Custom keys as search domain.

        >>> keys = ('frpaz', 'frply', 'frbve')
        >>> list(geo_t.findClosestFromPoint(point,
        ...                                 N=2,
        ...                                 grid=False,
        ...                                 from_keys=keys))
        [(482.84..., 'frbve'), (683.89..., 'frpaz')]
        """
        if from_keys is None:
            from_keys = iter(self)

        if grid and not self.hasGrid():
            raise ValueError('Attempting to use grid, but grid is None')

        if grid:
            for dist, key in self._ggrid.findClosestFromPoint(lat_lng=lat_lng,
                                                              N=N,
                                                              double_check=double_check,
                                                              from_keys=from_keys):
                yield dist, key

        else:
            iterable = self._buildDistances(lat_lng, from_keys)

            for dist, key in heapq.nsmallest(N, iterable):
                yield dist, key



    def findClosestFromKey(self, key, N=NB_CLOSEST, from_keys=None, grid=True, double_check=True):
        """
        Same as ``findClosestFromPoint``, except the point is given
        not by a ``(lat, lng)``, but with its key, like ``'ORY'`` or ``'SFO'``.
        We just look up in the base to retrieve latitude and longitude, then
        call ``findClosestFromPoint``.

        :param key:       the key of the element (like ``'SFO'``)
        :param N:         the N closest results wanted
        :param from_keys: if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform \
            ``findClosestFromKey``. This is useful when we have names and \
            have to perform a matching based on name and location \
            (see ``fuzzyFindNearPoint``).
        :param grid:    boolean, use grid or not
        :param double_check: when using grid, perform an additional check on \
                results distance, this is useful because the grid is \
                approximate, so the results are only as accurate as the \
                grid size
        :returns:       an iterable of ``(distance, key)`` like \
            ``[(3.2, 'SFO'), (4.5, 'LAX')]``

        >>> list(geo_a.findClosestFromKey('ORY')) # Orly
        [(0.0, 'ORY')]
        >>> list(geo_a.findClosestFromKey('ORY', N=3))
        [(0.0, 'ORY'), (18.80..., 'TNF'), (27.80..., 'LBG')]
        >>> # Corner case, from_keys empty is not used
        >>> list(geo_t.findClosestFromKey('ORY', N=2, from_keys=()))
        []
        >>> list(geo_t.findClosestFromKey(None, N=2))
        []

        No grid.

        >>> list(geo_o.findClosestFromKey('ORY', grid=False))
        [(0.0, 'ORY')]
        >>> list(geo_a.findClosestFromKey('ORY', N=3, grid=False))
        [(0.0, 'ORY'), (18.80..., 'TNF'), (27.80..., 'LBG')]
        >>> list(geo_t.findClosestFromKey('frnic', N=1, grid=False))
        [(0.0, 'frnic')]

        Custom keys as search domain.

        >>> keys = ('frpaz', 'frply', 'frbve')
        >>> list(geo_t.findClosestFromKey('frnic',
        ...                               N=2,
        ...                               grid=False,
        ...                               from_keys=keys))
        [(482.79..., 'frbve'), (683.52..., 'frpaz')]
        """
        if from_keys is None:
            from_keys = iter(self)

        if grid and not self.hasGrid():
            raise ValueError('Attempting to use grid, but grid is None')

        if key not in self:
            raise StopIteration

        if grid:
            for dist, key in self._ggrid.findClosestFromKey(key=key,
                                                            N=N,
                                                            double_check=double_check,
                                                            from_keys=from_keys):
                yield dist, key

        else:
            for dist, key in self.findClosestFromPoint(lat_lng=self.getLocation(key),
                                                       N=N,
                                                       from_keys=from_keys,
                                                       grid=grid,
                                                       double_check=double_check):
                yield dist, key



    @staticmethod
    def fuzzyClean(value):
        """Cleaning from LevenshteinUtils.

        >>> GeoBase.fuzzyClean('antibes ville 2')
        'antibes'
        """
        return '+'.join(clean(value))


    def _buildFuzzyRatios(self, fuzzy_value, field, min_match, keys):
        """
        Compute the iterable of (dist, keys) of a reference
        fuzzy_value and a list of keys.

        >>> list(geo_a._buildFuzzyRatios(fuzzy_value='marseille',
        ...                              field='name',
        ...                              min_match=0.80,
        ...                              keys=['ORY', 'MRS', 'CDG']))
        [(0.9..., 'MRS')]
        """
        for key in keys:
            # Do not fail on unkwown keys
            if key not in self:
                continue

            r = mod_leven(fuzzy_value, self.get(key, field))

            if r >= min_match:
                yield r, key


    def fuzzyFind(self, fuzzy_value, field, max_results=None, min_match=MIN_MATCH, from_keys=None):
        """
        Fuzzy searches are retrieving an information
        on a thing when we do not know the code.
        We compare the value ``fuzzy_value`` which is supposed to be a field
        (e.g. a city or a name), to all things we have in the base,
        and we output the best match.
        Matching is performed using Levenshtein module, with a modified
        version of the Lenvenshtein ratio, adapted to the type of data.

        Example: we look up 'Marseille Saint Ch.' in our base
        and we find the corresponding code by comparing all station
        names with ''Marseille Saint Ch.''.

        :param fuzzy_value: the value, like ``'Marseille'``
        :param field:       the field we look into, like ``'name'``
        :param max_results: max number of results, None means all results
        :param min_match:   filter out matches under this threshold
        :param from_keys:   if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform \
            ``fuzzyFind``. This is useful when we have geocodes and have to \
            perform a matching based on name and location (see \
            ``fuzzyFindNearPoint``).
        :returns:           an iterable of ``(distance, key)`` like \
                ``[(0.97, 'SFO'), (0.55, 'LAX')]``

        >>> geo_t.fuzzyFind('Marseille Charles', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyFind('paris de gaulle', 'name')[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyFind('paris de gaulle',
        ...                 field='name',
        ...                 max_results=3,
        ...                 min_match=0.55)
        [(0.78..., 'CDG'), (0.60..., 'HUX'), (0.57..., 'LBG')]

        Some corner cases.

        >>> geo_a.fuzzyFind('paris de gaulle', 'name', max_results=None)[0]
        (0.78..., 'CDG')
        >>> geo_a.fuzzyFind('paris de gaulle', 'name',
        ...                 max_results=1, from_keys=[])
        []
        """
        if from_keys is None:
            from_keys = iter(self)

        # All 'intelligence' is performed in the Levenshtein
        # module just here. All we do is minimize this distance
        iterable = self._buildFuzzyRatios(fuzzy_value, field, min_match, from_keys)

        if max_results is None:
            return sorted(iterable, reverse=True)
        else:
            return heapq.nlargest(max_results, iterable)



    def fuzzyFindNearPoint(self, lat_lng, radius, fuzzy_value, field, max_results=None, min_match=MIN_MATCH, from_keys=None, grid=True, double_check=True):
        """
        Same as ``fuzzyFind`` but with we search only within a radius
        from a geocode.

        :param lat_lng:     the lat_lng of the point (a tuple ``(lat, lng)``)
        :param radius:      the radius of the search (kilometers)
        :param fuzzy_value: the value, like ``'Marseille'``
        :param field:       the field we look into, like ``'name'``
        :param max_results: if ``None``, returns all, if an int, only \
                returns the first ones
        :param min_match:   filter out matches under this threshold
        :param from_keys:   if ``None``, it takes all keys in consideration, \
                else takes a from_keys iterable of keys to perform search.
        :param grid:        boolean, use grid or not
        :param double_check: when using grid, perform an additional check on \
                results distance, this is useful because the grid is \
                approximate, so the results are only as accurate as the \
                grid size
        :returns:           an iterable of ``(distance, key)`` like \
                ``[(0.97, 'SFO'), (0.55, 'LAX')]``

        >>> geo_a.fuzzyFind('Brussels', 'name', min_match=0.60)[0]
        (0.61..., 'BQT')
        >>> geo_a.get('BQT', 'name')  # Brussels just matched on Brest!!
        'Brest'
        >>> geo_a.get('BRU', 'name') # We wanted BRU for 'Bruxelles'
        'Bruxelles National'
        >>> 
        >>> # Now a request limited to a circle of 20km around BRU gives BRU
        >>> point = (50.9013, 4.4844)
        >>> geo_a.fuzzyFindNearPoint(point,
        ...                          radius=20,
        ...                          fuzzy_value='Brussels',
        ...                          field='name',
        ...                          min_match=0.40)[0]
        (0.46..., 'BRU')
        >>> 
        >>> # Now a request limited to some input keys
        >>> geo_a.fuzzyFindNearPoint(point,
        ...                          radius=2000,
        ...                          fuzzy_value='Brussels',
        ...                          field='name',
        ...                          max_results=1,
        ...                          min_match=0.30,
        ...                          from_keys=['ORY', 'CDG'])
        [(0.33..., 'ORY')]
        """
        if from_keys is None:
            from_keys = iter(self)

        nearest = (k for _, k in self.findNearPoint(lat_lng, radius, from_keys, grid, double_check))

        return self.fuzzyFind(fuzzy_value, field, max_results, min_match, from_keys=nearest)



    def fuzzyFindCached(self,
                       fuzzy_value,
                       field,
                       max_results=None,
                       min_match=MIN_MATCH,
                       from_keys=None,
                       verbose=False,
                       d_range=None):
        """
        Same as ``fuzzyFind`` but with a caching and bias system.

        :param fuzzy_value: the value, like ``'Marseille'``
        :param field:       the field we look into, like ``'name'``
        :param max_results: max number of results, None means all results
        :param min_match:   filter out matches under this threshold
        :param from_keys:   if ``None``, it takes all keys in consideration, \
            else takes ``from_keys`` iterable of keys to perform fuzzyFind. \
            This is useful when we have geocodes and have to perform a \
            matching based on name and location (see ``fuzzyFindNearPoint``).
        :param verbose:     display information on caching for a certain \
                range of similarity
        :param d_range:     the range of similarity
        :returns:           an iterable of ``(distance, key)`` like \
                ``[(0.97, 'SFO'), (0.55, 'LAX')]``

        >>> geo_t.fuzzyFindCached('Marseille Saint Ch.', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_a.fuzzyFindCached('paris de gaulle',
        ...                       field='name',
        ...                       verbose=True,
        ...                       d_range=(0, 1))[0]
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        (0.78..., 'CDG')
        >>> geo_a.fuzzyFindCached('paris de gaulle',
        ...                       field='name',
        ...                       min_match=0.60,
        ...                       max_results=2,
        ...                       verbose=True,
        ...                       d_range=(0, 1))
        [0.79]           paris+de+gaulle ->   paris+charles+de+gaulle (  CDG)
        [0.61]           paris+de+gaulle ->        bahias+de+huatulco (  HUX)
        [(0.78..., 'CDG'), (0.60..., 'HUX')]

        Some biasing:

        >>> geo_a.biasFuzzyCache('paris de gaulle',
        ...                      field='name',
        ...                      biased_result=[(0.5, 'Biased result')])
        >>> geo_a.fuzzyFindCached('paris de gaulle',
        ...                       field='name',
        ...                       max_results=None,
        ...                       verbose=True,
        ...                       d_range=(0, 1))
        Using bias: ('paris+de+gaulle', 'name', None, 0.75, None)
        [(0.5, 'Biased result')]
        >>> geo_a.clearFuzzyBiasCache()
        >>> geo_a.fuzzyFindCached('paris de gaulle',
        ...                       field='name',
        ...                       max_results=None,
        ...                       verbose=True,
        ...                       min_match=0.75)
        [(0.78..., 'CDG')]
        """
        if d_range is None:
            d_range = (min_match, 1.0)

        # Cleaning is for keeping only useful data
        entry = build_cache_key(self.fuzzyClean(fuzzy_value), field, max_results, min_match, from_keys)

        if entry in self._fuzzy_bias_cache:
            # If the entry is stored is our bias
            # cache, we do not perform the fuzzy search
            if verbose:
                print 'Using bias: %s' % str(entry)

            return self._fuzzy_bias_cache[entry]

        if entry not in self._fuzzy_cache:

            matches = self.fuzzyFind(*entry)

            self._fuzzy_cache[entry] = matches

            # We display information everytime a value is added to the cache
            if verbose:
                self._showFuzzyMatches(matches, fuzzy_value, field, d_range)

        return self._fuzzy_cache[entry]



    def biasFuzzyCache(self, fuzzy_value, field, max_results=None, min_match=MIN_MATCH, from_keys=None, biased_result=()):
        """
        If algorithms for fuzzy searches are failing on a single example,
        it is possible to use a first cache which will block
        the research and force the result.

        :param fuzzy_value:   the value, like ``'Marseille'``
        :param field:         the field we look into, like ``'name'``
        :param max_results:   if ``None``, returns all, if an int, only \
                returns the first ones
        :param min_match:     filter out matches under this threshold
        :param from_keys:     if ``None``, it takes all keys into \
                consideration, else takes ``from_keys`` iterable of keys \
                as search domain
        :param biased_result: the expected result
        :returns:             ``None``

        >>> geo_t.fuzzyFindCached('Marseille Saint Ch.', 'name')[0]
        (0.8..., 'frmsc')
        >>> geo_t.biasFuzzyCache('Marseille Saint Ch.',
        ...                      field='name',
        ...                      biased_result=[(1.0, 'Me!')])
        >>> geo_t.fuzzyFindCached('Marseille Saint Ch.', 'name')[0]
        (1.0, 'Me!')
        """
        # Cleaning is for keeping only useful data
        entry = build_cache_key(self.fuzzyClean(fuzzy_value), field, max_results, min_match, from_keys)

        self._fuzzy_bias_cache[entry] = biased_result


    def clearFuzzyCache(self):
        """Clear cache for fuzzy searches.

        >>> geo_t.clearFuzzyCache()
        """
        self._fuzzy_cache = {}


    def clearFuzzyBiasCache(self):
        """Clear biasing cache for fuzzy searches.

        >>> geo_t.clearFuzzyBiasCache()
        """
        self._fuzzy_bias_cache = {}



    def _showFuzzyMatches(self, matches, fuzzy_value, field, d_range):
        """Some debugging.
        """
        for d, key in matches:

            if d >= d_range[0] and d < d_range[1]:

                print "[%.2f] %25s -> %25s (%5s)" % \
                    (d,
                     self.fuzzyClean(fuzzy_value),
                     self.fuzzyClean(self.get(key, field)),
                     key)


    @staticmethod
    def phonemes(value, method='dmetaphone'):
        """Compute phonemes for any value.

        :param value:     the input value
        :param method:    change the phonetic method used
        :returns:         the phonemes

        >>> GeoBase.phonemes('sheekago')
        ['XKK', None]
        >>> GeoBase.phonemes('sheekago', 'nysiis')
        'SACAG'
        """
        get_phonemes, _ = build_get_phonemes(method)

        return get_phonemes(value)


    def phoneticFind(self, value, field, method='dmetaphone', from_keys=None, verbose=False):
        """Phonetic search.

        :param value:     the value for which we look for a match
        :param field:     the field, like ``'name'``
        :param method:    change the phonetic method used
        :param from_keys: if ``None``, it takes all keys in consideration, \
                else takes ``from_keys`` iterable of keys to perform search.
        :param verbose:   toggle verbosity
        :returns:         an iterable of (phonemes, key) matching

        >>> list(geo_o.get(k, 'name') for _, k in
        ...      geo_o.phoneticFind(value='chicago',
        ...                         field='name',
        ...                         method='dmetaphone',
        ...                         verbose=True))
        Looking for phonemes like ['XKK', None] (for "chicago")
        ['Chicago']
        >>> list(geo_o.get(k, 'name') for _, k in
        ...      geo_o.phoneticFind('chicago', 'name', 'nysiis'))
        ['Chicago']

        Alternate methods.

        >>> list(geo_o.phoneticFind('chicago', 'name', 'dmetaphone'))
        [(['XKK', None], 'CHI')]
        >>> list(geo_o.phoneticFind('chicago', 'name', 'metaphone'))
        [('XKK', 'CHI')]
        >>> list(geo_o.phoneticFind('chicago', 'name', 'nysiis'))
        [('CACAG', 'CHI')]
        """

        get_phonemes, matcher = build_get_phonemes(method)

        if from_keys is None:
            from_keys = iter(self)

        exp_phonemes = get_phonemes(value)

        if verbose:
            print 'Looking for phonemes like %s (for "%s")' % \
                    (str(exp_phonemes), value)

        for key in from_keys:
            # Do not fail on unkown keys
            if key not in self:
                continue

            phonemes = get_phonemes(self.get(key, field))

            if matcher(phonemes, exp_phonemes):
                yield phonemes, key



    def _resetData(self, key, data):
        """Reset key entry with dictionary of data.

        This method is hidden, because there if no check on
        fields types, and no check on data, which may lack
        the special fields like __key__ or __lno__, or
        contain illegal fields like ``None``.
        """
        self._things[key] = data


    def syncFields(self, mode='all', sort=True):
        """
        Iterate through the collection to look for all available fields.
        Then affect the result to ``self.fields``.

        If you execute this method, be aware that fields order may
        change depending on how dictionaries return their keys.
        To have better consistency, we automatically sort the found
        fields. You can change this behavior with the ``sort`` parameter.

        :param mode: ``'all'`` or ``'any'``, ``'all'`` will look for \
                fields shared by all keys, ``'any'`` will look for all \
                fields from all keys
        :param sort: sort the fields found
        :returns:    ``None``

        >>> from pprint import pprint
        >>> pprint(geo_t.fields)
        ['__key__',
         '__dup__',
         '__par__',
         '__lno__',
         'code',
         'lines@raw',
         'lines',
         'name',
         'info',
         'lat',
         'lng',
         '__gar__']

        Fields synchronisation, common fields for all keys.

        >>> geo_t.set('frnic', new_field='Nice Gare SNCF')
        >>> geo_t.syncFields(mode='all')
        >>> pprint(geo_t.fields) # did not change, except order
        ['__dup__',
         '__gar__',
         '__key__',
         '__lno__',
         '__par__',
         'code',
         'info',
         'lat',
         'lines',
         'lines@raw',
         'lng',
         'name']

        Fields synchronisation, all fields for all keys.

        >>> geo_t.syncFields(mode='any')
        >>> pprint(geo_t.fields) # notice the new field 'new_field'
        ['__dup__',
         '__gar__',
         '__key__',
         '__lno__',
         '__par__',
         'code',
         'info',
         'lat',
         'lines',
         'lines@raw',
         'lng',
         'name',
         'new_field']

        Restore previous state, drop new field and synchronize fields again.

        >>> geo_t.delete('frnic', 'new_field')
        >>> geo_t.syncFields()
        >>> pprint(geo_t.fields)
        ['__dup__',
         '__gar__',
         '__key__',
         '__lno__',
         '__par__',
         'code',
         'info',
         'lat',
         'lines',
         'lines@raw',
         'lng',
         'name']
        """
        if mode not in ('all', 'any'):
            raise ValueError('mode shoud be in %s, was "%s".' % \
                             (str(('all', 'any')), mode))

        if mode == 'any':
            found = set()
            for key in self:
                found = found | set(self.get(key).keys())

        else:
            # Fetching first
            for key in self:
                found = set(self.get(key).keys())
                break
            else:
                found = set()

            for key in self:
                found = found & set(self.get(key).keys())

        if sort:
            self.fields = sorted(found)
        else:
            self.fields = list(found)


    def set(self, key, **kwargs):
        """Method to manually change a value in the base.

        :param key:     the key we want to change a value of
        :param kwargs:  the keyword arguments containing new data
        :returns:      ``None``

        Here are a few examples.

        >>> geo_t.get('frnic', 'name')
        'Nice-Ville'
        >>> geo_t.set('frnic', name='Nice Gare SNCF')
        >>> geo_t.get('frnic', 'name')
        'Nice Gare SNCF'
        >>> geo_t.set('frnic', name='Nice-Ville') # tearDown

        We may even add new fields.

        >>> geo_t.set('frnic', new_field='some_value')
        >>> geo_t.get('frnic', 'new_field')
        'some_value'

        We can create just the key.

        >>> geo_t.set('NEW_KEY_1')
        >>> geo_t.get('NEW_KEY_1')
        {'__gar__': [], ..., '__lno__': 0, '__key__': 'NEW_KEY_1'}
        >>> geo_t.delete('NEW_KEY_1') # tearDown

        Examples with an empty base.

        >>> geo_f.keys()
        []

        Set a new key with a dict, then get the data back.

        >>> d = {
        ...     'code' : 'frnic',
        ...     'name' : 'Nice',
        ... }
        >>> geo_f.set('frnic', **d)
        >>> geo_f.keys()
        ['frnic']
        >>> geo_f.get('frnic', 'name')
        'Nice'

        The base fields are *not* automatically updated when setting data.

        >>> geo_f.fields
        []

        You can manually update the fields.

        >>> geo_f.syncFields()
        >>> geo_f.fields
        ['__dup__', '__gar__', '__key__', '__lno__', '__par__', 'code', 'name']
        """
        # If the key is not in the base, we add it
        if key not in self:
            self._things[key] = self._emptyData(key, lno=0)

        self._things[key].update(kwargs)



    def delete(self, key, field=None):
        """Method to manually remove a value in the base.

        :param key:   the key we want to delete
        :returns:     ``None``

        >>> data = geo_t.get('frxrn') # Output all data in one dict
        >>> geo_t.delete('frxrn')
        >>> geo_t.get('frxrn', 'name')
        Traceback (most recent call last):
        KeyError: 'Thing not found: frxrn'

        How to reverse the delete if data has been stored:

        >>> geo_t.set('frxrn', **data)
        >>> geo_t.get('frxrn', 'name')
        'Redon'

        We can delete just a field.

        >>> geo_t.delete('frxrn', 'lat')
        >>> geo_t.get('frxrn', 'lat')
        Traceback (most recent call last):
        KeyError: "Field 'lat' [for key 'frxrn'] not in ...
        >>> geo_t.get('frxrn', 'name')
        'Redon'

        And put it back again.

        >>> geo_t.set('frxrn', lat='47.65179')
        >>> geo_t.get('frxrn', 'lat')
        '47.65179'
        """
        if field is None:
            del self._things[key]
        else:
            del self._things[key][field]


    @staticmethod
    def hasTrepSupport():
        """Check if module has OpenTrep support.
        """
        return HAS_TREP_SUPPORT


    @staticmethod
    def trepSearch(fuzzy_value, trep_format='S', from_keys=None, verbose=False):
        """OpenTrep integration.

        If not hasTrepSupport(), main_trep is not defined
        and trepSearch will raise an exception if called.

        :param fuzzy_value: the fuzzy value
        :param trep_format: the format given to OpenTrep
        :param from_keys:   if ``None``, it takes all keys in consideration, \
                else takes ``from_keys`` iterable of keys to perform search.
        :param verbose:     toggle verbosity
        :returns:           an iterable of ``(distance, key)`` like \
                ``[(0.97, 'SFO'), (0.55, 'LAX')]``

        >>> if GeoBase.hasTrepSupport():
        ...     print geo_t.trepSearch('sna francisco los agneles') # doctest: +SKIP
        [(31.5192, 'SFO'), (46.284, 'LAX')]

        >>> if GeoBase.hasTrepSupport():
        ...     print geo_t.trepSearch('sna francisco', verbose=True) # doctest: +SKIP
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



def ext_split(value, split):
    """Extended split function handling None and '' splitter.

    :param value:  the value to be split
    :param split:  the splitter
    :returns:      the split value

    >>> ext_split('PAR', 'A')
    ('P', 'R')
    >>> ext_split('PAR', '')
    ('P', 'A', 'R')
    >>> ext_split('PAR', None)
    'PAR'

    Corner cases, weird input still returns iterable.

    >>> ext_split(None, ',')
    ()
    >>> ext_split('', ',')
    ()
    """
    if split is None:
        return value

    # Python split function has ''.split(';') -> ['']
    # But in this case we prefer having [] as a result
    # Also, this handles None cases, where data is missing
    if not value:
        return ()

    if split == '':
        # Here we convert a string like 'CA' into ('C', 'A')
        return tuple(value)

    return tuple(value.split(split))


def recursive_split(value, splits):
    """Recursive extended split.

    :param value:  the value to be split
    :param splits: the list of splitters
    :returns:      the split value

    >>> recursive_split('PAR^Paris/Parys', ['^', '/'])
    (('PAR',), ('Paris', 'Parys'))
    >>> recursive_split('|PAR|=', ['=', '|'])
    (('', 'PAR', ''),)

    Multiple splits on empty string should return empty tuple.

    >>> recursive_split('', ['^'])
    ()
    >>> recursive_split('', ['^', '/'])
    ()
    >>> recursive_split('', ['^', '/', ':'])
    ()
    """
    # Case where no splits
    if not splits:
        return value

    if len(splits) == 1:
        return ext_split(value, splits[0])

    if len(splits) == 2:
        return tuple(ext_split(v, splits[1])
                     for v in ext_split(value, splits[0]) if v)

    if len(splits) == 3:
        return tuple(tuple(ext_split(sv, splits[2])
                           for sv in ext_split(v, splits[1]) if sv)
                     for v in ext_split(value, splits[0]) if v)

    raise ValueError('Sub delimiter "%s" not supported.' % str(splits))


def recursive_join(value, splits, level=0):
    """recursive_join nested structures into str.

    >>> recursive_join((), ['/'])
    ''
    >>> recursive_join('T0', ['/'])
    'T0'
    >>> recursive_join(['T1', 'T1'], ['/'])
    'T1/T1'
    >>> recursive_join([('T2', 'T2'), 'T1'], ['/', ':'])
    'T2:T2/T1'
    >>> recursive_join([('T2', ['T3', 'T3']), 'T1'], ['/', ':', ','])
    'T2:T3,T3/T1'
    """
    # Case where no splits
    if not splits:
        return value

    if isinstance(value, (list, tuple, set)):
        if level >= len(splits):
            raise ValueError('Not enough splitters in %s' % str(splits))

        splitter = splits[level]
        level += 1

        return splitter.join(recursive_join(e, splits, level) for e in value)
    else:
        return str(value)


def iter_over_subdel(value, deep=False):
    """Iterator over recursive_split values.

    We iter over the sub elements of the structure.

    >>> list(iter_over_subdel(()))
    []
    >>> list(iter_over_subdel('T0'))
    ['T0']
    >>> list(iter_over_subdel(['T1', 'T1']))
    ['T1', 'T1']
    >>> list(iter_over_subdel([('T2', 'T2'), 'T1']))
    [('T2', 'T2'), 'T1']
    >>> list(iter_over_subdel([('T2', 'T2'), 'T1'], deep=True))
    ['T2', 'T2', 'T1']
    """
    if isinstance(value, (list, tuple, set)):
        for e in value:
            if not deep:
                yield e
            else:
                for ee in iter_over_subdel(e):
                    yield ee
    else:
        yield value



def tuplify(s):
    """
    Convert iterable into tuple,
    if string just put in in a tuple.

    >>> tuplify('test')
    ('test',)
    >>> tuplify(['test', 'titi'])
    ('test', 'titi')
    """
    if isinstance(s, str):
        return (s,)
    else:
        return tuple(s)



def build_get_phonemes(method):
    """Compute phonemes method and matching phonemes method.
    """
    if method == 'metaphone':
        get_phonemes = lambda s: dmeta(s)[0]
        matcher = lambda s1, s2: s1 == s2

    elif method == 'dmetaphone-strict':
        get_phonemes = dmeta
        matcher = lambda s1, s2: s1 == s2

    elif method == 'dmetaphone':
        get_phonemes = dmeta
        matcher = lambda s1, s2: set(s1) & set(s2) - set([None])

    elif method == 'nysiis':
        get_phonemes = nysiis
        matcher = lambda s1, s2: s1 == s2

    else:
        raise ValueError('Accepted methods are %s' % \
                         ['metaphone', 'dmetaphone-strict', 'dmetaphone', 'nysiis'])

    return get_phonemes, matcher



def build_cache_key(*args, **kwargs):
    """Build key for the cache of fuzzyFind, based on parameters.

    >>> build_cache_key(GeoBase.fuzzyClean('paris de gaulle'),
    ...                 'name',
    ...                 max_results=None,
    ...                 min_match=0,
    ...                 from_keys=None)
    ('paris+de+gaulle', 'name', None, None, 0)
    >>> build_cache_key(GeoBase.fuzzyClean('Antibes SNCF 2'),
    ...                 'name',
    ...                 max_results=3,
    ...                 min_match=0,
    ...                 from_keys=None)
    ('antibes', 'name', None, 3, 0)
    """
    # We handle the fact that dictionary are not sorted, but this
    # will build the smae key for parameters
    return tuple(args) + tuple(kwargs[k] for k in sorted(kwargs))



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

