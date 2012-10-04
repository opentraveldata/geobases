
RELEASE_REPO_URL="http://oridist.orinet.nce.amadeus.net/python/"

namespace :build do

  desc "Creating virtual environment"
  task :venv do
    puts "Creating virtual environment..."
    %x[ virtualenv . ]
  end

  desc "Entering virtual environment"
  task :activate do
    %x[ . bin/activate ]
  end

  desc "Exiting virtual environment"
  task :deactivate do
    %x[ deactivate ]
  end

  desc "Install Python module in a virtual environment"
  task :install => [:venv, :activate] do
    puts "Installation..."
    puts %x[ ./bin/python setup.py install ]
  end

  desc "Run test suite"
  task :test => [:install, :activate] do
    puts "Running tests..."
    %x[ ./bin/python test/test_GeoBases.py -v ]
  end

  desc "Build the package"
  task :package => [:test, :activate] do
    puts "Packaging..."
    %x[ ./bin/python setup.py sdist ]
  end

  desc "Publish the package"
  task :publish => :package do
    package_name=%x[ basename dist/*tar.gz ].strip
    package_url = "#{RELEASE_REPO_URL}/#{package_name}"
    %x[ nd -p dist/#{package_name} #{package_url} ]
    puts "Package #{package_name} published to #{RELEASE_REPO_URL}"
  end

end

task :default => 'build:publish'
