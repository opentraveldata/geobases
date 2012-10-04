
RELEASE_REPO_URL="http://oridist.orinet.nce.amadeus.net/python/"

namespace :build do

  desc "Creating virtual environment"
  task :venv do
    $stderr.puts "*"
    $stderr.puts "* Creating virtual environment..."
    $stderr.puts "*"
    %x[ virtualenv --clear --no-site-packages . ]
    unless $?.success?
      raise "Virtualenv creation failed"
    end
  end

  desc "Entering virtual environment"
  task :activate do
    $stderr.puts "*"
    $stderr.puts "* Activating..."
    $stderr.puts "*"
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
    $stderr.puts "*"
    $stderr.puts "* Installation..."
    $stderr.puts "*"
    # Here we use stderr to display the output
    # on Jenkins, stdout is not
    %x[ ./bin/python setup.py install >&2 ]
    unless $?.success?
      raise "Installation failed"
    end
  end

  desc "Run test suite"
  task :test => [:install, :activate] do
    $stderr.puts "*"
    $stderr.puts "* Running tests..."
    $stderr.puts "*"
    %x[ ./bin/python test/test_GeoBases.py -v ]
    unless $?.success?
      raise "Tests failed"
    end
  end

  desc "Clean building directories"
  task :clean do
    $stderr.puts "*"
    $stderr.puts "* Cleaning..."
    $stderr.puts "*"
    %x[ rm -rf build dist *.egg-info ]
  end

  desc "Build the package"
  task :package => [:clean, :test, :activate] do
    $stderr.puts "*"
    $stderr.puts "* Packaging..."
    $stderr.puts "*"
    %x[ ./bin/python setup.py sdist ]
    unless $?.success?
      raise "Packaging failed"
    end
  end

  desc "Publish the package"
  task :publish => :package do
    package_name=%x[ basename dist/*tar.gz ].strip
    package_url = "#{RELEASE_REPO_URL}/#{package_name}"
    $stderr.puts "*"
    $stderr.puts "* Package #{package_name} published to #{RELEASE_REPO_URL}"
    $stderr.puts "*"
    %x[ nd -p dist/#{package_name} #{package_url} ]
  end

end

task :default => 'build:publish'
