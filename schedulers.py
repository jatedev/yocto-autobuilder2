#
# SPDX-License-Identifier: GPL-2.0-only
#

from buildbot.plugins import schedulers as sched
from buildbot.plugins import util
from yoctoabb import config

from twisted.internet import defer
from twisted.python import log

from yoctoabb.yocto_console_view.yocto_console_view import ReleaseSelector

schedulers = []

branchdefaults = {
    'master': {
        'branch': 'master',
        'branch_poky': 'master',
        'branch_bitbake': 'master',
        'branch_meta-arm': 'master',
        'branch_meta-aws': 'master',
        'branch_meta-gplv2': 'master',
        'branch_meta-intel': 'master',
        'branch_meta-mingw': 'master',
        'branch_meta-openembedded': 'master',
        'branch_oecore': 'master',
    },
    'master-next': {
        'branch': 'master',
        'branch_poky': 'master-next',
        'branch_bitbake': 'master-next',
        'branch_meta-arm': 'master',
        'branch_meta-aws': 'master',
        'branch_meta-gplv2': 'master',
        'branch_meta-intel': 'master',
        'branch_meta-mingw': 'master',
        'branch_meta-openembedded': 'master',
        'branch_oecore': 'master-next',
    },
    'mut': {
        'branch': 'master',
        'branch_poky': 'ross/mut',
        'repo_poky': 'git://git.yoctoproject.org/poky-contrib',
        'branch_bitbake': 'master',
        'branch_meta-arm': 'master',
        'branch_meta-aws': 'master',
        'branch_meta-gplv2': 'master',
        'branch_meta-intel': 'master',
        'branch_meta-mingw': 'master',
        'branch_meta-openembedded': 'master',
        'branch_oecore': 'master',
    },
    'honister': {
        'branch': 'honister',
        'branch_poky': 'honister',
        'branch_bitbake': '1.52',
        'branch_meta-arm': 'honister',
        'branch_meta-aws': 'honister',
        'branch_meta-gplv2': 'honister',
        'branch_meta-intel': 'honister',
        'branch_meta-mingw': 'honister',
        'branch_meta-openembedded': 'honister',
        'branch_oecore': 'honister',
    },
    'hardknott': {
        'branch': 'hardknott',
        'branch_poky': 'hardknott',
        'branch_bitbake': '1.50',
        'branch_meta-arm': 'hardknott',
        'branch_meta-aws': 'hardknott',
        'branch_meta-gplv2': 'hardknott',
        'branch_meta-intel': 'hardknott',
        'branch_meta-mingw': 'hardknott',
        'branch_meta-openembedded': 'hardknott',
        'branch_oecore': 'hardknott',
    },
    'gatesgarth': {
        'branch': 'gatesgarth',
        'branch_poky': 'gatesgarth',
        'branch_bitbake': '1.48',
        'branch_meta-arm': 'gatesgarth',
        'branch_meta-aws': 'gatesgarth',
        'branch_meta-gplv2': 'gatesgarth',
        'branch_meta-intel': 'gatesgarth',
        'branch_meta-mingw': 'gatesgarth',
        'branch_meta-openembedded': 'gatesgarth',
        'branch_oecore': 'gatesgarth',
    },
    'dunfell': {
        'branch': 'dunfell',
        'branch_poky': 'dunfell',
        'branch_bitbake': '1.46',
        'branch_meta-arm': 'dunfell',
        'branch_meta-aws': 'dunfell',
        'branch_meta-gplv2': 'dunfell',
        'branch_meta-intel': 'dunfell',
        'branch_meta-mingw': 'dunfell',
        'branch_meta-openembedded': 'dunfell',
        'branch_oecore': 'dunfell',
    },
    'zeus': {
        'branch': 'zeus',
        'branch_poky': 'zeus',
        'branch_bitbake': '1.44',
        'branch_meta-gplv2': 'zeus',
        'branch_meta-intel': 'zeus',
        'branch_meta-mingw': 'zeus',
        'branch_oecore': 'zeus',
    },
    'warrior': {
        'branch': 'warrior',
        'branch_poky': 'warrior',
        'branch_bitbake': '1.42',
        'branch_meta-gplv2': 'warrior',
        'branch_meta-intel': 'warrior',
        'branch_meta-mingw': 'warrior',
        'branch_oecore': 'warrior',
    },
    'thud': {
        'branch': 'thud',
        'branch_poky': 'thud',
        'branch_bitbake': '1.40',
        'branch_meta-gplv2': 'thud',
        'branch_meta-intel': 'thud',
        'branch_meta-mingw': 'thud',
        'branch_oecore': 'thud',
    },
    'sumo': {
        'branch': 'sumo',
        'branch_poky': 'sumo',
        'branch_bitbake': '1.38',
        'branch_meta-gplv2': 'sumo',
        'branch_meta-intel': 'sumo',
        'branch_meta-mingw': 'sumo',
        'branch_oecore': 'sumo',
    },
    'rocko': {
        'branch': 'rocko',
        'branch_poky': 'rocko',
        'branch_bitbake': '1.36',
        'branch_meta-gplv2': 'rocko',
        'branch_meta-intel': 'rocko',
        'branch_meta-mingw': 'rocko',
        'branch_oecore': 'rocko',
    },
    'pyro': {
        'branch': 'pyro',
        'branch_poky': 'pyro',
        'branch_bitbake': '1.34',
        'branch_meta-gplv2': 'pyro',
        'branch_meta-intel': 'pyro',
        'branch_meta-mingw': 'pyro',
        'branch_oecore': 'pyro',
    },
    'morty': {
        'branch': 'morty',
        'branch_poky': 'morty',
        'branch_bitbake': '1.32',
        'branch_meta-gplv2': 'master',
        'branch_meta-intel': 'morty',
        'branch_meta-mingw': 'morty',
        'branch_oecore': 'morty',
    }
}

