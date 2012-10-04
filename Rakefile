
RELEASE_REPO_URL="http://oridist.orinet.nce.amadeus.net/python/"

namespace :build do

  desc "Creating virtual environment"
  task :venv do
    puts "*"
    puts "* Creating virtual environment..."
    puts "*"
    %x[ virtualenv --clear --no-site-packages . ]
  end

  desc "Entering virtual environment"
  task :activate do
    puts "*"
    puts "* Activating..."
    puts "*"
    # backticks required here, because source or . 
    # are shell builtins and therefore not accessible with
    # which
    %x[ `. bin/activate` ]
  end

  desc "Exiting virtual environment"
  task :deactivate do
    %x[ deactivate ]
  end

  desc "Install Python module in a virtual environment"
  task :install => [:venv, :activate] do
    puts "*"
    puts "* Installation..."
    puts "*"
    # Here we use stderr to display the output
    # on Jenkins, stdout is not
    %x[ ./bin/python setup.py install >&2 ]
  end

  desc "Run test suite"
  task :test => [:install, :activate] do
    puts "*"
    puts "* Running tests..."
    puts "*"
    %x[ ./bin/python test/test_GeoBases.py -v ]
  end

  desc "Clean building directories"
  task :clean do
    puts "*"
    puts "* Cleaning..."
    puts "*"
    %x[ rm -rf build dist *.egg-info ]
  end

  desc "Build the package"
  task :package => [:clean, :test, :activate] do
    puts "*"
    puts "* Packaging..."
    puts "*"
    %x[ ./bin/python setup.py sdist ]
  end

  desc "Publish the package"
  task :publish => :package do
    package_name=%x[ basename dist/*tar.gz ].strip
    package_url = "#{RELEASE_REPO_URL}/#{package_name}"
    puts "*"
    puts "* Package #{package_name} published to #{RELEASE_REPO_URL}"
    puts "*"
    %x[ nd -p dist/#{package_name} #{package_url} ]
  end

end

task :default => 'build:publish'
