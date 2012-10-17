#!/usr/bin/python
# -*- coding: utf-8 -*-


#from distutils.core import setup 
from setuptools import setup, find_packages 

setup(
    name = 'GeoBases',
    version = '2.7.2',
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
        'http://orinet/pythonpackages'
    ],
    install_requires = [
        # Private
        'FlaskUtils',
        'Daemonify',
        'SysUtils',
        #Public
        'argparse',
        'pyyaml',
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
            'DataSources/Sources.yaml',
            "DataSources/Airports/Geonames/airports_geonames_only_clean.csv",
            "DataSources/Airports/AirportsDotCsv/ORI_Simple_Airports_Database_Table.csv",
            "DataSources/Countries/countryInfo.txt",
            "DataSources/Continents/continentCodes.txt",
            "DataSources/TrainStations/NLS/NLS_CODES_RefDataSNCF.csv",
            "DataSources/TrainStations/UIC/sncfExtract_v1.0.csv",
            "DataSources/TrainStations/DataGouvFr/RFF/RFF_gares.ids.gm.man.red.csv",
            "DataSources/Languages/iso-languagecodes.txt",
            "DataSources/TimeZones/timeZones.txt",
            "DataSources/Cities/cities15000.txt",
            "DataSources/Cities/cities5000.txt",
            "DataSources/Cities/cities1000.txt",
            "DataSources/Por/Geonames/allCountriesHead.txt",
            "DataSources/Por/Ori/ori_por_public.csv",
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
