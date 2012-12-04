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
            echo "-f was triggered! Replacing old file anyway..." >&2
            FORCE=1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done


do_a_file() {

    local REF_URL="$1"
    local LOC_CSV="$2"

    echo -e "\n* Comparing local file and remote:\n"
    echo -e "1. $PWD/$LOC_CSV"
    echo -e "2. $REF_URL"

    # Downloading
    wget $REF_URL -O $TMP_CSV -o /dev/null

    # Commenting header
    sed -i '1s/^/#/g' $TMP_CSV

    echo -e "\n* Unified diff:"
    diff -u $LOC_CSV $TMP_CSV
    DIFF=`diff -u $LOC_CSV $TMP_CSV`
    echo

    if [ "$DIFF" = "" ]; then
        echo "Nothing to do."
        rm -f $TMP_CSV
        return 0
    fi

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
#REF_URL_1='http://redmine.orinet.nce.amadeus.net/projects/optd/repository/revisions/trunk/raw/refdata/ORI/ori_por_public.csv'
#REF_URL_2='http://redmine.orinet.nce.amadeus.net/projects/optd/repository/revisions/trunk/raw/refdata/ORI/ori_por_non_iata.csv'
REF_URL_1='https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_por_public.csv'
REF_URL_2='https://github.com/opentraveldata/optd/raw/trunk/refdata/ORI/ori_por_non_iata.csv'
REF_URL_3='http://redmine.orinet.nce.amadeus.net/projects/oripor/repository/revisions/trunk/raw/admin/ori_por.csv'
REF_URL_4='http://orinet.nce.amadeus.net/Projects/Data_Center/VOLATILE/airline/crb_airline.csv'

LOC_CSV_1='Por/Ori/ori_por_public.csv'
LOC_CSV_2='Por/Ori/ori_por_non_iata.csv'
LOC_CSV_3='Por/Ori/ori_por.csv'
LOC_CSV_4='Airlines/crb_airline.csv'

do_a_file "$REF_URL_1" "$LOC_CSV_1"
do_a_file "$REF_URL_2" "$LOC_CSV_2"
do_a_file "$REF_URL_3" "$LOC_CSV_3"
do_a_file "$REF_URL_4" "$LOC_CSV_4"

