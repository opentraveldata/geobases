#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This module is a launcher for GeoBase.
'''

from sys import stdin, stdout, stderr
import os

import pkg_resources
from datetime import datetime
from math import ceil
from itertools import izip_longest, chain
import textwrap

# Not in standard library
from termcolor import colored
import colorama
import argparse # in standard libraray for Python >= 2.7

# Private
from GeoBases import GeoBase



def checkPath(command):
    '''
    This checks if a command is in the PATH.
    '''
    path = os.popen('which %s 2> /dev/null' % command, 'r').read()

    if path:
        return True
    else:
        return False


def getObsoleteTermSize():
    '''
    This gives terminal size information using external
    command stty.
    This function is not great since where stdin is used, it
    raises an error.
    '''
    size = os.popen('stty size 2>/dev/null', 'r').read()

    if not size:
        return (80, 160)

    return tuple(int(d) for d in size.split())


def getTermSize():
    '''
    This gives terminal size information.
    '''
    env = os.environ

    def ioctl_GWINSZ(fd):
        '''Read terminal size.'''
        try:
            import fcntl, termios, struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except IOError:
            return
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except IOError:
            pass

    if not cr:
        cr = env.get('LINES', 25), env.get('COLUMNS', 80)

    return int(cr[0]), int(cr[1])


class RotatingColors(object):
    '''
    This class is used for generating alternate colors
    for the Linux output.
    '''
    def __init__(self, background):

        if background == 'black':
            self._availables = [
                 ('cyan',  None,      []),
                 ('white', 'on_grey', []),
            ]

        elif background == 'white':
            self._availables = [
                 ('grey', None,       []),
                 ('blue', 'on_white', []),
            ]

        else:
            raise ValueError('Accepted background color: "black" or "white", not "%s".' % \
                             background)

        self._background = background
        self._current    = 0


    def next(self):
        '''We increase the current color.
        '''
        self._current += 1

        if self._current == len(self._availables):
            self._current = 0


    def get(self):
        '''Get current color.'''
        return self._availables[self._current]


    def convertRaw(self, col):
        '''Get special raw color. Only change foreground color.
        '''
        current    = list(col)
        current[0] = 'yellow' if self._background == 'black' else 'green'
        return tuple(current)


    @staticmethod
    def convertBold(col):
        '''Get special field color. Only change bold type.
        '''
        current    = list(col)
        current[2] = ['bold']
        return tuple(current)


    @staticmethod
    def getEmph():
        '''Get special emphasized color.'''
        return ('white', 'on_blue', [])


    @staticmethod
    def getHeader():
        '''Get special header color.'''
        return ('red', None, [])


    @staticmethod
    def getSpecial():
        '''Get special property color.'''
        return ('magenta', None, [])



def fmt_ref(ref, ref_type, no_symb=False):
    '''
    Display the __ref__ depending on its type.
    '''
    if ref_type == 'distance':
        if no_symb:
            return '%.3f' % ref
        return '%.2f km' % ref

    if ref_type == 'percentage':
        if no_symb:
            return '%.3f' % ref
        return '%.1f %%' % (100 * ref)

    if ref_type == 'index':
        return '%s' % int(ref)

    raise ValueError('ref_type %s was not allowed' % ref_type)



def display(geob, list_of_things, omit, show, important, ref_type):
    '''
    Main display function in Linux terminal, with
    nice color and everything.
    '''
    if not list_of_things:
        stdout.write('\nNo elements to display.\n')
        return

    if not show:
        show = ['__ref__'] + geob.fields[:]

    # Building final shown headers
    show_wo_omit = [f for f in show if f not in omit]

    # Different behaviour given number of results
    # We adapt the width between MIN_CHAR_COL and MAX_CHAR_COL
    # given number of columns and term width
    n   = len(list_of_things)
    lim = int(getTermSize()[1] / float(n + 1))
    lim = min(MAX_CHAR_COL, max(MIN_CHAR_COL, lim))

    if n == 1:
        # We do not truncate names if only one result
        truncate = None
    else:
        truncate = lim

    c = RotatingColors(BACKGROUND_COLOR)

    for f in show_wo_omit:

        if f in important:
            col = c.getEmph()
        elif f == '__ref__':
            col = c.getHeader()
        elif str(f).startswith('__'):
            col = c.getSpecial() # For special fields like __dup__
        else:
            col = c.get()

        if str(f).endswith('@raw'):
            col = c.convertRaw(col)  # For @raw fields

        # Fields on the left
        stdout.write('\n' + fixed_width(f, c.convertBold(col), lim, truncate))

        if f == '__ref__':
            for h, _ in list_of_things:
                stdout.write(fixed_width(fmt_ref(h, ref_type), col, lim, truncate))
        else:
            for _, k in list_of_things:
                stdout.write(fixed_width(geob.get(k, f), col, lim, truncate))

        next(c)

    stdout.write('\n')


def display_quiet(geob, list_of_things, omit, show, ref_type, lim):
    '''
    This function displays the results in programming
    mode, with --quiet option. This is useful when you
    want to use use the result in a pipe for example.
    '''

    if not show:
        # Temporary
        t_show = ['__ref__'] + geob.fields[:]

        # In this default case, we remove splitted valued if
        # corresponding raw values exist
        show = [f for f in t_show if '%s@raw' % f not in t_show]

    # Building final shown headers
    show_wo_omit = [f for f in show if f not in omit]

    # Displaying headers
    stdout.write('#' + lim.join(str(f) for f in show_wo_omit) + '\n')

    for h, k in list_of_things:
        l = []
        for f in show_wo_omit:
            if f == '__ref__':
                l.append(fmt_ref(h, ref_type, no_symb=True))
            else:
                v = geob.get(k, f)
                # Small workaround to display nicely lists in quiet mode
                # Fields @raw are already handled with raw version, but
                # __dup__ field has no raw version for dumping
                if str(f).startswith('__') and isinstance(v, (list, tuple, set)):
                    l.append('/'.join(str(el) for el in v))
                else:
                    l.append(str(v))

        stdout.write(lim.join(l) + '\n')


def fixed_width(s, col, lim=25, truncate=None):
    '''
    This function is useful to display a string in the
    terminal with a fixed width. It is especially
    tricky with unicode strings containing accents.
    '''
    if truncate is None:
        truncate = 1000

    printer = '%%-%ss' % lim # is something like '%-3s'

    # To truncate on the appropriate number of characters
    # We decode before truncating (so non-ascii characters
    # will be counted only once when using len())
    # Then we encode again for stdout.write
    ds = str(s).decode('utf8')                      # decode
    es = (printer % ds[0:truncate]).encode('utf8')  # encode

    if len(ds) > truncate:
        es = es[:-2] + '… '

    return colored(es, *col)


def scan_coords(u_input, geob, verbose):
    '''
    This function tries to interpret the main
    argument as either coordinates (lat, lng) or
    a key like ORY.
    '''

    try:
        coords = tuple(float(l) for l in u_input.strip('()').split(','))

    except ValueError:
        # Scan coordinates failed, perhaps input was key
        if u_input not in geob:
            warn('key', u_input, geob._data, geob._source)
            exit(1)

        coords = geob.getLocation(u_input)

        if coords is None:
            error('geocode_unknown', u_input)

        return coords

    else:
        if len(coords) != 2:
            error('geocode_format', u_input)

        if verbose:
            print 'Geocode recognized: (%.3f, %.3f)' % coords

        return coords


def guess_delimiter(row):
    '''Heuristic to guess the top level delimiter.
    '''
    discarded  = set([
        '#', # this is for comments
        '_', # this is for spaces
        ' ', # spaces are not usually delimiter, unless we find no other
        '"', # this is for quoting
    ])
    candidates = set([l for l in row.rstrip() if not l.isalnum() and l not in discarded])
    counters   = dict((c, row.count(c)) for c in candidates)

    # Testing spaces from higher to lower, break on biggest match
    for alternate in [' ' * i for i in xrange(16, 3, -1)]:
        if row.count(alternate):
            counters[alternate] = row.count(alternate)
            break

    if counters:
        return max(counters.iteritems(), key=lambda x: x[1])[0]
    else:
        # In this case, we could not find any delimiter, we may
        # as well return ' '
        return ' '


def generate_headers(n):
    '''Generate n headers.
    '''
    for i in xrange(n):
        yield 'H%s' % i


def guess_headers(s_row):
    '''Heuristic to guess the lat/lng fields from first row.
    '''
    headers = list(generate_headers(len(s_row)))

    # Name candidates for lat/lng
    lat_candidates = set(['latitude',  'lat'])
    lng_candidates = set(['longitude', 'lng', 'lon'])

    lat_found, lng_found = False, False

    for i, f in enumerate(s_row):
        try:
            val = float(f)
        except ValueError:
            # Here the line was not a number, we check the name
            if f.lower() in lat_candidates and not lat_found:
                headers[i] = 'lat'
                lat_found  = True

            if f.lower() in lng_candidates and not lng_found:
                headers[i] = 'lng'
                lng_found  = True

        else:
            if val == int(val):
                # Round values are improbable as lat/lng
                continue

            if -90 < val < 90 and not lat_found:
                # latitude candidate
                headers[i] = 'lat'
                lat_found  = True

            elif -180 < val < 180 and not lng_found:
                # longitude candidate
                headers[i] = 'lng'
                lng_found  = True

    return headers


def guess_indexes(headers, s_row):
    '''Heuristic to guess indexes from headers and first row.
    '''
    discarded = set(['lat', 'lng'])

    for h, v in zip(headers, s_row):

        # Skip discarded and empty values
        if h not in discarded and v:
            # We test if the value is a float
            try:
                val = float(v)
            except ValueError:
                return [h]
            else:
                # Round values are possible as indexes
                if val == int(val):
                    return [h]

    return [headers[0]]


def fmt_on_two_cols(L, descriptor=stdout, layout='v'):
    '''
    Some formatting for help.
    '''
    n = float(len(L))
    h = int(ceil(n / 2)) # half+

    if layout == 'h':
        pairs = izip_longest(L[::2], L[1::2], fillvalue='')

    elif layout == 'v':
        pairs = izip_longest(L[:h], L[h:], fillvalue='')

    else:
        raise ValueError('Layout must be "h" or "v", but was "%s"' % layout)

    for p in pairs:
        print >> descriptor, '\t%-20s\t%-20s' % p


def warn(name, *args):
    '''
    Display a warning on stderr.
    '''

    if name == 'key':
        print >> stderr, '/!\ Key %s was not in GeoBase, for data "%s" and source %s' % \
                (args[0], args[1], args[2])


def error(name, *args):
    '''
    Display an error on stderr, then exit.
    First argument is the error type.
    '''

    if name == 'trep_support':
        print >> stderr, '\n/!\ No opentrep support. Check if opentrep wrapper can import libpyopentrep.'

    elif name == 'geocode_support':
        print >> stderr, '\n/!\ No geocoding support for data type %s.' % args[0]

    elif name == 'base':
        print >> stderr, '\n/!\ Wrong base "%s". You may select:' % args[0]
        fmt_on_two_cols(args[1], stderr)

    elif name == 'property':
        print >> stderr, '\n/!\ Wrong property "%s".' % args[0]
        print >> stderr, 'For data type %s, you may select:' % args[1]
        fmt_on_two_cols(args[2], stderr)

    elif name == 'field':
        print >> stderr, '\n/!\ Wrong field "%s".' % args[0]
        print >> stderr, 'For data type %s, you may select:' % args[1]
        fmt_on_two_cols(args[2], stderr)

    elif name == 'geocode_format':
        print >> stderr, '\n/!\ Bad geocode format: %s' % args[0]

    elif name == 'geocode_unknown':
        print >> stderr, '\n/!\ Geocode was unknown for %s' % args[0]

    elif name == 'empty_stdin':
        print >> stderr, '\n/!\ Stdin was empty'

    exit(1)


#######
#
#  MAIN
#
#######

# Global defaults
DEF_BASE          = 'ori_por'
DEF_FUZZY_LIMIT   = 0.70
DEF_NEAR_LIMIT    = 50.
DEF_CLOSEST_LIMIT = 10
DEF_TREP_FORMAT   = 'S'
DEF_QUIET_LIM     = '^'

# Terminal width defaults
DEF_CHAR_COL = 25
MIN_CHAR_COL = 3
MAX_CHAR_COL = 40
DEF_NUM_COL  = int(getTermSize()[1] / float(DEF_CHAR_COL)) - 1

ENV_WARNINGS = []

BACKGROUND_COLOR = os.getenv('BACKGROUND_COLOR', None) # 'white'

if BACKGROUND_COLOR not in ['black', 'white']:
    ENV_WARNINGS.append("""
    **********************************************************************
    $BACKGROUND_COLOR environment variable not properly set.             *
    Accepted values are 'black' and 'white'. Using default 'black' here. *
    To disable this message, add to your ~/.bashrc or ~/.zshrc:          *
                                                                         *
        export BACKGROUND_COLOR=black # or white                         *
                                                                         *
    *************************************************************** README
    """)

    BACKGROUND_COLOR = 'black'


if not checkPath('GeoBase'):
    ENV_WARNINGS.append("""
    **********************************************************************
    "GeoBase" does not seem to be in your $PATH.                         *
    To disable this message, add to your ~/.bashrc or ~/.zshrc:          *
                                                                         *
        export PATH=$PATH:$HOME/.local/bin                               *
                                                                         *
    *************************************************************** README
    """)


if ENV_WARNINGS:
    # Assume the user did not read the wiki :D
    ENV_WARNINGS.append("""
    **********************************************************************
    By the way, since you probably did not read the documentation :D,    *
    you should also add this for the completion to work with zsh.        *
    You're using zsh right o_O?                                          *
                                                                         *
        # Add custom completion scripts                                  *
        fpath=(~/.zsh/completion $fpath)                                 *
        autoload -U compinit                                             *
        compinit                                                         *
                                                                         *
    *************************************************************** README
    """)


def handle_args():
    '''Command line parsing.
    '''
    parser = argparse.ArgumentParser(description='Provide POR information.')

    parser.epilog = 'Example: %s ORY CDG' % parser.prog

    parser.add_argument('keys',
        help = 'Main argument (key, name, geocode depending on search mode)',
        nargs = '*')

    parser.add_argument('-b', '--base',
        help = '''Choose a different base, default is "%s". Also available are
                        stations, airports, countries... Give unadmissible base
                        and available values will be displayed.''' % DEF_BASE,
        default = DEF_BASE)

    parser.add_argument('-f', '--fuzzy',
        help = '''Rather than looking up a key, this mode will search the best
                        match from the property given by --fuzzy-property option for
                        the argument. Limit can be specified with --fuzzy-limit option.
                        By default, the "name" property is used for the search.''',
        default = None,
        nargs = '+')

    parser.add_argument('-F', '--fuzzy-property',
        help = '''When performing a fuzzy search, specify the property to be chosen.
                        Default is "name" if available, otherwise "__key__".
                        Give unadmissible property and available
                        values will be displayed.''',
        default = None)

    parser.add_argument('-L', '--fuzzy-limit',
        help = '''Specify a min limit for fuzzy searches, default is %s.
                        This is the Levenshtein ratio of the two strings.''' % DEF_FUZZY_LIMIT,
        default = DEF_FUZZY_LIMIT,
        type = float)

    parser.add_argument('-e', '--exact',
        help = '''Rather than looking up a key, this mode will search all keys
                        whose specific property given by --exact-property match the
                        argument. By default, the "__key__" property is used
                        for the search.''',
        default = None,
        nargs = '+')

    parser.add_argument('-E', '--exact-property',
        help = '''When performing an exact search, specify the property to be chosen.
                        Default is "__key__". Give unadmissible property and available
                        values will be displayed.''',
        default = None)

    parser.add_argument('-r', '--reverse',
        help = '''When possible, reverse the logic of the filter. Currently
                        only --exact support that.''',
        action = 'store_true')

    parser.add_argument('-n', '--near',
        help = '''Rather than looking up a key, this mode will search the entries
                        in a radius from a geocode or a key. Radius is given by --near-limit option,
                        and geocode is passed as argument. If you wish to give a geocode as
                        input, just pass it as argument with "lat, lng" format.''',
        default = None,
        nargs = '+')

    parser.add_argument('-N', '--near-limit',
        help = '''Specify a radius in km when performing geographical
                        searches with --near. Default is %s km.''' % DEF_NEAR_LIMIT,
        default = DEF_NEAR_LIMIT,
        type = float)

    parser.add_argument('-c', '--closest',
        help = '''Rather than looking up a key, this mode will search the closest entries
                        from a geocode or a key. Number of results is limited by --closest-limit option,
                        and geocode is passed as argument. If you wish to give a geocode as
                        input, just pass it as argument with "lat, lng" format.''',
        default = None,
        nargs = '+')

    parser.add_argument('-C', '--closest-limit',
        help = '''Specify a limit for closest search with --closest,
                        default is %s.''' % DEF_CLOSEST_LIMIT,
        default = DEF_CLOSEST_LIMIT,
        type = int)

    parser.add_argument('-t', '--trep',
        help = '''Rather than looking up a key, this mode will use opentrep.''',
        default = None,
        nargs = '+')

    parser.add_argument('-T', '--trep-format',
        help = '''Specify a format for trep searches with --trep,
                        default is "%s".''' % DEF_TREP_FORMAT,
        default = DEF_TREP_FORMAT)

    parser.add_argument('-g', '--gridless',
        help = '''When performing a geographical search, a geographical index is used.
                        This may lead to inaccurate results in some (rare) case when using
                        --closest searches (--near searches are never impacted).
                        Adding this option will disable the index, and browse the full
                        data set to look for the results.''',
        action = 'store_true')

    parser.add_argument('-o', '--omit',
        help = '''Does not print some characteristics of POR in stdout.
                        May help to get cleaner output. "__ref__" is an
                        available keyword with the
                        other geobase headers.''',
        nargs = '+',
        default = [])

    parser.add_argument('-s', '--show',
        help = '''Only print some characterics of POR in stdout.
                        May help to get cleaner output. "__ref__" is an
                        available keyword with the
                        other geobase headers.''',
        nargs = '+',
        default = [])

    parser.add_argument('-l', '--limit',
        help = '''Specify a limit for the number of results.
                        Default is %s, except in quiet mode where it is disabled.''' % DEF_NUM_COL,
        default = None)

    parser.add_argument('-i', '--interactive',
        help = '''Specify metadata for stdin data input.
                        3 optional values: delimiter, headers, indexes.
                        Multiple fields may be specified with "/" delimiter.
                        Default headers will use alphabet, and try to sniff lat/lng.
                        Use __head__ as header value to
                        burn the first line to define the headers.
                        Default indexes will take the first plausible field.
                        Default delimiter is smart :).
                        Example: -i ',' key/name/key2 key/key2''',
        nargs = '+',
        metavar = 'METADATA',
        default = None)

    parser.add_argument('-I', '--interactive-query',
        help = '''If passed, this option will consider stdin
                        input as key for query, not data for loading.''',
        action = 'store_true')

    parser.add_argument('-q', '--quiet',
        help = '''Does not provide the verbose output.
                        May still be combined with --omit and --show.''',
        action = 'store_true')

    parser.add_argument('-Q', '--quiet-delimiter',
        help = '''Custom delimiter in quiet mode. Default is "%s".''' % DEF_QUIET_LIM,
        default = DEF_QUIET_LIM)

    parser.add_argument('-m', '--map',
        help = '''If this option is set, instead of anything,
                        the script will display the data on a map and exit.''',
        action = 'store_true')

    parser.add_argument('-M', '--map-label',
        help = '''Change the label on map points. Default is "name" if available,
                        otherwise "__key__".''',
        default = None)

    parser.add_argument('-w', '--warnings',
        help = '''Provides additional information from GeoBase loading.''',
        action = 'store_true')

    parser.add_argument('-u', '--update',
        help = '''If this option is set, instead of anything,
                        the script will try to update some source files.''',
        action = 'store_true')

    parser.add_argument('-v', '--version',
        help = '''Display version information.''',
        action = 'store_true')

    return vars(parser.parse_args())


def main():
    '''
    Arguments handling.
    '''

    # Filter colored signals on terminals.
    # Necessary for Windows CMD
    colorama.init()

    #
    # COMMAND LINE MANAGEMENT
    args = handle_args()


    #
    # ARGUMENTS
    #
    with_grid = not args['gridless']
    verbose   = not args['quiet']
    warnings  = args['warnings']

    # Defining frontend
    if args['map']:
        frontend = 'map'
    elif not args['quiet']:
        frontend = 'terminal'
    else:
        frontend = 'quiet'

    if args['limit'] is None:
        # Limit was not set by user
        if frontend == 'terminal':
            limit = DEF_NUM_COL
        else:
            limit = None

    else:
        limit = int(args['limit'])



    #
    # CREATION
    #
    if verbose:
        before_init = datetime.now()

    if args['version']:
        r = pkg_resources.require("GeoBases")[0]
        print 'Project  : %s' % r.project_name
        print 'Version  : %s' % r.version
        print 'Location : %s' % r.location
        exit(0)

    if args['base'] not in GeoBase.BASES:
        error('base', args['base'], sorted(GeoBase.BASES.keys()))

    # Updating file
    if args['update']:
        GeoBase.update()
        exit(0)

    if not stdin.isatty() and not args['interactive_query']:

        try:
            first_l = stdin.next()
        except StopIteration:
            error('empty_stdin')

        source  = chain([first_l], stdin)
        # For sniffers, we rstrip
        first_l = first_l.rstrip()

        if args['interactive'] is None:
            delimiter = guess_delimiter(first_l)
            headers   = guess_headers(first_l.split(delimiter))
            indexes   = guess_indexes(headers, first_l.split(delimiter))
        else:
            dhi = args['interactive']

            if len(dhi) >= 1:
                delimiter = dhi[0]
            else:
                delimiter = guess_delimiter(first_l)

            if len(dhi) >= 2:
                if dhi[1] == '__head__':
                    headers = source.next().rstrip().split(delimiter)
                else:
                    headers = dhi[1].split('/')
            else:
                # Reprocessing the headers with custom delimiter
                headers = guess_headers(first_l.split(delimiter))

            if len(dhi) >= 3:
                indexes = dhi[2].split('/')
            else:
                # Reprocessing the indexes with custom headers
                indexes = guess_indexes(headers, first_l.split(delimiter))

        if verbose:
            print 'Loading GeoBase from stdin with [sniffed] option: -i "%s" "%s" "%s"' % \
                    (delimiter, '/'.join(headers), '/'.join(indexes))

        g = GeoBase(data='feed',
                    source=source,
                    delimiter=delimiter,
                    headers=headers,
                    indexes=indexes,
                    verbose=warnings)
    else:
        if verbose:
            print 'Loading GeoBase "%s"...' % args['base']

        g = GeoBase(data=args['base'], verbose=warnings)

    if verbose:
        after_init = datetime.now()


    # Tuning parameters
    if args['exact_property'] is None:
        args['exact_property'] = '__key__'

    if args['fuzzy_property'] is None:
        args['fuzzy_property'] = 'name' if 'name' in g.fields else '__key__'

    if args['map_label'] is None:
        args['map_label'] = 'name' if 'name' in g.fields else '__key__'



    #
    # FAILING
    #
    # Failing on lack of opentrep support if necessary
    if args['trep'] is not None:

        if not g.hasTrepSupport():
            error('trep_support')

    # Failing on lack of geocode support if necessary
    if args['near'] is not None or args['closest'] is not None:

        if not g.hasGeoSupport():
            error('geocode_support', args['base'])

    # Failing on wrong headers
    if args['exact'] is not None:

        if args['exact_property'] not in g.fields:
            error('property', args['exact_property'], args['base'], g.fields)

    if args['fuzzy'] is not None:

        if args['fuzzy_property'] not in g.fields:
            error('property', args['fuzzy_property'], args['base'], g.fields)

    # Failing on unkown fields
    for field in args['show'] + args['omit']:

        if field not in ['__ref__'] + g.fields:
            error('field', field, args['base'], ['__ref__'] + g.fields)



    #
    # MAIN
    #
    if verbose:
        if not stdin.isatty() and args['interactive_query']:
            print 'Looking for matches from stdin...'
        elif args['keys']:
            print 'Looking for matches from %s...' % ', '.join(args['keys'])
        else:
            print 'Looking for matches from *all* data...'

    # We start from either all keys available or keys listed by user
    # or from stdin if there is input
    if not stdin.isatty() and args['interactive_query']:
        res = []
        for row in stdin:
            res.extend(row.strip().split())
        res = enumerate(res)

    elif args['keys']:
        res = enumerate(args['keys'])
    else:
        res = enumerate(iter(g))

    # Keeping only keys in intermediate search
    ex_keys = lambda res : None if res is None else (e[1] for e in res)

    # Keeping track of last filter applied
    last = None

    # We are going to chain conditions
    # res will hold intermediate results
    if args['trep'] is not None:
        args['trep'] = ' '.join(args['trep'])
        if verbose:
            print 'Applying opentrep on "%s" [output %s]' % (args['trep'], args['trep_format'])

        res = g.trepGet(args['trep'], trep_format=args['trep_format'], from_keys=ex_keys(res), verbose=verbose)
        last = 'trep'


    if args['exact'] is not None:
        args['exact'] = ' '.join(args['exact'])
        if verbose:
            if args['reverse']:
                print 'Applying property %s != "%s"' % (args['exact_property'], args['exact'])
            else:
                print 'Applying property %s == "%s"' % (args['exact_property'], args['exact'])

        res = list(enumerate(g.getKeysWhere([(args['exact_property'], args['exact'])], from_keys=ex_keys(res), reverse=args['reverse'], force_str=True)))
        last = 'exact'


    if args['near'] is not None:
        args['near'] = ' '.join(args['near'])
        if verbose:
            print 'Applying near %s km from "%s"' % (args['near_limit'], args['near'])

        coords = scan_coords(args['near'], g, verbose)
        res = sorted(g.findNearPoint(coords, radius=args['near_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'near'


    if args['closest'] is not None:
        args['closest'] = ' '.join(args['closest'])
        if verbose:
            print 'Applying closest %s from "%s"' % (args['closest_limit'], args['closest'])

        coords = scan_coords(args['closest'], g, verbose)
        res = list(g.findClosestFromPoint(coords, N=args['closest_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'closest'


    if args['fuzzy'] is not None:
        args['fuzzy'] = ' '.join(args['fuzzy'])
        if verbose:
            print 'Applying property %s ~= "%s"' % (args['fuzzy_property'], args['fuzzy'])

        res = list(g.fuzzyGet(args['fuzzy'], args['fuzzy_property'], min_match=args['fuzzy_limit'], from_keys=ex_keys(res)))
        last = 'fuzzy'



    #
    # DISPLAY
    #

    # Saving to list
    res = list(res)

    # Removing unknown keys
    for h, k in res:
        if k not in g:
            warn('key', k, g._data, g._source)

    res = [(h, k) for h, k in res if k in g]


    # Keeping only "limit" first results
    nb_res_ini = len(res)

    if limit is not None:
        res = res[:limit]

    nb_res = len(res)

    if verbose:
        print 'Keeping %s result(s) from %s initially...' % (nb_res, nb_res_ini)


    # Highlighting some rows
    important = set(['__key__'])

    if args['exact'] is not None:
        important.add(args['exact_property'])

    if args['fuzzy'] is not None:
        important.add(args['fuzzy_property'])


    # __ref__ may be different thing depending on the last filter
    if last in ['near', 'closest']:
        ref_type = 'distance'
    elif last in ['trep', 'fuzzy']:
        ref_type = 'percentage'
    else:
        ref_type = 'index'

    # Display
    if frontend == 'map':
        status = g.visualize(output=g._data, label=args['map_label'], from_keys=ex_keys(res), big=100, verbose=True)

        if verbose:
            # We manually launch firefox, unless we risk a crash
            to_be_launched = []

            for template in status:
                if not template.endswith('_table.html'):
                    to_be_launched.append(template)
                else:
                    if nb_res <= 2000:
                        to_be_launched.append(template)
                    else:
                        print '\n/!\ Did not launch firefox for %s. We have %s rows and this may be slow.' % \
                                (template, nb_res)

            if to_be_launched:
                os.system('firefox %s &' % ' '.join(to_be_launched))

        if len(status) < 2:
            # At least one html not rendered
            frontend = 'terminal'
            res = res[:DEF_NUM_COL]

            print '\n/!\ %s template(s) not rendered. Switching to terminal frontend...' % (2 - len(status))


    if frontend == 'terminal':
        display(g, res, set(args['omit']), args['show'], important, ref_type)

        if verbose:
            end = datetime.now()
            print '\nDone in (total) %s = (init) %s + (post-init) %s' % \
                    (end - before_init, after_init - before_init, end - after_init)


    if frontend == 'quiet':
        display_quiet(g, res, set(args['omit']), args['show'], ref_type, args['quiet_delimiter'])


    if verbose:
        for warn_msg in ENV_WARNINGS:
            print textwrap.dedent(warn_msg),


if __name__ == '__main__':

    main()

