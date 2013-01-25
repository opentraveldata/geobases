#!/bin/bash

cd `dirname $0`

# pandoc 1.10 needed
echo 'Converting to mardown'
pandoc -f rst -t markdown ../README.rst > README.md
