Here is the actual file which is used as the reference for the GeoBase class.
This file is very similar to the one on the geonames folder, except you might notice
I commented some lines, which are actually duplicates IATA codes.

So the main algorithm to generate this file is :
    - use the Geonames source to generate the airport_geonames.csv
    - remove city-only entries, like PAR (done by the script, but you
      might want to check this)
    - comment bad duplicates, otherwise you might get exception when loading the geobase object.