def create_repo_inputs(reponame):
    """
    Given the name of a repository in yoctoab.config's repo dict creates
    StringParameter inputs to allow specification of alternative uri, branch
    and commit/hash values
    """

    repo = util.StringParameter("repo_{}".format(reponame),
                                label="Repository:",
                                default=config.repos[reponame][0])
    branch = util.StringParameter("branch_{}".format(reponame),
                                  label="Branch:",
                                  default=config.repos[reponame][1])
    commit = util.StringParameter("commit_{}".format(reponame),
                                  label="Revision:",
                                  default="HEAD")
    return [repo, branch, commit]


def repos_for_builder(buildername):
    """
    Returns a list of additional properties for a scheduler, a list of
    StringParameter allowing all of the repositories used by the
    builder/scheduler to be customised
    """

    parameters = []
    repos = config.buildertorepos.get(buildername)
    if not repos:
        repos = config.buildertorepos["default"]
    for repo in repos:
        inputs = create_repo_inputs(repo)
        parameters = parameters + [util.NestedParameter(name='', label=repo, fields=inputs, columns=2)]
    return parameters

def parent_default_props(buildername, branchname=None):
    props = {}
    props["swat_monitor"] = True
    repos = config.buildertorepos.get(buildername)
    if not repos:
        repos = config.buildertorepos["default"]
    if branchname:
        props['branch'] = branchname
    for repo in repos:
        props["repo_{}".format(repo)] = config.repos[repo][0]
        branchkey = "branch_{}".format(repo)
        if branchname and branchname in branchdefaults and branchkey in branchdefaults[branchname]:
            props[branchkey] = branchdefaults[branchname][branchkey]
        else:
            props[branchkey] = config.repos[repo][1]
        config.repos[repo][1]
        props["commit_{}".format(repo)] = "HEAD"
    return props

def buildappsrcrev_param():
    return util.StringParameter(
            name="buildappsrcrev",
            label="""Build appliance source revision to use. "None" means default to the srcrev currently in the recipe, use "AUTOREV" to use latest revision or specify a revision to use:""",
            default="AUTOREV")

def props_for_builder(builder):
    """
    Generate an appropriate list of properties to use on a builder-specific
    scheduler
    """

    swat_default = True
    if builder in ['auh', 'meta-oe']:
        swat_default = False

    props = []
    props.append(util.BooleanParameter(
        name="swat_monitor",
        label="Should SWAT monitor this build?",
        default=swat_default))
    if builder == 'build-appliance':
        props.append(buildappsrcrev_param())
    if builder in ['build-appliance', 'buildtools', 'eclipse-plugin-neon', 'eclipse-plugin-oxygen']:
        props.append(util.BooleanParameter(
            name="deploy_artefacts",
            label="Do we want to deploy artefacts? ",
            default=False
        ))
    props = props + repos_for_builder(builder)
    worker_list = config.builder_to_workers.get(builder, config.builder_to_workers['default'])
    props.append(util.ChoiceStringParameter(name="worker",
                              label="Worker to run the build on",
                              default="*",
                              multiple=False,
                              strict=True,
                              choices=worker_list + ["*"]))
    return props


