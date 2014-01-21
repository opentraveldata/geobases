=============
Release notes
=============

V6
==

+ 6.0 :

    + *API*: new data source for *aircraft* (based on OpenTravelData)
    + *API*: replace *ori_por_non_iata* source with *ori_por_no_longer_valid* source
    + *API*: new data source for *regions* (based on OpenTravelData)
    + *API*: ``city_code`` is now a splitted field for *ori_por* data source
    + *API*: speed and memory optimizations on ``findWith`` and ``findNear*`` queries
    + *API*: remove ``force_str`` option on ``findWith`` query
    + *CLI*: new ``-3/--3d`` option to enable *3D* visualizations
    + *API*: add WebGL-based 3D globe visualization
    + *CLI*: when doing searches from CLI, automatically convert delimited fields into their raw version
    + *CLI*: in ``--quiet`` mode, subdelimited fields are always dumped using their raw version
    + *API*: added private methods to handle fields (``isFieldDelimited``, ``isFieldSpecial``, ...)
    + *API*: refactor core Python part using mixins (new ``VisualMixinModule``)
    + *CLI*: new ``-D/--dashboard-options`` option to control the dashboard display
    + *CLI*: ``-D/--output-dir`` option is now ``-o/--output-dir``
    + *CLI*: ``-o/--omit`` option is now ``-x/--exclude``
    + *CLI*: new ``--port`` option to change the port for ``SimpleHTTPServer``, useful when running multiple instances
    + *CLI*: for ``SimpleHTTPServer``, no longer use *8000* port (too mainstream :D), now runs on port *4135*
    + *CLI*: for temporary files, new default is to put them in a separate ``tmpviz/`` local directory
    + *CLI*: new ``-d/--dashboard`` option for *dashboard* display (aggregated view)
    + *API*: new ``dashboardVisualize`` method for *dashboard* display (aggregated view)
    + *CLI*: ``-d/--disable-grid`` is now ``--no-grid`` (no short option)
    + *API*: new ``save`` method to store in the source file the current structure (using ``_skipped`` property)

V5
==

+ 5.0 :

    + *API*: fix failures on *Google App Engine* due to non persistent filesystem
    + *API*: new ``syncFields`` method to synchronize global fields from underlying data
    + *API*: ``set`` and ``setFromDict`` have been combined into one ``set`` method, using the keyword argument syntax
    + *CLI*: add ``-D/--output-dir`` option to configure directory output
    + *API*: add ``output_dir`` option to ``visualize`` and ``graphVisualize``
    + *API*: split the cache directory for each source and each version
    + *API/CLI*: add possibility to update zsh autocomplete file
    + *CLI*: removed ``-u/--update`` and ``-U/--update-forced``, now available with ``-A/--admin``
    + *API*: empty delimiter is accepted, and means we split on every char
    + *API*: ``__gar__`` special attribute no longer flatten uncollected data (now a list)
    + *API*: ``getLocation`` has a new *default* keyword argument to avoid key failure
    + *CLI*: learning mode with ``-a/--ask`` to learn of the CLI works
    + *CLI*: admin mode with ``-A/--admin`` to configure sources (persistent changes)
    + *CLI*: ``-A/--any`` is now ``-O/--or`` to control multiple ``--exact`` filters behavior
    + *CLI*: possibility to add a join clause on multiple fields with new ``-i`` argument (and possibility to ``--show`` it)
    + *API*: add map visualization possibilities on join clauses (another arg. for ``-M`` on CLI)
    + *API*: new ``-S/--show-additional`` method to add fields to the current display
    + *API*: new ``getJoinBase`` method to give access to external base properties
    + *CLI*: cache fields analysis to speed up quiet mode
    + *CLI*: properly flatten all nested structure in quiet mode
    + *CLI*: possibility to show external fields from ``--show`` using ``field:external_field`` syntax
    + *CLI*: display join fields wih a different color
    + *API*: autoreference for autojoin to avoid loading *ori_por* source twice
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
    + *CLI*: new ``--graph`` and ``--graph-fields`` options to draw graphs (like force directed graphs)
    + *API*: add graph visualization with ``graphVisualize``
    + *API*: handle local and remote archives as sources
    + *API*: make ``addGrid`` and ``dropGrid`` public methods to allow geographical re-indexation
    + *API*: HTTP failover in configuration file
    + *API*: simpler bash maintenance script now that skip is handled during loading
    + *API*: add ``skip`` directive to skip first lines
    + *CLI*: display sources and examples on ``--help``
    + *CLI*: display tips on ``--verbose`` when stdin data
    + *CLI*: change for ``-I``, default is exact search on a default field (no longer key search, use ``__key__`` for that)
    + *CLI*: clever autocomplete for zsh on displayed fields for the different options
    + *API*: new ``fuzzyClean`` and ``phonemes`` static methods
    + *API*: possiblity to draw on the map things that are not in the *GeoBase*
    + *API*: urls input for *YAML* configuration
    + *API*: new ``loaded`` attribute to describe loaded data, depends on ``source`` and ``paths``
    + *API*: accepts list of paths in configuration file, failover mechanism
    + *API*: make a difference between source at ``__init__`` and path in *YAML* file
    + *API/CLI*: phonetic searches with dmetaphone (``-p/-P/-y`` for CLI)
    + *CLI*: ``-w/--warnings => -v/--verbose``, ``-v/--version => -V/--version``, ``-g/--gridless => -d/--disable-grid``
    + *API*: more tests
    + *API*: consistent verbosity handling
    + *API*: multiple index possibility on every field with ``addIndex``, ``dropIndex``, ``hasIndex`` (use ``-i`` 5th argument)
    + *API*: line number indexation when ``key_fields`` is ``None``
    + *API*: changes in methods names for better consistency, ``find*`` (iterating through data) vs ``get*`` (fetching information)

