#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile, addTopLevel

addTopLevel(__file__, 4)

from GeoBases.GeoBaseModule import GeoBase
from GeoBases.GeoUtils import haversine
from GeoBases.LevenshteinUtils import mod_leven


def match(name, lat, lng, geoBase):

    # HAVERSINE PROJECTION :)
    hD, hmatch  = geoBase.findClosestFromPoint(lat, lng)[0]
    hmatch_name = geoBase.get(hmatch, 'name')
    hmatch_lat  = geoBase.get(hmatch, 'lat')
    hmatch_lng  = geoBase.get(hmatch, 'lng')
    
    hL = mod_leven(hmatch_name, name)
    

    # LEVENSHTEIN PROJECTION :)
    lL, lmatch  = geoBase.fuzzyGetCached(name, 'name', verbose=False)
    lmatch_name = geoBase.get(lmatch, 'name')
    lmatch_lat  = geoBase.get(lmatch, 'lat')
    lmatch_lng  = geoBase.get(lmatch, 'lng')
    
    lD = haversine((lat, lng), (lmatch_lat, lmatch_lng))


    if lD < 1.0 and lL == 1.0:
        # If name is perfect we go for it
        return (lD, lL, lmatch, lmatch_name, 'L')
        
    if lD >= 1.0 or lL < 0.70:  
        # If everything is bad, this means poor geolocalization, we go with levenshtein    
        return (lD, lL, lmatch, lmatch_name, 'L')       
        
    # Closest with Haversine
    return (hD, hL, hmatch, hmatch_name, 'H')



def project_on_geobase(source, geosource):

    geoBase = GeoBase(data='stations', source=geosource, verbose=True)
    cache = {}
    
    # GEM utils
    CODE = 0
    NAME = 1
    LAT  = 2
    LNG  = 3
    SEPARATOR = '^'
    

    with open(source) as f:

        for row in f:

            # Skip comments and empty lines
            if not row or row.startswith('#'):
                continue
                            
            row = row.strip().split(SEPARATOR)

            (D, L, match_code, match_name, method) = match(row[NAME], row[LAT], row[LNG], geoBase)
            
            if not analyse_match(method, D, L, row[CODE], row[NAME], match_code, match_name):
                continue
                
            if match_code in cache:
                print '* Warning, duplicate match %s -> %s' % (row[NAME], match_name) 
                
            cache[match_code] = {
                'code': row[CODE], 
                'lat' : row[LAT], 
                'lng' : row[LNG]
            }

    print "Import successful from %s" % source
            
    return cache



def analyse_match(method, D, L, entry, entry_name, match, match_name):

     if D < 0.1 and L == 1.0:
         #print '%s perfect match: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     if D < 0.1 and L >= 0.95:
         #print '%s *quasi* match: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     if D < 1.0 and L >= 0.95:
         #print '%s bit misplaced: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     if D < 1.0 and L >= 0.70:
         print '%s b. misspelled: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     if L == 1.0:
         print '%s guess on name: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     if D < 1.0:
         print '%s guess on loc.: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
         return 1
     
     print '%s ---- only got: %.3f %.3f %6s %25s --> %6s %25s' % (method, D, L, entry, entry_name, match, match_name)
     return 0


   

def add_GEM_entries(cache, source, output):

    # RFF utils
    CODE = 0
    NAME = 2
    LAT  = 4
    LNG  = 5
    SEPARATOR = '^'

    with open(output, 'w') as out:    
        with open(source) as f:
            
            for row in f:
                
                if row.startswith('#') or not row:
                    continue
                
                row = row.strip().split(SEPARATOR)
                
                if row[CODE] in cache:
                    
                    new_vals = cache[row[CODE]]
                    
                    print '* Changing %s to %s [%s]' % (row[CODE], new_vals['code'], row[NAME])
                    
                    row[CODE] = new_vals['code']
                    row[LAT]  = new_vals['lat']
                    row[LNG]  = new_vals['lng']
                    
                out.write(SEPARATOR.join(row) + '\n')                    

        print "Import successful from %s" % source                      
    print "Export successful of %s" % output


def add_GEM_RFF(gem_source, rff_source, rff_ouput):
    
    add_GEM_entries(project_on_geobase(gem_source, rff_source), rff_source, rff_ouput)
        
      
                
if __name__ == '__main__':

    add_GEM_RFF(localToFile(__file__, "../GaresEnMouvement/stations.csv"),
                localToFile(__file__, "RFF/RFF_gares.ids.csv"), 
                localToFile(__file__, "RFF/RFF_gares.ids.gm.csv"))




