# yoctoabb
Prototype of using yocto-autobuilder-helper from vanilla buildbot to replicate yocto-autobuilder configuration

## Introduction
The goal of this repository is to provide a buildbot configuration for use with
the yocto-autobuilder-helper[1] scripts which has as little code and as few
custom buildbot extensions as possible. The configuration merely collects
enough inputs from the user to furnish the yocto-autobuilder-helper scripts
with sufficient inputs to do their work.

The configuration was written for the latest (at time of writing) buildbot 1.0
release.

## Overview
The role of this buildbot configuration is simple, we want to provide
sufficient user-customisable parameters to trigger the yocto-autobuilder-helpers
build scripts.

Each builder, mapping to a named configuration in yocto-autobuilder-helper, is
created with steps and properties required to invoke the helper scripts in the
expected fashion.

We create custom schedulers for each builder with parameters configured on the
schedulers which can supply custom versions of the required values for the
yocto-autobuilder-helper script parameters.

### Code layout
- [builders.py](builders.py) -- configures the builders with minimal buildsteps to invoke the yocto-autobuilder-helper scripts
- lib/
  - [wiki.py](lib/wiki.py) -- implements some mediawiki related functionality as used by the wikilog plugin
reporters/
  - [wikilog.py](reporters/wikilog.py) -- our custom plugin to write info on build failures to a wiki page
- steps/
  - [writelayerinfo.py](steps/writelayerinfo.py) -- write the user supplied (or default) repos to a JSON file for use by the scripts
- [config.py](config.py) -- goal is to contain all values that might need changing to redeploy this code elsewhere. Goal hasn't yet been met.
- [master.cfg](master.cfg) -- calls into other scripts to do most configuration. Cluster specific config still lives here (i.e. controller url).
- [schedulers.py](schedulers.py) -- sets up the force schedulers with controls for modifying inputs for each builder.
- [services.py](services.py) -- configures irc, mail and wikilog reporters.
- [workers.py](workers.py) -- configures the worker objects
- [www.py](www.py) -- sets up the web UI

## Customisations
Whilst the goal is as little custom code as possible, there were some
customisations required both in order to support the yocto-autobuilder-helper
workflows and to replicate the workflows established with the outgoing
yocto-autobuilder[2].

### WriteLayerInfo buildstep
[steps/writelayerinfo.py](steps/writelayerinfo.py) -- implements a simple
custom buildset to iterate the repo_, branch_, and commit_ properties set by
the schedulers and write a JSON file with the user's values.

### WikiLog reporter
[reporters/wikilog.py](reporters/wikilog.py) -- a buildbot service to listen
for build failures and write some information on them to the configured wiki
page.

[lib/wiki.py](lib/wiki.py) -- some helper functions for the wiki plugin, much
of this code can be replaced by porting the plugin to be a
buildbot.util.service.HTTPClient implementation

## Deployment
The following deployment steps assume that the target system has a copy of
buildbot installed.

Various pieces of functionality _require_ that a copy of the
yocto-autobuilder-helper code be available in the home directory of the user
running buildbot at ~/yocto-autobuilder-helper.

__Note__: If using a reverse proxy be aware that modern buildbot uses a  websocket for various communications between the master and the web UI.
Refer to the buildbot documentation for information on how to correctly configure a reverse proxy: http://docs.buildbot.net/latest/manual/cfg-www.html#reverse-proxy-configuration

### Upstream Yocto Project autobuilder
#### on the controller_
```
$ buildbot create-master <yocto-controller>
$ cd <yocto-controller>
$ git clone https://git.yoctoproject.org/git/yocto-autobuilder2 yoctoabb
$ cd ..
$ ln -rs <yocto-controller>/yoctoabb/master.cfg <yocto-controller>/master.cfg
$ $EDITOR <yocto-controller>/yoctoabb/master.cfg
<modify c['buildbotURL']>
$ $EDITOR <yocto-controller>/yoctoabb/services.py
<Enable desired services, set appropriate configuration values>
$ $EDITOR <yocto-controller>/yoctoabb/www.py
<Configure and enable autorisation if desired>
$ $EDITOR <yocto-controller>/yoctoabb/config.py
<Modify configuration options such as worker configuration, etc.>
$ buildbot start <yocto-controller>
$ cd ..
## should be above <yocto-controller> location
git clone https://git.yoctoproject.org/git/yocto-autobuilder-helper
```

#### on the worker
```
$ buildbot-worker create-worker <yocto-worker> <localhost> <example-worker> <pass>
$ buildbot-worker start <yocto-worker>
```

NOTE: the 3rd parameter to create-worker, the worker name, need not be
hard-coded, for example pass `hostname` to use the host's configured name

### None upstream users
__TODO__: requires a custom config.json for yocto-autobuilder-helper

1. http://git.yoctoproject.org/clean/cgit.cgi/yocto-autobuilder-helper
2. http://git.yoctoproject.org/clean/cgit.cgi/yocto-autobuilder

## Contributions

Patches for this code should be sent to the yocto@lists.yoctoproject.org mailing list
with [yocto-autobuilder2] in the subject.
