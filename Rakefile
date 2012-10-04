
RELEASE_REPO_URL="http://oridist.orinet.nce.amadeus.net/python/"

namespace :build do

  desc "Install Python module in a virtual environment"
  task :install do
    puts "Installation..."
    %x[ virtualenv . ]
    %x[ . bin/activate ]
    %x[ ./bin/python setup.py install ]
  end

  desc "Run test suite"
  task :test => :install do
    puts "Running tests..."
    %x[ ./bin/python test/test_GeoBases.py -v ]
  end

  desc "Build the package"
  task :package => [:install, :test] do
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

task :default => 'build:package'
