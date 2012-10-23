
========
GeoBases
========

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
    scp dist/GeoBases-0.3.0.tar.gz ori-data@nceorilnx04:/remote/oridata/www/pythonpackages/

To create rpm packages::
    rm -rf build dist *.egg-info
    python setup.py bdist_rpm

If you install a package in user space, you may want to check
that your ~/.local/bin is in your $PATH, and that Python knows
where you site-package is (check your $PYTHONPATH).
This line should be added to your ~/.zshrc anyway::
    export PATH=$PATH:$HOME/.local/bin

Some precaution: if you are running debian/ubuntu, installation might
fail due to lack of compilation tool after fresh installation. If you have
an error like *Error: Python.h could not be found*, you can fix it with::
    sudo apt-get install python-dev


===========
Source code
===========


The master repository for that data processing project is located
on the Ori private Gitorious platform:
    http://gitorious.orinet.nce.amadeus.net/dataanalysis/geobases

The default branch is 'trunk'.

Hence, in order to clone it, do something like:
    mkdir -p ~/dev/srh
    cd ~/dev/srh
    git clone git@gitorious.orinet.nce.amadeus.net:dataanalysis/geobases.git
    cd geobases
    git checkout trunk

The project is managed on the ORI Redmine platform:
    http://redmine.orinet.nce.amadeus.net/projects/geobases


=================
Note on packaging
=================

The MANIFEST.in file is used to determine
which files will be included in a source distribution.
package_data directive in setup.py file is about which 
file will be exported in site-package after installation.
So you really need both if you want to produce installable
packages like rpms or zip which can be installed afterwards.

The Rakefile and release.yaml are just script for Jenkins.


=============
Release notes
=============

+ 3.3 : opentrep integration in webservices
+ 3.2 : opentrep integration in GeoBaseModule
+ 3.1 : code cleanup with pylint
+ 3.0 : opentrep integration in Linux CLI
+ 2.0 : CLI completely refactored, filtering system
+ 1.0 : API changes: unification of grid and not grid methods

