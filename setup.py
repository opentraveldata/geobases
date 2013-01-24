#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Main installation file for GeoBases.
'''

from __future__ import with_statement

from setuptools import setup
from os import getenv
import os.path as op
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
    'OpenTrep': ['OpenTrepWrapper>=0.6']
}

DEPENDENCY_LINKS = [
    # That one is a fork supporting Python 3
    'https://github.com/wor/python-Levenshtein/tarball/master#egg=python-Levenshtein-0.10.2.tar.gz',
    #'http://github.com/miohtama/python-Levenshtein/tarball/master#egg=python-Levenshtein-0.10.2.tar.gz'
]
DEPENDENCY_LINKS_EXTRAS = {
    'OpenTrep' : ['https://github.com/trep/wrapper/tarball/master#egg=OpenTrepWrapper-0.7.tar.gz']
}

# Managing OpenTrep dependency
WITH_OPENTREP = getenv('WITH_OPENTREP', None)

if WITH_OPENTREP == '1':
    # Forcing OpenTrepWrapper support
    INSTALL_REQUIRES.extend(EXTRAS_REQUIRE['OpenTrep'])
    DEPENDENCY_LINKS.extend(DEPENDENCY_LINKS_EXTRAS['OpenTrep'])

    print('/!\ Adding "%s" to mandatory dependencies' % \
            str(EXTRAS_REQUIRE['OpenTrep']), file=stderr)
else:
    print('/!\ Installing without "%s"' % \
            str(EXTRAS_REQUIRE['OpenTrep']), file=stderr)


try:
    # monkey patch: Crack SandboxViolation verification from
    # http://www.cubicweb.org/1422923
    #import setuptools.command.easy_install # only if easy_install avaible
    from setuptools.sandbox import DirectorySandbox as DS

    def _ok(*_):
        """Return True if ``path`` can be written during installation."""
        return True

    DS._ok = _ok

except ImportError:
    raise


# local files handling
def local(rel_path, root_file=__file__):
    """Handle local paths.
    """
    return op.join(op.realpath(op.dirname(root_file)), rel_path)

with open(local('VERSION')) as fl:
    VERSION = fl.read().rstrip()

with open(local('README')) as fl:
    LONG_DESCRIPTION = fl.read()

setup(
    name = 'GeoBases3K',
    version = VERSION,
    author = 'Alex Prengere',
    author_email = 'alex.prengere@amadeus.com',
    url = 'http://mediawiki.orinet.nce.amadeus.net/index.php/GeoBases',
    description = 'Provides data services.',
    long_description = LONG_DESCRIPTION,
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
    dependency_links = DEPENDENCY_LINKS,
    install_requires = INSTALL_REQUIRES,
    extras_require   = EXTRAS_REQUIRE,
    package_dir = {
        'GeoBases': 'GeoBases'
    },
    package_data = {
        'GeoBases': [
            "DataSources/Sources.yaml",
            "DataSources/CheckDataUpdates.sh",
            "MapAssets/*",
            "TablesAssets/*",
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
        # Tests should not be exported
        #('test', [
        #    'test/test_GeoBases.py'
        #]),
        # Will create dir if needed
        (op.join(getenv('HOME'), '.zsh/completion/'), [
            'completion/_GeoBase'
        ])
    ]
)

