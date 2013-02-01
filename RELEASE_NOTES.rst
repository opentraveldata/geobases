
=============
Release notes
=============

V4
==

+ 4.21 : multiple --exact searches with '/' separation, new --any option for and/or behavior
+ 4.20 : getKeysWhere now returns an iterable of (index, key) like any other search method
+ 4.19 : new findClosestFromKey method
+ 4.18 : adding default OSM tiles for maps
+ 4.17 : ori_por has a new field tvl_por_list, linking cities to POR
+ 4.16 : --indexes has a fourth optional parameter to toggle duplicates discarding
+ 4.15 : new cabins data, -U option to force data updates
+ 4.14 : new airlines data, with alliances
+ 4.13 : duplicates lines feature on map, __dad__ is renamed __par__, smart coloring for +/-
+ 4.12 : __dad__ is now a list, hasParents method, visualize now supports lines drawing
+ 4.11 : new bases for postal codes
+ 4.10 : new coloring scheme for markerless maps, slider to control circle size
+ 4.9  : multiple fields for global fuzzy/map defaults, markerless maps (only colored circles)
+ 4.8  : new base geonames FR and MC
+ 4.7  : new base capitals, which contains countries capitals coordinates
+ 4.6  : countries, stations, currencies and ori_por_private now have subdelimiters
+ 4.5  : big icons system, legend and lines buttons
+ 4.4  : map coloring system with third option of -M
+ 4.3  : SimpleHTTPServer is now used to serve html files
+ 4.2  : -I option now accepts arguments to support different fields on input, and exact or fuzzy
+ 4.1  : map update with circle drawings from any field with -M, new -Q header control
+ 4.0  : ori_por major update with correct city_names and full deduplication

V3
==

+ 3.40 : for --map option, we add a template with datatables
+ 3.39 : new -m option to draw points on a map
+ 3.38 : new -Q option to customize --quiet mode
+ 3.37 : new interactive with data reading from stdin (kind of awesome)
+ 3.36 : source keyword argument is now a file-like
+ 3.35 : Adding quoting feature to have csv from excel support (escaping delimiter when "")
+ 3.34 : Pypy partiall support on separate branch
+ 3.33 : Python 3 full support on separate branch
+ 3.32 : improve CLI with warnings on poor configuration, truncated symbol and white term mode
+ 3.31 : init options now overrides configuration file
+ 3.30 : ``from GeoBases import GeoBase`` works as import mechanism
+ 3.29 : changed some property names in configuration file, add discard_dups boolean
+ 3.28 : new duplicate mechanism: keep them and add @nb at the end of key
+ 3.27 : adding two office_IDs data source
+ 3.26 : autocomplete file is generated with Rake and reading YAML conf
+ 3.25 : added sub delimiters options; some refactoring
+ 3.24 : added --version for CLI; new option limit in conf to load partially the file
+ 3.23 : added autocomplete partial support for CLI
+ 3.22 : added new base for geonames_head and geonames_full, lines tracking
+ 3.21 : added new base for ori_por_private (and multi version)
+ 3.20 : outsource all airports/geonames code in separate project
+ 3.19 : outsource all webservices code in separate project
+ 3.18 : outsource all train stations generation script in separate project
+ 3.17 : added new base for locales
+ 3.16 : added new base for regions
+ 3.15 : added new base for airlines from CRB_Airline
+ 3.14 : handle multiple conditions in getKeysWhere, and/or cases
+ 3.13 : added __dup__ special field to count duplicates
+ 3.12 : new data source for currencies (wikipedia based)
+ 3.11 : added __gar__ special field to collect non documented data
+ 3.10 : added ori_por_non_iata support
+ 3.9  : added __lno__ special field for line number in the source file
+ 3.8  : reverse option for getKeysWhere, accessed through --reverse
+ 3.7  : improve Linux CLI, accept n arguments for every option
+ 3.6  : creation of __key__ for keys, new fields attribute
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

+ 1.0  : API changes: unification of grid and not grid methods


V0
==

+ 0.1  : first draft