for builder in config.subbuilders:
    schedulers.append(sched.ForceScheduler(
        name=builder,
        builderNames=[builder],
        reason=util.StringParameter(
                name="reason",
                label="""Reason (please note the reason for triggering the
 build and any expectations for the build's outcome:""",
                required=False),
        properties=props_for_builder(builder),
        buttonName="Force Build"))

@util.renderer
def builderNamesFromConfigQuick(props):
    #log.msg("builderNames: Sourcestamp %s, props %s" % (str(props.sourcestamps), str(props)))
    yp_branch = props.sourcestamps[0]['branch']

    builders = config.trigger_builders_wait_quick
    for b in config.trigger_builders_wait_quick_releases:
        if yp_branch and yp_branch.startswith(b):
            log.msg("builderNames: Filtering branch %s due to entry %s" % (str(yp_branch), str(b)))
            builders = config.trigger_builders_wait_quick_releases[b]

    return builders

@util.renderer
def builderNamesFromConfigFull(props):
    #log.msg("builderNames: Sourcestamp %s, props %s" % (str(props.sourcestamps), str(props)))
    yp_branch = props.sourcestamps[0]['branch']

    builders = config.trigger_builders_wait_full
    for b in config.trigger_builders_wait_full_releases:
        if yp_branch and yp_branch.startswith(b):
            log.msg("builderNames: Filtering branch %s due to entry %s" % (str(yp_branch), str(b)))
            builders = config.trigger_builders_wait_full_releases[b]

    # Only run performance runs on release builds
    if props.getProperty("is_release", False):
        builders = builders + config.trigger_builders_wait_perf

    return builders

# Upstream Triggerable class will rasise NotImplementedError() which will mean triggers abort upon reconfig
# Hack to intercept and ignore this, we'd rather they just survive in our case.
class ourTriggerable(sched.Triggerable):
    def reconfigService(self, name=None, *args, **kwargs):
        return

# nightly builder triggers various other builders
wait_quick = ourTriggerable(name="wait-quick",
                         builderNames=builderNamesFromConfigQuick)
schedulers.append(wait_quick)
wait_full = ourTriggerable(name="wait-full",
                         builderNames=builderNamesFromConfigFull)
schedulers.append(wait_full)

def parent_scheduler(target):
    return sched.ForceScheduler(
    name=target,
    builderNames=[target],
    buttonName="Start " + target + " Build",
    codebases = [util.CodebaseParameter(codebase='', label="yocto-autobuilder-helper:", project=None)],
    reason=util.StringParameter(
        name="reason",
        label="""Reason (please note the reason for triggering the build and
 any expectations for the build's outcome:""",
        required=False),
    properties=[
        ReleaseSelector(
            name="branchselector",
            default="master",
            label="Release Shortcut Selector",
            choices=["master", "master-next", "mut", "honister", "hardknott", "gatesgarth", "dunfell", "zeus", "warrior", "thud", "sumo", "rocko", "pyro", "morty"],
            selectors=branchdefaults),
        util.BooleanParameter(
            name="swat_monitor",
            label="Should SWAT monitor this build?",
            default=True),
        buildappsrcrev_param(),
        util.BooleanParameter(
            name="is_release",
            label="Generate a release?",
            default=False),
        util.StringParameter(
            name="yocto_number",  # used to form publish path
            label="Yocto Project Release Number (1.5, 1.6 etc.)"),
        util.ChoiceStringParameter(
            name="milestone_number",
            label="Milestone number",
            choices=["", "M1", "M2", "M3", "M4"],
            default=""
        ),
        util.ChoiceStringParameter(
            name="rc_number",
            label="Release candidate number",
            choices=["", "rc1", "rc2", "rc3", "rc4", "rc5", "rc6", "rc7",
                     "rc8", "rc9"],
            default=""),
        util.BooleanParameter(
            name="send_email",
            label="Send QA alert emails?",
            default=False),
        util.BooleanParameter(
            name="deploy_artefacts",
            label="Do we want to save build output? ",
            default=False)
    ]+repos_for_builder(target))

