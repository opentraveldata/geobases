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
    version = '3.21.3',
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
            "DataSources/Sources.yaml",
            "DataSources/CheckDataUpdates.sh",
            "DataSources/*/*.csv",
            "DataSources/*/*.txt",
            "DataSources/*/*/*.csv",
            "DataSources/*/*/*.txt",
        ]
    },
    #scripts = [
    #    'GeoBases/DataSources/CheckDataUpdates.sh'
    #],
    data_files = [
        ('test', [
            'test/test_GeoBases.py'
        ])
    ]
)