V4
==

+ 4.23 : add Windows support
+ 4.22 : UI fixes, all lines are not due to duplicates, draw by default if user defined lines
+ 4.21 : multiple ``-e/--exact`` searches with ``/`` separation, new ``-A/--any`` option for and/or behavior
+ 4.20 : ``getKeysWhere`` now returns an iterable of ``(index, key)`` like any other search method
+ 4.19 : new ``findClosestFromKey`` method
+ 4.18 : adding default *OpenStreetMaps* tiles for maps with ``-m/--map``
+ 4.17 : *ori_por* has a new field *tvl_por_list*, linking cities to points of reference
+ 4.16 : ``-i/--indexes`` has a fourth optional parameter to toggle duplicates discarding
+ 4.15 : new *cabins* data, ``-U/--udpate-forced`` option to force data updates
+ 4.14 : new *airlines* data, with alliances
+ 4.13 : duplicates lines feature on map, ``__dad__`` is renamed ``__par__``, smart coloring for +/-
+ 4.12 : ``__dad__`` is now a list, new ``hasParents`` method, visualize now supports lines drawing
+ 4.11 : new source for *postal codes*
+ 4.10 : new coloring scheme for markerless maps, slider to control circle size
+ 4.9  : multiple fields for global fuzzy/map defaults, markerless maps (only colored circles)
+ 4.8  : new source *geonames_FR* and *geonames_MC*
+ 4.7  : new source *capitals*, which contains countries capitals coordinates
+ 4.6  : countries, stations, currencies and ori_por_private now have *subdelimiters*
+ 4.5  : big icons system, legend and lines buttons
+ 4.4  : map coloring system with third option of ``-M/--map-options``
+ 4.3  : *SimpleHTTPServer* is now used to serve html files
+ 4.2  : ``-I/--interactive-query`` (uppercase ``-i``) accepts arguments to support different fields on input, and exact or fuzzy
+ 4.1  : map update with circle drawings from any field with ``-M/--map-options``, new ``-Q/--quiet-options`` header control
+ 4.0  : *ori_por* major update with correct city_names and full deduplication

V3
==

+ 3.40 : for ``-m/--map`` option, we add a template with datatables
+ 3.39 : new ``-m/--map`` option to draw points on a map
+ 3.38 : new ``-Q/--quiet-options`` option to customize ``-q/--quiet`` mode
+ 3.37 : new interactive mode with data reading from stdin
+ 3.36 : ``source`` keyword argument is now a filelike
+ 3.35 : Adding *quoting* feature to have csv from excel support (escaping delimiter when inside quotes)
+ 3.34 : *Pypy* partial support on separate branch
+ 3.33 : *Python 3* full support on separate branch
+ 3.32 : improve CLI with warnings on poor configuration, truncated symbol and white term mode
+ 3.31 : init options now overrides configuration file
+ 3.30 : ``from GeoBases import GeoBase`` works as import mechanism
+ 3.29 : changed some property names in configuration file, add *discard_dups* boolean
+ 3.28 : new duplicates mechanism: keep them and add @nb at the end of key
+ 3.27 : adding new data sources
+ 3.26 : autocomplete file is generated with *Rake* and reading *YAML* conf
+ 3.25 : add *subdelimiters* option
+ 3.24 : add ``-v/--version``, new option *limit* in conf to partially load the file
+ 3.23 : add partial autocomplete support for CLI
+ 3.22 : add new source for *geonames_head* and *geonames_full*, and lines tracking when loading
+ 3.21 : add new source for *ori_por* (and multi version)
+ 3.20 : outsource all airports/geonames code in separate project
+ 3.19 : outsource all webservices code in separate project
+ 3.18 : outsource all train stations generation script in separate project
+ 3.17 : add new source for *locales*
+ 3.16 : add new source for *regions*
+ 3.15 : add new source for *airlines*
+ 3.14 : handle multiple conditions in ``getKeysWhere``, and/or cases
+ 3.13 : add ``__dup__`` special field to count duplicates
+ 3.12 : new data source for *currencies* (based on wikipedia)
+ 3.11 : add ``__gar__`` special field to collect non documented data
+ 3.10 : add new source *ori_por_non_iata*
+ 3.9  : add ``__lno__`` special field for line number in the source file
+ 3.8  : reverse option for ``getKeysWhere``, accessed through ``--reverse``
+ 3.7  : improve Linux CLI, accept *n* arguments for every option accepting free text values
+ 3.6  : creation of ``__key__`` for keys, new ``fields`` attribute to collect all available fields
+ 3.5  : ``haversine`` method is now ``distance`` method
+ 3.4  : ``get`` method rewrite
+ 3.3  : *OpenTrep* integration in webservices
+ 3.2  : *OpenTrep* integration in *GeoBaseModule*
+ 3.1  : code cleanup with *pylint*
+ 3.0  : *OpenTrep* integration in CLI


V2
==

+ 2.0  : CLI completely refactored, filtering system


V1
==

+ 1.0  : unification of grid and not grid methods for geographical searches


V0
==

+ 0.1  : first draft
