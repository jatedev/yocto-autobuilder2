#
# SPDX-License-Identifier: GPL-2.0-only
#

from buildbot.plugins import *

from yoctoabb import config
from yoctoabb.steps.writelayerinfo import WriteLayerInfo
from yoctoabb.steps.runconfig import get_publish_dest, get_publish_resultdir, get_publish_name, RunConfigCheckSteps, TargetPresent
from buildbot.process.results import Results, SUCCESS, FAILURE, CANCELLED, WARNINGS, SKIPPED, EXCEPTION, RETRY

from twisted.python import log
from twisted.internet import defer

from datetime import datetime, timedelta
from dateutil.tz import tzutc

import os
import json
import random


builders = []

# Environment to pass into the workers, e.g. to load further local configuration
# fragments
extra_env = {}
if os.environ.get('ABHELPER_JSON'):
    extra_env['ABHELPER_JSON'] = os.environ['ABHELPER_JSON']

@util.renderer
def ensure_props_set(props):
    """
    When the various properties aren't set (i.e. a single builder was force
    triggered instead of being triggered by the nightly) we need to ensure they
    correct defaults are set and passed to the helper scripts.
    """
    return {
        "sharedrepolocation": props.getProperty("sharedrepolocation", ""),
        "swat_monitor": props.getProperty("swat_monitor", True),
        "build_type": props.getProperty("build_type", "quick"),
        "is_release": props.getProperty("is_release", False),
        "buildappsrcrev": props.getProperty("buildappsrcrev", ""),
        "deploy_artefacts": props.getProperty("deploy_artefacts", False),
        "publish_destination": props.getProperty("publish_destination", "")
    }

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
        repourl=config.repos["yocto-autobuilder-helper"][0],
        branch=config.repos["yocto-autobuilder-helper"][1],
        workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
        mode='incremental',
        haltOnFailure=True,
        name='Fetch yocto-autobuilder-helper'))
    f.addStep(TargetPresent())
    f.addStep(steps.SetProperties(properties=ensure_props_set))
    f.addStep(WriteLayerInfo(name='Write main layerinfo.json', haltOnFailure=True))
    f.addStep(steps.ShellCommand(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/shared-repo-unpack"),
                 util.Interpolate("%(prop:builddir)s/layerinfo.json"),
                 util.Interpolate("%(prop:builddir)s/build"),
                 util.Property("buildername"),
                 "-c", util.Interpolate("%(prop:sharedrepolocation)s"),
                 "--workername", util.Interpolate("%(prop:workername)s"),
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


    f.addStep(RunConfigCheckSteps(posttrigger=False))

    # If the build was successful, clean up the build directory
    f.addStep(steps.ShellCommand(
        command=[clob, util.Interpolate("%(prop:builddir)s/")],
        doStepIf=lambda step: step.build.results == SUCCESS,
        haltOnFailure=False,
        name="Clobber build dir"))

    return f

def nextWorker(bldr, workers, buildrequest):
    forced_worker = buildrequest.properties.getProperty("worker", "*")
    possible_workers = list(workers)

    # Old releases can only build on a subset of the workers, filter accordingly
    branch = None
    if '' in buildrequest.sources:
        # Has to be a better way to do this
        branch = buildrequest.sources[''].branch
    if branch and branch in config.workers_prev_releases:
        possible_workers = []
        for w in workers:
            if w.worker.workername.startswith(config.workers_prev_releases[branch]):
                possible_workers.append(w)
        log.msg("nextWorker: Limiting %s to workers %s for %s" % (str(bldr), str(possible_workers), branch))

    if forced_worker == "*":
        return random.choice(possible_workers) if possible_workers else None
    for w in possible_workers:
        if w.worker.workername == forced_worker:
            return w
    return None  # worker not yet available

# nextWorker above can block a request if there is no worker available.
# _getNextUnclaimedBuildRequest will always return the first request
# which then will always fail to find worker, and this will block the queue
# We therefore randomise the build requests queue with nextBuild to avoid
# blocking
def nextBuild(bldr, requests):
    return random.choice(requests) if requests else None

# regular builders
f = create_builder_factory()
for builder in config.subbuilders:
    workers = config.builder_to_workers.get(builder, None)
    if not workers:
        workers = config.builder_to_workers['default']
    builders.append(util.BuilderConfig(name=builder,
                                       workernames=workers, nextWorker=nextWorker, nextBuild=nextBuild,
                                       factory=f, env=extra_env))

# Prioritize assigning builders to available workers based on the length
# of the worker lists they are associated with. Builders that have fewer
# valid worker options should always be assigned first
# Add 2 seconds * length as the weight so tightly constrained builders go first
builder_bonuses = {}
for builder in config.builder_to_workers:
    bonus = (len(config.workers) - len(config.builder_to_workers)) * 2
    builder_bonuses[builder] = timedelta(seconds=bonus)

# Modified default algothirm from buildbot with a bonus mechanism (thanks tardyp!)
@defer.inlineCallbacks
def prioritizeBuilders(master, builders):
    # perform an asynchronous schwarzian transform, transforming None
    # into a really big date, so that any
    # date set to 'None' will appear at the
    # end of the list during comparisons.
    max_time = datetime.max
    # Need to set the timezone on the date, in order
    # to perform comparisons with other dates which
    # have the time zone set.
    max_time = max_time.replace(tzinfo=tzutc())

    @defer.inlineCallbacks
    def transform(bldr):
        time = yield bldr.getOldestRequestTime()
        if time is None:
            time = max_time
        else:
            if bldr.name in builder_bonuses:
                time = time + builder_bonuses[bldr.name]
        defer.returnValue((time, bldr))

    transformed = yield defer.gatherResults(
        [transform(bldr) for bldr in builders])

    # sort the transformed list synchronously, comparing None to the end of
    # the list
    def transformedKey(a):
        (date, builder) = a
        return (date, builder.name)

    transformed.sort(key=transformedKey)

    # and reverse the transform
    rv = [xf[1] for xf in transformed]
    return rv

def create_parent_builder_factory(buildername, waitname):
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
        repourl=config.repos["yocto-autobuilder-helper"][0],
        branch=config.repos["yocto-autobuilder-helper"][1],
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
    if buildername == "a-full":
        factory.addStep(steps.SetProperty(property="build_type", value="full"))
    else:
        factory.addStep(steps.SetProperty(property="build_type", value="quick"))

    # shared-repo-unpack
    factory.addStep(steps.ShellCommand(
        command=[
            util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/shared-repo-unpack"),
            util.Interpolate("%(prop:builddir)s/layerinfo.json"),
            util.Interpolate("%(prop:builddir)s/build"),
            util.Property("buildername"),
            "-c", util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
            "--workername", util.Interpolate("%(prop:workername)s"),
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
    factory.addStep(RunConfigCheckSteps(posttrigger=False))

    # trigger the buildsets contained in the nightly set
    # cascade yp_build_* since it makes the UI cleaner for skipped builds
    def get_props_set():
        set_props = {
            "sharedrepolocation": util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
            "is_release": util.Property("is_release"),
            "build_type": util.Property("build_type"),
            "buildappsrcrev": "",
            "deploy_artefacts": util.Property("deploy_artefacts"),
            "publish_destination": util.Property("publish_destination"),
            "yocto_number": util.Property("yocto_number"),
            "milestone_number": util.Property("milestone_number"),
            "rc_number": util.Property("rc_number"),
            "yp_build_revision": util.Property("yp_build_revision"),
            "yp_build_branch": util.Property("yp_build_branch")
        }

        for repo in config.buildertorepos[buildername]:
            set_props["branch_%s" % repo] = util.Property("branch_%s" % repo)
            set_props["commit_%s" % repo] = util.Property("commit_%s" % repo)
            set_props["repo_%s" % repo] = util.Property("repo_%s" % repo)
        set_props["yocto_number"] = util.Property("yocto_number")
        set_props["milestone_number"] = util.Property("milestone_number")
        set_props["rc_number"] = util.Property("rc_number")

        return set_props

    factory.addStep(steps.Trigger(schedulerNames=[waitname],
                                  waitForFinish=True,
                                  set_properties=get_props_set()))

    factory.addStep(RunConfigCheckSteps(posttrigger=True))

    factory.addStep(steps.ShellCommand(
        command=[
            util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/send-qa-email"),
            util.Property("send_email"),
            util.Interpolate("%(prop:builddir)s/layerinfo.json"),
            util.Interpolate("%(prop:sharedrepolocation)s"),
            "-p", get_publish_dest,
            "-r", get_publish_name,
            "-R", get_publish_resultdir
            ],
        name="Send QA Email"))


    factory.addStep(steps.ShellCommand(
                    command=["rm", "-fr", util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir))],
                    haltOnFailure=True,
                    name="Remove shared repo dir"))

    return factory

builders.append(util.BuilderConfig(name="a-quick", workernames=config.workers, factory=create_parent_builder_factory("a-quick", "wait-quick"), nextWorker=nextWorker, nextBuild=nextBuild, env=extra_env))
builders.append(util.BuilderConfig(name="a-full", workernames=config.workers, factory=create_parent_builder_factory("a-full", "wait-full"), nextWorker=nextWorker, nextBuild=nextBuild, env=extra_env))

def create_doc_builder_factory():
    f = util.BuildFactory()

    # NOTE: Assumes that yocto-autobuilder repo has been cloned to home
    # directory of the user running buildbot.
    clob = os.path.expanduser("~/yocto-autobuilder-helper/janitor/clobberdir")
    f.addStep(steps.ShellCommand(
        command=[clob, util.Interpolate("%(prop:builddir)s/")],
        haltOnFailure=True,
        name="Clobber build dir"))
    f.addStep(steps.Git(
        repourl=config.repos["yocto-autobuilder-helper"][0],
        branch=config.repos["yocto-autobuilder-helper"][1],
        workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
        mode='incremental',
        haltOnFailure=True,
        name='Fetch yocto-autobuilder-helper'))
    f.addStep(steps.Git(
        repourl=config.repos["yocto-docs"][0],
        branch=config.repos["yocto-docs"][1],
        workdir=util.Interpolate("%(prop:builddir)s/yocto-docs"),
        mode='incremental',
        haltOnFailure=True,
        name='Fetch yocto-docs'))
    f.addStep(steps.Git(
        repourl=config.repos["bitbake"][0],
        branch=config.repos["bitbake"][1],
        workdir=util.Interpolate("%(prop:builddir)s/bitbake"),
        mode='incremental',
        haltOnFailure=True,
        name='Fetch bitbake'))
    f.addStep(steps.ShellCommand(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-docs-build"),
                 util.Interpolate("%(prop:builddir)s"),
                 util.Interpolate("%(prop:builddir)s/yocto-docs"),
                 util.Interpolate("%(prop:builddir)s/bitbake")],
        haltOnFailure=True,
        name="Run documentation Build"))
    return f

# Only run one docs build at a time
docs_lock = util.MasterLock("docs_lock")
builders.append(util.BuilderConfig(name="docs", workernames=config.workers, factory=create_doc_builder_factory(), nextWorker=nextWorker, nextBuild=nextBuild, env=extra_env, locks=[docs_lock.access('exclusive')]))
