from buildbot.plugins import *

from yoctoabb import config
from yoctoabb.steps.writelayerinfo import WriteLayerInfo
from yoctoabb.steps.observer import RunConfigLogObserver
from datetime import datetime

import os
import json


builders = []
maxsteps = 9

# Environment to pass into the workers, e.g. to load further local configuration
# fragments
extra_env = {}
#extra_env = {"ABHELPER_JSON" : "config.json /home/pokybuild/config-local.json"}

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


def get_publish_internal(props, basename=False):
    """
    Calculate the location to which artefacts should be published and store it
    as a property for use by other workers.
    """
    dest = ""
    deploy = props.getProperty("deploy_artefacts", False)
    if deploy:
        rel_name = ""
        dest = props.getProperty("publish_destination", "")
        if dest:
            if basename:
                return os.path.basename(dest)
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
            dest_base = os.path.join(config.publish_dest,
                                     props.getProperty("buildername"),
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
        if basename:
            return os.path.basename(dest)
        return dest
    else:
        return ""

@util.renderer
def get_publish_dest(props):
    return get_publish_internal(props, basename=False)

@util.renderer
def get_publish_name(props):
    return get_publish_internal(props, basename=True)

@util.renderer
def ensure_props_set(props):
    """
    When the various properties aren't set (i.e. a single builder was force
    triggered instead of being triggered by the nightly) we need to ensure they
    correct defaults are set and passed to the helper scripts.
    """
    return {
        "sharedrepolocation": props.getProperty("sharedrepolocation", ""),
        "is_release": props.getProperty("is_release", False),
        "buildappsrcrev": props.getProperty("buildappsrcrev", ""),
        "deploy_artefacts": props.getProperty("deploy_artefacts", False),
        "publish_destination": props.getProperty("publish_destination", "")
    }

def get_buildlogs(maxsteps):
    logfiles = {}
    for i in range(1, maxsteps):
        for j in ['a', 'b', 'c', 'd']:
            logfiles["step" + str(i) + str(j)] = "build/command.log." + str(i) + str(j)
    return logfiles

def create_builder_factory():
    f = util.BuildFactory()

    # NOTE: Assumes that yocto-autobuilder repo has been cloned to home
    # directory of the user running buildbot.
    clob = os.path.expanduser("~/yocto-autobuilder-helper/janitor/clobberdir")
    f.addStep(steps.ShellCommand(
        command=[clob, util.Interpolate("%(prop:builddir)s/")],
        haltOnFailure=True,
        name="Clobber build dir"))
    f.addStep(steps.Git(
        repourl='git://git.yoctoproject.org/yocto-autobuilder-helper',
        workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
        mode='incremental',
        haltOnFailure=True,
        name='Fetch yocto-autobuilder-helper'))
    f.addStep(steps.SetProperties(properties=ensure_props_set))
    f.addStep(WriteLayerInfo(name='Write main layerinfo.json', haltOnFailure=True))
    f.addStep(steps.ShellCommand(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/shared-repo-unpack"),
                 util.Interpolate("%(prop:builddir)s/layerinfo.json"),
                 util.Interpolate("%(prop:builddir)s/build"),
                 util.Property("buildername"),
                 "-c", util.Interpolate("%(prop:sharedrepolocation)s"),
                 "-p", get_publish_dest],
        haltOnFailure=True,
        name="Unpack shared repositories"))

    f.addStep(steps.SetPropertyFromCommand(command=util.Interpolate("cd %(prop:sharedrepolocation)s/poky; git rev-parse HEAD"),
                                           property="yp_build_revision",
                                           haltOnFailure=True,
                                           name='Set build revision'))

    f.addStep(steps.SetPropertyFromCommand(command=util.Interpolate("cd %(prop:sharedrepolocation)s/poky; git rev-parse --abbrev-ref HEAD"),
                                           property="yp_build_branch",
                                           haltOnFailure=True,
                                           name='Set build branch'))

    f.addStep(RunConfigLogObserver(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-config"),
                 util.Property("buildername"),
                 util.Interpolate("%(prop:builddir)s/build/build"),
                 util.Interpolate("%(prop:branch_poky)s"),
                 util.Interpolate("%(prop:repo_poky)s"),
                 "-s", get_sstate_release_number,
                 "-b", util.Interpolate("%(prop:buildappsrcrev)s"),
                 "-p", get_publish_dest,
                 "-u", util.URLForBuild,
                 "-q"],
        name="run-config",
        logfiles=get_buildlogs(maxsteps),
        lazylogfiles=True,
        maxsteps=maxsteps,
        timeout=16200))  # default of 1200s/20min is too short, use 4.5hrs
    return f


