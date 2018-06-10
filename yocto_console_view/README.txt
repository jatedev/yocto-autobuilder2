This custom buildbot plugin does three things:

* Replaces the "Console View" with our own "Yocto Console View"
* Adds a yoctochangedetails element to customise the information we display about a build
  (link to the code repository, link to error reporting for the build)
* Add a custom field element, ReleaseSelector to the force build scheduler allowing 
  us to customise the form input fields to allow auto population of fields for 
  specific release branch combinations

The plugin ships in compiled form along with its source code. The generated files are:

yocto_console_view/static/*
yocto_console_view/VERSION

In order to build this plugin you need a buildbot development environment setup along
with its dependencies. FIXME, add more info on building.

