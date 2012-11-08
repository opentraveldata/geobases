
========
GeoBases
========

Project
=======

All doc has been moved here for this package:
    http://mediawiki.orinet.nce.amadeus.net/index.php/GeoBases

To run the tests::
    find ./ -name '*pyc' -exec rm {} \;
    python test/test_GeoBases.py -v

To install the package::
    git clone git@gitorious.orinet.nce.amadeus.net:dataanalysis/geobases.git
    cd geobases
    python setup.py install --user

You may try to remove the package with pip::
    pip uninstall GeoBases

To create source distribution (pip-installable)::
    python setup.py sdist

To deploy source package on python packages repository::
    rake

If you install a package in user space, you may want to check
that your ~/.local/bin is in your $PATH, and that Python knows
where you site-package is (check your $PYTHONPATH).
This line should be added to your ~/.zshrc anyway::
    export PATH=$PATH:$HOME/.local/bin

Some precaution: if you are running debian/ubuntu, installation might
fail due to lack of compilation tool after fresh installation. If you have
an error like *Error: Python.h could not be found*, you can fix it with::
    sudo apt-get install python-dev g++


Quickstart
==========

After installation::

    >>> from GeoBases.GeoBaseModule import GeoBase
    >>> g = GeoBase(data='ori_por', verbose=False)

Then, to get information::

    >>> g.get('CDG', 'city_code')
    'PAR'
    >>> g.distance('ORY', 'CDG')
    34.87...


Note on packaging
=================

The MANIFEST.in file is used to determine
which files will be included in a source distribution.
package_data directive in setup.py file is about which 
file will be exported in site-package after installation.
So you really need both if you want to produce installable
packages like rpms or zip which can be installed afterwards.

The Rakefile and release.yaml are just script for Jenkins.

