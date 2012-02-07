#!/bin/bash

HTML_DIR=/tmp/crobelin/sncf
STATION_FILE=station_list.txt

mkdir -p $HTML_DIR
cut -d'^' -f 1 $STATION_FILE | while read CODE
do
  INPUT_FILE=$HTML_DIR/${CODE}.html
  grep 'Coordonn&eacute;es GPS :' $INPUT_FILE | perl -pe "s/.*<\/span>(-?[0-9\.]+),+(-?[0-9\.]+)<.*/$CODE^\1^\2/ig"
done