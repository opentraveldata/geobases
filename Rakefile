
require 'yaml'
require 'pathname'

ROOT_PATH = File.expand_path File.dirname(__FILE__)
FILE_PATH = File.join ROOT_PATH, 'release.yaml'

# Read YAML configuration
File.open(FILE_PATH) { |f| YAML.load f }.each do |param, val|
  Object.const_set "#{param.upcase}", val
end

# Default values if not in configuration file
if not defined? ENVIRONMENT
    ENVIRONMENT = {}
end

if not defined? PYTHON
    PYTHON = '/usr/bin/python'
end

if not defined? VENV_PYTHON
    VENV_PYTHON = './bin/python'
end

if not defined? TEST_FILE
    TEST_FILE = nil
end

if not defined? PACKAGE_NAME
    PACKAGE_NAME = nil
end

if not defined? REPO_URL
    REPO_URL = nil
end


namespace :build do

  desc "Set environment variables"
  task :global_vars do
    # Define environment variables
    if not ENVIRONMENT.nil?
      ENVIRONMENT.each do |key, val|
        puts "'#{key}' set to '#{val}'"
        ENV[key] = val
      end
    end
  end

  desc "Clean virtualenv directories"
  task :venv_clean do
    %x[ rm -rf bin lib lib64 include ]
  end

  desc "Creating virtual environment"
  task :venv => [:global_vars, :venv_clean] do
    %x[ virtualenv --clear --no-site-packages -p #{PYTHON} . >&2 ]
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
    # Here we use stderr to display the output on Jenkins
    # stdout is captured
    %x[ #{VENV_PYTHON} setup.py develop >&2 ]
    raise "Dependencies failed" unless $?.success?
  end

  desc "Run test suite"
  task :test => [:deps, :activate] do
    if not TEST_FILE.nil? and not TEST_FILE.empty?
      %x[ #{VENV_PYTHON} #{TEST_FILE} -v >&2 ]
    end
    raise "Tests failed" unless $?.success?
  end

  desc "Clean building directories"
  task :clean do
    %x[ rm -rf build dist *.egg-info ]
  end

  desc "Build the package"
  task :package => [:clean, :test, :activate] do
    %x[ #{VENV_PYTHON} setup.py sdist >&2 ]
    raise "Packaging failed" unless $?.success?
  end

  desc "Publish the package"
  task :publish => :package do
    local_package=%x[ basename dist/*tar.gz ].strip
    if PACKAGE_NAME.nil?
        package_name=local_package
    else
        package_name=PACKAGE_NAME
    end
    package_url = "#{REPO_URL}/#{package_name}"
    %x[ nd -p dist/#{local_package} #{package_url} ]
    raise "Publishing failed" unless $?.success?
    puts "Package #{local_package} published to #{REPO_URL} as #{package_name}"
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
    %x[ #{VENV_PYTHON} setup.py install >&2 ]
    raise "Installation failed" unless $?.success?
  end

end

task :default => 'build:publish'
