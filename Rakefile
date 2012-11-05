
require 'yaml'
require 'pathname'

ROOT_PATH = File.expand_path File.dirname(__FILE__)

RELEASE_FILE_PATH = File.join ROOT_PATH, 'release.yaml'

# Read YAML configuration
File.open(RELEASE_FILE_PATH) { |f| YAML.load f }.each do |param, val|
  Object.const_set "RELEASE_#{param.upcase}", val
end


namespace :build do

  desc "Creating virtual environment"
  task :venv do
    %x[ virtualenv --clear --no-site-packages . >&2 ]
    raise "Virtualenv creation failed" unless $?.success?
  end

  desc "Entering virtual environment"
  task :activate do
    # backticks required here, because source or . 
    # are shell builtins and therefore not accessible with
    # which
    %x[ `. bin/activate` ]
  end

  desc "Exiting virtual environment"
  task :deactivate do
    %x[ deactivate ]
  end

  desc "Install dependencies in a virtual environment"
  task :deps => [:venv, :activate] do
    # Here we use stderr to display the output
    # on Jenkins, stdout is not
    %x[ ./bin/python setup.py develop >&2 ]
    raise "Dependencies failed" unless $?.success?
  end


  desc "Run test suite"
  task :test => [:deps, :activate] do
    if not RELEASE_TEST_FILE.nil? and not RELEASE_TEST_FILE.empty?
      %x[ ./bin/python #{RELEASE_TEST_FILE} -v ]
    end
    raise "Tests failed" unless $?.success?
  end

  desc "Clean building directories"
  task :clean do
    %x[ rm -rf build dist *.egg-info ]
  end

  desc "Build the package"
  task :package => [:clean, :test, :activate] do
    %x[ ./bin/python setup.py sdist >&2 ]
    raise "Packaging failed" unless $?.success?
  end

  desc "Publish the package"
  task :publish => :package do
    package_name=%x[ basename dist/*tar.gz ].strip
    package_url = "#{RELEASE_REPO_URL}/#{package_name}"
    %x[ nd -p dist/#{package_name} #{package_url} ]
    raise "Publishing failed" unless $?.success?
    puts "Package #{package_name} published to #{RELEASE_REPO_URL}"
  end

  desc "Create .deb"
  task :debian => [:clean, :test] do
    fpm_bin = %x[ env PATH=$PATH:$(gem env gemdir)/bin which fpm ].strip
    unless $?.success? && File.executable?(fpm_bin)
      raise "Failed to locate the FPM binary"
    end
    %x[ #{fpm_bin} -t deb -s python setup.py ]
  end

  desc "Install Python module in a virtual environment"
  task :install => [:venv, :activate] do
    %x[ ./bin/python setup.py install >&2 ]
    raise "Installation failed" unless $?.success?
  end

end

task :default => 'build:publish'
