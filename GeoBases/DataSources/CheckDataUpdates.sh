#!/bin/bash

# Moving to the script directory
# We could move to the installation directory if we knew it
cd `dirname $0`

TMP_DIR='/tmp'

TMP_VIEW_1='/tmp/fsdlkghiueevlr_02.csv'
TMP_VIEW_2='/tmp/fsdlkghiueevlr_03.csv'

# By default, we will ask the user permission to replace
# the old file, unless -f option is triggered
FORCE=0

while getopts ":f" opt; do
    case $opt in
        f)
            echo "Forced update! All files will be replaced..." >&2
            FORCE=1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done


view() {
    if [ -f $1 ] ; then
        case $1 in
            *.tar.bz2)   tar xvjf $1     ;;
            *.tar.gz)    tar xvzf $1     ;;
            *.bz2)       bunzip2 $1      ;;
            *.rar)       unrar x $1      ;;
            *.gz)        gunzip $1       ;;
            *.tar)       tar xvf $1      ;;
            *.tbz2)      tar xvjf $1     ;;
            *.tgz)       tar xvzf $1     ;;
            *.zip)       unzip -qca $1   ;;
            *.Z)         uncompress $1   ;;
            *.7z)        7z x $1         ;;
            *)           cat $1          ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

extract_one() {
    unzip -q $1 $2
    mv $2 $1
}

comment_head() {
    sed -i '1s/^/#/g' $1
}

split_fcodes() {
    sed -i 's/^\(.\)\./\1\t/g' $1
}


do_a_file() {

    local TMP_CSV
    local REF_URL="$1"
    local LOC_CSV="$2"
    local SPECIAL="$3"

    echo -e "\n* Comparing local and source:"
    echo -e "1. $PWD/$LOC_CSV"
    echo -e "2. $REF_URL"

    # Downloading
    TMP_CSV="$TMP_DIR"/`basename $REF_URL`
    wget --no-check-certificate $REF_URL -O $TMP_CSV -o /dev/null

    # Special process
    if [ "$SPECIAL" = "1" ]; then
        split_fcodes $TMP_CSV
    fi

    if [ ! -f "$LOC_CSV" ]; then
        echo -e "\n* $LOC_CSV does not exist!"
        touch "$LOC_CSV"
    fi

    # Computing diff
    view $LOC_CSV > $TMP_VIEW_1
    view $TMP_CSV > $TMP_VIEW_2
    DIFF=`diff -u $TMP_VIEW_1 $TMP_VIEW_2`

    if [ "$DIFF" = "" ]; then
        echo "* Nothing to do."
        rm -f $TMP_CSV
        return 0
    fi

    echo -e "\n* Unified diff:"
    diff -u $TMP_VIEW_1 $TMP_VIEW_2

    if [ "$FORCE" = "0" ]; then
        echo -n "Replace? [Y/N]: "
        read RESPONSE
    else
        RESPONSE="Y"
    fi

    if [ "$RESPONSE" = "Y" ]; then
        echo "You chose to replace."
        mv $TMP_CSV $LOC_CSV
    else
        echo "You chose not to replace."
        rm -f $TMP_CSV
    fi

}

# Files
REF_URL_01='https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_por_public.csv'
REF_URL_02='https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_por_no_longer_valid.csv'
REF_URL_04='https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_airlines.csv'
REF_URL_14='https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_region_details.csv'
REF_URL_15='https://raw.github.com/opentraveldata/optd/trunk/refdata/ORI/ori_aircraft.csv'
REF_URL_05='http://download.geonames.org/export/dump/countryInfo.txt'
REF_URL_06='http://download.geonames.org/export/dump/timeZones.txt'
REF_URL_07='http://download.geonames.org/export/dump/iso-languagecodes.txt'
REF_URL_08='http://download.geonames.org/export/dump/featureCodes_en.txt'
REF_URL_09='http://download.geonames.org/export/dump/cities15000.zip'
REF_URL_10='http://download.geonames.org/export/dump/FR.zip'
REF_URL_11='http://download.geonames.org/export/dump/MC.zip'
REF_URL_12='http://download.geonames.org/export/zip/FR.zip'
REF_URL_13='http://download.geonames.org/export/zip/MC.zip'

LOC_CSV_01='Por/Ori/ori_por_public.csv'
LOC_CSV_02='Por/Ori/ori_por_no_longer_valid.csv'
LOC_CSV_04='Airlines/ori_airlines.csv'
LOC_CSV_14='Regions/ori_region_details.csv'
LOC_CSV_15='Aircraft/ori_aircraft.csv'
LOC_CSV_05='Countries/countryInfo.txt'
LOC_CSV_06='TimeZones/timeZones.txt'
LOC_CSV_07='Languages/iso-languagecodes.txt'
LOC_CSV_08='FeatureCodes/featureCodes_en.txt'
LOC_CSV_09='Cities/cities15000.zip'
LOC_CSV_10='Por/GeoNames/FR.zip'
LOC_CSV_11='Por/GeoNames/MC.zip'
LOC_CSV_12='PostalCodes/GeoNames/FR.zip'
LOC_CSV_13='PostalCodes/GeoNames/MC.zip'


#do_a_file REF_URL LOC_CSV
do_a_file "$REF_URL_04" "$LOC_CSV_04"
do_a_file "$REF_URL_05" "$LOC_CSV_05"
do_a_file "$REF_URL_06" "$LOC_CSV_06"
do_a_file "$REF_URL_07" "$LOC_CSV_07"
do_a_file "$REF_URL_08" "$LOC_CSV_08" 1
do_a_file "$REF_URL_09" "$LOC_CSV_09"
do_a_file "$REF_URL_10" "$LOC_CSV_10"
do_a_file "$REF_URL_11" "$LOC_CSV_11"
do_a_file "$REF_URL_12" "$LOC_CSV_12"
do_a_file "$REF_URL_13" "$LOC_CSV_13"
do_a_file "$REF_URL_14" "$LOC_CSV_14"
do_a_file "$REF_URL_15" "$LOC_CSV_15"

# The longest at the end
do_a_file "$REF_URL_02" "$LOC_CSV_02"
do_a_file "$REF_URL_01" "$LOC_CSV_01"

