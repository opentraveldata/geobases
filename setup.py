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
            'DataSources/*/*csv', 
            'DataSources/*/*/*csv'
        ]
    }
    #data_files = [
    #    ('GeoBases', ['README', 'COPYING', 'setup.py'])
    #],
    #scripts = [
    #    'GeoBases/DataSources/CheckOriPorUpdates.sh'
    #]

)
