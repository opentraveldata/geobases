#!/usr/bin/python
# -*- coding: utf-8 -*-

import simplejson as json
import sys

try:
    sys.path.append ('/usr/lib64')

    # Initialise the OpenTrep C++ library
    import libpyopentrep

except ImportError:
    # libpyopentrep could not be found
    raise ImportError("*libpyopentrep* raised ImportError.")



def compactResultParser(resultString):
    '''
    Compact result parser. The result string contains the main matches,
    separated by commas (','), along with their associated weights, given
    as percentage numbers. For every main match:

     - Columns (':') separate potential extra matches (i.e., matches with the same
       matching percentage).
     - Dashes ('-') separate potential alternate matches (i.e., matches with lower
       matching percentages).

    Samples of result string to be parsed:

     % pyopentrep -f S nice sna francisco vancouver niznayou
     'nce/100,sfo/100-emb/98-jcc/97,yvr/100-cxh/83-xea/83-ydt/83;niznayou'
     % pyopentrep -f S fr
     'aur:avf:bae:bou:chr:cmf:cqf:csf:cvf:dij/100'

    '''

    # Strip out the unrecognised keywords
    if ';' in resultString:
        str_matches, unrecognized = resultString.split(';', 1)
    else:
        str_matches, unrecognized = resultString, ''


    if not str_matches:
        return [], ''


    codes = []

    for alter_loc in str_matches.split(','):

        for extra_loc in alter_loc.split('-'):

            extra_loc, score = extra_loc.split('/', 1)

            for code in extra_loc.split(':'):

                codes.append((float(score), code.upper()))

                # We break because we only want to first
                break

            # We break because we only want to first
            break

    return codes, unrecognized



def interpretFromJSON (json_str):
    '''
    JSON interpreter. The JSON structure contains a list with the main matches,
    along with their associated fields (weights, coordinates, etc).
    For every main match:

     - There is a potential list of extra matches (i.e., matches with the same
       matching percentage).
     - There is a potential list of alternate matches (i.e., matches with lower
       matching percentages).

    Samples of result string to be parsed:

     - pyopentrep -f J nice sna francisco
       - {'locations':[
            {'names':[
               {'name': 'nice'}, {'name': 'nice/fr:cote d azur'}],
             'city_code': 'nce'},
            {'names':[
               {'name': 'san francisco'}, {'name': 'san francisco/ca/us:intl'}],
             'city_code': 'sfo',
             'alternates':[
                  {'names':[
                      {'name': 'san francisco emb'},
                      {'name': 'san francisco/ca/us:embarkader'}],
                      'city_code': 'sfo'},
                  {'names':[
                      {'name': 'san francisco jcc'},
                      {'name': 'san francisco/ca/us:china hpt'}],
                      'city_code': 'sfo'}
            ]}
         ]}

     - pyopentrep -f J fr
       - {'locations':[
            {'names':[
               {'name': 'aurillac'}, {'name': 'aurillac/fr'}],
                'extras':[
                {'names':[
                  {'name': 'avoriaz'}, {'name': 'avoriaz/fr'}],
                'city_code': 'avf'},
               {'names':[
                  {'name': 'barcelonnette'}, {'name': 'barcelonnette/fr'}],
                'city_code': 'bae'}
            ]}
         ]}
    '''

    return '; '.join(
        '-'.join([
            loc['iata_code'],
            loc['icao_code'],
            loc['geonames_id'],
            '%.2f%%' % float(loc['page_rank']),
            loc['city_code'],
            '%.2f' % float(loc['lat']),
            '%.2f' % float(loc['lon'])
        ])
        for loc in json.loads(json_str)['locations']
    )



def getPaths(openTrepLibrary):
    '''
    File-paths details
    '''

    # Calls the underlying OpenTrep library service
    filePathList = openTrepLibrary.getPaths().split(';')

    # Report the results
    print "ORI-maintained list of POR (points of reference): '%s'" % filePathList[0]
    print "Xapian-based travel database/index: '%s'" % filePathList[1]


