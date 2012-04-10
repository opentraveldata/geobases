#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup 
#from distutils.core import setup 

setup(
    name = 'GeoBases',
    version = '0.2',
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
    install_requires = [
        'argparse',
        'python_geohash', 
        'python_Levenshtein', 
        'Flask', 
        'tornado',
        'termcolor',
        'colorama'
    ],
    package_dir = {
        'GeoBases': 'GeoBases'
    },
    package_data = {
        'GeoBases': [
            'DataSources/*sh', 
            "DataSources/Airports/airports_geobase.csv",
            "DataSources/Airports/AirportsDotCsv/ORI_Simple_Airports_Database_Table.csv",
            "DataSources/Airports/OriPor/ori_por_public.csv",
            "DataSources/Countries/list_countries.csv",
            "DataSources/TrainStations/stations_geobase.csv",
            "DataSources/TrainStations/NLS/NLS_CODES_RefDataSNCF.csv"
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
