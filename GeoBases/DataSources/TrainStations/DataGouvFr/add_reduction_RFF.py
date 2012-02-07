#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile, addTopLevel


try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
    
    
def load_RFF(source):
    
    cache = OrderedDict()
    
    # RFF utils
    CODE = 0
    LINE = 1
    NAME = 2
    INFO = 3
    LAT  = 4
    LNG  = 5
    SEPARATOR = '^'
    
    with open(source) as f:

        for row in f:
            
            # Skip comments and empty lines
            if not row or row.startswith('#'):
                #print row
                continue
                            
            row = row.strip().split(SEPARATOR)
            
            if 'Desserte Voyageur' not in row[INFO].split('-'):
                continue
            
            if row[CODE] not in cache:
                
                cache[row[CODE]] = {
                    'lines' : [],
                    'name'  : row[NAME],
                    'info'  : row[INFO], 
                    'lat'   : row[LAT],
                    'lng'   : row[LNG]
                }
                
            if row[LINE] not in cache[row[CODE]]['lines']:
                # No duplicates here
                # Warning: there are real duplicates in RFF file
                cache[row[CODE]]['lines'].append(row[LINE])
                
    return cache

    print "Import successful from %s" % source



def reduct_lines(cache, output):
    
    # RFF utils
    SEPARATOR = '^'

    with open(output, 'w') as out:
      
        for code, d in cache.iteritems():
            
            out.write(SEPARATOR.join([code, 
                                     ','.join(d['lines']),
                                     d['name'],
                                     d['info'],
                                     d['lat'],
                                     d['lng']]) + '\n')
                          
    print "Export successful of %s" % output


def add_reduction_RFF(source, output):
    
    reduct_lines(load_RFF(source), output)
       
                
if __name__ == '__main__':

    add_reduction_RFF(localToFile(__file__, "RFF/RFF_gares.ids.gm.man.csv"), 
                      localToFile(__file__, "RFF/RFF_gares.ids.gm.man.red.csv"))





