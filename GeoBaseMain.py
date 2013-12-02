#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is a launcher for the GeoBases package.
"""

import sys
import os
import os.path as op

from math import ceil, log
from itertools import izip_longest, chain
from textwrap import dedent
import platform
import re
import json

# Not in standard library
from termcolor import colored
import colorama
import argparse # in standard libraray for Python >= 2.7

# Private
from GeoBases import GeoBase, DEFAULTS, SourcesManager, is_remote, is_archive


IS_WINDOWS = platform.system() in ('Windows',)

if not IS_WINDOWS:
    import signal
    # On windows, SIGPIPE does not exist
    # Do not produce broken pipes when head and tail are used
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


try:
    # Hack to remove escape char when importing readline
    os.environ['TERM'] = 'linux'

    # readline is not available on every platform
    # this may cause ImportError
    import readline
    import glob

    def complete(text, state):
        """Activate autocomplete on raw_input.
        """
        return (glob.glob(text + '*') + [None])[state]

    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)


    def ask_input(prompt, prefill=''):
        """Custom default when asking for input.
        """
        readline.set_startup_hook(lambda: readline.insert_text(str(prefill)))
        try:
            return raw_input(prompt)
        finally:
            readline.set_startup_hook()

except ImportError:

    def ask_input(prompt, prefill=''):
        """Fallback.
        """
        if prefill:
            answer = raw_input('%s[%s] ' % (prompt, str(prefill)))
        else:
            answer = raw_input('%s' % prompt)

        if answer:
            return answer
        else:
            # No answer, returning default
            return prefill


def ask_till_ok(msg, allowed=None, show=True, is_ok=None, fail_message=None, boolean=False, default=False, prefill=''):
    """Ask a question and only accept a list of possibilities as response.
    """
    if boolean:
        allowed = ('Y', 'y', 'N', 'n', '')
        show = False

    if is_ok is None:
        is_ok = lambda r: True

    if allowed is None:
        is_allowed = lambda r: True
    else:
        is_allowed = lambda r: r in allowed

    # Start
    if show and allowed is not None:
        two_col_print(allowed)

    response = ask_input(msg, prefill).strip()

    while not is_ok(response) or not is_allowed(response):
        if fail_message is not None:
            print fail_message
        response = ask_input(msg, prefill).strip()

    if not boolean:
        return response
    else:
        if default is True:
            return response in ('Y', 'y', '')
        else:
            return response in ('Y', 'y')


def is_in_path(command):
    """This checks if a command is in the PATH.
    """
    path = os.popen('which %s 2> /dev/null' % command, 'r').read()

    if path:
        return True
    else:
        return False


def get_stty_size():
    """
    This gives terminal size information using external
    command stty.
    This function is not great since where stdin is used, stty
    fails and we return the default case.
    """
    size = os.popen('stty size 2>/dev/null', 'r').read()

    if not size:
        return (80, 160)

    return tuple(int(d) for d in size.split())


def get_term_size():
    """
    This gives terminal size information.
    """
    try:
        import fcntl, termios, struct
    except ImportError:
        return get_stty_size()

    def ioctl_GWINSZ(fd):
        """Read terminal size."""
        try:
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except IOError:
            return
        return cr

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
        current[0] = 'yellow' if self._background == 'black' else 'cyan'
        return tuple(current)


    @staticmethod
    def convertJoin(col):
        """Get special join color. Only change foreground color.
        """
        current    = list(col)
        current[0] = 'green'
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
        """Get special field color.
        """
        return ('magenta', None, [])


def flatten(value, level=0):
    """Flatten nested structures into str.

    >>> flatten(())
    ''
    >>> flatten('T0')
    'T0'
    >>> flatten(['T1', 'T1'])
    'T1/T1'
    >>> flatten([('T2', 'T2'), 'T1'])
    'T2:T2/T1'
    >>> flatten([('T2', ['T3', 'T3']), 'T1'])
    'T2:T3,T3/T1'

    None is flatten as ''.

    >>> flatten([('T2', ['T3', None]), 'T1'])
    'T2:T3,/T1'
    """
    splitters = ['/', ':', ',']

    if level >= len(splitters):
        splitter = '|'
    else:
        splitter = splitters[level]

    level += 1

    if isinstance(value, (list, tuple, set)):
        return splitter.join(flatten(e, level) for e in value)
    else:
        return str(value) if value is not None else ''


def check_ext_field(geob, field):
    """
    Check if a field given by user contains
    join fields and external field.
    """
    l = field.split(':', 1)

    if len(l) <= 1:
        return field, None

    f, ext_f = l

    if geob.hasJoin(f):
        return f, ext_f

    # In case of multiple join fields
    f = tuple(f.split(SPLIT))

    if geob.hasJoin(f):
        return f, ext_f

    return field, None


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

    if ref_type == 'phonemes':
        if isinstance(ref, (list, tuple, set)):
            return SPLIT.join(str(e) for e in ref)
        else:
            return str(ref)

    if ref_type == 'index':
        return '%s' % int(ref)

    raise ValueError('ref_type %s was not allowed' % ref_type)



def display_terminal(geob, list_of_things, shown_fields, ref_type, important):
    """
    Main display function in Linux terminal, with
    nice color and everything.
    """
    if not list_of_things:
        print 'No elements to display.'
        return

    # Different behaviour given number of results
    # We adapt the width between MIN_CHAR_COL and MAX_CHAR_COL
    # given number of columns and term width
    n   = len(list_of_things)
    lim = int(get_term_size()[1] / float(n + 1))
    lim = min(MAX_CHAR_COL, max(MIN_CHAR_COL, lim))

    if n == 1:
        # We do not truncate names if only one result
        truncate = None
    else:
        truncate = lim

    c = RotatingColors(BACKGROUND_COLOR)

    for f in shown_fields:
        # Computing clean fields, external fields, ...
        if f == REF:
            cf = REF
        else:
            cf, ext_f = check_ext_field(geob, f)
            if ext_f is None:
                get = lambda k: geob.get(k, cf)
            else:
                get = lambda k: geob.get(k, cf, ext_field=ext_f)

        if cf in important:
            col = c.getEmph()
        elif cf == REF:
            col = c.getHeader()
        elif geob._isFieldSpecial(cf):
            col = c.getSpecial() # For special fields like __dup__
        else:
            col = c.get()

        if geob._isFieldRaw(cf):
            col = c.convertRaw(col)  # For raw fields

        if geob.hasJoin(cf):
            col = c.convertJoin(col) # For joined fields

        # Fields on the left
        l = [fixed_width(f, c.convertBold(col), lim, truncate)]

        if f == REF:
            for h, _ in list_of_things:
                l.append(fixed_width(fmt_ref(h, ref_type), col, lim, truncate))
        else:
            for _, k in list_of_things:
                l.append(fixed_width(get(k), col, lim, truncate))

        next(c)
        print ''.join(l)


def fields_to_show(defaults, exclude, show, show_additional):
    """Process fields to show.
    """
    if not show:
        show = defaults

    # Building final shown headers
    shown_fields = [f for f in show if f not in exclude]

    # Trying to cleverly position addtional field
    positions = []
    for af in show_additional:
        for i, f in enumerate(shown_fields):
            if af.startswith(f):
                positions.append(i+1)
                break
        else:
            positions.append(-1)

    already_inserted = 0
    for af, p in zip(show_additional, positions):
        if p == -1:
            shown_fields.append(af)
        else:
            shown_fields.insert(p + already_inserted, af)
            already_inserted += 1

    return shown_fields



def display_quiet(geob, list_of_things, shown_fields, ref_type, delim, header):
    """
    This function displays the results in programming
    mode, with --quiet option. This is useful when you
    want to use use the result in a pipe for example.
    """
    # Headers joined
    j_headers = delim.join(str(f) for f in shown_fields)

    # Displaying headers only for RH et CH
    if header == 'RH':
        print j_headers
    elif header == 'CH':
        print '#%s' % j_headers

    # Caching getters
    getters = {}
    for f in shown_fields:
        if f == REF:
            continue
        cf, ext_f = check_ext_field(geob, f)
        if ext_f is None:
            getters[f] = cf, ext_f, lambda k, cf, ext_f: geob.get(k, cf)
        else:
            getters[f] = cf, ext_f, lambda k, cf, ext_f: geob.get(k, cf, ext_field=ext_f)

    for h, k in list_of_things:
        l = []
        for f in shown_fields:
            if f == REF:
                l.append(fmt_ref(h, ref_type, no_symb=True))
            else:
                # Get from getters cache
                cf, ext_f, get = getters[f]

                v = get(k, cf, ext_f)
                # Small workaround to display nicely lists in quiet mode
                # Delimited fields are already handled with raw version, but
                # __dup__ field has no raw version for dumping
                if isinstance(v, (list, tuple, set)):
                    l.append(flatten(v))
                else:
                    l.append(str(v) if v is not None else '')

        print delim.join(l)


def display_browser(templates, output_dir, nb_res, address, port):
    """Display templates in the browser.
    """
    # Save current working directory
    previous_wd = os.getcwd()

    if not output_dir:
        output_dir = '.'

    # Moving where files are
    os.chdir(output_dir)

    # We manually launch browser, unless we risk a crash
    to_be_launched = []

    for template in templates:
        # Getting relative path for current working dir
        template = op.relpath(template, output_dir)

        if template.endswith('_table.html'):
            if nb_res <= TABLE_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print '/!\ "%s %s:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (BROWSER, address, port, template, nb_res)

        elif template.endswith('_map.html'):
            if nb_res <= MAP_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print '/!\ "%s %s:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (BROWSER, address, port, template, nb_res)

        elif template.endswith('_globe.html'):
            if nb_res <= GLOBE_BROWSER_LIM:
                to_be_launched.append(template)
            else:
                print '/!\ "%s %s:%s/%s" not launched automatically. %s results, may be slow.' % \
                        (BROWSER, address, port, template, nb_res)
        else:
            to_be_launched.append(template)

    if to_be_launched:
        urls = ['%s:%s/%s' % (address, port, tpl) for tpl in to_be_launched]
        os.system('%s %s 2>/dev/null &' % (BROWSER, ' '.join(urls)))

    # Serving the output_dir, where we are
    launch_http_server(address, port)

    # Moving back
    os.chdir(previous_wd)


def launch_http_server(address, port):
    """Launch a SimpleHTTPServer.
    """
    import SimpleHTTPServer
    import SocketServer

    class MyTCPServer(SocketServer.TCPServer):
        """Overrides standard library.
        """
        allow_reuse_address = True

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd   = MyTCPServer((address, port), Handler)

    try:
        print '* Serving on %s:%s (hit ctrl+C to stop)' % (address, port)
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
    # Then we encode again before display
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
    warn('key', u_input, geob.data, geob.loaded)
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
        '@', # this is for duplicated keys
        '-', # this is usually a datetime separator
        '/', # same
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


ADD_INFO_REG = re.compile("([^{}]*)({?[^{}]*}?)({?[^{}]*}?)")

def clean_headers(headers):
    """
    Remove additional informations from headers,
    and return what was found.
    """
    subdelimiters = {}
    join          = []

    for i, h in enumerate(headers):

        m = ADD_INFO_REG.match(h)
        if m is None:
            continue

        clean_h, jn, subd = m.groups()
        headers[i] = clean_h

        # We consider the join only if the user did not give nothing or empty {}
        jn = jn.strip('{}')
        if jn:
            join.append({
                'fields' : clean_h,
                'with'   : jn.split(':', 1)
            })

        # For the subdelimiters we consider {} as empty string
        if subd:
            subd = subd.strip('{}')
            if subd == '':
                subdelimiters[clean_h] = ''
            else:
                subdelimiters[clean_h] = subd.split(':')

    return join, subdelimiters


def guess_headers(row, delimiter):
    """Heuristic to guess the lat/lng fields from first row.
    """
    if delimiter:
        row = row.split(delimiter)
    else:
        row = list(row)

    headers = list(generate_headers(len(row)))

    # Name candidates for lat/lng
    lat_candidates = set(['latitude',  'lat'])
    lng_candidates = set(['longitude', 'lng', 'lon'])

    lat_found, lng_found = False, False

    for i, f in enumerate(row):
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


def score_key(v):
    """Eval likelihood of being a good field for generating keys.

    The shorter the better, and int get a len() of 1.
    0, 1 and floats are weird for key_fields, as well as 1-letter strings.
    """
    if str(v).endswith('__key__') or str(v).lower().endswith('id'):
        return 0

    if isinstance(v, float):
        return 1000

    if isinstance(v, int):
        if v <= 1: # we avoid a domain error on next case
            return 10
        return max(2, 25 / log(v))

    return len(v) if len(v) >= 2 else 10


def guess_key_fields(row, delimiter, headers):
    """Heuristic to guess key_fields from headers and first row.
    """
    if not headers:
        return []

    if delimiter:
        row = row.split(delimiter)
    else:
        row = list(row)

    discarded  = set(['lat', 'lng'])
    candidates = []

    for h, v in zip(headers, row):
        # Skip discarded and empty values
        if h not in discarded and v:
            try:
                val = float(v)
            except ValueError:
                # is *not* a number
                candidates.append((h, score_key(v)))
            else:
                # is a number
                if val == int(val):
                    candidates.append((h, score_key(int(val))))
                else:
                    candidates.append((h, score_key(val)))

    if not candidates:
        return [headers[0]]

    return [ min(candidates, key=lambda x: x[1])[0] ]


def build_pairs(L, layout='v'):
    """
    Some formatting for help.
    """
    n = float(len(L))
    h = int(ceil(n / 2)) # half+

    if layout == 'h':
        return izip_longest(L[::2], L[1::2], fillvalue='')

    if layout == 'v':
        return izip_longest(L[:h], L[h:], fillvalue='')

    raise ValueError('Layout must be "h" or "v", but was "%s"' % layout)


def split_if_several(value):
    """Only split if several elements.
    """
    value = value.split(SPLIT)

    if len(value) == 1:
        return value[0]
    return value


def to_CLI(option, value):
    """Format stuff from the configuration file.
    """
    if option == 'path':
        return value['file']

    if option == 'delimiter':
        return str(value)

    if option == 'headers':
        return flatten(value)

    if option == 'key_fields':
        if value is None:
            return ''
        else:
            return flatten(value)

    if option == 'index':
        return flatten(value)

    if option == 'join':
        if len(value['with']) < 2:
            if not value['with'][0]:
                return flatten(value['fields'])
            return '%s{%s}' % (flatten(value['fields']),
                               value['with'][0])
        else:
            return '%s{%s:%s}' % (flatten(value['fields']),
                                  value['with'][0],
                                  flatten(value['with'][1]))

    raise ValueError('Did not understand option "%s".' % option)


def best_field(candidates, possibilities, default=None):
    """Select best candidate in possibilities.
    """
    for candidate in candidates:
        if candidate in possibilities:
            return candidate
    return default


def two_col_print(L):
    """Display enumerable on two columns.
    """
    print
    for p in build_pairs(L):
        print '\t%-20s\t%-20s' % p
    print


def warn(name, *args):
    """
    Display a warning on stderr.
    """
    if name == 'key':
        print >> sys.stderr, '/!\ Key %s was not in base, for data "%s" and source %s' % \
                (args[0], args[1], args[2])

    if name == 'installation':
        print >> sys.stderr, '/!\ %s is not installed, no package information available.' % \
                args[0]


def error(name, *args):
    """
    Display an error on stderr, then exit.
    First argument is the error type.
    """
    if name == 'trep_support':
        print >> sys.stderr, '\n/!\ No opentrep support. Check if OpenTrepWrapper can import libpyopentrep.'

    elif name == 'geocode_support':
        print >> sys.stderr, '\n/!\ No geocoding support for data type %s.' % args[0]

    elif name == 'data':
        print >> sys.stderr, '\n/!\ Wrong data type "%s". You may select:' % args[0]
        for p in build_pairs(args[1]):
            print >> sys.stderr, '\t%-20s\t%-20s' % p

    elif name == 'field':
        print >> sys.stderr, '\n/!\ Wrong field "%s".' % args[0]
        print >> sys.stderr, 'For data type "%s", you may select:' % args[1]
        for p in build_pairs(args[2]):
            print >> sys.stderr, '\t%-20s\t%-20s' % p

    elif name == 'geocode_format':
        print >> sys.stderr, '\n/!\ Bad geocode format: %s' % args[0]

    elif name == 'geocode_unknown':
        print >> sys.stderr, '\n/!\ Geocode was unknown for %s' % args[0]

    elif name == 'empty_stdin':
        print >> sys.stderr, '\n/!\ Stdin was empty'

    elif name == 'wrong_value':
        print >> sys.stderr, '\n/!\ Wrong value "%s", should be in:' % args[0]
        for p in build_pairs(args[1]):
            print >> sys.stderr, '\t%-20s\t%-20s' % p

    elif name == 'type':
        print >> sys.stderr, '\n/!\ Wrong type for "%s", should be %s, but was "%s".' % \
                (args[0], args[1], args[2])

    elif name == 'aborting':
        print >> sys.stderr, '\n\n/!\ %s' % args[0]

    elif name == 'not_allowed':
        print >> sys.stderr, '\n/!\ Value "%s" not allowed.' % args[0]

    exit(1)


def panic_mode():
    """Panic mode.
    """
    # Here we have a broken source file
    print '\n/!\ Source file seems broken.\n'

    try:
        restore = ask_till_ok('Restore file %s\nFrom origin  %s [yN]? ' % \
                              (S_MANAGER.sources_conf_path,
                               S_MANAGER.sources_conf_path_origin),
                              boolean=True,
                              default=False)

    except (KeyboardInterrupt, EOFError):
        print '\n\nYou should have said "Yes" :).'

    else:
        if restore:
            S_MANAGER.restore(clean_cache=False)
            print '\nRestored.'
        else:
            print '\nDid not restore.'



#######
#
#  MAIN
#
#######

# Global defaults
PACKAGE_NAME = 'GeoBasesDev'
SCRIPT_NAME  = 'GeoBase'
DESCRIPTION  = 'Data services and visualization - development version'

# Sources manager
S_MANAGER = SourcesManager()

# Contact info
CONTACT_INFO = '''
Report bugs : geobases.dev@gmail.com
Home page   : http://opentraveldata.github.com/geobases
API doc     : https://geobases.readthedocs.org
Wiki pages  : https://github.com/opentraveldata/geobases/wiki/_pages
'''

try:
    HELP_SOURCES = S_MANAGER.build_status()
except (KeyError, ValueError, TypeError):
    # Here we have a broken source file
    panic_mode()
    exit(1)


CLI_EXAMPLES = '''
* Command line examples

 $ %s ORY CDG                    # query on the keys ORY and CDG
 $ %s --closest CDG              # find closest from CDG
 $ %s --near '48.853, 2.348'     # find near some geocode
 $ %s --fuzzy "san francisko"    # fuzzy search, with typo ;)
 $ %s --admin                    # administrate the data sources
 $ %s --help                     # your best friend
 $ cat data.csv | %s             # with your data
''' % ((op.basename(sys.argv[0]),) * 7)

DEF_BASE            = 'ori_por'
DEF_FUZZY_LIMIT     = 0.85
DEF_NEAR_LIMIT      = 50.
DEF_CLOSEST_LIMIT   = 10
DEF_TREP_FORMAT     = 'S'
DEF_QUIET_DELIM     = '^'
DEF_QUIET_HEADER    = 'CH'
DEF_FUZZY_FIELDS    = ('name', 'country_name', 'currency_name', '__key__')
DEF_EXACT_FIELDS    = ('__key__',)
DEF_PHONETIC_FIELDS = ('name', 'country_name', 'currency_name', '__key__')
DEF_PHONETIC_METHOD = 'dmetaphone'
DEF_EXCLUDE_FIELDS  = []
DEF_SHOW_FIELDS     = []
DEF_SHOW_ADD_FIELDS = []

# Magic value option to skip and leave default, or disable
SKIP    = '_'
SPLIT   = '/'
DISABLE = '__none__'
REF     = '__ref__'

ALLOWED_ICON_TYPES       = (None, 'auto', 'S', 'B')
ALLOWED_INTER_TYPES      = ('__key__', '__exact__', '__fuzzy__', '__phonetic__')
ALLOWED_PHONETIC_METHODS = ('dmetaphone', 'dmetaphone-strict', 'metaphone', 'nysiis')
ALLOWED_COMMANDS         = ('status', 'fullstatus',
                            'add', 'edit', 'zshautocomp',
                            'drop', 'restore', 'fullrestore',
                            'update', 'forceupdate')

DEF_INTER_FIELDS = ('iata_code', '__key__')
DEF_INTER_TYPE   = '__exact__'

# Considered truthy values for command line option
TRUTHY = ('1', 'Y')

# Duplicates handling in feed mode
DEF_DISCARD_RAW = 'F'
DEF_DISCARD     = False
DEF_INDICES     = []

DEF_JOIN_RAW = SKIP
DEF_JOIN     = []

# Globals for http server
ADDRESS = '0.0.0.0'
PORT    = 4135
BROWSER = 'firefox'

if is_in_path('google-chrome'):
    BROWSER = 'google-chrome'

# For temporary files
DEF_OUTPUT_DIR = 'tmpviz'

# Defaults for map
DEF_LABEL_FIELDS     = ('name',       'country_name', '__key__')
DEF_WEIGHT_FIELDS    = ('page_rank',  'population',   None)
DEF_COLOR_FIELDS     = ('raw_offset', 'fclass',       None)
DEF_ICON_TYPE        = 'auto' # icon type: small, big, auto, ...
DEF_LINK_DUPLICATES  = True
DEF_DRAW_JOIN_FIELDS = True

MAP_BROWSER_LIM   = 8000   # limit for launching browser automatically
GLOBE_BROWSER_LIM = 8000   # limit for launching browser automatically
TABLE_BROWSER_LIM = 2000   # limit for launching browser automatically

# Graph defaults, generate_headers is used for stdin input
DEF_GRAPH_WEIGHT = None
DEF_GRAPH_FIELDS = ('continent_name', 'raw_offset',
                    'alliance_code',  'unified_code') + \
                   tuple(generate_headers(5)) + \
                   ('__key__',)

# Dashboard defaults
DEF_DASHBOARD_WEIGHT = None
DEF_DASHBOARD_KEEP   = 4

# Terminal width defaults
DEF_CHAR_COL = 25
MIN_CHAR_COL = 3
MAX_CHAR_COL = 40
DEF_NUM_COL  = int(get_term_size()[1] / float(DEF_CHAR_COL)) - 1

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


if not is_in_path(SCRIPT_NAME):
    ENV_WARNINGS.append('''
    **********************************************************************
    "%s" does not seem to be in your $PATH.                         *
    To disable this message, add to your ~/.bashrc or ~/.zshrc:          *
                                                                         *
        export PATH=$PATH:$HOME/.local/bin
                                                                         *
    *************************************************************** README
    ''' % SCRIPT_NAME)


if ENV_WARNINGS:
    # Assume the user did not read the wiki :D
    ENV_WARNINGS.append('''
    **********************************************************************
    By the way, since you probably did not read the documentation :D,    *
    you should also add this for the completion to work with zsh.        *
    You are using zsh right o_O?                                         *
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
    fmt_or = lambda L : ' or '.join('"%s"' % str(e) for e in L)

    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.epilog = '%s\n%s\n%s' % (CLI_EXAMPLES, HELP_SOURCES, CONTACT_INFO)

    parser.add_argument('keys',
        help = dedent('''\
        Main argument. This will be used as a list of keys on which we
        apply filters. Leave empty to consider all keys.
        '''),
        metavar = 'KEY',
        nargs = '*')

    parser.add_argument('-A', '--admin',
        help = dedent('''\
        This option can be used to administrate sources.
        It accepts a two optional arguments: command, base.
        As command argument, you may use either
        %s,
        %s.
        Leave empty and answer questions otherwise.
        ''' % (', '.join(ALLOWED_COMMANDS[:5]),
               ', '.join(ALLOWED_COMMANDS[5:]))),
        nargs = '*',
        metavar = 'COMMAND',
        default = None)

    parser.add_argument('-a', '--ask',
        help = dedent('''\
        This option turns on learning mode, where you just
        answer questions about what you want to do.
        '''),
        action = 'store_true')

    parser.add_argument('-b', '--base',
        help = dedent('''\
        Choose a different data type, default is "%s".
        Also available are stations, airports, countries...
        Give unadmissible value and all possibilities will be displayed.
        ''' % DEF_BASE),
        metavar = 'BASE',
        default = DEF_BASE)

    parser.add_argument('-f', '--fuzzy',
        help = dedent('''\
        Rather than looking up a key, this mode will search the best
        match for the field given by --fuzzy-field option, for
        the argument. Limit can be specified with --fuzzy-limit option.
        '''),
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-F', '--fuzzy-field',
        help = dedent('''\
        When performing a fuzzy search, specify the field to be chosen.
        Default is %s
        depending on fields.
        Give unadmissible field and available values will be displayed.
        ''' % fmt_or(DEF_FUZZY_FIELDS)),
        metavar = 'FIELD',
        default = None)

    parser.add_argument('-L', '--fuzzy-limit',
        help = dedent('''\
        Specify a min limit for fuzzy searches, default is %s.
        This is the Levenshtein ratio of the two strings.
        ''' % DEF_FUZZY_LIMIT),
        metavar = 'RATIO',
        default = DEF_FUZZY_LIMIT,
        type = float)

    parser.add_argument('-p', '--phonetic',
        help = dedent('''\
        Rather than looking up a key, this mode will search the best phonetic
        match for the field given by --phonetic-field option, for
        the argument. This works well only for english.
        Use --phonetic-method to change the method used.
        '''),
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-P', '--phonetic-field',
        help = dedent('''\
        When performing a phonetic search, specify the field to be chosen.
        Default is %s
        depending on fields.
        Give unadmissible field and available values will be displayed.
        ''' % fmt_or(DEF_PHONETIC_FIELDS)),
        metavar = 'FIELD',
        default = None)

    parser.add_argument('-y', '--phonetic-method',
        help = dedent('''\
        By default, --phonetic uses "%s" method.
        With this option, you can change the phonetic method to
        %s.
        ''' % (DEF_PHONETIC_METHOD, fmt_or(ALLOWED_PHONETIC_METHODS))),
        metavar = 'METHOD',
        default = DEF_PHONETIC_METHOD)

    parser.add_argument('-e', '--exact',
        help = dedent('''\
        Rather than looking up a key, this mode will search all keys
        whose specific field given by --exact-field match the
        argument. By default, the %s field is used for the search.
        You can have several field matching by giving multiple values
        delimited by "%s" for --exact-field. Make sure you give the
        same number of values delimited also by "%s" then.
        ''' % (fmt_or(DEF_EXACT_FIELDS), SPLIT, SPLIT)),
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-E', '--exact-field',
        help = dedent('''\
        When performing an exact search, specify the field to be chosen.
        Default is %s. Give unadmissible field and available
        values will be displayed.
        You can give multiple fields delimited by "%s". Make sure
        you give the same number of values delimited also by "%s" for -e then.
        ''' % (fmt_or(DEF_EXACT_FIELDS), SPLIT, SPLIT)),
        metavar = 'FIELD',
        default = None)

    parser.add_argument('-r', '--reverse',
        help = dedent('''\
        When possible, reverse the logic of the filter. Currently
        only --exact supports that.
        '''),
        action = 'store_true')

    parser.add_argument('-O', '--or',
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
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-N', '--near-limit',
        help = dedent('''\
        Specify a radius in km when performing geographical
        searches with --near. Default is %s km.
        ''' % DEF_NEAR_LIMIT),
        metavar = 'RADIUS',
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
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-C', '--closest-limit',
        help = dedent('''\
        Specify a limit for closest search with --closest, default is %s.
        ''' % DEF_CLOSEST_LIMIT),
        metavar = 'LIM',
        default = DEF_CLOSEST_LIMIT,
        type = int)

    parser.add_argument('--no-grid',
        help = dedent('''\
        When performing a geographical search, a geographical index is used.
        This may lead to inaccurate results in some (rare) case when using
        --closest searches (--near searches are never impacted).
        Adding this option will disable the index, and browse the full
        data set to look for the results.
        '''),
        action = 'store_true')

    parser.add_argument('-t', '--trep',
        help = dedent('''\
        Rather than looking up a key, this mode will use opentrep.
        '''),
        metavar = 'VALUE',
        default = None,
        nargs = '+')

    parser.add_argument('-T', '--trep-format',
        help = dedent('''\
        Specify a format for trep searches with --trep, default is "%s".
        ''' % DEF_TREP_FORMAT),
        metavar = 'FORMAT',
        default = DEF_TREP_FORMAT)

    parser.add_argument('-x', '--exclude',
        help = dedent('''\
        Does not print some fields on stdout.
        May help to get cleaner output.
        "%s" is an available value as well as any other fields.
        ''' % REF),
        metavar = 'FIELD',
        nargs = '+',
        default = DEF_EXCLUDE_FIELDS)

    parser.add_argument('-s', '--show',
        help = dedent('''\
        Only print some fields on stdout.
        May help to get cleaner output.
        "%s" is an available value as well as any other fields.
        ''' % REF),
        metavar = 'FIELD',
        nargs = '+',
        default = DEF_SHOW_FIELDS)

    parser.add_argument('-S', '--show-additional',
        help = dedent('''\
        In addition to the normal displayed fields, add other fields.
        This is useful for displaying fields with join information,
        with the field:external_field syntax.
        '''),
        metavar = 'FIELD',
        nargs = '+',
        default = DEF_SHOW_ADD_FIELDS)

    parser.add_argument('-l', '--limit',
        help = dedent('''\
        Specify a limit for the number of results.
        This must be an integer.
        Default is %s, except in quiet display where it is disabled.
        ''' % DEF_NUM_COL),
        metavar = 'NUM',
        default = None)

    parser.add_argument('-i', '--indexation',
        help = dedent('''\
        Specify metadata, for stdin input as well as existing bases.
        This will override defaults for existing bases.
        6 optional arguments: delimiter, headers, key_fields, discard_dups, indices, join.
            1) default delimiter is smart :).
            2) default headers will use numbers, and try to sniff lat/lng.
               Use __head__ as header value to
               burn the first line to define the headers.
               Use header{base:external_field}{subdelimiter} syntax to define
               a join clause for a header, and/or a subdelimiter.
               To give just the subdelimiter you may use header{}{subdelimiter}.
            3) default key_fields will take the first plausible field.
               Put %s to use None as key_fields, which will cause the keys
               to be generated from the line numbers.
            4) discard_dups is a boolean to toggle duplicated keys dropping.
               Put %s as a truthy value, any other value will be falsy.
            5) indices is a field, if given, this will build an index on that field
               to speed up findWith queries.
            6) join is a join clause defined with fields{base:external_fields}.
               This clause can concern multiple fields delimited by "%s".
        Multiple fields may be specified with "%s" delimiter.
        For any field, you may put "%s" to leave the default value.
        Example: -i ',' key/name/country key/country _
        ''' % (DISABLE, fmt_or(TRUTHY), SPLIT, SPLIT, SKIP)),
        nargs = '+',
        metavar = 'OPTION',
        default = [])

    parser.add_argument('-I', '--interactive-query',
        help = dedent('''\
        If given, this option will consider stdin
        input as query material, not data for loading.
        It will read values line by line, and perform a search on them.
        2 optional arguments: field, type.
            1) field is the field from which the data is supposed to be.
               Default is %s depending on fields.
            2) type is the type of matching, either
               %s.
               Default is "%s".
               __key__ type means we will perform a direct key retrieval.
               For fuzzy searches, default ratio is set to %s,
               but can be changed with --fuzzy-limit.
               For phonetic searches, default method is %s,
               but can be changed with --phonetic-method.
        For any field, you may put "%s" to leave the default value.
        Example: -I icao_code __fuzzy__
        ''' % (fmt_or(DEF_INTER_FIELDS), fmt_or(ALLOWED_INTER_TYPES),
               DEF_INTER_TYPE, DEF_FUZZY_LIMIT, DEF_PHONETIC_METHOD, SKIP)),
        nargs = '*',
        metavar = 'OPTION',
        default = None)

    parser.add_argument('-q', '--quiet',
        help = dedent('''\
        Turn off verbosity and provide a programmer friendly output.
        This is a csv-like output, and may still be combined with
        --show and --exclude. Configure with --quiet-options.
        '''),
        action = 'store_true')

    parser.add_argument('-Q', '--quiet-options',
        help = dedent('''\
        Customize the quiet display.
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
        metavar = 'OPTION',
        default = [])

    parser.add_argument('-m', '--map',
        help = dedent('''\
        This is the map display.
        Configure with --map-options.
        HTML/Javascript/JSON files are generated.
        Unless --quiet is also set, a browser will be launched
        and a simple HTTP server will serve the HTML results
        on %s:%s by default.
        ''' % (ADDRESS, PORT)),
        action = 'store_true')

    parser.add_argument('-M', '--map-options',
        help = dedent('''\
        Customize the map display.
        6 optional arguments: label, weight, color, icon, duplicates, draw_join_fields.
            1) label is the field to display on map points.
               Default is %s depending on fields.
            2) weight is the field used to draw circles around points.
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
            6) draw_join_fields is a boolean to toggle lines drawing when
               scanning joined fields who may have geocoding information.
               Default is %s. Put %s as a truthy value,
               any other value will be falsy.
        For any field, you may put "%s" to leave the default value.
        Example: -M _ population _ __none__ _
        ''' % ((fmt_or(DEF_LABEL_FIELDS), fmt_or(DEF_WEIGHT_FIELDS), DISABLE,
                fmt_or(DEF_COLOR_FIELDS), DISABLE, DISABLE, DEF_ICON_TYPE,
                DEF_LINK_DUPLICATES, fmt_or(TRUTHY), DEF_DRAW_JOIN_FIELDS,
                fmt_or(TRUTHY), SKIP))),
        nargs = '+',
        metavar = 'OPTION',
        default = [])

    parser.add_argument('-3', '--3d',
        help = dedent('''\
        When available, enable 3D visualizations.
        This enables the 3D WebGL-based globe when using the map display.
        '''),
        action = 'store_true')

    parser.add_argument('-g', '--graph',
        help = dedent('''\
        This is the graph display (like force directed graph).
        Configure with --graph-fields.
        HTML/Javascript/JSON files are generated.
        Unless --quiet is also set, a browser will be launched
        and a simple HTTP server will serve the HTML results
        on %s:%s by default.
        ''' % (ADDRESS, PORT)),
        action = 'store_true')

    parser.add_argument('-G', '--graph-fields',
        help = dedent('''\
        This option has n arguments: fields used to build
        the graph display. Nodes are the field values. Edges
        represent the data.
        Defaults are, depending on fields, picked in
        %s [...].
        ''' % ', '.join(DEF_GRAPH_FIELDS[0:5])),
        nargs = '+',
        metavar = 'FIELD',
        default = [])

    parser.add_argument('-W', '--graph-weight',
        help = dedent('''\
        This option defines the field used to compute weights
        when drawing graphs. Put "%s" (which will be None) not
        to use any fields, but just count the number of lines.
        Default is counting the number of lines.
        ''' % DISABLE),
        metavar = 'FIELD',
        default = DEF_GRAPH_WEIGHT)

    parser.add_argument('-w', '--with-types',
        help = dedent('''\
        When drawing graphs, consider values from different
        fields to be of different types. Concretely, if there
        are no types, this means we will create only one node
        if the same value is found accross different fields.
        With this option turned on, we would create different
        nodes.
        '''),
        action = 'store_true')

    parser.add_argument('-d', '--dashboard',
        help = dedent('''\
        This is the dashboard display (aggregated view).
        HTML/Javascript/JSON files are generated.
        Unless --quiet is also set, a browser will be launched
        and a simple HTTP server will serve the HTML results
        on %s:%s by default.
        ''' % (ADDRESS, PORT)),
        action = 'store_true')

    parser.add_argument('-D', '--dashboard-options',
        help = dedent('''\
        Customize the dashboard display.
        2 optional arguments: weight, keep.
            1) default weight is "%s".
            2) the second parameter is used to control
               the number of elements kept in each graph.
               Default is %s.
        For any field, you may put "%s" to leave the default value.
        Example: -D _ 10
        ''' % (DEF_DASHBOARD_WEIGHT, DEF_DASHBOARD_KEEP, SKIP)),
        nargs = '+',
        metavar = 'OPTION',
        default = [])

    parser.add_argument('-o', '--output-dir',
        help = dedent('''\
        This option defines the output directory for
        temporary files generated with --map, --graph, --dashboard.
        Default is the current directory.
        '''),
        metavar = 'DIR',
        default = DEF_OUTPUT_DIR)

    parser.add_argument('--port',
        help = dedent('''\
        This option defines the port when serving HTML content.
        Default is %s.
        ''' % PORT),
        metavar = 'PORT',
        type=int,
        default = PORT)

    parser.add_argument('-v', '--verbose',
        help = dedent('''\
        Provides additional informations:
            * warnings during data loading and queries
            * timing information for profiling
            * hints on how to make a data source permanent
            * probably other things
        '''),
        action = 'store_true')

    parser.add_argument('-V', '--version',
        help = dedent('''\
        Display version information.
        '''),
        action = 'store_true')

    return vars(parser.parse_args())



def admin_path(ref_path, source, questions, verbose):
    """Admin path for a source.
    """
    path = ask_input(questions['path'], to_CLI('path', ref_path)).strip()

    if not path:
        print '----- Empty path, deleted'
        return None, None

    path = {
        'file' : path
    }

    if is_remote(path):
        path['local'] = False
    else:
        # ref_path has 'local' because of previous convert_paths_format
        path['local'] = ask_till_ok(questions['local'] % \
                                    ('Yn' if ref_path['local'] else 'yN'),
                                    boolean=True,
                                    default=ref_path['local'])

    if path['file'].endswith('.zip'):
        extract = ask_till_ok(questions['extract'],
                              is_ok = lambda r: r,
                              fail_message='-/!\- Cannot be empty',
                              prefill=ref_path.get('extract', ''))

        path['extract'] = extract

    if not is_remote(path):

        if path['local'] is False:
            path['file'] = op.realpath(path['file'])

        # For non remote paths we propose copy in cache dir
        if is_archive(path):
            # We propose to store the root archive in cache
            use_cached = ask_till_ok(questions['copy_1'] % (op.basename(path['file']), S_MANAGER.cache_dir),
                                     boolean=True)

            if use_cached:
                _, copied = S_MANAGER.copy_to_cache(path['file'], source)
                path['file'] = op.realpath(copied)

    # We propose for tmp files to be used as source path
    filename = S_MANAGER.handle_path(path, source, verbose=verbose)

    if filename is None:
        print '/!\ An error occurred when handling "%s".' % str(path)
        return None, None

    use_cached = ask_till_ok(questions['copy_2'] % (op.basename(filename), S_MANAGER.cache_dir),
                             boolean=True)

    if use_cached:
        _, copied = S_MANAGER.copy_to_cache(filename, source)
        path['file'] = op.realpath(copied)

    return path, filename


def admin_mode(admin, with_hints=True, verbose=True):
    """Handle admin commands.
    """
    banner = dedent("""\
    ---------------------------------------------------------------
                         WELCOME TO ADMIN MODE

                     You will be guided through the
                    possibilities by answering a few
                   questions. This mode will help you
                          configure the file:
              %s
    ---------------------------------------------------------------\
    """ % S_MANAGER.sources_conf_path)

    help_ = dedent("""
    Sources status
    (*) status      : display short data source status
    (*) fullstatus  : display full data source configuration

    Add/Edit sources definition
    (*) add         : add a new data source
    (*) edit        : edit an existing data source
    (*) zshautocomp : update Zsh autocomplete file

    Update data
    (*) update      : download and show updates for sources with master remotes
    (*) forceupdate : download and force update of sources with master remotes

    Danger Zone!
    (*) drop        : drop all information for one data source
    (*) restore     : factory reset of all data sources information
    (*) fullrestore : restore, and clean the cache %s
    """ % S_MANAGER.cache_dir)

    questions = {
        'command'   : '[ 0 ] Command: ',
        'source'    : '[ 1 ] Source name: ',
        'path'      : '[2/8] Path: ',
        'local'     : '[   ] Is the path local to the installation directory [%s]? ',
        'extract'   : '[   ] Which file in archive? ',
        'copy_1'    : '[   ] Copy %s in %s and use as source path from there [yN]? ',
        'copy_2'    : '[   ] Use %s as source path from %s [yN]? ',
        'delimiter' : '[3/8] Delimiter: ',
        'headers'   : '[4/8] Headers: ',
        'key_fields': '[5/8] Key field(s): ',
        'index'     : '[6/8] Index: ',
        'join'      : '[7/8] Join clause: ',
        'confirm'   : '[8/8] Confirm [Yn]? ',
        'new'       : '[   ] Add new %s [yN]? ',
        'update_zsh': '[   ] Update Zsh autocomplete [yN]? ',
    }

    hints = {
        'source'    : dedent("""
                      HINT * Enter a new name to define a new source.
                      """),
        'paths'     : dedent("""
                      HINT * Paths can be urls or normal file paths.
                           * zip archives are supported.
                           * For remote files and archives, temporary
                           * files will be put in the cache directory:
                           * %s
                           * These files may be used as data sources paths.
                           * Add several paths to have a failover mechanism.
                           * Leave empty to delete path.
                      """ % S_MANAGER.cache_dir),
        'delimiter' : dedent("""
                      HINT * The delimiter is the character delimiting fields.
                           * Leave empty to split every character.
                      """),
        'headers'   : dedent("""
                      HINT * Headers are column names, separated with "%s".
                           * lat and lng will be guessed for new sources.
                      """ % SPLIT),
        'key_fields': dedent("""
                      HINT * Key fields are fields used to generate keys,
                           * use "%s" if several fields.
                           * Leave empty to use line numbers as keys.
                      """ % SPLIT),
        'indices'   : dedent("""
                      HINT * Indices are a list of index to speed up some queries.
                           * For multiple fields index, separate with "%s".
                           * Leave empty to delete index.
                      """ % SPLIT),
        'join'      : dedent("""
                      HINT * Join clauses are useful to say that a key can be found
                           * in another data source. Use the "field{base:external_field}"
                           * syntax to define one.
                           * Leave empty to delete join clause.
                      """),
    }

    # Was banner displayed
    bannered = False

    if len(admin) < 1:
        print banner
        bannered = True
        print help_
        command = ask_till_ok(questions['command'], ALLOWED_COMMANDS, show=False)
    else:
        command = admin[0]

    if command not in ALLOWED_COMMANDS:
        error('wrong_value', command, ALLOWED_COMMANDS)

    # These ones do not need the second argument source_name
    if command == 'restore':
        S_MANAGER.restore(clean_cache=False)
        S_MANAGER.update_autocomplete(verbose=False)
        return

    if command == 'fullrestore':
        S_MANAGER.restore(clean_cache=True)
        S_MANAGER.update_autocomplete(verbose=False)
        return

    if command == 'update':
        S_MANAGER.check_data_updates()
        return

    if command == 'forceupdate':
        S_MANAGER.check_data_updates(force=True)
        return

    if command == 'zshautocomp':
        status = S_MANAGER.update_autocomplete(verbose=True)
        if status:
            print '\n===== Restart shell now.'
        return

    if len(admin) < 2:
        if not bannered:
            print banner
            bannered = True
        if command in ['status', 'fullstatus']:
            two_col_print(sorted(S_MANAGER) + ['*'])
            source_name = ask_till_ok(questions['source'], sorted(S_MANAGER) + ['*', ''], show=False)

        elif command in ['drop']:
            two_col_print(sorted(S_MANAGER))
            source_name = ask_till_ok(questions['source'], sorted(S_MANAGER), show=False)

        elif command in ['edit']:
            if with_hints:
                print hints['source'],
            two_col_print(sorted(S_MANAGER))
            source_name = ask_till_ok(questions['source'],
                                      is_ok = lambda r: r,
                                      fail_message='-/!\- Cannot be empty')
        else:
            # add
            if with_hints:
                print hints['source']
            source_name = ask_till_ok(questions['source'],
                                      is_ok = lambda r: r,
                                      fail_message='-/!\- Cannot be empty')
    else:
        source_name = admin[1]

    # None is not allowed for drop and edit
    if source_name in ('', '*'):
        source_name = None

    if command == 'status':
        print S_MANAGER.build_status(source_name)
        return

    if command == 'fullstatus':
        S_MANAGER.full_status(source_name)
        return

    # Source name cannot be None past that point
    if source_name is None:
        error('not_allowed', None)

    if command == 'drop':
        S_MANAGER.drop(source_name)
        S_MANAGER.save()
        return

    if command in ('add', 'edit'):
        if source_name not in S_MANAGER:
            S_MANAGER.add(source_name)
            if command == 'edit':
                print '----- New source "%s" created! Switching to "add" mode.' % source_name
                command = 'add'
        else:
            if command == 'add':
                print '----- Source "%s" exists! Switch to "edit" mode.' % source_name
                command = 'edit'

        # We get existing conf
        conf = S_MANAGER.get(source_name)
        if conf is None:
            conf = {}

        def_paths      = conf.get('paths',      DEFAULTS['paths'])
        def_delimiter  = conf.get('delimiter',  DEFAULTS['delimiter'])
        def_headers    = conf.get('headers',    DEFAULTS['headers'])
        def_key_fields = conf.get('key_fields', DEFAULTS['key_fields'])
        def_indices    = conf.get('indices',    DEFAULTS['indices'])
        def_join       = conf.get('join',       DEFAULTS['join'])

        get_empty_path  = lambda : { 'file': '', 'local': False }
        get_empty_index = lambda : ''
        get_empty_join  = lambda : { 'fields' : [], 'with' : [''] }

        if not def_paths:
            if command == 'add':
                def_paths = [get_empty_path()]
            else:
                def_paths = []
        else:
            def_paths = S_MANAGER.convert_paths_format(def_paths)

        if not def_indices:
            if command == 'add':
                def_indices = []
                #def_indices = [get_empty_index()]
            else:
                def_indices = []

        if not def_join:
            if command == 'add':
                def_join = []
                #def_join = [get_empty_join()]
            else:
                def_join = []

        # We will add non empty values here
        new_conf = {
            'paths'   : [],
            'indices' : [],
            'join'    : [],
        }

        # Fake first line for sources without paths
        first_l = ''

        # 1. Paths
        if with_hints:
            print hints['paths']
        i = 0
        while True:
            if i < len(def_paths):
                ref_path = def_paths[i]
                i += 1
            else:
                # We add a new empty path if the user wants to add another one
                add_another = ask_till_ok(questions['new'] % 'path', boolean=True)

                if add_another:
                    ref_path = get_empty_path()
                else:
                    break

            path, filename = admin_path(ref_path, source_name, questions, verbose)

            if path is None:
                continue

            new_conf['paths'].append(path)

            try:
                with open(filename) as fl:
                    first_l = fl.next().rstrip()
            except IOError:
                print
                print '!!!!! Could not open "%s". Check the path.' % filename
                return

            # No need to download and check the first lines for known files
            if to_CLI('path', ref_path) != to_CLI('path', path):
                print
                print '>>>> first line >>>>'
                print first_l
                print '<<<<<<<<<<<<<<<<<<<<'

                def_delimiter  = guess_delimiter(first_l)
                def_headers    = guess_headers(first_l, def_delimiter)
                def_key_fields = guess_key_fields(first_l, def_delimiter, def_headers)


        # 2. Delimiter
        if with_hints:
            print hints['delimiter']
        delimiter = ask_input(questions['delimiter'], to_CLI('delimiter', def_delimiter))
        new_conf['delimiter'] = delimiter

        if to_CLI('delimiter', def_delimiter) != to_CLI('delimiter', delimiter):
            def_headers    = guess_headers(first_l, delimiter)
            def_key_fields = guess_key_fields(first_l, delimiter, def_headers)


        # 3. Headers
        if with_hints:
            print hints['headers']
        headers = ask_input(questions['headers'], to_CLI('headers', def_headers)).strip()
        if not headers:
            headers = []
        else:
            headers = headers.split(SPLIT)

        join, subdelimiters = clean_headers(headers)
        new_conf['headers'] = headers

        if join:
            new_conf['join'] = join
            print '----- Detected join %s' % str(join)

        if subdelimiters:
            new_conf['subdelimiters'] = subdelimiters
            print '----- Detected subdelimiters %s' % str(subdelimiters)

        if to_CLI('headers', def_headers) != to_CLI('headers', headers):
            def_key_fields = guess_key_fields(first_l, delimiter, headers)


        # 4. Key fields
        if with_hints:
            print hints['key_fields']
        key_fields = ask_input(questions['key_fields'], to_CLI('key_fields', def_key_fields)).strip()
        key_fields = split_if_several(key_fields)

        if not key_fields:
            new_conf['key_fields'] = None
        else:
            new_conf['key_fields'] = key_fields


        # 5. Indices
        if with_hints:
            print hints['indices']
        i = 0
        while True:
            if i < len(def_indices):
                ref_index = def_indices[i]
                i += 1
            else:
                # We add a new empty path if the user wants to add another one
                add_another = ask_till_ok(questions['new'] % 'index', boolean=True)

                if add_another:
                    ref_index = get_empty_index()
                else:
                    break

            index = ask_input(questions['index'], to_CLI('index', ref_index)).strip()
            if not index:
                print '----- Empty index, deleted'
            else:
                index = split_if_several(index)
                new_conf['indices'].append(index)


        # 6. Join
        if with_hints:
            print hints['join']
        i = 0
        while True:
            if i < len(def_join):
                ref_join = def_join[i]
                i += 1
            else:
                # We add a new empty path if the user wants to add another one
                add_another = ask_till_ok(questions['new'] % 'join', boolean=True)

                if add_another:
                    ref_join = get_empty_join()
                else:
                    break

            m_join = ask_input(questions['join'], to_CLI('join', ref_join)).strip()
            m_join = clean_headers(m_join.split(SPLIT))[0]

            if not m_join:
                print '----- Empty join, deleted'
            else:
                m_join[0]['fields'] = split_if_several(m_join[0]['fields'])

                if len(m_join[0]['with']) > 1:
                    m_join[0]['with'][1] = split_if_several(m_join[0]['with'][1])

                new_conf['join'].extend(m_join)

        # Removing non-changes
        old_conf = {}
        for option, config in new_conf.items():
            if option in conf:
                if config == conf[option]:
                    del new_conf[option]
                else:
                    old_conf[option] = conf[option]

        if not new_conf:
            print '\n===== No changes'
            return

        print
        print '--- [before]'
        print S_MANAGER.convert({ source_name : old_conf })

        print '+++ [after]'
        print S_MANAGER.convert({ source_name : new_conf })

        confirm = ask_till_ok(questions['confirm'], boolean=True, default=True)

        if not confirm:
            print '\n===== Aborted'
            return

        S_MANAGER.update(source_name, new_conf)
        S_MANAGER.save()
        print '\n===== Changes saved to %s' % S_MANAGER.sources_conf_path

        update_zsh = ask_till_ok(questions['update_zsh'], boolean=True, default=False)
        if update_zsh:
            status = S_MANAGER.update_autocomplete(verbose=True)
            if status:
                print '\n===== Restart shell now.'



def ask_mode():
    """Learning mode.
    """

    print dedent("""\
    -----------------------------------------------------
                   WELCOME TO LEARNING MODE

                You will be guided through the
               possibilities by answering a few
                         questions.
    -----------------------------------------------------\
    """)

    questions = {
        'source'   : '[1/5] Which data source do you want to work with? ',
        'all_keys' : '[2/5] Consider all data for this source [Yn]? ',
        'from_keys': '[   ] Which keys should we consider (separated with " ")? ',
        'search'   : '[3/5] What kind of search? ',
        'field'    : '[4/5] On which field? ',
        'value'    : '[   ] Which value to look for? ',
        'point'    : '[4/5] From which point (key or geocode)? ',
        'radius'   : '[   ] Which radius for the search (kms)? ',
        'limit'    : '[   ] Which limit for the search (number of results)? ',
        'display'  : '[5/5] Which display? ',
        'execute'  : '[   ] Execute the command [Yn]? ',
    }

    # 1. Choose base
    base = ask_till_ok(questions['source'], sorted(S_MANAGER), prefill='ori_por')

    # 2. Choose from keys
    all_keys = ask_till_ok(questions['all_keys'], boolean=True, default=True)

    if all_keys:
        from_keys = None
    else:
        from_keys = ask_input(questions['from_keys']).strip().split()

    # 3. Choose search type
    print dedent("""
    (*) none     : no search done, all data used
    (*) exact    : make an exact search on a specific field
    (*) fuzzy    : make a fuzzy search on a specific field
    (*) phonetic : make a phonetic search on a specific field
    (*) near     : make a geographical search from a point with a radius
    (*) closest  : make a geographical search from a point with a number of results
    """)
    search = ask_till_ok(questions['search'], ['none', 'exact', 'fuzzy', 'phonetic', 'near', 'closest'], show=False)

    if search.strip().lower() in ('none',):
        search = None

    # 4. Search parameters
    field, value, radius, limit = None, None, None, None

    if search in ['exact', 'fuzzy', 'phonetic']:
        field = ask_till_ok(questions['field'], sorted(S_MANAGER.get(base)['headers']), prefill='name')
        value = ask_till_ok(questions['value'],
                            is_ok = lambda r: r,
                            fail_message='-/!\- Cannot be empty')

    elif search in ['near']:
        value = ask_till_ok(questions['point'],
                            is_ok = lambda r: r,
                            fail_message='-/!\- Cannot be empty')
        radius = ask_input(questions['radius'], prefill='50').strip()

    elif search in ['closest']:
        value = ask_till_ok(questions['point'],
                            is_ok = lambda r: r,
                            fail_message='-/!\- Cannot be empty')
        limit = ask_input(questions['limit'], prefill='5').strip()

    # 5. Display
    print dedent("""
    (*) terminal  : display in the terminal, with nice colors and everything
    (*) quiet     : display on stdout, with csv-like formatting
    (*) map       : display on a map
    (*) graph     : display on a graph (like force directed graph)
    (*) dashboard : display on a dashboard (aggregated view)
    """)
    display = ask_till_ok(questions['display'],
                          ['terminal', 'quiet', 'map', 'graph', 'dashboard'],
                          prefill='terminal',
                          show=False)

    # 6. Conclusion
    parameters = {
        'base'      : base,
        'from_keys' : from_keys,
        'search'    : search,
        'field'     : field,
        'radius'    : radius,
        'limit'     : limit,
        'value'     : value,
        'display'   : display
    }

    print
    print '-----------------------------------------------------'
    print
    print '              Congrats! You choosed:                 '
    print
    for k, v in parameters.iteritems():
        if v is not None:
            print '(*) %-10s => "%s"' % (str(k), str(v))
        #else:
        #    print '(*) %-10s => None' % str(k)

    # One liner
    print
    print '            Equivalent one-liner command             '
    print '        with long options and short options          '
    print

    # Long options
    base_part         = '--base %s' % base
    from_keys_part    = '' if from_keys is None else ' '.join(from_keys)
    search_part       = ('--%s "%s"' % (search, value)) if search is not None else ''
    display_part     = ('--%s' % display) if display != 'terminal' else ''

    if search in ['exact', 'fuzzy', 'phonetic']:
        search_field_part = '--%s-field %s' % (search, field)
    elif search in ['near']:
        search_field_part = '--%s-limit %s' % (search, radius)
    elif search in ['closest']:
        search_field_part = '--%s-limit %s' % (search, limit)
    else:
        search_field_part = ''

    command = ' '.join(e for e in [SCRIPT_NAME,
                                   from_keys_part,
                                   base_part,
                                   search_field_part,
                                   search_part,
                                   display_part] if e)
    print command


    # Short options
    base_part         = '-b %s' % base
    from_keys_part    = '' if from_keys is None else ' '.join(from_keys)
    search_part       = ('-%s "%s"' % (search[0], value)) if search is not None else ''
    display_part      = ('-%s' % display[0]) if display != 'terminal' else ''

    if search in ['exact', 'fuzzy', 'phonetic']:
        search_field_part = '-%s %s' % (search[0].upper(), field)
    elif search in ['near']:
        search_field_part = '-%s %s' % (search[0].upper(), radius)
    elif search in ['closest']:
        search_field_part = '-%s %s' % (search[0].upper(), limit)
    else:
        search_field_part = ''

    command = ' '.join(e for e in [SCRIPT_NAME,
                                   from_keys_part,
                                   base_part,
                                   search_field_part,
                                   search_part,
                                   display_part] if e)
    print command
    print '-----------------------------------------------------'
    print

    execute = ask_till_ok(questions['execute'], boolean=True, default=True)
    if execute:
        os.system(command)

    return parameters



# How to profile: execute this and uncomment @profile
# $ kernprof.py --line-by-line --view file.py ORY
#@profile
def main():
    """
    Main function.
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
    with_grid = not args['no_grid']
    verbose   = not args['quiet']
    logorrhea = args['verbose']

    # Defining frontend
    if args['map']:
        frontend = 'map'
    elif args['graph']:
        frontend = 'graph'
    elif args['dashboard']:
        frontend = 'dashboard'
    elif args['quiet']:
        frontend = 'quiet'
    else:
        frontend = 'terminal'

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
            error('type', 'limit', 'int', args['limit'])

    # Interactive query?
    interactive_query_mode = args['interactive_query'] is not None


    #
    # CREATION
    #
    if logorrhea:
        from datetime import datetime
        before_init = datetime.now()

    if args['version']:
        import pkg_resources
        try:
            r = pkg_resources.require(PACKAGE_NAME)[0]
            print 'Project    : %s' % r.project_name
            print 'Version    : %s' % r.version
            print 'Egg name   : %s' % r.egg_name()
            print 'Location   : %s' % r.location
            print 'Requires   : %s' % ', '.join(str(e) for e in r.requires())
            print 'Extras     : %s' % ', '.join(str(e) for e in r.extras)

        except pkg_resources.DistributionNotFound:
            warn('installation', PACKAGE_NAME)

        if logorrhea:
            print
            print 'Package    : %s' % PACKAGE_NAME
            print 'Script     : %s' % SCRIPT_NAME
            print 'Description: %s' % DESCRIPTION
            print 'Cache dir  : %s' % S_MANAGER.cache_dir
            print 'Config     : %s' % S_MANAGER.sources_conf_path
        exit(0)


    if args['admin'] is not None:
        try:
            admin_mode(args['admin'], with_hints=verbose, verbose=logorrhea)
        except (KeyboardInterrupt, EOFError):
            error('aborting', 'Aborting, changes will not be saved.')
        exit(0)


    if args['ask']:
        try:
            ask_mode()
        except (KeyboardInterrupt, EOFError):
            error('aborting', 'Learning session is over :S.')
        exit(0)


    if args['base'] not in S_MANAGER:
        error('data', args['base'], sorted(S_MANAGER))


    if not sys.stdin.isatty() and not interactive_query_mode:
        try:
            first_l = sys.stdin.next()
        except StopIteration:
            error('empty_stdin')

        source  = chain([first_l], sys.stdin)
        first_l = first_l.rstrip() # For sniffers, we rstrip

        delimiter  = guess_delimiter(first_l)
        headers    = guess_headers(first_l, delimiter)
        key_fields = guess_key_fields(first_l, delimiter, headers)

        headers_r     = None # to store raw headers given
        subdelimiters = {}
        join          = []

        discard_dups_r = DEF_DISCARD_RAW
        discard_dups   = DEF_DISCARD
        indices        = DEF_INDICES

        m_join_r = DEF_JOIN_RAW
        m_join   = DEF_JOIN

        if len(args['indexation']) >= 1 and args['indexation'][0] != SKIP:
            delimiter = args['indexation'][0]

        if len(args['indexation']) >= 2 and args['indexation'][1] != SKIP:
            if args['indexation'][1] == '__head__':
                headers = source.next().rstrip().split(delimiter)
            else:
                headers   = args['indexation'][1].split(SPLIT)
                headers_r = headers[:] # backup
                l_join, l_subdelimiters = clean_headers(headers)
                join.extend(l_join)
                subdelimiters.update(l_subdelimiters)
        else:
            # Reprocessing the headers with custom delimiter
            headers = guess_headers(first_l, delimiter)

        if len(args['indexation']) >= 3 and args['indexation'][2] != SKIP:
            key_fields = None if args['indexation'][2] == DISABLE else args['indexation'][2].split(SPLIT)
        else:
            # Reprocessing the key_fields with custom headers
            key_fields = guess_key_fields(first_l, delimiter, headers)

        if len(args['indexation']) >= 4 and args['indexation'][3] != SKIP:
            discard_dups_r = args['indexation'][3]
            discard_dups   = discard_dups_r in TRUTHY

        if len(args['indexation']) >= 5 and args['indexation'][4] != SKIP:
            indices = [] if args['indexation'][4] == DISABLE else [args['indexation'][4].split(SPLIT)]

        if len(args['indexation']) >= 6 and args['indexation'][5] != SKIP:
            m_join_r = args['indexation'][5]
            m_join   = [] if args['indexation'][5] == DISABLE else clean_headers([args['indexation'][5]])[0]

            if m_join:
                m_join[0]['fields'] = tuple(m_join[0]['fields'].split(SPLIT))

                if len(m_join[0]['with']) > 1:
                    m_join[0]['with'][1] = tuple(m_join[0]['with'][1].split(SPLIT))

                join.extend(m_join)

        # Checking join bases
        for e in join:
            if e['with'][0] not in S_MANAGER:
                error('data', e['with'][0], sorted(S_MANAGER))

        if verbose:
            print 'Loading from stdin with [sniffed] option: -i "%s" "%s" "%s" "%s" "%s" "%s"' % \
                    (delimiter,
                     SPLIT.join(headers if headers_r is None else headers_r),
                     SPLIT.join(key_fields) if key_fields is not None else DISABLE,
                     discard_dups_r,
                     SPLIT.join(indices[0]) if indices else DISABLE,
                     m_join_r)

        options = {
            'source'       : source,
            'delimiter'    : delimiter,
            'headers'      : headers,
            'key_fields'   : key_fields,
            'discard_dups' : discard_dups,
            'indices'      : indices,
            'subdelimiters': subdelimiters,
            'join'         : join,
            'verbose'      : logorrhea
        }

        g = GeoBase(data='feed', **options)

        if logorrhea:
            S_MANAGER.help_permanent_add(options)

    else:
        # -i options overrides default
        add_options = {}

        if len(args['indexation']) >= 1 and args['indexation'][0] != SKIP:
            add_options['delimiter'] = args['indexation'][0]

        if len(args['indexation']) >= 2 and args['indexation'][1] != SKIP:
            add_options['headers'] = args['indexation'][1].split(SPLIT)
            l_join, l_subdelimiters = clean_headers(add_options['headers'])

            if l_join:
                add_options['join'] = l_join
            if l_subdelimiters:
                add_options['subdelimiters'] = l_subdelimiters

        if len(args['indexation']) >= 3 and args['indexation'][2] != SKIP:
            add_options['key_fields'] = None if args['indexation'][2] == DISABLE else args['indexation'][2].split(SPLIT)

        if len(args['indexation']) >= 4 and args['indexation'][3] != SKIP:
            add_options['discard_dups'] = args['indexation'][3] in TRUTHY

        if len(args['indexation']) >= 5 and args['indexation'][4] != SKIP:
            add_options['indices'] = [] if args['indexation'][4] == DISABLE else [args['indexation'][4].split(SPLIT)]
        if len(args['indexation']) >= 6 and args['indexation'][5] != SKIP:
            m_join = [] if args['indexation'][5] == DISABLE else clean_headers([args['indexation'][5]])[0]

            if m_join:
                m_join[0]['fields'] = tuple(m_join[0]['fields'].split(SPLIT))

                if len(m_join[0]['with']) > 1:
                    m_join[0]['with'][1] = tuple(m_join[0]['with'][1].split(SPLIT))

                if 'join' in add_options:
                    add_options['join'].extend(m_join)
                else:
                    add_options['join'] = m_join

        if verbose:
            if not add_options:
                print 'Loading "%s"...' % args['base']
            else:
                print 'Loading "%s" with custom: %s ...' % \
                        (args['base'], ' ; '.join('%s = %s' % kv for kv in add_options.items()))

        g = GeoBase(data=args['base'], verbose=logorrhea, **add_options)

    if logorrhea:
        after_init = datetime.now()

    # Tuning parameters
    if args['exact_field'] is None or args['exact_field'] == SKIP:
        args['exact_field'] = best_field(DEF_EXACT_FIELDS, g.fields)

    if args['exact_field'] is None:
        # Can happen if no match with best_field (happens with data="feed")
        exact_fields = [None]
    else:
        exact_fields = args['exact_field'].split(SPLIT)

    if args['fuzzy_field'] is None or args['fuzzy_field'] == SKIP:
        args['fuzzy_field'] = best_field(DEF_FUZZY_FIELDS, g.fields)

    if args['phonetic_field'] is None or args['phonetic_field'] == SKIP:
        args['phonetic_field'] = best_field(DEF_PHONETIC_FIELDS, g.fields)

    # We automatically convert subdelimited fields into raw version
    for i, f in enumerate(exact_fields):
        if g._isFieldDelimited(f):
            exact_fields[i] = g._convertFieldToRaw(f)

    if g._isFieldDelimited(args['fuzzy_field']):
        args['fuzzy_field'] = g._convertFieldToRaw(args['fuzzy_field'])

    if g._isFieldDelimited(args['phonetic_field']):
        args['phonetic_field'] = g._convertFieldToRaw(args['phonetic_field'])

    # Server config
    address = ADDRESS
    port = PORT

    if args['port'] != SKIP:
        port = args['port']

    # Temporary file folder
    output_dir = DEF_OUTPUT_DIR

    if args['output_dir'] != SKIP:
        output_dir = args['output_dir']

    # With 3D
    use_3D = args['3d']

    # Reading map options
    icon_label       = best_field(DEF_LABEL_FIELDS,  g.fields)
    icon_weight      = best_field(DEF_WEIGHT_FIELDS, g.fields)
    icon_color       = best_field(DEF_COLOR_FIELDS,  g.fields)
    icon_type        = DEF_ICON_TYPE
    link_duplicates  = DEF_LINK_DUPLICATES
    draw_join_fields = DEF_DRAW_JOIN_FIELDS

    if len(args['map_options']) >= 1 and args['map_options'][0] != SKIP:
        icon_label = args['map_options'][0]

    if len(args['map_options']) >= 2 and args['map_options'][1] != SKIP:
        icon_weight = None if args['map_options'][1] == DISABLE else args['map_options'][1]

    if len(args['map_options']) >= 3 and args['map_options'][2] != SKIP:
        icon_color = None if args['map_options'][2] == DISABLE else args['map_options'][2]

    if len(args['map_options']) >= 4 and args['map_options'][3] != SKIP:
        icon_type = None if args['map_options'][3] == DISABLE else args['map_options'][3]

    if len(args['map_options']) >= 5 and args['map_options'][4] != SKIP:
        link_duplicates = args['map_options'][4] in TRUTHY

    if len(args['map_options']) >= 6 and args['map_options'][5] != SKIP:
        draw_join_fields = args['map_options'][5] in TRUTHY

    # Reading graph options
    # Default graph_fields is first two available from DEF_GRAPH_FIELDS
    graph_fields = [f for f in DEF_GRAPH_FIELDS if f in g.fields][0:2]
    graph_weight = DEF_GRAPH_WEIGHT

    if len(args['graph_fields']) >= 1:
        # If user gave something for forget the defaults
        graph_fields = [f for f in args['graph_fields'] if f != SKIP]

    if args['graph_weight'] != SKIP:
        graph_weight = None if args['graph_weight'] == DISABLE else args['graph_weight']

    # Reading quiet options
    quiet_delimiter = DEF_QUIET_DELIM
    header_display  = DEF_QUIET_HEADER

    if len(args['quiet_options']) >= 1 and args['quiet_options'][0] != SKIP:
        quiet_delimiter = args['quiet_options'][0]

    if len(args['quiet_options']) >= 2 and args['quiet_options'][1] != SKIP:
        header_display = args['quiet_options'][1]

    # Reading dashboard options
    dashboard_weight = DEF_DASHBOARD_WEIGHT
    dashboard_keep   = DEF_DASHBOARD_KEEP

    if len(args['dashboard_options']) >= 1 and args['dashboard_options'][0] != SKIP:
        dashboard_weight = None if args['dashboard_options'][0] == DISABLE else args['dashboard_options'][0]

    if len(args['dashboard_options']) >= 2 and args['dashboard_options'][1] != SKIP:
        dashboard_keep = args['dashboard_options'][1]

    # Reading interactive query options
    interactive_field = best_field(DEF_INTER_FIELDS, g.fields)
    interactive_type  = DEF_INTER_TYPE

    if interactive_query_mode:
        if len(args['interactive_query']) >= 1 and args['interactive_query'][0] != SKIP:
            interactive_field = args['interactive_query'][0]

        if len(args['interactive_query']) >= 2 and args['interactive_query'][1] != SKIP:
            interactive_type = args['interactive_query'][1]

    if g._isFieldDelimited(interactive_field):
        interactive_field = g._convertFieldToRaw(interactive_field)

    # Reading phonetic options
    phonetic_method = args['phonetic_method']

    # show / exclude
    if args['exclude'] == SKIP:
        args['exclude'] = DEF_EXCLUDE_FIELDS

    if args['show'] == SKIP:
        args['show'] = DEF_SHOW_FIELDS

    if args['show_additional'] == SKIP:
        args['show_additional'] = DEF_SHOW_ADD_FIELDS



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
        for field in exact_fields:
            if field not in g.fields:
                error('field', field, g.data, sorted(g.fields))

    if args['fuzzy'] is not None:
        if args['fuzzy_field'] not in g.fields:
            error('field', args['fuzzy_field'], g.data, sorted(g.fields))

    if args['phonetic'] is not None:
        if args['phonetic_field'] not in g.fields:
            error('field', args['phonetic_field'], g.data, sorted(g.fields))

    # Failing on unknown fields
    fields_to_test = [
        f for f in (icon_label, icon_weight, icon_color,
                    interactive_field,
                    graph_weight, dashboard_weight)
        if f is not None
    ] + graph_fields

    for field in args['show'] + args['show_additional'] + args['exclude'] + fields_to_test:
        field, ext_field = check_ext_field(g, field)

        if field not in [REF] + g.fields:
            # Join fields call are ok, but they are not in self.fields
            if not g.hasJoin(field):
                error('field', field, g.data, sorted([REF]    + \
                                                     g.fields + \
                                                     ['(join) %s:' % SPLIT.join(k) for k in g._join]))

        if ext_field is not None:
            ext_g = g.getJoinBase(field)
            if ext_field not in [REF] + ext_g.fields + ['__loc__']:
                error('field', ext_field, ext_g.data, sorted([REF] + ext_g.fields))

    # Testing icon_type from -M
    if icon_type not in ALLOWED_ICON_TYPES:
        error('wrong_value', icon_type, ALLOWED_ICON_TYPES)

    # Testing -I option
    if interactive_type not in ALLOWED_INTER_TYPES:
        error('wrong_value', interactive_type, ALLOWED_INTER_TYPES)

    # Testing -y option
    if phonetic_method not in ALLOWED_PHONETIC_METHODS:
        error('wrong_value', phonetic_method, ALLOWED_PHONETIC_METHODS)

    # Testing if keep is an int
    try:
        dashboard_keep = int(dashboard_keep)
    except ValueError:
        error('type', 'keep', 'int', dashboard_keep)

    #
    # MAIN
    #
    if verbose:
        if not sys.stdin.isatty() and interactive_query_mode:
            print 'Looking for matches from stdin query: %s search %s' % \
                    (interactive_type,
                     '' if interactive_type == '__key__' else 'on %s...' % interactive_field)
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
    if not sys.stdin.isatty() and interactive_query_mode:
        values = [row.strip() for row in sys.stdin]
        # Query type
        if interactive_type == '__key__':
            res = enumerate(values)
            last = None

        elif interactive_type == '__exact__':
            # Indexing if not already done at init
            g.addIndex(interactive_field, verbose=logorrhea)

            res = []
            for val in values:
                conditions = [(interactive_field, val)]
                res.extend(list(g.findWith(conditions, mode='or', verbose=logorrhea)))

            # Other way to do it by putting all lines in one *or* condition
            # But for over 1000 lines, this becomes slower than querying each line
            #conditions = [(interactive_field, val) for val in values]
            #res = g.findWith(conditions, mode='or', verbose=logorrhea)
            last = 'exact'

        elif interactive_type == '__fuzzy__':
            res = []
            for val in values:
                res.extend(list(g.fuzzyFindCached(val, interactive_field, min_match=args['fuzzy_limit'], verbose=logorrhea)))
            last = 'fuzzy'

        elif interactive_type == '__phonetic__':
            res = []
            for val in values:
                res.extend(list(g.phoneticFind(val, interactive_field, method=phonetic_method, verbose=logorrhea)))
            last = 'phonetic'

    elif args['keys']:
        res = enumerate(args['keys'])
    else:
        res = enumerate(g)

    # We are going to chain conditions
    # res will hold intermediate results
    if args['trep'] is not None:
        args['trep'] = ' '.join(args['trep'])
        if verbose:
            print '(*) Applying: trep search on "%s" (output %s)' % (args['trep'], args['trep_format'])

        res = g.trepSearch(args['trep'], trep_format=args['trep_format'], from_keys=ex_keys(res), verbose=verbose)
        last = 'trep'


    if args['exact'] is not None:
        args['exact'] = ' '.join(args['exact'])

        exact_values = args['exact'].split(SPLIT, len(exact_fields) - 1)
        conditions = list(izip_longest(exact_fields, exact_values, fillvalue=''))
        mode = 'or' if args['or'] else 'and'

        if verbose:
            if args['reverse']:
                print '(*) Applying: field %s' % (' %s ' % mode).join('%s != "%s"' % c for c in conditions)
            else:
                print '(*) Applying: field %s' % (' %s ' % mode).join('%s == "%s"' % c for c in conditions)

        res = list(g.findWith(conditions, from_keys=ex_keys(res), reverse=args['reverse'], mode=mode, verbose=logorrhea))
        last = 'exact'


    if args['fuzzy'] is not None:
        args['fuzzy'] = ' '.join(args['fuzzy'])
        if verbose:
            print '(*) Applying: field %s ~= "%s" (min. %.1f%%)' % (args['fuzzy_field'], args['fuzzy'], 100 * args['fuzzy_limit'])

        res = list(g.fuzzyFind(args['fuzzy'], args['fuzzy_field'], min_match=args['fuzzy_limit'], from_keys=ex_keys(res)))
        last = 'fuzzy'


    if args['phonetic'] is not None:
        args['phonetic'] = ' '.join(args['phonetic'])
        if verbose:
            print '(*) Applying: field %s sounds ~ "%s" with %s' % (args['phonetic_field'], args['phonetic'], phonetic_method)

        res = sorted(g.phoneticFind(args['phonetic'], args['phonetic_field'], method=phonetic_method, from_keys=ex_keys(res), verbose=logorrhea))
        last = 'phonetic'


    if args['near'] is not None:
        args['near'] = ' '.join(args['near'])
        if verbose:
            print '(*) Applying: near %s km from "%s" (%s grid)' % (args['near_limit'], args['near'], 'with' if with_grid else 'without')

        coords = scan_coords(args['near'], g, verbose)
        res = sorted(g.findNearPoint(coords, radius=args['near_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'near'


    if args['closest'] is not None:
        args['closest'] = ' '.join(args['closest'])
        if verbose:
            print '(*) Applying: closest %s from "%s" (%s grid)' % (args['closest_limit'], args['closest'], 'with' if with_grid else 'without')

        coords = scan_coords(args['closest'], g, verbose)
        res = list(g.findClosestFromPoint(coords, N=args['closest_limit'], grid=with_grid, from_keys=ex_keys(res)))
        last = 'closest'



    #
    # DISPLAY
    #

    # Saving to list
    res = list(res)

    # We clock the time here because now the res iterator has been used
    if logorrhea:
        end = datetime.now()
        print 'Done in %s = (load) %s + (search) %s' % \
                (end - before_init, after_init - before_init, end - after_init)

    # Removing unknown keys
    for h, k in res:
        if k not in g:
            warn('key', k, g.data, g.loaded)

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
        for prop in exact_fields:
            important.add(prop)

    if args['fuzzy'] is not None:
        important.add(args['fuzzy_field'])

    if args['phonetic'] is not None:
        important.add(args['phonetic_field'])

    if interactive_query_mode:
        important.add(interactive_field)

    # reference may be different thing depending on the last filter
    if last in ['near', 'closest']:
        ref_type = 'distance'
    elif last in ['trep', 'fuzzy']:
        ref_type = 'percentage'
    elif last in ['phonetic']:
        ref_type = 'phonemes'
    else:
        ref_type = 'index'

    # Display
    if frontend == 'map':
        visu_info = g.visualize(output=g.data,
                                output_dir=output_dir,
                                icon_label=icon_label,
                                icon_weight=icon_weight,
                                icon_color=icon_color,
                                icon_type=icon_type,
                                from_keys=ex_keys(res),
                                add_lines=None,
                                add_anonymous_icons=None,
                                add_anonymous_lines=None,
                                link_duplicates=link_duplicates,
                                draw_join_fields=draw_join_fields,
                                catalog=None,
                                line_colors=None,
                                use_3D=use_3D,
                                verbose=True,
                                warnings=logorrhea)

        rendered, (templates, _) = visu_info

        if templates and verbose:
            display_browser(templates, output_dir, nb_res, address, port)

        if 'map' not in rendered:
            # Happens if you try to use --map
            # on non geographical data
            frontend = 'terminal'
            res = res[:DEF_NUM_COL]

            print '/!\ Map template not rendered. Switching to terminal frontend...'


    if frontend == 'graph':
        visu_info = g.graphVisualize(graph_fields=graph_fields,
                                     graph_weight=graph_weight,
                                     with_types=args['with_types'],
                                     from_keys=ex_keys(res),
                                     output=g.data,
                                     output_dir=output_dir,
                                     verbose=verbose)

        rendered, (templates, _) = visu_info

        if templates and verbose:
            display_browser(templates, output_dir, nb_res, address, port)
        else:
            # In quiet mode we do not launch the server
            # but we display the graph structure
            print json.dumps(g.buildGraphData(graph_fields=graph_fields,
                                              graph_weight=graph_weight,
                                              with_types=args['with_types'],
                                              directed=False,
                                              from_keys=ex_keys(res)),
                             indent=4)

    if frontend == 'dashboard':
        visu_info = g.dashboardVisualize(output=g.data,
                                         output_dir=output_dir,
                                         keep=dashboard_keep,
                                         dashboard_weight=dashboard_weight,
                                         from_keys=ex_keys(res),
                                         verbose=verbose)

        rendered, (templates, _) = visu_info

        if templates and verbose:
            display_browser(templates, output_dir, nb_res, address, port)
        else:
            # In quiet mode we do not launch the server
            # but we display the graph structure
            print json.dumps(g.buildDashboardData(keep=dashboard_keep,
                                                  weight=dashboard_weight,
                                                  from_keys=ex_keys(res)),
                             indent=4)


    if frontend == 'terminal':
        shown_fields = fields_to_show([REF] + g.fields[:],
                                      set(args['exclude']),
                                      args['show'],
                                      args['show_additional'])

        print
        display_terminal(g, res, shown_fields, ref_type, important)


    if frontend == 'quiet':
        # As default, we do not put special fields (except __key__)
        # For subdelimited fields, we handle split fields later
        defaults = [REF] + [
            f for f in g.fields if g._isFieldNormal(f) or f == '__key__'
        ]

        shown_fields = fields_to_show(defaults,
                                      set(args['exclude']),
                                      args['show'],
                                      args['show_additional'])

        # We convert all delimited fields to the raw version
        for i, f in enumerate(shown_fields):
            if g._isFieldDelimited(f):
                shown_fields[i] = g._convertFieldToRaw(f)

        display_quiet(g, res, shown_fields, ref_type, quiet_delimiter, header_display)


    if verbose and not IS_WINDOWS:
        for warn_msg in ENV_WARNINGS:
            print dedent(warn_msg),


def _test():
    """When called directly, launching doctests.
    """
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    #_test()
    main()

