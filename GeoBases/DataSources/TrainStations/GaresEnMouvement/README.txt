1) Downloading html files from gares-en-mouvement: download.sh
   - Requires the station list, with 5-letter station code in first column (with columns separated by ^), e.g., "frzao^Cahors"
   - Change the path to station list file and directory where html files will be saved
   - Launch download.sh
   - Output: html files downloaded from gares-en-mouvement, for all stations in station list

2) Parsing html files: parse.sh
   - Requires the station list, with 5-letter station code in first column (with columns separated by ^), e.g., "frzao^Cahors"
   - Requires html files downloaded from gares-en-mouvement
   - Change the path to station list file and directory where html files will be saved
   - Launch parse.sh
   - Output: standard output with 5-letter station code, longitude and latitude, separated by ^

The problem at this point is that the longitude of the stations is almost always positive, even for stations that are West of the Greenwich meridian.

Here is how I identified whether stations have positive or negative longitudes

3) Some manual work:
   - Sort station_list.txt and output of parse.sh by station code and join them to obtain the following csv delimited by ^:
   station code, station name, latitude, longitude (potentially with incorrect sign)
   - Get cities1000.txt from geonames

4) Match station names and city names, and make sure the matched station and city are not too far from each other: get_east_west.py
   - I actually needed to change the names of the station to make the match easier, e.g., Paris St Lazare --> Paris
   - Output: station code, station name, city name (potentially wrong), flag_match (whether there was a match based on names), longitude sign, new longitude (for information)
   - More manual work to correct the records where no match could be found
