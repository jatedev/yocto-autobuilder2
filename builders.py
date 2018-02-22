from buildbot.plugins import *

from yoctoabb import config
from yoctoabb.steps.writelayerinfo import WriteLayerInfo

import os


builders = []


def get_sstate_release_number():
    # TODO: implement
    # release_number = util.Interpolate("%(prop:yocto_number)s")
    # if not release_number:
    #     return ""
    # release_components = release_number.split('.', 3)
    # return '.'.join(release_components).strip('.')
    return "None"


def get_publish_dest():
    # if deploy_artifacts property is False return None
    return "None"  # FIXME: based on SetDest?


@util.renderer
def ensure_props_set(props):
    """
    When the various properties aren't set (i.e. a single builder was force
    triggered instead of being triggered by the nightly) we need to ensure they
    correct defaults are set and passed to the helper scripts.
    """
    return {
        "sharedrepolocation": props.getProperty("sharedrepolocation", "None"),
        "is_release": props.getProperty("is_release", "None"),
        "buildappsrcrev": props.getProperty("buildappsrcrev", "None")
    }


def create_builder_factory():
    f = util.BuildFactory()

    # FIXME: use RP's script
    f.addStep(steps.ShellCommand(
        command=["rm", "-fr", util.Interpolate("%(prop:builddir)s/")],
        name="Clobber build dir"))
    f.addStep(steps.Git(
        repourl='git://git.yoctoproject.org/yocto-autobuilder-helper',
        workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
        mode='incremental',
        name='Fetch yocto-autobuilder-helper'))
    f.addStep(steps.SetProperties(properties=ensure_props_set))
    f.addStep(WriteLayerInfo(name='Write main layerinfo.json'))
    f.addStep(steps.ShellCommand(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/shared-repo-unpack"),
                 util.Interpolate("%(prop:builddir)s/layerinfo.json"),
                 util.Interpolate("%(prop:sharedrepolocation)s"),
                 util.Interpolate("%(prop:builddir)s/build"),
                 util.Property("buildername"),
                 util.Property("is_release")],
        name="Unpack shared repositories"))
    f.addStep(steps.ShellCommand(
        command=[util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-config"),
                 util.Property("buildername"),
                 util.Interpolate("%(prop:builddir)s/build/build"),
                 util.Interpolate("%(prop:branch_poky)s"),
                 util.Interpolate("%(prop:repo_poky)s"),
                 get_sstate_release_number(),
                 util.Interpolate("%(prop:buildappsrcrev)s"),
                 get_publish_dest(),
                 util.URLForBuild],
        name="run-config"))
    return f


# regular builders
f = create_builder_factory()
for builder in config.triggered_builders:
    workers = config.builder_to_workers.get(builder, None)
    if not workers:
        workers = config.builder_to_workers['default']
    builders.append(util.BuilderConfig(name=builder,
                                       workernames=workers,
                                       factory=f))

factory = util.BuildFactory()
# FIXME: use RP's script
factory.addStep(steps.ShellCommand(
    command=["rm", "-fr", util.Interpolate("%(prop:builddir)s/")],
    name="Clobber build dir"))
# check out the source
factory.addStep(steps.Git(
    repourl='git://git.yoctoproject.org/yocto-autobuilder-helper',
    workdir=util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper"),
    mode='incremental',
    name='Fetch yocto-autobuilder-helper'))
factory.addStep(WriteLayerInfo(name='Write main layerinfo.json'))
factory.addStep(steps.ShellCommand(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/prepare-shared-repos"),
        util.Interpolate("%(prop:builddir)s/layerinfo.json"),
        util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
        config.publish_dest],
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
        util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
        util.Interpolate("%(prop:builddir)s/build"),
        util.Property("buildername"),
        util.Property("is_release")],
    name="Unpack shared repositories"))

# run-config
factory.addStep(steps.ShellCommand(
    command=[
        util.Interpolate("%(prop:builddir)s/yocto-autobuilder-helper/scripts/run-config"),
        util.Property("buildername"),
        util.Interpolate("%(prop:builddir)s/build/build"),
        util.Interpolate("%(prop:branch_poky)s"),
        util.Interpolate("%(prop:repo_poky)s"),
        get_sstate_release_number(),
        "None",
        get_publish_dest(),
        util.URLForBuild],
    name="run-config"))

# trigger the buildsets contained in the nightly set
set_props = {
    "sharedrepolocation": util.Interpolate("{}/%(prop:buildername)s-%(prop:buildnumber)s".format(config.sharedrepodir)),
    "is_release": util.Property("is_release"),
    "buildappsrcrev": "None",
    "branch_poky": util.Property("branch_poky"),
    "commit_poky": util.Property("commit_poky"),
    "repo_poky": util.Property("repo_poky")
}
factory.addStep(steps.Trigger(schedulerNames=['nowait'],
                              waitForFinish=False,
                              set_properties=set_props))
factory.addStep(steps.Trigger(schedulerNames=['wait'],
                              waitForFinish=True,
                              set_properties=set_props))

# selftest
factory.addStep(steps.ShellCommand(
    command=". ./oe-init-build-env; bitbake-selftest",
    workdir=util.Interpolate("%(prop:builddir)s/build")
))

# TODO: trigger buildhistory_nowait - possibly no longer required?

# TODO: send QA mail if a release - compose and pass to sendmail command?

# TODO: update Current Link if published

builders.append(
    util.BuilderConfig(name="nightly",
                       workernames=config.workers,
                       factory=factory))
