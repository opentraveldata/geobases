#!/bin/bash

# Moving to the script directory
# We could move to the installation directory if we knew it
cd `dirname $0`

TMP_CSV='/tmp/fsdlkghiueevlr_01.csv'

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

    local REF_URL="$1"
    local LOC_CSV="$2"
    local NO_HEAD="$3"
    local UNZIP_F="$4"
    local CHOOSED="$5"
    local SPECIAL="$6"

    echo -e "\n* Comparing local and source:"
    echo -e "1. $PWD/$LOC_CSV"
    echo -e "2. $REF_URL"

    # Downloading
    wget $REF_URL -O $TMP_CSV -o /dev/null

    # Unzip if necessary
    if [ "$UNZIP_F" = "1" ]; then
        extract_one $TMP_CSV $CHOOSED
    fi

    # Commenting header
    if [ "$NO_HEAD" = "1" ]; then
        comment_head $TMP_CSV
    fi

    # Special process
    if [ "$SPECIAL" = "1" ]; then
        split_fcodes $TMP_CSV
    fi

    if [ ! -f "$LOC_CSV" ]; then
        echo -e "\n* $LOC_CSV does not exist!"
        touch "$LOC_CSV"
    fi

    # Computing diff
    DIFF=`diff -u $LOC_CSV $TMP_CSV`

    if [ "$DIFF" = "" ]; then
        echo "* Nothing to do."
        rm -f $TMP_CSV
        return 0
    fi

    echo -e "\n* Unified diff:"
    diff -u $LOC_CSV $TMP_CSV

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
REF_URL_01='https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_por_public.csv'
REF_URL_02='https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_por_non_iata.csv'
REF_URL_04='https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_airlines.csv'
REF_URL_05='http://download.geonames.org/export/dump/countryInfo.txt'
REF_URL_06='http://download.geonames.org/export/dump/timeZones.txt'
REF_URL_07='http://download.geonames.org/export/dump/iso-languagecodes.txt'
REF_URL_08='http://download.geonames.org/export/dump/featureCodes_en.txt'
REF_URL_09='http://download.geonames.org/export/dump/cities15000.zip'
CHOOSED_09='cities15000.txt'
REF_URL_10='http://download.geonames.org/export/dump/FR.zip'
CHOOSED_10='FR.txt'
REF_URL_11='http://download.geonames.org/export/dump/MC.zip'
CHOOSED_11='MC.txt'
REF_URL_12='http://download.geonames.org/export/zip/FR.zip'
CHOOSED_12='FR.txt'
REF_URL_13='http://download.geonames.org/export/zip/MC.zip'
CHOOSED_13='MC.txt'

LOC_CSV_01='Por/Ori/ori_por_public.csv'
LOC_CSV_02='Por/Ori/ori_por_non_iata.csv'
LOC_CSV_04='Airlines/ori_airlines.csv'
LOC_CSV_05='Countries/countryInfo.txt'
LOC_CSV_06='TimeZones/timeZones.txt'
LOC_CSV_07='Languages/iso-languagecodes.txt'
LOC_CSV_08='FeatureCodes/featureCodes_en.txt'
LOC_CSV_09='Cities/cities15000.txt'
LOC_CSV_10='Por/GeoNames/FR.txt'
LOC_CSV_11='Por/GeoNames/MC.txt'
LOC_CSV_12='PostalCodes/GeoNames/FR.txt'
LOC_CSV_13='PostalCodes/GeoNames/MC.txt'


#do_a_file REF_URL LOC_CSV NO_HEAD UNZIP_F
do_a_file "$REF_URL_04" "$LOC_CSV_04" 1
do_a_file "$REF_URL_05" "$LOC_CSV_05" 0
do_a_file "$REF_URL_06" "$LOC_CSV_06" 1
do_a_file "$REF_URL_07" "$LOC_CSV_07" 1
do_a_file "$REF_URL_08" "$LOC_CSV_08" 0 0 ""            1
do_a_file "$REF_URL_09" "$LOC_CSV_09" 0 1 "$CHOOSED_09"
do_a_file "$REF_URL_10" "$LOC_CSV_10" 0 1 "$CHOOSED_10"
do_a_file "$REF_URL_11" "$LOC_CSV_11" 0 1 "$CHOOSED_11"
do_a_file "$REF_URL_12" "$LOC_CSV_12" 0 1 "$CHOOSED_12"
do_a_file "$REF_URL_13" "$LOC_CSV_13" 0 1 "$CHOOSED_13"

# The longest at the end
do_a_file "$REF_URL_02" "$LOC_CSV_02" 1
do_a_file "$REF_URL_01" "$LOC_CSV_01" 1

