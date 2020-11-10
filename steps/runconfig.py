from twisted.internet import defer
from buildbot.plugins import steps, util
from buildbot.process import buildstep
from buildbot.process.results import Results, SUCCESS, FAILURE, CANCELLED, WARNINGS, SKIPPED, EXCEPTION, RETRY

from yoctoabb.steps.observer import RunConfigLogObserver

import json
import datetime
import os
import sys

from yoctoabb import config

maxsteps = 9

def get_publish_internal(props):
    """
    Calculate the location to which artefacts should be published and store it
    as a property for use by other workers.
    """
    # Cache the value in the publish_detination property
    dest = props.getProperty("publish_destination", "")
    if dest:
        return dest

    if props.getProperty("is_release", False):
        milestone = props.getProperty("milestone_number", "")
        rc_number = props.getProperty("rc_number", "")
        snapshot = ""
        if milestone:
            snapshot += "_" + milestone
        if rc_number:
            snapshot += "." + rc_number

        rel_name = "yocto-" + props.getProperty("yocto_number", "") + snapshot
        dest = os.path.join(config.publish_dest, "releases", rel_name)
    else:
        dest_base = os.path.join(config.publish_dest, 'non-release',
                                 datetime.now().strftime("%Y%m%d"))

        # We want to make sure that we aren't writing artefacts to a publish
        # directory which already exists, therefore we keep a list of used
        # publish paths to prevent re-use. We store that in a JSON file.
        useddests = {}
        # NOTE: we make a strong assumption here that this code lives in a
        # directory which is an immediate child of the buildbot master's
        # working directory.
        basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..")
        persist = os.path.join(basedir, "pub_locations.json")
        if os.path.exists(persist):
            with open(persist) as f:
                useddests = json.load(f)

        rev = useddests.get(dest_base, "")
        if rev:  # incremenent and use
            rev = int(rev) + 1
        else:  # use the base path and store rev 0
            rev = 1
        dest = "%s-%s" % (dest_base, rev)
        # need to update the used destinations
        useddests[dest_base] = rev
        # save the info, overwriting the file if it exists
        with open(persist, 'w') as out:
            json.dump(useddests, out)

    # set the destination as a property to be inherited by workers, so that
    # all workers in a triggered set publish to the same location
    props.setProperty("publish_destination", dest,
                          "get_publish_dest")
    return dest

@util.renderer
def get_publish_dest(props):
    deploy = props.getProperty("deploy_artefacts", False)
    if not deploy:
        return ""
    return get_publish_internal(props)

@util.renderer
def get_publish_resultdir(props):
    return get_publish_internal(props) + "/testresults"

@util.renderer
def get_publish_name(props):
    dest = get_publish_internal(props)
    if dest:
        return os.path.basename(dest)
    return dest

@util.renderer
def get_sstate_release_number(props):
    """
    Uses the values submitted to the scheduler to determine the major number
    of the release for the purposes of publishing per-major release
    shared-state artefacts.
    """
    release_number = props.getProperty("yocto_number")
    if not release_number:
        return ""
    release_components = release_number.split('.', 3)
    return '.'.join(release_components).strip('.')

def get_runconfig_command(posttrigger=False):
    runconfig_command = [util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-config")]
    if posttrigger:
        runconfig_command.append(util.Interpolate("%(prop:buildername)s-posttrigger"))
    else:
        runconfig_command.append(util.Property("buildername"))
    runconfig_command.extend([ 
        util.Interpolate("%(prop:builddir)s/build/build"),
        util.Interpolate("%(prop:branch_poky)s"),
        util.Interpolate("%(prop:repo_poky)s"),
        "--sstateprefix", get_sstate_release_number,
        "--buildappsrcrev", util.Interpolate("%(prop:buildappsrcrev)s"),
        "--publish-dir", get_publish_dest,
        "--build-type", util.Interpolate("%(prop:build_type)s"),
        "--workername", util.Interpolate("%(prop:workername)s"),
        "--build-url", util.URLForBuild,
        "--results-dir", get_publish_resultdir,
        "--quietlogging"])
    return runconfig_command

def get_buildlogs(maxsteps):
    logfiles = {}
    for i in range(1, maxsteps):
        for j in ['a', 'b', 'c', 'd']:
            logfiles["step" + str(i) + str(j)] = "build/command.log." + str(i) + str(j)
    return logfiles

def get_runconfig_legacy_step(posttrigger):
    step = RunConfigLogObserver(
        command=get_runconfig_command(posttrigger),
        name="run-config",
        logfiles=get_buildlogs(maxsteps),
        lazylogfiles=True,
        maxsteps=maxsteps,
        timeout=16200)  # default of 1200s/20min is too short, use 4.5hrs
    return step

