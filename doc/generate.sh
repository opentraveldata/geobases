#!/bin/bash

DIRNAME=`dirname $0`
cd $DIRNAME

# Making sure we run on last version
pip uninstall GeoBases

# Generation
export PYTHONPATH=.:..:$PYTHONPATH
make clean
make html

# Package
cd _build/html
zip -r api.zip *
echo -e "\n\n* Export with: cp $DIRNAME/_build/html/api.zip\n\n"

# View
firefox index.html

