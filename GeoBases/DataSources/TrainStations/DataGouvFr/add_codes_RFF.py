#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile


class generate_id(object):
    '''
    Class to generate line ids for additional stations.
    
    >>> gl = generate_id()
    >>> gl()
    '1000001'
    >>> gl()
    '1000002'
    '''
    def __init__(self):
        self.r = 0
        
    def __call__(self):
        
        self.r += 1        
        return 'fr%s' % self.r
    
      

def add_codes_RFF(source, output):

    # RFF utils
    NAME = 1
    LAT  = 2
    LNG  = 3
    SEPARATOR = '^'
    
    cache  = {}
    gen_id = generate_id() 
    
    with open(output, 'w') as out:
        with open(source) as f:
                 
            
            for row in f:
                
                if not row or row.startswith('#'):
                    continue
                
                row = row.strip().split(SEPARATOR)
                
                if row[NAME] not in cache:
                    # We put a cache here because
                    # some lines must have the same id,
                    # because they referenced a station on a line,
                    # and if the station is on several lines
                    # we will have several rows talking about 
                    # the same station
                    cache[row[NAME]] = gen_id()
                
                out.write(cache[row[NAME]] + '^' + '^'.join(row) + '\n')

        print "Import successful from %s" % source                      
    print "Export successful of %s" % output
            
                
if __name__ == '__main__':

    add_codes_RFF(localToFile(__file__, "RFF/RFF_gares.csv"), 
                  localToFile(__file__, "RFF/RFF_gares.ids.csv"))

