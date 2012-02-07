Here is the actual file which is used as the reference for the GeoBase class.
This file is very similar to the one in the DataGouvFr RFF file, except you might notice
I added some train stations manually at the end, based on what station I
encountered in the schedule files, and what I found as a matching
station on GeoHack. Some codes have also been changed to match the ones of GareEnMouvement.

So the main algorithm to produce this file:
    - use GareEnMouvements to scrap a first stations.csv
    - use data.gouv.fr to get the RFF file with all geocoded stations
    - add random codes into the RFF file (add_codes_RFF.py)
    - match codes from GareEnMouvements in the RFF file (add_GEM_RFF.py)
    - add manually all others European stations (add_LaMano_RFF.py)
    - reduce the lines duplicates and remove 'Non exploitee' stations (add_reduction_RFF.py)

Use generate_files.py script to generate them all at once.
Copy the result as stations_geobase.csv in this folder.

NB: Another script has been written to test NLS code integration, but
so far I have not really included that in the main stream, since it
does not really help and adds another uncertainty on the matching 
(the matching can only be done on the name for this integration).