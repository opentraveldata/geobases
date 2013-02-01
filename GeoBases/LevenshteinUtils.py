#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is composed of several functions useful
for performing string comparisons. It is oriented for data like names of
cities, airports, train stations, because the string comparisons
will not count standard words like 'ville' or 'sncf'.


Functions frequently used by other modules:

- *mod_leven*: a function to compute the distance between two
  strings. It is based on the Levenshtein ratio.
- *clean*: a function to clean string before comparisons


This module strongly relies on one other module:

- *Levenshtein*: this module implements some standard algorithms
  to compare strings, such as the Levenshtein distance

Simple examples::

    >>> clean('St-Etienne" " \t')
    ['saint', 'etienne']
    >>> clean('antibes sncf 2 (centre)')
    ['antibes', 'centre']
    >>> mod_leven('antibes', 'antibs')
    0.92...
    >>> mod_leven('Aéroport CDG  2', 'aeroport-cdg')
    1.0
"""

import re
from Levenshtein import ratio as LevenRatio
#from Levenshtein import distance as LevenDist


PARENTHESIS_RE = re.compile('^(?P<before>[^()]*?)\((?P<in>[^()]*?)\)(?P<after>[^()]*?)$')

PARTS = ('before',
         'in',
         'after')

# These are letters replaced
ACCENTS = ( ('é', 'e'),
            ('è', 'e'),
            ('ê', 'e'),
            ('ë', 'e'),
            ('à', 'a'),
            ('â', 'a'),
            ('ù', 'u'),
            ('û', 'u'),
            ('ç', 'c'),
            ('ô', 'o'),
            ('î', 'i'),
            ('ï', 'i'),
            ('í', 'i'))

# These are separators
SEPARATORS = ('+', '-', ' ', '\t',
              ':', ',', ';', '.',
              "'", '"', '?', '!',
              "#", '@', '|', '\n')

# These are words replaced
ALIASES = ( ('st', 'saint'),
            ('hb', 'hbf') )

# These are removed
TRANSPARENTS = (
    # French ones
    'le',     'la',    'les',
    'ville',  'sncf',  'hbf',
    'bains',  'eaux',  'rive',
    'droite', 'gauche',
    # English ones
    'a',      'an',    'the',
    'and',    'or'
)

# Toggle inclusion heuristic
HEURISTIC_INCLUSION       = True
HEURISTIC_INCLUSION_VALUE = 0.90


def str_lowercase(string):
    """
    Lower case adapted for str type.

    >>> print('Étaples'.lower()) # Fail!
    Étaples
    >>> print(str_lowercase('Étaples')) # Win!
    étaples
    """
    if isinstance(string, unicode):
        return string.lower()

    if isinstance(string, str):
        return string.decode('utf8').lower().encode('utf8')

    raise ValueError('Input %s is not instance of <str> or <unicode>' % string)



def handle_accents(string):
    """
    Remove accentuated characters in a word, and
    replace them with non-accentuated ones.

    :param string: the string to be processed
    :returns:      the unaccentuad string

    >>> handle_accents('être')
    'etre'
    >>> handle_accents('St-Etienne SNCF (Châteaucreux)')
    'St-Etienne SNCF (Chateaucreux)'
    """
    for a, u in ACCENTS:
        string = string.replace(a, u)

    return string


def handle_parenthesis_info(string, parts=None):
    """
    When a word contains parenthesis, this function picks
    only the part *before* the parenthesis.

    :param string: the string to be processed
    :param parts:  whichi part to keep, either 'before', 'in', or 'after'
    :returns:      the parenthesis-free string

    >>> handle_parenthesis_info('Lyon Part-Dieu (TGV)')
    'Lyon Part-Dieu TGV'
    >>> handle_parenthesis_info('Lyon Part-Dieu (TGV)', parts=['before'])
    'Lyon Part-Dieu'
    >>> handle_parenthesis_info('(Sncf) City')
    'Sncf City'
    >>> handle_parenthesis_info('Lyon (Sncf) City', parts=['in', 'after'])
    'Sncf City'
    >>> handle_parenthesis_info('St-Etienne SNCF (Chateaucreux)')
    'St-Etienne SNCF Chateaucreux'
    """
    if parts is None:
        parts = PARTS

    m = PARENTHESIS_RE.match(string)

    if m is None:
        return string

    return ' '.join([m.groupdict()[p].strip() for p in parts]).strip()



def split_separators(string):
    """
    When a word contains different separators, this function
    split the word using all separators.

    :param string:     the string to be processed
    :returns:          the list of words after splitting

    >>> split_separators('Lyon Part-Dieu')
    ['Lyon', 'Part', 'Dieu']
    >>> split_separators('St-Etienne SNCF ')
    ['St', 'Etienne', 'SNCF', '']
    """
    for sep in SEPARATORS:
        string = string.replace(sep, SEPARATORS[0])

    return string.split(SEPARATORS[0])


def handle_alias(strings):
    """
    Some common words have different ways to be used.
    This function normalize those, to have a better
    comparison tool later.
    For example, we can replace 'st' by 'saint'.

    :param strings: the list of words to be processed
    :returns:       the list of words after normalization

    >>> handle_alias(['st', 'etienne', 'SNCF', ''])
    ['saint', 'etienne', 'SNCF', '']
    """
    return [ dict(ALIASES).get(s, s) for s in strings ]


def handle_transparent(strings):
    """
    Some words are often parts irrelevant to string comparison.
    This function remove those, to have a better
    comparison tool later.
    For example, we can remove 'ville' or 'sncf'.

    :param strings:      the list of words to be processed
    :returns:            the list of words after normalization

    >>> handle_transparent(['saint', 'etienne', 'sncf', ''])
    ['saint', 'etienne', '']
    >>> handle_transparent(['aix', 'ville'])
    ['aix']
    """
    return [ s for s in strings if s not in TRANSPARENTS ]


def handle_numbers_spaces(strings):
    """
    Some words contains numbers irrelevant to string comparison.
    This function remove those, to have a better
    comparison tool later.
    It also removes blanks which could have been left
    during earlier removals.

    :param strings: the list of words to be processed
    :returns:       the list of words number-free

    >>> handle_numbers_spaces(['saint', 'etienne', '2', ''])
    ['saint', 'etienne']
    """
    # We remove blanks or tabulation, and number
    return [ s for s in strings if s.strip() and not s.isdigit() ]



def clean(string):
    """
    Global cleaning function which put
    all previous ones together.

    This function cleans the string to have a better comparison.
    Different steps:

    - lower and strip (remove leading and trailing spaces/tabulations)
    - manage accentuated characters, parenthesis
    - properly split the string
    - handle common aliases, irrelevant words, numbers and spaces

    :param string: the string to be processed
    :returns:      the clean string

    >>> clean('Paris')
    ['paris']
    >>> clean('Paris ville')
    ['paris']
    >>> clean('St-Etienne')
    ['saint', 'etienne']
    >>> clean('Aix-Les   Bains')
    ['aix']
    >>> clean('antibes sncf 2 (centre)')
    ['antibes', 'centre']
    """
    # Basic cleaning
    # We remove blanks or tabulation, and number
    return handle_numbers_spaces(
           handle_transparent(
           handle_alias(
           split_separators(
           handle_parenthesis_info(
           handle_accents(
           str_lowercase(
               string.strip()
           )))))))


def is_sublist(subL, L):
    """
    This function tests the inclusion of a list in another one.

    :param subL:  the tested sub-list
    :param L:     the tested list
    :returns:     a boolean

    >>> is_sublist([2], [2,3])
    True
    >>> is_sublist([2,3], [2,3])
    True
    >>> is_sublist([], [2,3])  # [] is a sub-list of everyone
    True
    >>> is_sublist([2,3], [])
    False
    >>> is_sublist([4], [2,3])
    False
    >>> is_sublist([2,3], [3,2]) # Order matter
    False
    >>> is_sublist([2,3,4], [2,3])
    False
    >>> is_sublist([2,3], [2,3,4])
    True
    """
    n, ns  = len(L), len(subL)

    return any( (subL == L[i:i+ns]) for i in xrange(n-ns+1) )



def mod_leven(str1, str2, heuristic_inclusion=HEURISTIC_INCLUSION, heuristic_inclusion_value=HEURISTIC_INCLUSION_VALUE):
    """
    The main comparison function.
    In fact, the real work has already been done previously,
    with the cleaning function.

    This function uses Levenshtein ratio to evaluate the
    distance between the two strings. It is up to the user to
    define which distance is acceptable for classic mispelling, but
    from my point of view, 90% is fairly acceptable.

    When we have a inclusion of one string in the other (list inclusion,
    not possible to include partial words such as toul for toulon),
    we put the ratio of similarity to 90%, this is heuristic.
    Why not 100%? Because, if another entry in the base really match 100%,
    this will probably be an even better match, such as:
    orleans+gervais matches orleans with inclusion heuristic (so 90%),
    but we also have the real orleans+gervais station in the base,
    and this one is a 100% match, so this will take over as the best match.

    Sometimes rare cases of high ratio are not relevant.
    For example, Toul match Toulon with 80%, but this
    is wrong, and may be handled with a cache to manage exceptional
    failing by the graph module, or by upping the acceptance limit.

    :param str1: the first string to compare
    :param str2: the second string to compare
    :param heuristic_inclusion: boolean to toggle the heuristic inclusion
    :param heuristic_inclusion_value: for heuristic inclusion, the value considered
    :returns:    the distance, which is a ratio (0% to 100%)

    >>> mod_leven('antibes', 'antibs')
    0.92...
    >>> mod_leven('toul', 'toulon')
    0.8...
    >>> mod_leven('Aéroport CDG  2 TGV', 'aeroport-cdg') # Inclusion
    0.9...
    >>> mod_leven('Bains les bains', 'Tulle')
    0.0

    Tweaking behavior.

    >>> mod_leven('Aéroport CDG  2 TGV', 'aeroport-cdg', False) # No inclusion
    0.85...
    """
    str1 = clean(str1)
    str2 = clean(str2)

    # Cleaning reduced one to empty string
    # We do not want mismatch so...
    if not str1 or not str2:
        return 0.

    r = LevenRatio('+'.join(str1), '+'.join(str2))

    # Perfect match, finished
    if r == 1.0:
        return r

    # Heuristic of strict inclusion
    if heuristic_inclusion:
        if is_sublist(str1, str2) or is_sublist(str2, str1):
            return heuristic_inclusion_value

    return r


def _test():
    """
    When called directly, launching doctests.
    """
    import doctest
    opt =  (doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE |
            doctest.REPORT_ONLY_FIRST_FAILURE)

    doctest.testmod(optionflags=opt)



if __name__ == '__main__':

    _test()

    import sys

    if len(sys.argv) >= 3:

        str_1, str_2 = sys.argv[1], sys.argv[2]

        print '1) %-30s ---> %-30s' % (str_1, '+'.join(clean(str_1)))
        print '2) %-30s ---> %-30s' % (str_2, '+'.join(clean(str_2)))
        print
        print 'Similiarity: %.2f%%' % (100 * mod_leven(str_1, str_2))

