#!/bin/bash

DIRNAME=`dirname $0`
cd $DIRNAME
cd ..

# Making sure we run on last version
pip uninstall GeoBases
export PYTHONPATH=.:..:$PYTHONPATH

echo -e "Running..."
coverage erase
coverage run ./test/test_GeoBases.py -v
rm -f $DIRNAME/htmlcov/*
coverage html --directory=$DIRNAME/htmlcov --omit="$HOME/.local*"

# Results
echo -e "\n\n* HTML results in $DIRNAME/htmlcov"
firefox $DIRNAME/htmlcov/index.html