# regular builders
f = create_builder_factory()
for builder in config.triggered_builders:
    workers = config.builder_to_workers.get(builder, None)
    if not workers:
        workers = config.builder_to_workers['default']
    builders.append(util.BuilderConfig(name=builder,
                                       workernames=workers,
                                       factory=f, env=extra_env))

factory = util.BuildFactory()
# NOTE: Assumes that yocto-autobuilder repo has been cloned to home
# directory of the user running buildbot.
clob = os.path.expanduser("~/yocto-autobuilder-helper/janitor/clobberdir")
factory.addStep(steps.ShellCommand(
                command=[clob, util.Interpolate("%(prop:builddir)s/")],
                haltOnFailure=True,
                name="Clobber build dir"))
# check out the source
factory.addStep(steps.Git(
    repourl='git://git.yoctoproject.org/yocto-autobuilder-helper',
    workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
    mode='incremental',
    haltOnFailure=True,
    name='Fetch yocto-autobuilder-helper'))
factory.addStep(WriteLayerInfo(name='Write main layerinfo.json', haltOnFailure=True))
factory.addStep(steps.ShellCommand(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/prepare-shared-repos"),
        util.Interpolate("%(prop:builddir)s/layerinfo.json"),
        util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
        "-p", get_publish_dest],
    haltOnFailure=True,
    name="Prepare shared repositories"))
factory.addStep(steps.SetProperty(
    property="sharedrepolocation",
    value=util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir))
))

# shared-repo-unpack
factory.addStep(steps.ShellCommand(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/shared-repo-unpack"),
        util.Interpolate("%(prop:builddir)s/layerinfo.json"),
        util.Interpolate("%(prop:builddir)s/build"),
        util.Property("buildername"),
        "-c", util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
        "-p", util.Property("is_release")],
    haltOnFailure=True,
    name="Unpack shared repositories"))

factory.addStep(steps.SetPropertyFromCommand(command=util.Interpolate("cd %(prop:sharedrepolocation)s/poky; git rev-parse HEAD"),
                                             property="yp_build_revision",
                                             haltOnFailure=True,
                                             name='Set build revision'))

factory.addStep(steps.SetPropertyFromCommand(command=util.Interpolate("cd %(prop:sharedrepolocation)s/poky; git rev-parse --abbrev-ref HEAD"),
                                             property="yp_build_branch",
                                             haltOnFailure=True,
                                             name='Set build branch'))

# run-config
factory.addStep(RunConfigLogObserver(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-config"),
        util.Property("buildername"),
        util.Interpolate("%(prop:builddir)s/build/build"),
        util.Interpolate("%(prop:branch_poky)s"),
        util.Interpolate("%(prop:repo_poky)s"),
        "-s", get_sstate_release_number,
        "-p", get_publish_dest,
        "-u", util.URLForBuild,
        "-q"],
    name="run-config",
    logfiles=get_buildlogs(maxsteps),
    lazylogfiles=True,
    maxsteps=maxsteps,
    timeout=16200))  # default of 1200s/20min is too short, use 4.5hrs

# trigger the buildsets contained in the nightly set
def get_props_set():
    set_props = {
        "sharedrepolocation": util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
        "is_release": util.Property("is_release"),
        "buildappsrcrev": "",
        "deploy_artefacts": util.Property("deploy_artefacts"),
        "publish_destination": util.Property("publish_destination"),
        "yocto_number": util.Property("yocto_number"),
        "milestone_number": util.Property("milestone_number"),
        "rc_number": util.Property("rc_number")
    }

    for repo in config.repos:
        set_props["branch_%s" % repo] = util.Property("branch_%s" % repo)
        set_props["commit_%s" % repo] = util.Property("commit_%s" % repo)
        set_props["repo_%s" % repo] = util.Property("repo_%s" % repo)
    set_props["yocto_number"] = util.Property("yocto_number")
    set_props["milestone_number"] = util.Property("milestone_number")
    set_props["rc_number"] = util.Property("rc_number")

    return set_props

factory.addStep(steps.Trigger(schedulerNames=['wait'],
                              waitForFinish=True,
                              set_properties=get_props_set()))

factory.addStep(steps.ShellCommand(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/send-qa-email"),
        util.Property("send_email"),
        util.Interpolate("%(prop:builddir)s/layerinfo.json"),
        util.Interpolate("%(prop:sharedrepolocation)s"),
        "-p", get_publish_dest,
        "-r", get_publish_name
        ],
    name="Send QA Email"))

builders.append(
    util.BuilderConfig(name="nightly",
                       workernames=config.workers,
                       factory=factory, env=extra_env))
