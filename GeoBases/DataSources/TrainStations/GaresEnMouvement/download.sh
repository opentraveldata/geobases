#!/bin/bash

HTML_DIR=/tmp/crobelin/sncf
STATION_FILE=station_list.txt

mkdir -p $HTML_DIR
cut -d'^' -f 1 $STATION_FILE | while read CODE
do
  URL="http://www.gares-en-mouvement.com/votre_gare.php?gare=$CODE"
  HTML_FILE=$HTML_DIR/${CODE}.html
  curl $URL > $HTML_FILE
done