def index(openTrepLibrary, xapianDBPath, verbose=False):
    '''
    Indexation
    '''

    if verbose:
        # DEBUG
        print "Perform the indexation of the (Xapian-based) travel database."
        print "That operation may take several minutes on some slow machines."
        print "It takes less than 20 seconds on fast ones..."

    # Calls the underlying OpenTrep library service
    result = openTrepLibrary.index()

    if verbose:
        # Report the results
        print "Done. Indexed " + result + " POR (points of reference)"



def search(openTrepLibrary, searchString, outputFormat, verbose):
    '''Search.

    If no search string was supplied as arguments of the command-line,
    ask the user for some


    Call the OpenTrep C++ library.

    The 'I' (Interpretation from JSON) output format is just an example
    of how to use the output generated by the OpenTrep library. Hence,
    that latter does not support that "output format". So, the raw JSON
    format is required, and the JSON string will then be parsed and
    interpreted by the interpretFromJSON() method, just to show how it
    works
    '''

    opentrepOutputFormat = outputFormat

    if opentrepOutputFormat == 'I':
        opentrepOutputFormat = 'J'

    result = openTrepLibrary.search(opentrepOutputFormat, searchString)
    if verbose:
        print ' -> Raw result: %s' % result

    # When the compact format is selected, the result string has to be
    # parsed accordingly.
    if outputFormat == 'S':
        return compactResultParser(result)

    # When the full details have been requested, the result string is
    # potentially big and complex, and is not aimed to be
    # parsed. So, the result string is just displayed/dumped as is.
    if outputFormat == 'F':
        return result

    # When the raw JSON format has been requested, no handling is necessary.
    if outputFormat == 'J':
        return result

    # The interpreted JSON format is an example of how to extract relevant
    # information from the corresponding Python structure. That code can be
    # copied/pasted by clients to the OpenTREP library.
    if outputFormat == 'I':
        return interpretFromJSON(result)



def main_trep(searchString=None, command=None, outputFormat=None, xapianDBPath=None, verbose=True, from_keys=None):

    # Command, either 'search' or 'index'
    if command is None:
        command = 'search'

    # Format of the output
    if outputFormat is None:
        outputFormat = 'S'

    # Options
    if xapianDBPath is None:
        xapianDBPath = "/tmp/opentrep/traveldb"

    # Default search string
    if searchString is None:
        searchString = 'sna francicso rio de janero lso angles reykyavki'


    openTrepLibrary = libpyopentrep.OpenTrepSearcher()

    initOK = openTrepLibrary.init(xapianDBPath, 'pyopentrep.log')

    if not initOK:
        raise Exception('The OpenTrepLibrary cannot be initialised')

    # Print out the file-path details
    if verbose and False:
        # Actually we do not want to display this :D
        getPaths(openTrepLibrary)

    if command == 'index':
        index(openTrepLibrary, xapianDBPath)
        r = None, None
    else:
        r = search(openTrepLibrary, searchString, outputFormat, verbose)

    # Free the OpenTREP library resource
    openTrepLibrary.finalize()

    if outputFormat != 'S':
        # Only this outputFormat is handled by upper layers
        # So for others we display it and return an empty
        # list to avoid failures
        print r
        return []

    if from_keys is None:
        return r[0]
    else:
        from_keys = set(from_keys)
        return [(k, e) for k, e in r[0] if e in from_keys]


def _test():

    test_1 = 'nce/100,sfo/100-emb/98-jcc/97,yvr/100-cxh/83-xea/83-ydt/83;niznayou'
    print test_1
    print compactResultParser(test_1)
    print

    test_2 = 'aur:avf:bae:bou:chr:cmf:cqf:csf:cvf:dij/100'
    print test_2
    print compactResultParser(test_2)
    print


if __name__ == '__main__':

    _test()

    print main_trep(searchString=sys.argv[1])

