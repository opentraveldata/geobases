#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is a launcher for GeoBase.
'''



from GeoBases.GeoBaseModule import GeoBase

import os
import os.path as op
import argparse

from datetime import datetime
from termcolor import colored
import colorama

import sys


def getTermSize():

    size  = os.popen('stty size', 'r').read()

    if not size:
        return (80, 160)

    return tuple(int(d) for d in size.split())



class RotatingColors(object):

    def __init__(self):

        self._availables = [
             ('white', None),
             ('cyan', 'on_grey')
        ]

        self._current = 0


    def next(self):

        self._current += 1

        if self._current == len(self._availables):
            self._current = 0

        return self


    def get(self):

        return self._availables[self._current]


    def getEmph(self):

        return ('grey', 'on_green')


    def getHeader(self):

        return ('grey', 'on_yellow')


def display(geob, list_of_things, omit, show, important):

    if not show:
        show = ['__ref__'] + geob._headers[:]

    # Different behaviour given
    # number of results
    # We adapt the width between 25 and 40 
    #given number of columns and term width
    n = len(list_of_things)

    lim = min(40, max(25, int(getTermSize()[1] / float(n+1))))

    if n == 1:
        # We do not truncate names if only one result
        truncate = None
    else:
        truncate = lim

    c = RotatingColors()

    for f in show:
        if f not in omit:

            if f in important:
                col = c.getEmph()
            else:
                col = c.get()

            if f == '__ref__':

                sys.stdout.write('\n' + fixed_width(f, c.getHeader(), lim, truncate))

                for h, k in list_of_things:
                    if k in geob:
                        sys.stdout.write(fixed_width('%.3f' % h, c.getHeader(), lim, truncate))

            else:
                sys.stdout.write('\n' + fixed_width(f, col, lim, truncate))

                for _, k in list_of_things:
                    if k in geob:
                        sys.stdout.write(fixed_width(geob.get(k, f), col, lim, truncate))

            c.next()

    sys.stdout.write('\n')


def display_quiet(geob, list_of_things, omit, show):

    if not show:
        show = ['__ref__'] + geob._headers[:]

    for h, k in list_of_things:

        if k not in geob:
            continue

        l = []

        for f in show:
            if f not in omit:

                if f == '__ref__':
                    l.append('%.3f' % h)
                else:
                    l.append(geob.get(k, f))

        sys.stdout.write('^'.join(l) + '\n')


def fixed_width(s, col, lim=25, truncate=None):

    if truncate is None:
        truncate = 1000

    return colored((('%-' + str(lim) + 's') % s)[0:truncate], *col)


def scan_coords(u_input, geob, verbose):

    try:
        coords = tuple(float(l) for l in u_input.strip('()').split(','))

    except ValueError:
        # Scan coordinates failed, perhaps input was key
        if u_input not in geob:
            warn('key', u_input, geob._data, geob._source)
            exit(1)

        return geob.getLocation(u_input)

    else:
        if len(coords) != 2:
            error('geocode_format', u_input)

        if verbose:
            print 'Geocode recognized: (%.3f, %.3f)' % coords
        return coords


def display_on_two_cols(a_list, descriptor=sys.stdout):
    '''
    Some formatting for help.
    '''

    for p in zip(a_list[::2], a_list[1::2]):
        print >> descriptor, '\t%-15s\t%-15s' % p

    if len(a_list) % 2 != 0:
        print >> descriptor, '\t%-15s' % a_list[-1]



def warn(name, *args):

    if name == 'key':
        print >> sys.stderr, '/!\ Key %s was not in GeoBase, for data "%s" and source %s' % \
                (args[0], args[1], args[2])


def error(name, *args):

    if name == 'geocode_support':
        print >> sys.stderr, '\n/!\ No geocoding support for data type %s.' % args[0]

    elif name == 'base':
        print >> sys.stderr, '\n/!\ Wrong base "%s". You may select:' % args[0]
        display_on_two_cols(args[1], sys.stderr)

    elif name == 'property':
        print >> sys.stderr, '\n/!\ Wrong property "%s".' % args[0]
        print >> sys.stderr, 'For data type %s, you may select:' % args[1]
        display_on_two_cols(args[2], sys.stderr)

    elif name == 'field':
        print >> sys.stderr, '\n/!\ Wrong field "%s".' % args[0]
        print >> sys.stderr, 'For data type %s, you may select:' % args[1]
        display_on_two_cols(args[2], sys.stderr)

    elif name == 'geocode_format':
        print >> sys.stderr, '\n/!\ Bad geocode format: %s' % args[0]

    exit(1)


def main():

    # Filter colored signals on terminals.
    # Necessary for Windows CMD
    colorama.init()

    #
    # COMMAND LINE MANAGEMENT
    #
    parser = argparse.ArgumentParser(description='Provide POR information.')

    parser.epilog = 'Example: python %s ORY CDG' % parser.prog

    parser.add_argument('keys',
        help='Main argument (key, name, geocode depending on search mode)',
        nargs='*'
    )

    parser.add_argument('-b', '--base',
        help = '''Choose a different base, default is ori_por. Also available are
                        stations, airports, countries... Give unadmissible base 
                        and available values will be displayed.''',
        default = 'ori_por'
    )

    parser.add_argument('-f', '--fuzzy',
        help = '''Rather than looking up a key, this mode will search the best
                        match from the property given by --fuzzy-property option for
                        the argument. Limit can be specified with --fuzzy-limit option.
                        By default, the "name" property is used for the search.''',
        default = None
    )

    parser.add_argument('-L', '--fuzzy-limit',
        help = '''Specify a limit for fuzzy searches, default is 0.80.''',
        default = 0.85,
        type=float
    )

    parser.add_argument('-F', '--fuzzy-property',
        help = '''When performing a fuzzy search, specify the property to be chosen.
                        Default is "name". Give unadmissible property and available
                        values will be displayed.''',
        default = 'name'
    )

    parser.add_argument('-e', '--exact',
        help = '''Rather than looking up a key, this mode will search all keys
                        whose specific property given by --exact-property match the 
                        argument. By default, the "code" property is used 
                        for the search.''',
        default = None
    )

    parser.add_argument('-E', '--exact-property',
        help = '''When performing an exact search, specify the property to be chosen.
                        Default is "code". Give unadmissible property and available
                        values will be displayed.''',
        default = 'code'
    )

    parser.add_argument('-l', '--limit',
        help = '''Specify a limit for the number of results.
                        Default is 4, except in quiet mode where it is disabled.''',
        default = None
    )

    parser.add_argument('-r', '--radius',
        help = '''Specify a radius in km when performing geographical
                        searches. Default is 50 kms.''',
        default = 50.,
        type=float
    )

    parser.add_argument('-n', '--near',
        help = '''Rather than looking up a key, this mode will search the entries
                        in a radius from a geocode or a key. Radius is given by --radius option,
                        and geocode is passed as argument. If you wish to give a geocode as
                        input, just pass it as argument with "lat, lng" format.''',
        default = None
    )

    parser.add_argument('-c', '--closest',
        help = '''Rather than looking up a key, this mode will search the closest entries
                        from a geocode or a key. Number of results is limited by --closest-limit option,
                        and geocode is passed as argument. If you wish to give a geocode as
                        input, just pass it as argument with "lat, lng" format.''',
        default = None
    )

    parser.add_argument('-C', '--closest-limit',
        help = '''Specify a limit for closest searches, default is 10.''',
        default = 10,
        type=int
    )

    parser.add_argument('-w', '--without-grid',
        help = '''When performing a geographical search, a geographical index is used.
                        This may lead to inaccurate results in some (rare) cases. Adding this
                        option will disable the index, and browse the full data set to
                        look for the results.''',
        action='store_true'
    )

    parser.add_argument('-q', '--quiet',
        help = '''Does not provide the verbose output.''',
        action='store_true'
    )

    parser.add_argument('-v', '--verbose',
        help = '''Provides additional information from GeoBase loading.''',
        action='store_true'
    )

    parser.add_argument('-o', '--omit',
        help = '''Does not print some characteristics of POR in stdout.
                        May help to get cleaner output. "__ref__" is an
                        available keyword with the
                        other geobase headers.''',
        nargs = '+',
        default = []
    )

    parser.add_argument('-s', '--show',
        help = '''Only print some characterics of POR in stdout.
                        May help to get cleaner output. "__ref__" is an
                        available keyword with the
                        other geobase headers.''',
        nargs = '+',
        default = []
    )

    parser.add_argument('-u', '--update',
        help = '''If this option is set, before anything is done, 
                        the script will try to update the ori_por source file.''',
        action='store_true'
    )

    args = vars(parser.parse_args())



    #
    # ARGUMENTS
    #
    with_grid = not args['without_grid']
    verbose   = not args['quiet']

    if args['limit'] is None:
        # Limit was not set by user
        if args['quiet']:
            limit = None
        else:
            limit = 4

    else:
        limit = int(args['limit'])





    #
    # CREATION
    #
    if args['base'] not in GeoBase.BASES:
        error('base', args['base'], list(GeoBase.BASES.keys()))

    # Updating file
    if args['update']:
        GeoBase.update()

    if verbose:
        print 'Loading GeoBase...'

    g = GeoBase(data=args['base'], verbose=args['verbose'])



    #
    # FAILING
    #

    # Failing on lack of geocode support if necessary
    if args['near'] is not None or args['closest'] is not None:

        if not g.hasGeoSupport():
            error('geocode_support', args['base'])

    # Failing on wrong headers
    if args['exact'] is not None:

        if args['exact_property'] not in g._headers:
            error('property', args['exact_property'], args['base'], list(g._headers))

    if args['fuzzy'] is not None:

        if args['fuzzy_property'] not in g._headers:
            error('property', args['fuzzy_property'], args['base'], list(g._headers))


    #
    # MAIN
    #

    if verbose:
        before = datetime.now()

        if args['keys']:
            print 'Looking for matches from %s...' % ', '.join(args['keys'])
        else:
            print 'Looking for all matches...'

    # We start from either all keys available or keys listed by user
    if args['keys']:
        res = enumerate(args['keys'])
    else:
        res = enumerate(iter(g))

    # Keeping only keys in intermediate search
    ex_keys = lambda res : None if res is None else (e[1] for e in res)

    # We are going to chain conditions
    # res will hold intermediate results
    if args['exact'] is not None:

        res = list(enumerate(g.getKeysWhere(args['exact_property'], args['exact'], from_keys=ex_keys(res))))

        if verbose:
            print 'Applying property %s = "%s"' % (args['exact_property'], args['exact'])


    if args['near'] is not None:

        coords = scan_coords(args['near'], g, verbose)
        res = sorted(g.findNearPoint(coords, radius=args['radius'], grid=with_grid, from_keys=ex_keys(res)))

        if verbose:
            print 'Applying near %s kms' % args['radius']


    if args['closest'] is not None:

        coords = scan_coords(args['closest'], g, verbose)
        res = list(g.findClosestFromPoint(coords, N=args['closest_limit'], grid=with_grid, from_keys=ex_keys(res)))

        if verbose:
            print 'Applying closest %s' % args['closest_limit']


    if args['fuzzy'] is not None:

        res = list(g.fuzzyGet(args['fuzzy'], args['fuzzy_property'], from_keys=ex_keys(res), min_match=args['fuzzy_limit']))

        if verbose:
            print 'Applying property %s ~ "%s"' % (args['fuzzy_property'], args['fuzzy'])


    # Keeping only limit first results
    res = list(res)

    if limit is not None:
        res = res[:limit]


    #
    # DISPLAY
    #
    for (h, k) in res:
        if k not in g:
            warn('key', k, g._data, g._source)

    for field in args['show'] + args['omit']: 

        if field not in ['__ref__'] + list(g._headers):

            error('field', field, args['base'], ['__ref__'] + list(g._headers))

    # Highlighting some rows
    important = set(['code', args['fuzzy_property'], args['exact_property']])

    if verbose:

        display(g, res, set(args['omit']), args['show'], important)

        print '\nDone in %s' % (datetime.now() - before)

    else:
        display_quiet(g, res, set(args['omit']), args['show'])


if __name__ == '__main__':

    main()

