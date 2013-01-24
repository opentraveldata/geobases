#!/bin/bash

# pandoc 1.10 needed
pandoc -f rst -t markdown README.rst > README.md.new
