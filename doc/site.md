News!
-----

Version 5 has just been released. Check out the [release notes](https://github.com/opentraveldata/geobases/wiki/News)!

Introduction
------------

This project provides tools to play with geographical data. It also
works with non-geographical data, except for map visualizations :).

There are embedded data sources in the project, but you can easily play
with your own data in addition to the available ones.
After data loading, you can:

-   perform various types of queries (find *this key*, or find keys
    with *this property*)
-   make *fuzzy searches* based on string distance (find things *roughly
    named like this*)
-   make *phonetic searches* (find things *sounding like this*)
-   make *geographical searches* (find things *next to this place*)
-   get results on a map, or export it as csv data, or as a Python
    object

This is entirely written in Python. The core part is a Python package,
but there is a command line tool as well! Get it with *easy\_install*,
then you can see where are airports with *international* in their name:

```bash
$ GeoBase --fuzzy international --map
```

![](https://raw.github.com/opentraveldata/geobases/public/examples/GeoBases-map-points.png)

You can perform all types of queries:
```bash
$ GeoBase --base cities --fuzzy "san francisko" # typo here :)
```

Of course, you can use your own data for map display:
```bash
$ cat coords.csv
p1,48.22,2.33
p2,49.33,2.24
$ cat coords.csv | GeoBase --map
```

And for every other thing as well:
```bash
$ cat edges.csv
A,B
A,C
D,A
$ cat edges.csv | GeoBase --graph
```

![](https://raw.github.com/opentraveldata/geobases/public/examples/GeoBases-graph.png)

Administrate the data sources:
```bash
$ GeoBase --admin
```

We are currently gathering input from the community to define the next
version features, so do not hesitate to open issues on the [github
page](https://github.com/opentraveldata/geobases).

Documentation
-------------

Here are some useful links:

-   the [API documentation](https://geobases.readthedocs.org) for the Python package
-   the [wiki pages](https://github.com/opentraveldata/geobases/wiki/_pages) for any question!
-   the [twitter account](https://twitter.com/geobasesdev) for the latest news

Installation
------------

### Prerequisites

These prerequisites are very standard packages which are often installed
by default on Linux distributions. But make sure you have them anyway.

First you need to install *setuptools* (as *root*):

```bash
$ apt-get install python-setuptools    # for debian
$ yum install python-setuptools.noarch # for fedora
```

Then you need some basics compilation stuff to compile dependencies
(also as *root*):

```bash
$ apt-get install python-dev g++    # for debian
$ yum install python-devel gcc-c++  # for fedora
```

### From PyPI

You can install it from [PyPI](https://crate.io/packages/GeoBases):

```bash
$ easy_install --user -U GeoBases
```

There is a development version also on [PyPI](https://crate.io/packages/GeoBasesDev):

```bash
$ easy_install --user -U GeoBasesDev
```

### From Github

You can clone the project from
[github](https://github.com/opentraveldata/geobases.git):

```bash
$ git clone https://github.com/opentraveldata/geobases.git
```

Then install the package and its dependencies:

```bash
$ cd geobases
$ python setup.py install --user # for user space
```

### Final steps

A script is put in `~/.local/bin`, to be able to use it, put
that in your `~/.bashrc` or `~/.zshrc`:

```bash
export PATH=$PATH:$HOME/.local/bin
export BACKGROUND_COLOR=black # or 'white', your call
```

If you use zsh and want to have awesome *autocomplete* for the main script, add this to
your `~/.zshrc`:

```bash
# Add custom completion scripts
fpath=(~/.zsh/completion $fpath)
autoload -U compinit
compinit
```

### Python 3 support

There is *Python 3* support, you can
try it by *changing branch* before installation. Install setuptools and python3-dev as
prerequisites, then:

```bash
$ git checkout 3000
$ python3 setup.py install --user
```

You can also install the package from [PyPI](https://crate.io/packages/GeoBases3K):
```bash
$ easy_install-3.2 --user -U GeoBases3K
```

Quickstart
----------

```python
>>> from GeoBases import GeoBase
>>> geo_o = GeoBase(data='ori_por', verbose=False)
>>> geo_a = GeoBase(data='airports', verbose=False)
>>> geo_t = GeoBase(data='stations', verbose=False)
```

You can provide other values for the *data* parameter. All data sources
are documented in a [single *YAML* file](https://github.com/opentraveldata/geobases/blob/public/GeoBases/DataSources/Sources.yaml):

-   *data="ori\_por"* will load a local version of [this
    file](https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_por_public.csv),
    this is the most complete source for airports, use it!
-   *data="airports"* will use geonames as data source for airports
-   *data="stations"* will use RFF data, from [the open data
    website](http://www.data.gouv.fr), as data source for french train
    stations
-   *data="stations\_nls"* will use NLS nomenclature as data source for
    french train stations
-   *data="stations\_uic"* will use UIC nomenclature as data source for
    french train stations
-   *data="countries"* will load data on countries
-   *data="capitals"* will load data on countries capitals
-   *data="continents"* will load data on continents
-   *data="timezones"* will load data on timezones
-   *data="languages"* will load data on languages
-   *data="cities"* will load data on cities, extracted from geonames
-   *data="currencies"* will load data on currencies, extracted from
    wikipedia
-   *data="airlines"* will load data on airlines, extracted from [that
    file](https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_airlines.csv)
-   *data="cabins"* will load data on cabins
-   *data="locales"* will load data on locales
-   *data="location\_types"* will load data on location types
-   *data="feature\_classes"* will load data on feature classes
-   *data="feature\_codes"* will load data on feature codes
-   *data="ori\_por\_non\_iata"* will load some non-iata data excluded
    from *ori\_por*
-   *data="geonames\_MC"* will load MC data of geonames
-   *data="geonames\_FR"* will load FR data of geonames
-   *data="postal\_codes\_MC"* will load MC postal codes data
-   *data="postal\_codes\_FR"* will load FR postal codes data
-   *data="feed"* will create an empty instance

All features are unaware of the underlying data, and are available as
long as the headers are properly set in the configuration file, or from
the [Python API](https://geobases.readthedocs.org). For
geographical features, you have to name the latitude field `lat`, and
the longitude field `lng`.

Features
--------

### Information access

```python
>>> geo_o.get('CDG', 'city_code')
'PAR'
>>> geo_o.get('BRU', 'name')
'Bruxelles National'
>>> geo_t.get('frnic', 'name')
'Nice-Ville'
>>> geo_t.get('fr_not_exist', 'name', default='NAME')
'NAME'
```

You can put your own data in a `GeoBase` class, either by loading your
own file when creating the instance, or by creating an empty instance
and using the `set` method.

### Find things with properties

```python
>>> conditions = [('city_code', 'PAR'), ('location_type', 'H')]
>>> list(geo_o.findWith(conditions, mode='and'))
[(2, 'JDP'), (2, 'JPU')]
>>>
>>> conditions = [('city_code', 'PAR'), ('city_code', 'LON')]
>>> len(list(geo_o.findWith(conditions, mode='or')))
36
```

### Distance computation

```python
>>> geo_o.distance('CDG', 'NCE')
694.5162...
```

### Find things near a geocode

```python
>>> # Paris, airports <= 40km
>>> [k for _, k in sorted(geo_a.findNearPoint((48.84, 2.367), 40))]
['ORY', 'LBG', 'TNF', 'CDG']
>>>
>>> # Nice, stations <= 4km
>>> iterable = geo_t.findNearPoint((43.70, 7.26), 4)
>>> [geo_t.get(k, 'name') for _, k in iterable]
['Nice-Ville', 'Nice-St-Roch', 'Nice-Riquier']
```

### Find things near another thing

```python
>>> sorted(geo_a.findNearKey('ORY', 50)) # Orly, airports <= 50km
[(0.0, 'ORY'), (18.8..., 'TNF'), (27.8..., 'LBG'), (34.8..., 'CDG')]
>>>
>>> sorted(geo_t.findNearKey('frnic', 3)) # Nice station, <= 3km
[(0.0, 'frnic'), (2.2..., 'fr4342'), (2.3..., 'fr5737')]
```

### Find closest things from a geocode

```python
>>> list(geo_a.findClosestFromPoint((43.70, 7.26))) # Nice
[(5.82..., 'NCE')]
>>>
>>> list(geo_a.findClosestFromPoint((43.70, 7.26), N=3)) # Nice
[(5.82..., 'NCE'), (30.28..., 'CEQ'), (79.71..., 'ALL')]
```

### Approximate name matching

```python
>>> geo_t.fuzzyFind('Marseille Charles', 'name')[0]
(0.8..., 'frmsc')
>>> geo_a.fuzzyFind('paris de gaulle', 'name')[0]
(0.78..., 'CDG')
```

### Map display

```python
>>> geo_t.visualize()
> Affecting category None     to color blue    | volume 3190
* Added lines for duplicates linking, total 0

* Now you may use your browser to visualize:
example_map.html example_table.html

* If you want to clean the temporary files:
rm example.json ...

(['example_map.html', 'example_table.html'], 2)
```

![](https://raw.github.com/opentraveldata/geobases/public/examples/GeoBases-map-circles.png)

Standalone script
-----------------

Installation of the package will also deploy a standalone script named
`GeoBase`:

```bash
$ GeoBase ORY CDG              # query on the keys ORY and CDG
$ GeoBase --closest CDG        # closest from CDG
$ GeoBase --near LIG           # near LIG
$ GeoBase --fuzzy marseille    # fuzzy search on 'marseille'
$ GeoBase --help               # your best friend
```

![](https://raw.github.com/opentraveldata/geobases/public/examples/GeoBases-CLI-2.png)

In the previous picture, you have an overview of the command line
verbose display. Three displays are available for the command line tool:

-   the verbose display
-   the csv display with `--quiet`
-   the map display with `--map`
-   the graph display with `--graph`

With the verbose display, entries are displayed on each column, and the
available fields on each line. Fields starting with `__` like
`__field__` are special. This means they were added during data loading:

-   `__key__` is the field containing the *id* of the entry. Ids are
    defined with a list of fields in the configuration file.
-   `__dup__` is the field containing a list of duplicated keys. Indeed
    there is mechanism handling duplicated keys by default, which
    creates new keys if the key already exists in the `GeoBase`.
-   `__par__` is the field containing the parent key if the key is
    duplicated.
-   `__lno__` is the field containing the line number during loading.
-   `__gar__` is the field containing the data which was not loaded on
    the line (this can be because the line was not well formatted, or
    because there were missing headers).

More examples here, for example how to do a search on a field, like
admin\_code (`B8` is french riviera):

```bash
$ GeoBase -E adm1_code -e B8
```

Same with csv output (customize with `--show`):

```bash
$ GeoBase -E adm1_code -e B8 --quiet
```

Make a fuzzy search:

```bash
$ GeoBase --fuzzy sur mer
```

All data under 200 km from Paris:

```bash
$ GeoBase --near PAR -N 200
```

Map display for a specific GMT offset:

```bash
$ GeoBase -E gmt_offset -e 1.0 --map
```

Reading data input directly on stdin:

```bash
$ echo -e 'ORY^Orly\nCDG^Charles' | GeoBase
```
