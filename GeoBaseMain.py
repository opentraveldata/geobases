#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is a launcher for GeoBase.
"""

from sys import stdin, stdout, stderr
import os

import pkg_resources
from datetime import datetime
from math import ceil, log
from itertools import izip_longest, chain
import fcntl, termios, struct
from textwrap import dedent
import signal

import SimpleHTTPServer
import SocketServer

# Not in standard library
from termcolor import colored
import colorama
import argparse # in standard libraray for Python >= 2.7

# Private
from GeoBases import GeoBase, BASES

# Do not produce broken pipes when head and tail are used
signal.signal(signal.SIGPIPE, signal.SIG_DFL)



def checkPath(command):
    """
    This checks if a command is in the PATH.
    """
    path = os.popen('which %s 2> /dev/null' % command, 'r').read()

    if path:
        return True
    else:
        return False


def getObsoleteTermSize():
    """
    This gives terminal size information using external
    command stty.
    This function is not great since where stdin is used, it
    raises an error.
    """
    size = os.popen('stty size 2>/dev/null', 'r').read()

    if not size:
        return (80, 160)

    return tuple(int(d) for d in size.split())


def ioctl_GWINSZ(fd):
    """Read terminal size.
    """
    try:
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except IOError:
        return
    return cr


def getTermSize():
    """
    This gives terminal size information.
    """
    env = os.environ
    cr  = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

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
    """
    This class is used for generating alternate colors
    for the Linux output.
    """
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
        """We increase the current color.
        """
        self._current += 1

        if self._current == len(self._availables):
            self._current = 0


    def get(self):
        """Get current color.
        """
        return self._availables[self._current]


    def convertRaw(self, col):
        """Get special raw color. Only change foreground color.
        """
        current    = list(col)
        current[0] = 'yellow' if self._background == 'black' else 'green'
        return tuple(current)


    @staticmethod
    def convertBold(col):
        """Get special field color. Only change bold type.
        """
        current    = list(col)
        current[2] = ['bold']
        return tuple(current)


    @staticmethod
    def getEmph():
        """Get special emphasized color.
        """
        return ('white', 'on_blue', [])


    @staticmethod
    def getHeader():
        """Get special header color.
        """
        return ('red', None, [])


    @staticmethod
    def getSpecial():
        """Get special property color.
        """
        return ('magenta', None, [])



def fmt_ref(ref, ref_type, no_symb=False):
    """
    Display the reference depending on its type.
    """
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
    """
    Main display function in Linux terminal, with
    nice color and everything.
    """
    if not list_of_things:
        stdout.write('\nNo elements to display.\n')
        return

    if not show:
        show = [REF] + geob.fields[:]

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
        elif f == REF:
            col = c.getHeader()
        elif str(f).startswith('__'):
            col = c.getSpecial() # For special fields like __dup__
        else:
            col = c.get()

        if str(f).endswith('@raw'):
            col = c.convertRaw(col)  # For @raw fields

        # Fields on the left
        stdout.write('\n' + fixed_width(f, c.convertBold(col), lim, truncate))

        if f == REF:
            for h, _ in list_of_things:
                stdout.write(fixed_width(fmt_ref(h, ref_type), col, lim, truncate))
        else:
            for _, k in list_of_things:
                stdout.write(fixed_width(geob.get(k, f), col, lim, truncate))

        next(c)

    stdout.write('\n')


def display_quiet(geob, list_of_things, omit, show, ref_type, delim, header):
    """
    This function displays the results in programming
    mode, with --quiet option. This is useful when you
    want to use use the result in a pipe for example.
    """
    if not show:
        # Temporary
        t_show = [REF] + geob.fields[:]

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
            if f == REF:
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


def display_browser(templates, nb_res):
    """Display templates in the browser.
    """
    # We manually launch firefox, unless we risk a crash
    to_be_launched = []

    for template in templates:
        if template.endswith('_table.html'):
            if nb_res <= TABLE_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print '/!\ "firefox localhost:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (PORT, template, nb_res)

        elif template.endswith('_map.html'):
            if nb_res <= MAP_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print '/!\ "firefox localhost:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (PORT, template, nb_res)
        else:
            to_be_launched.append(template)

    if to_be_launched:
        urls = ['localhost:%s/%s' % (PORT, tpl) for tpl in to_be_launched]
        os.system('firefox %s &' % ' '.join(urls))



def launch_http_server(address, port):
    """Launch a SimpleHTTPServer.
    """
    class MyTCPServer(SocketServer.TCPServer):
        """Overrides standard library.
        """
        allow_reuse_address = True

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd   = MyTCPServer((address, port), Handler)

    try:
        print '* Serving on localhost:%s (hit ctrl+C to stop)' % port
        httpd.serve_forever()

    except KeyboardInterrupt:
        print '\n* Shutting down gracefully...'
        httpd.shutdown()
        print '* Done'



def fixed_width(s, col, lim=25, truncate=None):
    """
    This function is useful to display a string in the
    terminal with a fixed width. It is especially
    tricky with unicode strings containing accents.
    """
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
    """
    This function tries to interpret the main
    argument as either coordinates (lat, lng) or
    a key like ORY.
    """
    # First we try input a direct key
    if u_input in geob:
        coords = geob.getLocation(u_input)

        if coords is None:
            error('geocode_unknown', u_input)

        return coords

    # Then we try input as geocode
    try:
        free_geo = u_input.strip('()')

        for char in '\\', '"', "'":
            free_geo = free_geo.replace(char, '')

        for sep in '^', ';', ',':
            free_geo = free_geo.replace(sep, ' ')

        coords = tuple(float(l) for l in free_geo.split())

    except ValueError:
        pass
    else:
        if len(coords) == 2        and \
           -90  <= coords[0] <= 90 and \
           -180 <= coords[1] <= 180:

            if verbose:
                print 'Geocode recognized: (%.3f, %.3f)' % coords

            return coords

        error('geocode_format', u_input)

    # All cases failed
    warn('key', u_input, geob.data, geob._source)
    exit(1)


def guess_delimiter(row):
    """Heuristic to guess the top level delimiter.
    """
    discarded  = set([
        '#', # this is for comments
        '_', # this is for spaces
        ' ', # spaces are not usually delimiter, unless we find no other
        '"', # this is for quoting
        '.', # this is for decimal numbers
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
    """Generate n headers.
    """
    for i in xrange(n):
        yield 'H%s' % i


def guess_headers(s_row):
    """Heuristic to guess the lat/lng fields from first row.
    """
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

            if -90 <= val <= 90 and not lat_found:
                # possible latitude field
                headers[i] = 'lat'
                lat_found  = True

            elif -180 <= val <= 180 and not lng_found:
                # possible longitude field
                headers[i] = 'lng'
                lng_found  = True

    return headers


def score_index(f):
    """Eval likelihood of being an index.

    The shorter the better, and int get a len() of 1.
    0, 1 and floats are weird for indexes, as well as 1-letter strings.
    """
    if str(f).endswith('__key__') or str(f).lower().endswith('id'):
        return 0

    if isinstance(f, float):
        return 1000

    if isinstance(f, int):
        if f <= 1: # we avoid a domain error on next case
            return 10
        return max(2, 25 / log(f))

    return len(f) if len(f) >= 2 else 10


def guess_indexes(headers, s_row):
    """Heuristic to guess indexes from headers and first row.
    """
    discarded  = set(['lat', 'lng'])
    candidates = []

    for h, v in zip(headers, s_row):
        # Skip discarded and empty values
        if h not in discarded and v:
            try:
                val = float(v)
            except ValueError:
                # is *not* a number
                candidates.append((h, score_index(v)))
            else:
                # is a number
                if val == int(val):
                    candidates.append((h, score_index(int(val))))
                else:
                    candidates.append((h, score_index(val)))

    if not candidates:
        return [headers[0]]

    return [ min(candidates, key=lambda x: x[1])[0] ]


def fmt_on_two_cols(L, descriptor=stdout, layout='v'):
    """
    Some formatting for help.
    """
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


def best_field(candidates, possibilities, default=None):
    """Select best candidate in possibilities.
    """
    for candidate in candidates:
        if candidate in possibilities:
            return candidate
    return default


def warn(name, *args):
    """
    Display a warning on stderr.
    """
    if name == 'key':
        print >> stderr, '/!\ Key %s was not in GeoBase, for data "%s" and source %s' % \
                (args[0], args[1], args[2])


def error(name, *args):
    """
    Display an error on stderr, then exit.
    First argument is the error type.
    """
    if name == 'trep_support':
        print >> stderr, '\n/!\ No opentrep support. Check if OpenTrepWrapper can import libpyopentrep.'

    elif name == 'geocode_support':
        print >> stderr, '\n/!\ No geocoding support for data type %s.' % args[0]

    elif name == 'base':
        print >> stderr, '\n/!\ Wrong data type "%s". You may select:' % args[0]
        fmt_on_two_cols(args[1], stderr)

    elif name == 'property':
        print >> stderr, '\n/!\ Wrong property "%s".' % args[0]
        print >> stderr, 'For data type "%s", you may select:' % args[1]
        fmt_on_two_cols(args[2], stderr)

    elif name == 'field':
        print >> stderr, '\n/!\ Wrong field "%s".' % args[0]
        print >> stderr, 'For data type "%s", you may select:' % args[1]
        fmt_on_two_cols(args[2], stderr)

    elif name == 'geocode_format':
        print >> stderr, '\n/!\ Bad geocode format: %s' % args[0]

    elif name == 'geocode_unknown':
        print >> stderr, '\n/!\ Geocode was unknown for %s' % args[0]

    elif name == 'empty_stdin':
        print >> stderr, '\n/!\ Stdin was empty'

    elif name == 'wrong_value':
        print >> stderr, '\n/!\ Wrong value "%s", should be in "%s".' % (args[0], args[1])

    elif name == 'type':
        print >> stderr, '\n/!\ Wrong type for "%s", should be %s.' % (args[0], args[1])

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
DEF_QUIET_DELIM   = '^'
DEF_QUIET_HEADER  = 'CH'
DEF_INTER_FUZZY_L = 0.99
DEF_FUZZY_FIELDS  = ('name', 'country_name', 'currency_name', '__key__')
DEF_EXACT_FIELDS  = ('__key__',)

ALLOWED_ICON_TYPES  = (None, 'auto', 'S', 'B')
ALLOWED_INTER_TYPES = ('__exact__', '__fuzzy__')

DEF_INTER_FIELD = '__key__'
DEF_INTER_TYPE  = '__exact__'

# Considered truthy values for command line option
TRUTHY = ('1', 'Y')

# Duplicates handling in feed mode
DEF_DISCARD_RAW = 'F'
DEF_DISCARD     = False

# Magic value option to skip and leave default, or disable
SKIP    = '_'
SPLIT   = '/'
DISABLE = '__none__'
REF     = '__ref__'

# Port for SimpleHTTPServer
ADDRESS = '0.0.0.0'
PORT    = 8000

# Defaults for map
DEF_LABEL_FIELDS    = ('name',       'country_name', '__key__')
DEF_SIZE_FIELDS     = ('page_rank',  'population',   None)
DEF_COLOR_FIELDS    = ('raw_offset', 'fclass',       None)
DEF_ICON_TYPE       = 'auto' # icon type: small, big, auto, ...
DEF_LINK_DUPLICATES = True

MAP_BROWSER_LIM   = 8000   # limit for launching browser automatically
TABLE_BROWSER_LIM = 2000   # limit for launching browser automatically

# Terminal width defaults
DEF_CHAR_COL = 25
MIN_CHAR_COL = 3
MAX_CHAR_COL = 40
DEF_NUM_COL  = int(getTermSize()[1] / float(DEF_CHAR_COL)) - 1

ENV_WARNINGS = []

BACKGROUND_COLOR = os.getenv('BACKGROUND_COLOR', None) # 'white'

if BACKGROUND_COLOR not in ['black', 'white']:
    ENV_WARNINGS.append('''
    **********************************************************************
    $BACKGROUND_COLOR environment variable not properly set.             *
    Accepted values are 'black' and 'white'. Using default 'black' here. *
    To disable this message, add to your ~/.bashrc or ~/.zshrc:          *
                                                                         *
        export BACKGROUND_COLOR=black # or white
                                                                         *
    *************************************************************** README
    ''')

    BACKGROUND_COLOR = 'black'


if not checkPath('GeoBase'):
    ENV_WARNINGS.append('''
    **********************************************************************
    "GeoBase" does not seem to be in your $PATH.                         *
    To disable this message, add to your ~/.bashrc or ~/.zshrc:          *
                                                                         *
        export PATH=$PATH:$HOME/.local/bin
                                                                         *
    *************************************************************** README
    ''')


if ENV_WARNINGS:
    # Assume the user did not read the wiki :D
    ENV_WARNINGS.append('''
    **********************************************************************
    By the way, since you probably did not read the documentation :D,    *
    you should also add this for the completion to work with zsh.        *
    You're using zsh right o_O?                                          *
                                                                         *
        # Add custom completion scripts
        fpath=(~/.zsh/completion $fpath)
        autoload -U compinit
        compinit
                                                                         *
    *************************************************************** README
    ''')


def handle_args():
    """Command line parsing.
    """
    # or list formatter
    fmt_or = lambda L : ' or '.join('"%s"' % e if e is not None else 'None' for e in L)

    parser = argparse.ArgumentParser(description='Provides data services.',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.epilog = 'Example: %s ORY CDG' % parser.prog

    parser.add_argument('keys',
        help = dedent('''\
        Main argument. This will be used as a list of keys on which we
        apply filters. Leave empty to consider all keys.
        '''),
        nargs = '*')

    parser.add_argument('-b', '--base',
        help = dedent('''\
        Choose a different data type, default is "%s". Also available are
        stations, airports, countries... Give unadmissible value
        and all possibilities will be displayed.
        ''' % DEF_BASE),
        default = DEF_BASE)

    parser.add_argument('-f', '--fuzzy',
        help = dedent('''\
        Rather than looking up a key, this mode will search the best
        match from the property given by --fuzzy-property option for
        the argument. Limit can be specified with --fuzzy-limit option.
        '''),
        default = None,
        nargs = '+')

    parser.add_argument('-F', '--fuzzy-property',
        help = dedent('''\
        When performing a fuzzy search, specify the property to be chosen.
        Default is %s
        depending on fields.
        Give unadmissible property and available values will be displayed.
        ''' % fmt_or(DEF_FUZZY_FIELDS)),
        default = None)

    parser.add_argument('-L', '--fuzzy-limit',
        help = dedent('''\
        Specify a min limit for fuzzy searches, default is %s.
        This is the Levenshtein ratio of the two strings.
        ''' % DEF_FUZZY_LIMIT),
        default = DEF_FUZZY_LIMIT,
        type = float)

    parser.add_argument('-e', '--exact',
        help = dedent('''\
        Rather than looking up a key, this mode will search all keys
        whose specific property given by --exact-property match the
        argument. By default, the %s property is used for the search.
        You can have several property matching by giving multiple values
        separated by "%s" for --exact-property. Make sure you give the
        same number of values separated also by "%s" then.
        ''' % (fmt_or(DEF_EXACT_FIELDS), SPLIT, SPLIT)),
        default = None,
        nargs = '+')

    parser.add_argument('-E', '--exact-property',
        help = dedent('''\
        When performing an exact search, specify the property to be chosen.
        Default is %s. Give unadmissible property and available
        values will be displayed.
        You can give multiple properties separated by "%s". Make sure
        you give the same number of values separated also by "%s" for -e then.
        ''' % (fmt_or(DEF_EXACT_FIELDS), SPLIT, SPLIT)),
        default = None)

    parser.add_argument('-r', '--reverse',
        help = dedent('''\
        When possible, reverse the logic of the filter. Currently
        only --exact supports that.
        '''),
        action = 'store_true')

    parser.add_argument('-a', '--any',
        help = dedent('''\
        By default, --exact multiple searches are combined with *and*,
        passing this option will change that to a *or*.
        '''),
        action = 'store_true')

    parser.add_argument('-n', '--near',
        help = dedent('''\
        Rather than looking up a key, this mode will search the entries
        close to a geocode or a key. Radius is given by --near-limit
        option, and geocode is given as main argument. If you wish to give
        a geocode as input, use the 'lat, lng' format, with quotes.
        Example: -n CDG
        '''),
        default = None,
        nargs = '+')

    parser.add_argument('-N', '--near-limit',
        help = dedent('''\
        Specify a radius in km when performing geographical
        searches with --near. Default is %s km.
        ''' % DEF_NEAR_LIMIT),
        default = DEF_NEAR_LIMIT,
        type = float)

    parser.add_argument('-c', '--closest',
        help = dedent('''\
        Rather than looking up a key, this mode will search the closest entries
        from a geocode or a key. Number of results is limited by --closest-limit
        option, and geocode is given as main argument. If you wish to give
        a geocode as input, use the 'lat, lng' format, with quotes.
        Example: -c '48.853, 2.348'
        '''),
        default = None,
        nargs = '+')

    parser.add_argument('-C', '--closest-limit',
        help = dedent('''\
        Specify a limit for closest search with --closest, default is %s.
        ''' % DEF_CLOSEST_LIMIT),
        default = DEF_CLOSEST_LIMIT,
        type = int)

    parser.add_argument('-t', '--trep',
        help = dedent('''\
        Rather than looking up a key, this mode will use opentrep.
        '''),
        default = None,
        nargs = '+')

    parser.add_argument('-T', '--trep-format',
        help = dedent('''\
        Specify a format for trep searches with --trep, default is "%s".
        ''' % DEF_TREP_FORMAT),
        default = DEF_TREP_FORMAT)

    parser.add_argument('-g', '--gridless',
        help = dedent('''\
        When performing a geographical search, a geographical index is used.
        This may lead to inaccurate results in some (rare) case when using
        --closest searches (--near searches are never impacted).
        Adding this option will disable the index, and browse the full
        data set to look for the results.
        '''),
        action = 'store_true')

    parser.add_argument('-o', '--omit',
        help = dedent('''\
        Does not print some fields on stdout.
        May help to get cleaner output.
        "%s" is an available keyword as well as any other geobase fields.
        ''' % REF),
        nargs = '+',
        default = [])

    parser.add_argument('-s', '--show',
        help = dedent('''\
        Only print some fields on stdout.
        May help to get cleaner output.
        "%s" is an available keyword as well as any other geobase fields.
        ''' % REF),
        nargs = '+',
        default = [])

    parser.add_argument('-l', '--limit',
        help = dedent('''\
        Specify a limit for the number of results.
        This must be an integer.
        Default is %s, except in quiet mode where it is disabled.
        ''' % DEF_NUM_COL),
        default = None)

    parser.add_argument('-i', '--indexes',
        help = dedent('''\
        Specify metadata, for stdin input as well as existing bases.
        This will override defaults for existing bases.
        4 optional arguments: delimiter, headers, indexes, discard_dups.
            1) default delimiter is smart :).
            2) default headers will use numbers, and try to sniff lat/lng.
               Use __head__ as header value to
               burn the first line to define the headers.
            3) default indexes will take the first plausible field.
            4) discard_dups is a boolean to toggle duplicated keys dropping.
               Default is %s. Put %s as a truthy value,
               any other value will be falsy.
        Multiple fields may be specified with "%s" delimiter.
        For any field, you may put "%s" to leave the default value.
        Example: -i ',' key/name/country key/country _
        ''' % (DEF_DISCARD, fmt_or(TRUTHY), SPLIT, SKIP)),
        nargs = '+',
        metavar = 'METADATA',
        default = [])

    parser.add_argument('-I', '--interactive-query',
        help = dedent('''\
        If given, this option will consider stdin
        input as query material, not data for loading.
        It will read values line by line, and perform a search on them.
        2 optional arguments: field, type.
            1) field is the field from which the data is supposed to be.
            2) type is the type of matching, either %s.
               For fuzzy searches, the ratio is set to %s.
        For any field, you may put "%s" to leave the default value.
        Example: -I icao_code __fuzzy__
        ''' % (fmt_or(ALLOWED_INTER_TYPES), DEF_INTER_FUZZY_L, SKIP)),
        nargs = '*',
        metavar = 'OPTION',
        default = None)

    parser.add_argument('-q', '--quiet',
        help = dedent('''\
        Turn off verbosity and provide a programmer friendly output.
        This is a csv-like output, and may still be combined with
        --omit and --show. Configure with --quiet-options.
        '''),
        action = 'store_true')

    parser.add_argument('-Q', '--quiet-options',
        help = dedent('''\
        Custom the quiet mode.
        2 optional arguments: delimiter, header.
            1) default delimiter is "%s".
            2) the second parameter is used to control
               header display:
                   - RH to add a raw header,
                   - CH to add a commented header,
                   - any other value will not display the header.
               Default is "%s".
        For any field, you may put "%s" to leave the default value.
        Example: -Q ';' RH
        ''' % (DEF_QUIET_DELIM, DEF_QUIET_HEADER, SKIP)),
        nargs = '+',
        metavar = 'INFO',
        default = [])

    parser.add_argument('-m', '--map',
        help = dedent('''\
        This is the map output.
        Configure with --map-data.
        '''),
        action = 'store_true')

    parser.add_argument('-M', '--map-data',
        help = dedent('''\
        5 optional arguments: label, size, color, icon, duplicates.
            1) label is the field to display on map points.
               Default is %s depending on fields.
            2) size is the field used to draw circles around points.
               Default is %s depending on fields.
               Put "%s" to disable circles.
            3) color is the field use to color icons.
               Default is %s depending on fields.
               Put "%s" to disable coloring.
            4) icon is the icon type, either:
                   - "B" for big,
                   - "S" for small,
                   - "auto" for automatic,
                   - "%s" to disable icons.
               Default is "%s".
            5) duplicates is a boolean to toggle lines between duplicated keys.
               Default is %s. Put %s as a truthy value,
               any other value will be falsy.
        For any field, you may put "%s" to leave the default value.
        Example: -M _ population _ __none__ _
        ''' % ((fmt_or(DEF_LABEL_FIELDS), fmt_or(DEF_SIZE_FIELDS), DISABLE,
                fmt_or(DEF_COLOR_FIELDS), DISABLE, DISABLE, DEF_ICON_TYPE,
                DEF_LINK_DUPLICATES, fmt_or(TRUTHY), SKIP))),
        nargs = '+',
        metavar = 'FIELDS',
        default = [])

    parser.add_argument('-w', '--warnings',
        help = dedent('''\
        Provides additional information from data loading.
        '''),
        action = 'store_true')

    parser.add_argument('-u', '--update',
        help = dedent('''\
        If this option is set, instead of anything,
        the script will try to update the data files.
        Differences will be shown and the user has to answer
        'Y' or 'N' for each file.
        '''),
        action = 'store_true')

    parser.add_argument('-U', '--update-forced',
        help = dedent('''\
        If this option is set, instead of anything,
        the script will force the update of all data files.
        '''),
        action = 'store_true')

    parser.add_argument('-v', '--version',
        help = dedent('''\
        Display version information.
        '''),
        action = 'store_true')

    return vars(parser.parse_args())


def main():
    """
    Arguments handling.
    """
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
        try:
            limit = int(args['limit'])
        except ValueError:
            error('type', args['limit'], 'int')

    # Interactive query?
    interactive_query_mode = args['interactive_query'] is not None


    #
    # CREATION
    #
    if verbose:
        before_init = datetime.now()

    if args['version']:
        r = pkg_resources.require("GeoBases")[0]
        print 'Project  : %s' % r.project_name
        print 'Version  : %s' % r.version
        print 'Egg name : %s' % r.egg_name()
        print 'Location : %s' % r.location
        print 'Requires : %s' % ', '.join(str(e) for e in r.requires())
        print 'Extras   : %s' % ', '.join(str(e) for e in r.extras)
        exit(0)

    if args['base'] not in BASES:
        error('base', args['base'], sorted(BASES.keys()))

    # Updating file
    if args['update']:
        GeoBase.update()
        exit(0)

    if args['update_forced']:
        GeoBase.update(force=True)
        exit(0)

    if not stdin.isatty() and not interactive_query_mode:
        try:
            first_l = stdin.next()
        except StopIteration:
            error('empty_stdin')

        source  = chain([first_l], stdin)
        first_l = first_l.rstrip() # For sniffers, we rstrip

        delimiter = guess_delimiter(first_l)
        headers   = guess_headers(first_l.split(delimiter))
        indexes   = guess_indexes(headers, first_l.split(delimiter))

        discard_dups_r = DEF_DISCARD_RAW
        discard_dups   = DEF_DISCARD

        if len(args['indexes']) >= 1 and args['indexes'][0] != SKIP:
            delimiter = args['indexes'][0]

        if len(args['indexes']) >= 2 and args['indexes'][1] != SKIP:
            if args['indexes'][1] == '__head__':
                headers = source.next().rstrip().split(delimiter)
            else:
                headers = args['indexes'][1].split(SPLIT)
        else:
            # Reprocessing the headers with custom delimiter
            headers = guess_headers(first_l.split(delimiter))

        if len(args['indexes']) >= 3 and args['indexes'][2] != SKIP:
            indexes = args['indexes'][2].split(SPLIT)
        else:
            # Reprocessing the indexes with custom headers
            indexes = guess_indexes(headers, first_l.split(delimiter))

        if len(args['indexes']) >= 4 and args['indexes'][3] != SKIP:
            discard_dups_r = args['indexes'][3]
            discard_dups   = discard_dups_r in TRUTHY

        if verbose:
            print 'Loading GeoBase from stdin with [sniffed] option: -i "%s" "%s" "%s" "%s"' % \
                    (delimiter, SPLIT.join(headers), SPLIT.join(indexes), discard_dups_r)

        g = GeoBase(data='feed',
                    source=source,
                    delimiter=delimiter,
                    headers=headers,
                    indexes=indexes,
                    discard_dups=discard_dups,
                    verbose=warnings)
    else:
        # -i options overrides default
        add_options = {}

        if len(args['indexes']) >= 1 and args['indexes'][0] != SKIP:
            add_options['delimiter'] = args['indexes'][0]

        if len(args['indexes']) >= 2 and args['indexes'][1] != SKIP:
            add_options['headers'] = args['indexes'][1].split(SPLIT)

        if len(args['indexes']) >= 3 and args['indexes'][2] != SKIP:
            add_options['indexes'] = args['indexes'][2].split(SPLIT)

        if len(args['indexes']) >= 4 and args['indexes'][3] != SKIP:
            add_options['discard_dups'] = args['indexes'][3] in TRUTHY

        if verbose:
            if not add_options:
                print 'Loading GeoBase "%s"...' % args['base']
            else:
                print 'Loading GeoBase "%s" with custom: %s ...' % \
                        (args['base'], ' and '.join('%s = %s' % kv for kv in add_options.items()))

        g = GeoBase(data=args['base'], verbose=warnings, **add_options)

    if verbose:
        after_init = datetime.now()

    # Tuning parameters
    if args['exact_property'] is None:
        args['exact_property'] = best_field(DEF_EXACT_FIELDS, g.fields)

    exact_properties = args['exact_property'].split(SPLIT)

    if args['fuzzy_property'] is None:
        args['fuzzy_property'] = best_field(DEF_FUZZY_FIELDS, g.fields)

    # Reading map options
    label           = best_field(DEF_LABEL_FIELDS, g.fields)
    point_size      = best_field(DEF_SIZE_FIELDS,  g.fields)
    point_color     = best_field(DEF_COLOR_FIELDS, g.fields)
    icon_type       = DEF_ICON_TYPE
    link_duplicates = DEF_LINK_DUPLICATES

    if len(args['map_data']) >= 1 and args['map_data'][0] != SKIP:
        label = args['map_data'][0]

    if len(args['map_data']) >= 2 and args['map_data'][1] != SKIP:
        point_size = None if args['map_data'][1] == DISABLE else args['map_data'][1]

    if len(args['map_data']) >= 3 and args['map_data'][2] != SKIP:
        point_color = None if args['map_data'][2] == DISABLE else args['map_data'][2]

    if len(args['map_data']) >= 4 and args['map_data'][3] != SKIP:
        icon_type = None if args['map_data'][3] == DISABLE else args['map_data'][3]

    if len(args['map_data']) >= 5 and args['map_data'][4] != SKIP:
        link_duplicates = args['map_data'][4] in TRUTHY

    # Reading quiet options
    quiet_delimiter = DEF_QUIET_DELIM
    header_display  = DEF_QUIET_HEADER

    if len(args['quiet_options']) >= 1 and args['quiet_options'][0] != SKIP:
        quiet_delimiter = args['quiet_options'][0]

    if len(args['quiet_options']) >= 2 and args['quiet_options'][1] != SKIP:
        header_display = args['quiet_options'][1]

    # Reading interactive query options
    interactive_field = DEF_INTER_FIELD
    interactive_type  = DEF_INTER_TYPE

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
            error('geocode_support', g.data)

    # Failing on wrong headers
    if args['exact'] is not None:
        for field in exact_properties:
            if field not in g.fields:
                error('property', field, g.data, g.fields)

    if args['fuzzy'] is not None:
        if args['fuzzy_property'] not in g.fields:
            error('property', args['fuzzy_property'], g.data, g.fields)

    # Failing on unknown fields
    fields_to_test = [
        f for f in (label, point_size, point_color, interactive_field)
        if f is not None
    ]

    for field in args['show'] + args['omit'] + fields_to_test:
        if field not in [REF] + g.fields:
            error('field', field, g.data, [REF] + g.fields)

    # Testing icon_type from -M
    if icon_type not in ALLOWED_ICON_TYPES:
        error('wrong_value', icon_type, ALLOWED_ICON_TYPES)

    # Testing -I option
    if interactive_type not in ALLOWED_INTER_TYPES:
        error('wrong_value', interactive_type, ALLOWED_INTER_TYPES)



    #
    # MAIN
    #
    if verbose:
        if not stdin.isatty() and interactive_query_mode:
            print 'Looking for matches from stdin query...'
        elif args['keys']:
            print 'Looking for matches from %s...' % ', '.join(args['keys'])
        else:
            print 'Looking for matches from *all* data...'

    # Keeping track of last filter applied
    last = None

    # Keeping only keys in intermediate search
    ex_keys = lambda res : None if res is None else (e[1] for e in res)

    # We start from either all keys available or keys listed by user
    # or from stdin if there is input
    if not stdin.isatty() and interactive_query_mode:
        values = [row.strip() for row in stdin]
        # Query type
        if interactive_type == '__exact__':
            if interactive_field == '__key__':
                res = enumerate(values)
            else:
                conditions = [(interactive_field, val) for val in values]
                res = g.getKeysWhere(conditions, force_str=True, mode='or')
                last = 'exact'

        elif interactive_type == '__fuzzy__':
            res = []
            for val in values:
                res.extend(list(g.fuzzyGet(val, interactive_field, min_match=DEF_INTER_FUZZY_L)))
            last = 'fuzzy'

    elif args['keys']:
        res = enumerate(args['keys'])
    else:
        res = enumerate(g)

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

        exact_values = args['exact'].split(SPLIT, len(exact_properties) - 1)
        conditions = list(izip_longest(exact_properties, exact_values, fillvalue=''))
        mode = 'or' if args['any'] else 'and'

        if verbose:
            if args['reverse']:
                print 'Applying property %s' % (' %s ' % mode).join('%s != "%s"' % c for c in conditions)
            else:
                print 'Applying property %s' % (' %s ' % mode).join('%s == "%s"' % c for c in conditions)

        res = list(g.getKeysWhere(conditions, from_keys=ex_keys(res), reverse=args['reverse'], mode=mode, force_str=True))
        last = 'exact'


    if args['fuzzy'] is not None:
        args['fuzzy'] = ' '.join(args['fuzzy'])
        if verbose:
            print 'Applying property %s ~= "%s"' % (args['fuzzy_property'], args['fuzzy'])

        res = list(g.fuzzyGet(args['fuzzy'], args['fuzzy_property'], min_match=args['fuzzy_limit'], from_keys=ex_keys(res)))
        last = 'fuzzy'


    if args['near'] is not None:
        args['near'] = ' '.join(args['near'])
        if verbose:
            print 'Applying near %s km from "%s" (%s grid)' % (args['near_limit'], args['near'], 'with' if with_grid else 'without')

        coords = scan_coords(args['near'], g, verbose)
        res = sorted(g.findNearPoint(coords, radius=args['near_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'near'


    if args['closest'] is not None:
        args['closest'] = ' '.join(args['closest'])
        if verbose:
            print 'Applying closest %s from "%s" (%s grid)' % (args['closest_limit'], args['closest'], 'with' if with_grid else 'without')

        coords = scan_coords(args['closest'], g, verbose)
        res = list(g.findClosestFromPoint(coords, N=args['closest_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'closest'


    if verbose:
        end = datetime.now()
        print 'Done in %s = (load) %s + (search) %s' % \
                (end - before_init, after_init - before_init, end - after_init)


    #
    # DISPLAY
    #

    # Saving to list
    res = list(res)

    # Removing unknown keys
    for h, k in res:
        if k not in g:
            warn('key', k, g.data, g._source)

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
        for prop in exact_properties:
            important.add(prop)

    if args['fuzzy'] is not None:
        important.add(args['fuzzy_property'])

    if interactive_query_mode:
        important.add(interactive_field)

    # reference may be different thing depending on the last filter
    if last in ['near', 'closest']:
        ref_type = 'distance'
    elif last in ['trep', 'fuzzy']:
        ref_type = 'percentage'
    else:
        ref_type = 'index'

    # Display
    if frontend == 'map':
        templates, max_t = g.visualize(output=g.data,
                                       label=label,
                                       point_size=point_size,
                                       point_color=point_color,
                                       icon_type=icon_type,
                                       from_keys=ex_keys(res),
                                       link_duplicates=link_duplicates,
                                       verbose=True)

        if templates and verbose:
            display_browser(templates, nb_res)
            launch_http_server(ADDRESS, PORT)

        if len(templates) < max_t:
            # At least one html not rendered
            frontend = 'terminal'
            res = res[:DEF_NUM_COL]

            print '/!\ %s template(s) not rendered. Switching to terminal frontend...' % \
                    (max_t - len(templates))


    # We protect the stdout.write against the IOError
    if frontend == 'terminal':
        display(g, res, set(args['omit']), args['show'], important, ref_type)

    if frontend == 'quiet':
        display_quiet(g, res, set(args['omit']), args['show'], ref_type, quiet_delimiter, header_display)

    if verbose:
        for warn_msg in ENV_WARNINGS:
            print dedent(warn_msg),



if __name__ == '__main__':

    main()

