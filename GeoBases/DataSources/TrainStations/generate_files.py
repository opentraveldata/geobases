#!/usr/bin/python
# -*- coding: utf-8 -*-

from SysUtils import localToFile

from DataGouvFr.add_codes_RFF     import add_codes_RFF
from DataGouvFr.add_GEM_RFF       import add_GEM_RFF
from DataGouvFr.add_LaMano_RFF    import add_LaMano_RFF
from DataGouvFr.add_reduction_RFF import add_reduction_RFF


                
if __name__ == '__main__':

    add_codes_RFF(localToFile(__file__, "DataGouvFr/RFF/RFF_gares.csv"), 
                  localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.csv"))

    add_GEM_RFF(localToFile(__file__, "./GaresEnMouvement/stations.csv"),
                localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.csv"), 
                localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.csv"))

    add_LaMano_RFF(localToFile(__file__, "./LaMano/additional_stations.csv"),
                   localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.csv"), 
                   localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.man.csv"))

    add_reduction_RFF(localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.man.csv"), 
                      localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.man.red.csv"))

    print '\nDone.\nCopying "RFF_gares.ids.gm.man.red.csv" in upper directory as "stations_geobase.csv"'
    
    add_reduction_RFF(localToFile(__file__, "DataGouvFr/RFF/RFF_gares.ids.gm.man.csv"), 
                      localToFile(__file__, "stations_geobase.csv"))

