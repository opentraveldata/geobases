#!/usr/bin/python
# -*- coding: utf-8 -*-

import simplejson as json
import sys

try:
    sys.path.append ('/usr/lib64')

    # Initialise the OpenTrep C++ library
    import libpyopentrep

except ImportError:
    print >> sys.stderr, '* "import libpyopentrep" raised ImportError.'
    print >> sys.stderr

    raise



##
# Compact result parser. The result string contains the main matches,
# separated by commas (','), along with their associated weights, given
# as percentage numbers. For every main match:
#  - Columns (':') separate potential extra matches (i.e., matches with the same
#    matching percentage).
#  - Dashes ('-') separate potential alternate matches (i.e., matches with lower
#    matching percentages).
#
# Samples of result string to be parsed:
#  - pyopentrep -f S nice sna francisco vancouver niznayou
#    - 'nce/100,sfo/100-emb/98-jcc/97,yvr/100-cxh/83-xea/83-ydt/83;niznayou'
#  - pyopentrep -f S fr
#    - 'aur:avf:bae:bou:chr:cmf:cqf:csf:cvf:dij/100'
def compactResultParser(resultString):

    # Parsing begins
    # 1. First, strip out the unrecognised keywords
    if ';' in resultString:
        str_matches, unrecognized = resultString.split(';', 1)
    else:
        str_matches, unrecognized = resultString, ''


    # 2. Then, for each matching location, the alternate matches have to be
    #    stored aside.
    if not str_matches:
        return [], ''

    codes = []

    for alter_location in str_matches.split(','):

        for extra_location in alter_location.split('-'):

            extra_loc, score = extra_location.split('/', 1)

            for code in extra_loc.split(':'):

                codes.append((float(score), code.upper()))

                # We break because we only want to first
                break

            # We break because we only want to first
            break

    return codes, unrecognized


##
# JSON interpreter. The JSON structure contains a list with the main matches,
# along with their associated fields (weights, coordinates, etc).
# For every main match:
#  - There is a potential list of extra matches (i.e., matches with the same
#    matching percentage).
#  - There is a potential list of alternate matches (i.e., matches with lower
#    matching percentages).
#
# Samples of result string to be parsed:
#  - pyopentrep -f J nice sna francisco
#    - {'locations':[
#         {'names':[
#            {'name': 'nice'}, {'name': 'nice/fr:cote d azur'}],
#          'city_code': 'nce'},
#         {'names':[
#            {'name': 'san francisco'}, {'name': 'san francisco/ca/us:intl'}],
#          'city_code': 'sfo',
#          'alternates':[
#               {'names':[
#                   {'name': 'san francisco emb'},
#                   {'name': 'san francisco/ca/us:embarkader'}],
#                   'city_code': 'sfo'},
#               {'names':[
#                   {'name': 'san francisco jcc'},
#                   {'name': 'san francisco/ca/us:china hpt'}],
#                   'city_code': 'sfo'}
#         ]}
#      ]}
#  - pyopentrep -f J fr
#    - {'locations':[
#         {'names':[
#            {'name': 'aurillac'}, {'name': 'aurillac/fr'}],
#          'extras':[
#            {'names':[
#               {'name': 'avoriaz'}, {'name': 'avoriaz/fr'}],
#             'city_code': 'avf'},
#            {'names':[
#               {'name': 'barcelonnette'}, {'name': 'barcelonnette/fr'}],
#             'city_code': 'bae'}
#         ]}
#      ]}
def interpretFromJSON (jsonFormattedResult):
    parsedStruct = json.loads (jsonFormattedResult)

    interpretedString = ''

    for location in parsedStruct['locations']:

        interpretedString += location['iata_code'] + '-' 
        interpretedString += location['icao_code'] + '-' 
        interpretedString += location['geonames_id'] + ' ' 
        interpretedString += '(' + location['page_rank'] + '%) / '
        interpretedString += location['city_code'] + ": "
        interpretedString += location['lat'] + ' ' 
        interpretedString += location['lon'] + '; '

    #
    return interpretedString


##
# File-path details
#
def getPaths (openTrepLibrary):
    # Calls the underlying OpenTrep library service
    filePathListString = openTrepLibrary.getPaths()
    filePathList = filePathListString.split(';')

    # Report the results
    print "ORI-maintained list of POR (points of reference): '" + filePathList[0] + "'"
    print "Xapian-based travel database/index: '" + filePathList[1] + "'"


##
# Indexation
#
def index (openTrepLibrary, xapianDBPath):
    # DEBUG
    print "Perform the indexation of the (Xapian-based) travel database."
    print "That operation may take several minutes on some slow machines."
    print "It takes less than 20 seconds on fast ones..."

    # Calls the underlying OpenTrep library service
    result = openTrepLibrary.index()

    # Report the results
    print "Done. Indexed " + result + " POR (points of reference)"


##
# Search
#
def search (openTrepLibrary, searchString, outputFormat, verbose):
    # If no search string was supplied as arguments of the command-line,
    # ask the user for some

    ##
    # Call the OpenTrep C++ library.
    #
    # The 'I' (Interpretation from JSON) output format is just an example
    # of how to use the output generated by the OpenTrep library. Hence,
    # that latter does not support that "output format". So, the raw JSON
    # format is required, and the JSON string will then be parsed and
    # interpreted by the interpretFromJSON() method, just to show how it
    # works
    opentrepOutputFormat = outputFormat

    if opentrepOutputFormat == 'I':
        opentrepOutputFormat = 'J'

    result = openTrepLibrary.search(opentrepOutputFormat, searchString)
    if verbose:
        print 'Raw result: %s' % result

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



if __name__ == '__main__':


    test_1 = 'nce/100,sfo/100-emb/98-jcc/97,yvr/100-cxh/83-xea/83-ydt/83;niznayou'
    print test_1
    print compactResultParser(test_1)

    test_2 = 'aur:avf:bae:bou:chr:cmf:cqf:csf:cvf:dij/100'
    print test_2
    print compactResultParser(test_2)

    print
    print main_trep(searchString=sys.argv[1])

