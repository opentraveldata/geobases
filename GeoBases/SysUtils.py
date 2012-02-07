#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is a set of functions useful to manipulate the Python path,
and provides generic functions to handle path names.

Main functions:

    - *getAbsDirname*: build the directory path.
    - *localToFile*: build the path when we have a file path and a relative
      path from this file path.
    - *addTopLevel*: this function adds recursively the parent directories,
      in the Python path.

Examples::

    >>> getAbsDirname('here/test.py') #doctest: +SKIP
    'C:\\Documents and Settings\\aprengere\\workspace\\network_connections\\tools\\test\\here'
    >>>
    >>> localToFile('here/test.py', 'source.csv') #doctest: +SKIP
    'C:\\Documents and Settings\\aprengere\\workspace\\network_connections\\tools\\test\\here\\source.csv'
    >>>
    >>> addTopLevel(__file__, toplevel=2)

'''

import os
import sys


def getAbsDirname(filepath):
    '''
    Get the real directory name

    :param filepath: the absolute file path
    :returns: the path

    >>> getAbsDirname('here/test.py')  #doctest: +SKIP
    'C:\\Documents and Settings\\aprengere\\workspace\\network_connections\\tools\\test\\here'
    '''

    dirname = os.path.dirname(filepath)
    if dirname == '':
        dirname = '.'

    return os.path.realpath(dirname)


def localToFile(filepath, localpath):
    '''
    Build the path when we have a file path and a relative
    path from this file path.
    Useful when manipulating static files loaded by Python classes.

    :param filepath: the file path we want to add the parents in the path
    :param localpath: the relative path from this file path
    :returns: the path

    >>> localToFile('here/test.py', 'source.csv') #doctest: +SKIP
    'C:\\Documents and Settings\\aprengere\\workspace\\network_connections\\tools\\test\\here\\source.csv'
    '''

    return os.path.join(getAbsDirname(filepath), localpath)



def _addDir(dirname):
    '''
    This function adds the directory *dirname*
    in the python path.

    :param dirname: the directory we want to add in the path
    :returns: None

    >>> print sys.path
    [...
    >>> _addDir('.')
    >>> print sys.path[-1] #doctest: +SKIP
    .
    '''

    if dirname not in sys.path:
        sys.path.append(dirname)



def _upDir(dirname):
    '''
    This function returns the parent directory of *dirname*.

    :param dirname: the directory we want to add the parent in the path
    :returns: None

    >>> _upDir('toto/test')
    'toto'
    '''

    return os.path.split(dirname)[0]


def addTopLevel(filepath, toplevel=1):
    '''
    This function adds recursively the parent directories *filepath*,
    in the python path.

    :param filepath: the file path we want to add the parents in the path
    :param toplevel: the level we want to reach, 1 means the parent
    :returns: None

    >>> addTopLevel('.', toplevel=2)
    '''

    dirname = getAbsDirname(filepath)

    for _ in xrange(toplevel):
        dirname = _upDir(dirname)
        _addDir(dirname)





def _test():
    '''
    When called directly, launching doctests.
    '''
    import doctest

    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE )
            #doctest.IGNORE_EXCEPTION_DETAIL)

    globs = {
    }

    doctest.testmod(optionflags=opt,
                    extraglobs=globs,
                    verbose=False)


if __name__ == '__main__':
    _test()

