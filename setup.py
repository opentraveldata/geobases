#!/usr/bin/python
# -*- coding: utf-8 -*-


#from distutils.core import setup 
from setuptools import setup, find_packages 

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
            'GeoBase = GeoBaseMain:main',
            'WebSrvGeoBases = WebSrvGeoBasesMain:main'
        ]
    },
    #packages=find_packages(),
    packages = [
        'GeoBases',
        'GeoBases.Webservice'
    ],
    py_modules = [
        'GeoBaseMain',
        'WebSrvGeoBasesMain'
    ],
    dependency_links = [
        'http://172.16.198.71/basket'
    ],
    install_requires = [
        # Private
        'FlaskUtils',
        'Daemonize',
        'SysUtils',
        #Public
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
