#!/bin/bash

DIRNAME=`dirname $0`
cd $DIRNAME
cd ..

# Making sure we run on last version
pip uninstall GeoBases
export PYTHONPATH=.:..:$PYTHONPATH

coverage erase
coverage run ./test/test_GeoBases.py -v
rm -f $DIRNAME/htmlcov/*
coverage html

# Results
echo -e "\n* HTML results in $DIRNAME/htmlcov"
firefox $DIRNAME/htmlcov/index.html

# Deployment
echo -e "\nTo deploy on coveralls.io, execute (need .coveralls.yml repo_token set):\n$ coveralls"
