#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Main installation file for GeoBases.
'''


#from distutils.core import setup
from setuptools import setup

setup(
    name = 'GeoBases',
    version = '3.19.2',
    author = 'Alex Prengere',
    author_email = 'alex.prengere@amadeus.com',
    url = 'http://mediawiki.orinet.nce.amadeus.net/index.php/GeoBases',
    #license = open('COPYING').read(),
    description = 'Some geographical functions.',
    long_description = open('README').read(),
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
        'http://orinet/pythonpackages'
    ],
    install_requires = [
        # Private
        'OpenTrepWrapper>=0.5',
        # Public - core
        'pyyaml',
        'python_geohash', 
        'python_Levenshtein', 
        # Public - CLI
        'argparse',
        'termcolor',
        'colorama'
    ],
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