schedulers.append(parent_scheduler("a-quick"))
schedulers.append(parent_scheduler("a-full"))


schedulers.append(sched.ForceScheduler(
        name="docs",
        builderNames=["docs"],
        reason=util.StringParameter(
                name="reason",
                label="""Reason (please note the reason for triggering the docs build:""",
                required=False),
        properties=props_for_builder("docs"),
        buttonName="Force Build"))


# Run a-quick at 1am each day Mon-Sat so we keep master tested and up to date in sstate and buildhistory
schedulers.append(sched.Nightly(name='nightly-quick', branch='master', properties=parent_default_props('a-quick'),
                  builderNames=['a-quick'], hour=1, minute=0, dayOfWeek=[0,1,2,3,4,5]))
# Run a-full at 1am Sun each Week
schedulers.append(sched.Nightly(name='nightly-full', branch='master', properties=parent_default_props('a-full'),
                  builderNames=['a-full'], hour=1, minute=0, dayOfWeek=6))

# Run check-layer-nightly each day for master
schedulers.append(sched.Nightly(name='nightly-check-layer', branch='master', properties=parent_default_props('check-layer-nightly'),
                  builderNames=['check-layer-nightly'], hour=0, minute=0))

# Run check-layer-nightly twice a week for honister
schedulers.append(sched.Nightly(name='nightly-check-layer-honister', properties=parent_default_props('check-layer-nightly', 'honister'),
                  builderNames=['check-layer-nightly'], dayOfWeek=[2, 5], hour=2, minute=0, codebases = {'' : {'branch' : 'honister'}}))

# Run check-layer-nightly twice a week for hardknott
schedulers.append(sched.Nightly(name='nightly-check-layer-hardknott', properties=parent_default_props('check-layer-nightly', 'hardknott'),
                  builderNames=['check-layer-nightly'], dayOfWeek=[0, 3], hour=2, minute=0, codebases = {'' : {'branch' : 'hardknott'}}))

# Run check-layer-nightly twice a week for dunfell
schedulers.append(sched.Nightly(name='nightly-check-layer-dunfell', properties=parent_default_props('check-layer-nightly', 'dunfell'),
                  builderNames=['check-layer-nightly'], dayOfWeek=[1, 4], hour=2, minute=0, codebases = {'' : {'branch' : 'dunfell'}}))

# Run the build performance tests at 3am, 9am, 3pm and 9pm
schedulers.append(sched.Nightly(name='nightly-buildperf-ubuntu1604', branch='master', properties=parent_default_props('buildperf-ubuntu1604'),
                  builderNames=['buildperf-ubuntu1604'], hour=[3,9,15,21], minute=0))
schedulers.append(sched.Nightly(name='nightly-buildperf-centos7', branch='master', properties=parent_default_props('buildperf-centos7'),
                  builderNames=['buildperf-centos7'], hour=[3,9,15,21], minute=0))

# Run the AUH every Sunday
schedulers.append(sched.Nightly(name='nightly-auh', branch='master', properties=parent_default_props('auh'),
                  builderNames=['auh'], dayOfWeek=6, hour=5, minute=0))

# If any of our sphinx docs branches change, trigger a build
schedulers.append(sched.AnyBranchScheduler(name="yocto-docs-changed",
            change_filter=util.ChangeFilter(project=["yocto-docs"], branch=[None, "master", "master-next", "honister", "hardknott", "gatesgarth", "dunfell", "transition"]),
            codebases = ['', 'yocto-docs', 'bitbake'],
            treeStableTimer=60,
            builderNames=["docs"]))

# If bitbake's sphinx docs change, trigger a build
def isbitbakeDocFile(change):
    for f in change.files:
        if "doc/" in f:
            return True
    return False
schedulers.append(sched.AnyBranchScheduler(name="bitbake-docs-changed",
            change_filter=util.ChangeFilter(project=["bitbake"], branch=["master", "1.52", "1.50", "1.48", "1.46"]),
            codebases = ['', 'yocto-docs', 'bitbake'],
            fileIsImportant=isbitbakeDocFile,
            onlyImportant=True,
            treeStableTimer=60,
            builderNames=["docs"]))
