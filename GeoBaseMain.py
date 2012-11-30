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
from itertools import zip_longest, chain
import textwrap
import signal

from http.server import HTTPServer, SimpleHTTPRequestHandler

# Not in standard library
from termcolor import colored
import colorama
import argparse # in standard libraray for Python >= 2.7

# Private
from GeoBases import GeoBase

# Do not produce broken pipes when head and tail are used
signal.signal(signal.SIGPIPE, signal.SIG_DFL)



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


    def __next__(self):
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


def display_quiet(geob, list_of_things, omit, show, ref_type, delim, header):
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
    if header == 'CH':
        stdout.write('#' + delim.join(str(f) for f in show_wo_omit) + '\n')
    elif header == 'RH':
        stdout.write(delim.join(str(f) for f in show_wo_omit) + '\n')
    else:
        # Every other value will not display a header
        pass

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

        stdout.write(delim.join(l) + '\n')


def display_browser(status, nb_res):
    '''Display templates in the browser.

    '''
    # We manually launch firefox, unless we risk a crash
    to_be_launched = []

    for template in status:
        if template.endswith('_table.html'):
            if nb_res <= TABLE_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print('/!\ "firefox localhost:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (PORT, template, nb_res))

        elif template.endswith('_map.html'):
            if nb_res <= MAP_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print('/!\ "firefox localhost:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (PORT, template, nb_res))
        else:
            to_be_launched.append(template)

    if to_be_launched:
        urls = ['localhost:%s/%s' % (PORT, tpl) for tpl in to_be_launched]
        os.system('firefox %s &' % ' '.join(urls))

    # Note that in Python 3 we do not have to overload the class
    # with allow_address_reuse
    httpd = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)

    try:
        print('* Serving on localhost:%s (hit ctrl+C to stop)' % PORT)
        httpd.serve_forever()

    except KeyboardInterrupt:
        print('\n* Shutting down gracefully...')
        httpd.shutdown()
        print('* Done')



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
    ds = str(s)
    es = printer % ds[0:truncate]

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
            print('Geocode recognized: (%.3f, %.3f)' % coords)

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
    for alternate in [' ' * i for i in range(16, 3, -1)]:
        if row.count(alternate):
            counters[alternate] = row.count(alternate)
            break

    if counters:
        return max(counters.items(), key=lambda x: x[1])[0]
    else:
        # In this case, we could not find any delimiter, we may
        # as well return ' '
        return ' '


def generate_headers(n):
    '''Generate n headers.
    '''
    for i in range(n):
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


def score_index(f):
    '''Eval likelihood of being an index.

    The shorter the better, and int get a len() of 1.
    0, 1 and floats are weird for indexes, as well as 1-letter strings.
    '''
    if str(f).endswith('__key__') or str(f).lower().endswith('id'):
        return 0

    try:
        l = len(f) if len(f) >= 2 else 10
    except TypeError:
        # int or float
        if f in [0, 1] or isinstance(f, float):
            l = 1000
        else:
            l = 1
    return l


def guess_indexes(headers, s_row):
    '''Heuristic to guess indexes from headers and first row.
    '''
    discarded  = set(['lat', 'lng'])
    candidates = []

    for h, v in zip(headers, s_row):
        # Skip discarded and empty values
        if h not in discarded and v:
            try:
                val = float(v)
            except ValueError:
                # not a number
                candidates.append((h, v))
            else:
                if val == int(val):
                    candidates.append((h, int(val)))
                else:
                    candidates.append((h, val))

    if not candidates:
        return [headers[0]]

    return [ min(candidates, key=lambda x: score_index(x[1]))[0] ]


def fmt_on_two_cols(L, descriptor=stdout, layout='v'):
    '''
    Some formatting for help.
    '''
    n = float(len(L))
    h = int(ceil(n / 2)) # half+

    if layout == 'h':
        pairs = zip_longest(L[::2], L[1::2], fillvalue='')

    elif layout == 'v':
        pairs = zip_longest(L[:h], L[h:], fillvalue='')

    else:
        raise ValueError('Layout must be "h" or "v", but was "%s"' % layout)

    for p in pairs:
        print('\t%-20s\t%-20s' % p, file=descriptor)


def warn(name, *args):
    '''
    Display a warning on stderr.
    '''

    if name == 'key':
        print('/!\ Key %s was not in GeoBase, for data "%s" and source %s' % \
                (args[0], args[1], args[2]), file=stderr)


def error(name, *args):
    '''
    Display an error on stderr, then exit.
    First argument is the error type.
    '''

    if name == 'trep_support':
        print('\n/!\ No opentrep support. Check if OpenTrepWrapper can import libpyopentrep.', file=stderr)

    elif name == 'geocode_support':
        print('\n/!\ No geocoding support for data type %s.' % args[0], file=stderr)

    elif name == 'base':
        print('\n/!\ Wrong base "%s". You may select:' % args[0], file=stderr)
        fmt_on_two_cols(args[1], stderr)

    elif name == 'property':
        print('\n/!\ Wrong property "%s".' % args[0], file=stderr)
        print('For data type "%s", you may select:' % args[1], file=stderr)
        fmt_on_two_cols(args[2], stderr)

    elif name == 'field':
        print('\n/!\ Wrong field "%s".' % args[0], file=stderr)
        print('For data type "%s", you may select:' % args[1], file=stderr)
        fmt_on_two_cols(args[2], stderr)

    elif name == 'geocode_format':
        print('\n/!\ Bad geocode format: %s' % args[0], file=stderr)

    elif name == 'geocode_unknown':
        print('\n/!\ Geocode was unknown for %s' % args[0], file=stderr)

    elif name == 'empty_stdin':
        print('\n/!\ Stdin was empty', file=stderr)

    elif name == 'wrong_value':
        print('\n/!\ Wrong value "%s", should be in "%s".' % (args[0], args[1]), file=stderr)

    exit(1)


#######
#
#  MAIN
#
#######

# Global defaults
DEF_BASE          = 'ori_por'
DEF_FUZZY_LIMIT   = 0.85
DEF_NEAR_LIMIT    = 50.
DEF_CLOSEST_LIMIT = 10
DEF_TREP_FORMAT   = 'S'
DEF_QUIET_LIM     = '^'
DEF_QUIET_HEADER  = 'CH'
DEF_INTER_FUZZY_L = 0.99
DEF_FUZZY_FIELD   = 'name'

# Magic value option to skip and leave default, or disable
SKIP    = '_'
DISABLE = '__none__'

# Port for SimpleHTTPServer
PORT = 8000

# Defaults for map
DEF_LABEL_FIELD   = 'name'
DEF_SIZE_FIELD    = 'page_rank'
DEF_COLOR_FIELD   = 'raw_offset'
DEF_BIG_ICONS     = 150  # threshold for using big icons
MAP_BROWSER_LIM   = 8000 # limit for launching browser automatically
TABLE_BROWSER_LIM = 2000 # limit for launching browser automatically

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
                        By default, the "%s" property is used for the search.''' % \
                        DEF_FUZZY_FIELD,
        default = None,
        nargs = '+')

    parser.add_argument('-F', '--fuzzy-property',
        help = '''When performing a fuzzy search, specify the property to be chosen.
                        Default is "%s" if available, otherwise "__key__".
                        Give unadmissible property and available
                        values will be displayed.''' % DEF_FUZZY_FIELD,
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
                        Default is %s, except in quiet mode where it is disabled.''' % \
                        DEF_NUM_COL,
        default = None)

    parser.add_argument('-i', '--indexes',
        help = '''Specify metadata for data input, for stdin input
                        as well as defaults overriding for existing bases.
                        3 optional values: delimiter, headers, indexes.
                        Multiple fields may be specified with "/" delimiter.
                        Default headers will use alphabet, and try to sniff lat/lng.
                        Use __head__ as header value to
                        burn the first line to define the headers.
                        Default indexes will take the first plausible field.
                        Default delimiter is smart :).
                        For any field, you may put "%s" to leave the default value.
                        Example: -i ',' key/name/key2 key/key2''' % SKIP,
        nargs = '+',
        metavar = 'METADATA',
        default = [])

    parser.add_argument('-I', '--interactive-query',
        help = '''If passed, this option will consider stdin
                        input as key for query, not data for loading.
                        It has optional arguments. The first one is the field
                        from which the data is supposed to be. The second is the
                        type of matching, either "__exact__" or "__fuzzy__". For fuzzy
                        searches, the ratio is set to %s.
                        For any field, you may put "%s" to leave the default value.
                        Example: -I icao_code __fuzzy__''' % (DEF_INTER_FUZZY_L, SKIP),
        nargs = '*',
        metavar = 'OPTION',
        default = None)

    parser.add_argument('-q', '--quiet',
        help = '''Does not provide the verbose output.
                        May still be combined with --omit and --show.''',
        action = 'store_true')

    parser.add_argument('-Q', '--quiet-options',
        help = '''Custom delimiter in quiet mode. Default is "%s".
                        Accepts a second optional parameter to control
                        header display: RH to add a raw header, CH to
                        add a commented header, any other value will
                        not display the header. Default is "%s".
                        For any field, you may put "%s" to leave the default value.
                        Example: -Q ';' RH''' % \
                        (DEF_QUIET_LIM, DEF_QUIET_HEADER, SKIP),
        nargs = '+',
        metavar = 'INFO',
        default = [])

    parser.add_argument('-m', '--map',
        help = '''If this option is set, instead of anything,
                        the script will display the data on a map and exit.''',
        action = 'store_true')

    parser.add_argument('-M', '--map-data',
        help = '''4 optional values.
                        The first one is the field to display on map points.
                        Default is "%s" if available, otherwise "__key__".
                        The second optional value is the field used to draw
                        circles around points. Default is "%s" if available.
                        Put "%s" to disable circles.
                        The third optional value is the field use to color icons.
                        Default is "%s" if available.
                        Put "%s" to disable coloring.
                        The fourth optional value is the big icons threshold, this must
                        be an integer, default is %s.
                        For any field, you may put "%s" to leave the default value.
                        Example: -M name population __none__''' % \
                        (DEF_LABEL_FIELD, DEF_SIZE_FIELD, DISABLE, DEF_COLOR_FIELD, DISABLE, DEF_BIG_ICONS, SKIP),
        nargs = '+',
        metavar = 'FIELDS',
        default = [])

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

    # Interactive query?
    interactive_query_mode = args['interactive_query'] is not None


    #
    # CREATION
    #
    if verbose:
        before_init = datetime.now()

    if args['version']:
        r = pkg_resources.require("GeoBases")[0]
        print('Project  : %s' % r.project_name)
        print('Version  : %s' % r.version)
        print('Location : %s' % r.location)
        exit(0)

    if args['base'] not in GeoBase.BASES:
        error('base', args['base'], sorted(GeoBase.BASES.keys()))

    # Updating file
    if args['update']:
        GeoBase.update()
        exit(0)

    if not stdin.isatty() and not interactive_query_mode:
        try:
            first_l = next(stdin)
        except StopIteration:
            error('empty_stdin')

        source  = chain([first_l], stdin)
        first_l = first_l.rstrip() # For sniffers, we rstrip

        delimiter = guess_delimiter(first_l)
        headers   = guess_headers(first_l.split(delimiter))
        indexes   = guess_indexes(headers, first_l.split(delimiter))

        if len(args['indexes']) >= 1 and args['indexes'][0] != SKIP:
            delimiter = args['indexes'][0]

        if len(args['indexes']) >= 2 and args['indexes'][1] != SKIP:
            if args['indexes'][1] == '__head__':
                headers = source.next().rstrip().split(delimiter)
            else:
                headers = args['indexes'][1].split('/')
        else:
            # Reprocessing the headers with custom delimiter
            headers = guess_headers(first_l.split(delimiter))

        if len(args['indexes']) >= 3 and args['indexes'][2] != SKIP:
            indexes = args['indexes'][2].split('/')
        else:
            # Reprocessing the indexes with custom headers
            indexes = guess_indexes(headers, first_l.split(delimiter))

        if verbose:
            print('Loading GeoBase from stdin with [sniffed] option: -i "%s" "%s" "%s"' % \
                    (delimiter, '/'.join(headers), '/'.join(indexes)))

        g = GeoBase(data='feed',
                    source=source,
                    delimiter=delimiter,
                    headers=headers,
                    indexes=indexes,
                    verbose=warnings)
    else:
        # -i options overrides default
        add_options = {}

        if len(args['indexes']) >= 1 and args['indexes'][0] != SKIP:
            add_options['delimiter'] = args['indexes'][0]

        if len(args['indexes']) >= 2 and args['indexes'][1] != SKIP:
            add_options['headers'] = args['indexes'][1].split('/')

        if len(args['indexes']) >= 3 and args['indexes'][2] != SKIP:
            add_options['indexes'] = args['indexes'][2].split('/')

        if verbose:
            if not add_options:
                print('Loading GeoBase "%s"...' % args['base'])
            else:
                print('Loading GeoBase "%s" with custom %s...' % \
                        (args['base'], ', '.join('%s=%s' % kv for kv in add_options.items())))

        g = GeoBase(data=args['base'], verbose=warnings, **add_options)

    if verbose:
        after_init = datetime.now()


    # Tuning parameters
    if args['exact_property'] is None:
        args['exact_property'] = '__key__'

    if args['fuzzy_property'] is None:
        args['fuzzy_property'] = DEF_FUZZY_FIELD if DEF_FUZZY_FIELD in g.fields else '__key__'

    # Reading map options
    label       = DEF_LABEL_FIELD if DEF_LABEL_FIELD in g.fields else '__key__'
    size_field  = DEF_SIZE_FIELD  if DEF_SIZE_FIELD  in g.fields else None
    color_field = DEF_COLOR_FIELD if DEF_COLOR_FIELD in g.fields else None
    big_icons   = DEF_BIG_ICONS

    if len(args['map_data']) >= 1 and args['map_data'][0] != SKIP:
        label = args['map_data'][0]

    if len(args['map_data']) >= 2 and args['map_data'][1] != SKIP:
        size_field = None if args['map_data'][1] == DISABLE else args['map_data'][1]

    if len(args['map_data']) >= 3 and args['map_data'][2] != SKIP:
        color_field = None if args['map_data'][2] == DISABLE else args['map_data'][2]

    if len(args['map_data']) >= 4 and args['map_data'][3] != SKIP:
        big_icons = int(args['map_data'][3])

    # Reading quiet options
    quiet_delimiter = DEF_QUIET_LIM
    header_display  = DEF_QUIET_HEADER

    if len(args['quiet_options']) >= 1 and args['quiet_options'][0] != SKIP:
        quiet_delimiter = args['quiet_options'][0]

    if len(args['quiet_options']) >= 2 and args['quiet_options'][1] != SKIP:
        header_display = args['quiet_options'][1]

    # Reading interactive query options
    interactive_field = '__key__'
    interactive_type  = '__exact__'

    if interactive_query_mode:
        if len(args['interactive_query']) >= 1 and args['interactive_query'][0] != SKIP:
            interactive_field = args['interactive_query'][0]

        if len(args['interactive_query']) >= 2 and args['interactive_query'][1] != SKIP:
            interactive_type = args['interactive_query'][1]



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
            error('geocode_support', g._data)

    # Failing on wrong headers
    if args['exact'] is not None:
        if args['exact_property'] not in g.fields:
            error('property', args['exact_property'], g._data, g.fields)

    if args['fuzzy'] is not None:
        if args['fuzzy_property'] not in g.fields:
            error('property', args['fuzzy_property'], g._data, g.fields)

    # Failing on unknown fields
    fields_to_test = [f for f in (label, size_field, color_field, interactive_field) if f is not None]

    for field in args['show'] + args['omit'] + fields_to_test:
        if field not in ['__ref__'] + g.fields:
            error('field', field, g._data, ['__ref__'] + g.fields)

    # Testing -M option
    allowed_types = ['__exact__', '__fuzzy__']

    if interactive_type not in allowed_types:
        error('wrong_value', interactive_type, allowed_types)



    #
    # MAIN
    #
    if verbose:
        if not stdin.isatty() and interactive_query_mode:
            print('Looking for matches from stdin query...')
        elif args['keys']:
            print('Looking for matches from %s...' % ', '.join(args['keys']))
        else:
            print('Looking for matches from *all* data...')

    # Keeping track of last filter applied
    last = None

    # Keeping only keys in intermediate search
    ex_keys = lambda res : None if res is None else (e[1] for e in res)

    # We start from either all keys available or keys listed by user
    # or from stdin if there is input
    if not stdin.isatty() and interactive_query_mode:
        values = []
        for row in stdin:
            values.extend(row.strip().split())

        # Query type
        if interactive_type == '__exact__':
            if interactive_field == '__key__':
                res = enumerate(values)
            else:
                conditions = [(interactive_field, val) for val in values]
                res = enumerate(g.getKeysWhere(conditions, force_str=True, mode='or'))
                last = 'exact'

        elif interactive_type == '__fuzzy__':
            res = []
            for val in values:
                res.extend(list(g.fuzzyGet(val, interactive_field, min_match=DEF_INTER_FUZZY_L)))
            last = 'fuzzy'

    elif args['keys']:
        res = enumerate(args['keys'])
    else:
        res = enumerate(iter(g))

    # We are going to chain conditions
    # res will hold intermediate results
    if args['trep'] is not None:
        args['trep'] = ' '.join(args['trep'])
        if verbose:
            print('Applying opentrep on "%s" [output %s]' % (args['trep'], args['trep_format']))

        res = g.trepGet(args['trep'], trep_format=args['trep_format'], from_keys=ex_keys(res), verbose=verbose)
        last = 'trep'


    if args['exact'] is not None:
        args['exact'] = ' '.join(args['exact'])
        if verbose:
            if args['reverse']:
                print('Applying property %s != "%s"' % (args['exact_property'], args['exact']))
            else:
                print('Applying property %s == "%s"' % (args['exact_property'], args['exact']))

        res = list(enumerate(g.getKeysWhere([(args['exact_property'], args['exact'])],
                                            from_keys=ex_keys(res),
                                            reverse=args['reverse'],
                                            force_str=True)))
        last = 'exact'


    if args['near'] is not None:
        args['near'] = ' '.join(args['near'])
        if verbose:
            print('Applying near %s km from "%s"' % (args['near_limit'], args['near']))

        coords = scan_coords(args['near'], g, verbose)
        res = sorted(g.findNearPoint(coords, radius=args['near_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'near'


    if args['closest'] is not None:
        args['closest'] = ' '.join(args['closest'])
        if verbose:
            print('Applying closest %s from "%s"' % (args['closest_limit'], args['closest']))

        coords = scan_coords(args['closest'], g, verbose)
        res = list(g.findClosestFromPoint(coords, N=args['closest_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'closest'


    if args['fuzzy'] is not None:
        args['fuzzy'] = ' '.join(args['fuzzy'])
        if verbose:
            print('Applying property %s ~= "%s"' % (args['fuzzy_property'], args['fuzzy']))

        res = list(g.fuzzyGet(args['fuzzy'], args['fuzzy_property'], min_match=args['fuzzy_limit'], from_keys=ex_keys(res)))
        last = 'fuzzy'


    if verbose:
        end = datetime.now()
        print('Done in %s = (load) %s + (search) %s' % \
                (end - before_init, after_init - before_init, end - after_init))


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
        print('Keeping %s result(s) from %s initially...' % (nb_res, nb_res_ini))


    # Highlighting some rows
    important = set(['__key__'])

    if args['exact'] is not None:
        important.add(args['exact_property'])

    if args['fuzzy'] is not None:
        important.add(args['fuzzy_property'])

    if interactive_query_mode:
        important.add(interactive_field)

    # __ref__ may be different thing depending on the last filter
    if last in ['near', 'closest']:
        ref_type = 'distance'
    elif last in ['trep', 'fuzzy']:
        ref_type = 'percentage'
    else:
        ref_type = 'index'

    # Display
    if frontend == 'map':
        status = g.visualize(output=g._data,
                             label=label,
                             point_size=size_field,
                             point_color=color_field,
                             from_keys=ex_keys(res),
                             big_limit=big_icons,
                             verbose=True)

        if verbose:
            display_browser(status, nb_res)

        if len(status) < 2:
            # At least one html not rendered
            frontend = 'terminal'
            res = res[:DEF_NUM_COL]

            print('/!\ %s template(s) not rendered. Switching to terminal frontend...' % (2 - len(status)))


    # We protect the stdout.write against the IOError
    if frontend == 'terminal':
        display(g, res, set(args['omit']), args['show'], important, ref_type)

    if frontend == 'quiet':
        display_quiet(g, res, set(args['omit']), args['show'], ref_type, quiet_delimiter, header_display)

    if verbose:
        for warn_msg in ENV_WARNINGS:
            print(textwrap.dedent(warn_msg), end="")


if __name__ == '__main__':

    main()

