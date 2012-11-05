#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Main installation file for GeoBases.
'''

from setuptools import setup
from os import getenv
from sys import stderr

INSTALL_REQUIRES = [
    # Public - core
    'pyyaml',
    'python_geohash',
    'python_Levenshtein',
    # Public - CLI
    'argparse',
    'termcolor',
    'colorama'
]

EXTRAS_REQUIRE = {
    # Private
    'OpenTrep': ['OpenTrepWrapper>=0.5']
}

# Managing OpenTrep dependency
WITH_OPENTREP = getenv('WITH_OPENTREP', None)

if WITH_OPENTREP:
    # Forcing OpenTrepWrapper support
    INSTALL_REQUIRES.extend(EXTRAS_REQUIRE['OpenTrep'])

    print >> stderr, '/!\ Adding "%s" to mandatory dependencies' % \
            str(EXTRAS_REQUIRE['OpenTrep'])
else:
    print >> stderr, '/!\ Installing without "%s"' % \
            str(EXTRAS_REQUIRE['OpenTrep'])


setup(
    name = 'GeoBases',
    version = '3.19.3',
    author = 'Alex Prengere',
    author_email = 'alex.prengere@amadeus.com',
    url = 'http://mediawiki.orinet.nce.amadeus.net/index.php/GeoBases',
    description = 'Some geographical functions.',
    ## This line induces bugs because it lacks the file relative path
    #long_description = open('README').read(),
    #
    # Manage standalone scripts
    entry_points = {
        'console_scripts' : [
            'GeoBase = GeoBaseMain:main'
        ]
    },
    #packages=find_packages(),
    packages = [
        'GeoBases'
    ],
    py_modules = [
        'GeoBaseMain'
    ],
    dependency_links = [
        'http://oridist.orinet/python/'
    ],
    install_requires = INSTALL_REQUIRES,
    extras_require   = EXTRAS_REQUIRE,
    package_dir = {
        'GeoBases': 'GeoBases'
    },
    package_data = {
        'GeoBases': [
            'DataSources/Sources.yaml',
            "DataSources/Airports/Geonames/airports_geonames_only_clean.csv",
            "DataSources/Airports/AirportsDotCsv/ORI_Simple_Airports_Database_Table.csv",
            "DataSources/Countries/countryInfo.txt",
            "DataSources/Continents/continentCodes.txt",
            "DataSources/TrainStations/NLS/NLS_CODES_RefDataSNCF.csv",
            "DataSources/TrainStations/UIC/sncfExtract_v1.0.csv",
            "DataSources/TrainStations/DataGouvFr/RFF_gares.ids.gm.man.red.csv",
            "DataSources/Languages/iso-languagecodes.txt",
            "DataSources/TimeZones/timeZones.txt",
            "DataSources/Cities/cities15000.txt",
            "DataSources/Cities/cities5000.txt",
            "DataSources/Cities/cities1000.txt",
            "DataSources/Por/Geonames/allCountriesHead.txt",
            "DataSources/Por/Ori/ori_por_public.csv",
            "DataSources/Por/Ori/ori_por_non_iata.csv",
            "DataSources/Currencies/wiki_source_ISO_4217.csv", # Currencies
            "DataSources/Airlines/CRB_AIRLINE.csv",
            "DataSources/Regions/regions.csv",
            "DataSources/Locales/locales.csv",
            "DataSources/LocationTypes/location_types.csv",
            "DataSources/Por/Ori/CheckOriPorUpdates.sh"
        ]
    },
    #scripts = [
    #    'GeoBases/DataSources/CheckOriPorUpdates.sh'
    #],
    data_files = [
        ('test', [
            'test/test_GeoBases.py'
        ])
    ]
)
