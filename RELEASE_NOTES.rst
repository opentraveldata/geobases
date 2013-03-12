=============
Release notes
=============

V5
==

+ 5.0 :

    + *API*: split the cache directory for each source and each version
    + *API/CLI*: add possibility to update zsh autocomplete file
    + *CLI*: removed ``-u/--update`` and ``-U/--update-forced``, now available with ``-A/--admin``
    + *API*: empty delimiter is accepted, and means we split on every char
    + *API*: ``__gar__`` special attribute no longer flatten uncollected data (now a list)
    + *API*: getLocation has a new *default* keyword argument to avoid key failure
    + *CLI*: learning mode with ``-a/--ask`` to learn of the CLI works
    + *CLI*: admin mode with ``-A/--admin`` to configure sources (persistent changes)
    + *CLI*: ``-A/--any`` is now ``-O/--or`` to control multiple ``--exact`` filters behavior
    + *CLI*: possibility to add a join clause on multiple fields with new ``-i`` argument (and possibility to ``--show`` it)
    + *API*: Added map visualization possibilities on join clauses (another arg. for ``-M`` on CLI)
    + *API*: new ``-S/--show-additional`` method to add fields to the current display
    + *API*: new getJoinBase method to give access to external base properties
    + *CLI*: cache fields analysis to speed up quiet mode
    + *CLI*: properly flatten all nested structure in quiet mode
    + *CLI*: possibility to show external fields from ``--show`` using ``field:external_field`` syntax
    + *CLI*: display join fields wih a different color
    + *API*: autoreference for autojoin to avoid loading ori_por twice
    + *API*: new ``hasJoin`` method
    + *CLI*: possibility to add subdelimiters and join clauses with ``header{base:field{subdel}`` syntax
    + *API*: multiple join clause implementation on multiple fields, integrated with subdelimiters
    + *API*: subdelimiters are no longer filled with ``None``
    + *API*: new ``updateIndex`` and ``updateGrid`` methods
    + *API*: ``addIndex`` does not update index, ``addGrid`` does not update grid
    + *API/CLI*: cache directory instead of local directory for download and extraction
    + *API*: allow ``paths`` as *GeoBase* init argument (same behavior as configuration file)
    + *CLI*: configure graph weight with ``-W/--graph-weight`` for CLI
    + *API/CLI*: typing system when graph building, ``-w/--with-types`` to toggle from CLI
    + *CLI*: if available, launch *google-chrome* instead of firefox for HTML display
    + *CLI*: ``--graph`` and ``--graph-fields`` to draw graphs
    + *API*: add graph visualization with ``graphVisualize``
    + *API*: handle local and remote archives as sources
    + *API*: make ``addGrid`` and ``dropGrid`` public methods to allow geographical re-indexation
    + *API*: HTTP failover in configuration file
    + *API*: simpler bash maintenance script now that skip is handled during loading
    + *API*: add ``skip`` directive to skip first lines
    + *CLI*: display sources and examples on ``--help``
    + *CLI*: display tips on ``--verbose`` when stdin data
    + *CLI*: ``-I`` is now slightly different, default is exact search on a default field (no longer key search, use ``__key__`` for that)
    + *CLI*: clever autocomplete for zsh on displayed fields for the different options
    + *API*: new ``fuzzyClean`` and ``phonemes`` static methods
    + *API*: possiblity to draw on the map things that are not in the *GeoBase*
    + *API*: urls input for YAML configuration
    + *API*: new ``loaded`` attribute to describe loaded data, depends on ``source`` and ``paths``
    + *API*: accepts list of paths in configuration file, failover mechanism
    + *API*: make a difference between source at ``__init__`` and path in YAML file
    + *API/CLI*: phonetic searches with dmetaphone (``-p/-P/-y`` for CLI)
    + *CLI*: ``-w/--warnings`` is now ``-v/--verbose,`` ``-v/--version`` is ``-V/--version,`` ``-g/--gridless`` is ``-d/--disable-grid``
    + *API*: more tests
    + *API*: consistent verbosity handling
    + *API*: multiple index possibility on every field with ``addIndex``, ``dropIndex``, ``hasIndex`` (use ``-i`` for CLI)
    + *API*: line number indexation when ``key_fields`` is ``None``
    + *API*: changes in methods names for better consistency, ``find*`` (iterating through data) vs ``get*`` (fetching information)

V4
==

+ 4.23 : add windows support
+ 4.22 : UI fixes, all lines are not due to duplicates, draw by default if user defined lines
+ 4.21 : multiple ``--exact`` searches with '/' separation, new ``--any`` option for and/or behavior
+ 4.20 : getKeysWhere now returns an iterable of (index, key) like any other search method
+ 4.19 : new findClosestFromKey method
+ 4.18 : adding default OSM tiles for maps
+ 4.17 : ori_por has a new field tvl_por_list, linking cities to POR
+ 4.16 : ``--indexes`` has a fourth optional parameter to toggle duplicates discarding
+ 4.15 : new cabins data, ``-U`` option to force data updates
+ 4.14 : new airlines data, with alliances
+ 4.13 : duplicates lines feature on map, ``__dad__`` is renamed ``__par__``, smart coloring for +/-
+ 4.12 : ``__dad__`` is now a list, hasParents method, visualize now supports lines drawing
+ 4.11 : new bases for postal codes
+ 4.10 : new coloring scheme for markerless maps, slider to control circle size
+ 4.9  : multiple fields for global fuzzy/map defaults, markerless maps (only colored circles)
+ 4.8  : new base geonames FR and MC
+ 4.7  : new base capitals, which contains countries capitals coordinates
+ 4.6  : countries, stations, currencies and ori_por_private now have subdelimiters
+ 4.5  : big icons system, legend and lines buttons
+ 4.4  : map coloring system with third option of ``-M``
+ 4.3  : SimpleHTTPServer is now used to serve html files
+ 4.2  : ``-I`` (uppercase i)option now accepts arguments to support different fields on input, and exact or fuzzy
+ 4.1  : map update with circle drawings from any field with ``-M,`` new ``-Q`` header control
+ 4.0  : ori_por major update with correct city_names and full deduplication

V3
==

+ 3.40 : for ``--map`` option, we add a template with datatables
+ 3.39 : new ``-m`` option to draw points on a map
+ 3.38 : new ``-Q`` option to customize ``--quiet`` mode
+ 3.37 : new interactive mode with data reading from stdin (kind of awesome)
+ 3.36 : source keyword argument is now a filelike
+ 3.35 : Adding quoting feature to have csv from excel support (escaping delimiter when "")
+ 3.34 : Pypy partial support on separate branch
+ 3.33 : Python 3 full support on separate branch
+ 3.32 : improve CLI with warnings on poor configuration, truncated symbol and white term mode
+ 3.31 : init options now overrides configuration file
+ 3.30 : ``from GeoBases import GeoBase`` works as import mechanism
+ 3.29 : changed some property names in configuration file, add discard_dups boolean
+ 3.28 : new duplicates mechanism: keep them and add @nb at the end of key
+ 3.27 : adding two new data source
+ 3.26 : autocomplete file is generated with Rake and reading YAML conf
+ 3.25 : added sub delimiters options; some refactoring
+ 3.24 : added ``--version``, new option *limit* in conf to partially load the file
+ 3.23 : added partial autocomplete support for CLI
+ 3.22 : added new base for geonames_head and geonames_full, and lines tracking when loading
+ 3.21 : added new base for ori_por (and multi version)
+ 3.20 : outsource all airports/geonames code in separate project
+ 3.19 : outsource all webservices code in separate project
+ 3.18 : outsource all train stations generation script in separate project
+ 3.17 : added new base for locales
+ 3.16 : added new base for regions
+ 3.15 : added new base for airlines
+ 3.14 : handle multiple conditions in getKeysWhere, and/or cases
+ 3.13 : added ``__dup__`` special field to count duplicates
+ 3.12 : new data source for currencies (wikipedia based)
+ 3.11 : added ``__gar__`` special field to collect non documented data
+ 3.10 : added ori_por_non_iata support
+ 3.9  : added ``__lno__`` special field for line number in the source file
+ 3.8  : reverse option for getKeysWhere, accessed through ``--reverse``
+ 3.7  : improve Linux CLI, accept n arguments for every option
+ 3.6  : creation of ``__key__`` for keys, new fields attribute
+ 3.5  : haversine method is now distance method
+ 3.4  : get method rewrite
+ 3.3  : opentrep integration in webservices
+ 3.2  : opentrep integration in GeoBaseModule
+ 3.1  : code cleanup with pylint
+ 3.0  : opentrep integration in Linux CLI


V2
==

+ 2.0  : CLI completely refactored, filtering system


V1
==

+ 1.0  : unification of grid and not grid methods for geographical searches


V0
==

+ 0.1  : first draft
