#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile, addTopLevel

addTopLevel(__file__, 4)

from GeoBases.GeoBaseModule import GeoBase
from GeoBases.GeoUtils import haversine
from GeoBases.LevenshteinUtils import mod_leven


def match(name, geoBase):

    # LEVENSHTEIN PROJECTION :)
    match, L  = geoBase.fuzzyGetCached(name, 'name', verbose=False)
    match_name = geoBase.get(match, 'name')

    return (L, match, match_name)

    

def project_on_geobase(source, geosource):

    geoBase = GeoBase(data='stations', source=geosource, verbose=True)
    
    # NLS utils
    UIC_CODE    = 0
    DESCRIPTION = 1
    NLS_CODE    = 2
    PHYSICAL    = 3
    SEPARATOR   = ','

    cache = {}
    
    with open(source) as f:

        for row in f:

            # Skip comments and empty lines
            if not row or row.startswith('#'):
                continue
                            
            row = row.lower().strip().split(SEPARATOR)

            (L, match_code, match_name) = match(row[DESCRIPTION], geoBase)
            
            if not analyse_match(L, row[NLS_CODE], row[DESCRIPTION], match_code, match_name):
                continue
                
            if match_code in cache:
                print '* Warning, duplicate match %s -> %s' % (row[DESCRIPTION], match_name) 
                
            cache[match_code] = {
                'code': row[NLS_CODE]
            }


    print "Import successful from %s" % source
            
    return cache



def analyse_match(L, entry, entry_name, match, match_name):

     if L == 1.0:
         print 'perfect match: %.3f %6s %25s --> %6s %25s' % (L, entry, entry_name, match, match_name)
         return 1
     
     if L >= 0.95:
         #print '*quasi* match: %.3f %6s %25s --> %6s %25s' % (L, entry, entry_name, match, match_name)
         return 0

     if L >= 0.90:
         #print 'b. misspelled: %.3f %6s %25s --> %6s %25s' % (L, entry, entry_name, match, match_name)
         return 0

     #print '---- only got: %.3f %6s %25s --> %6s %25s' % (L, entry, entry_name, match, match_name)
     return 0

       
def add_NLS_entries(cache, source, output):

    # RFF utils
    CODE = 0
    NAME = 2
    LAT  = 4
    LNG  = 5
    SEPARATOR = '^'
    
    with open(source) as f:
        with open(output, 'w') as out:
            
            for row in f:
                
                if row.startswith('#') or not row:
                    continue
                
                row = row.strip().split(SEPARATOR)
                
                if row[CODE] in cache:
                    
                    new_vals = cache[row[CODE]]
                    
                    print '* Changing %s to %s [%s]' % (row[CODE], new_vals['code'], row[NAME])
                    
                    row[CODE] = new_vals['code']
                    
                out.write(SEPARATOR.join(row) + '\n')                    

    print "Import successful from %s" % source


def add_NLS_RFF(nls_source, rff_source, rff_ouput):
       
    add_NLS_entries(project_on_geobase(nls_source, rff_source), rff_source, rff_ouput)
        
      
                
if __name__ == '__main__':

    add_NLS_RFF(localToFile(__file__, "../NLS/NLS CODES RefDataSNCF.csv"),
                localToFile(__file__, "RFF/RFF_gares.ids.csv"), 
                localToFile(__file__, "RFF/RFF_gares.ids.nls.csv"))




