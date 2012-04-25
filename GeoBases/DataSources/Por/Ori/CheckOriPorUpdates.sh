#!/bin/bash

# Files
REF_URL='http://redmine.orinet.nce.amadeus.net/projects/optd/repository/revisions/trunk/entry/refdata/ORI/ori_por_public.csv'
TMP_CSV='tmp_01.csv'

# Moving to the script directory
# We could move to the installation directory if we knew it
cd `dirname $0`
LOC_CSV='ori_por_public.csv'

echo "Considering local oripor file $LOC_CSV."


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

# Downloading
wget $REF_URL -O $TMP_CSV

# Commenting header
sed -i '1s/^/#/g' $TMP_CSV

echo "Unified diff:"
diff -u $LOC_CSV $TMP_CSV

if [ "$FORCE" == "0" ]; then
    echo -n "Replace? [Y/N]: "
    read RESPONSE
else
    RESPONSE="Y"
fi

if [ "$RESPONSE" == "Y" ]; then
    echo "You chose to replace."
    mv $TMP_CSV $LOC_CSV
else
    echo "You chose not to replace."
    rm $TMP_CSV
fi


