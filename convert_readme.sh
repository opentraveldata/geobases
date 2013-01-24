#!/bin/bash

# pandoc 1.10 needed
echo 'Downloading README.rst'
rm -f README.rst*
wget 'https://raw.github.com/opentraveldata/geobases/public/README.rst' -o /dev/null

echo 'Converting to mardown'
pandoc -f rst -t markdown README.rst > README.md

# pandoc leaves some underscores after urls
echo 'Finishing formatting'
sed -i 's/)\\_/)/g' README.md

echo 'Cleaning'
rm README.rst
