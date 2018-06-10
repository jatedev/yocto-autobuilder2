from buildbot.plugins import schedulers as sched
from buildbot.plugins import util
from yoctoabb import config

from yoctoabb.yocto_console_view.yocto_console_view import ReleaseSelector

schedulers = []


def create_repo_inputs(reponame):
    """
    Given the name of a repository in yoctoab.config's repo dict creates
    StringParameter inputs to allow specification of alternative uri, branch
    and commit/hash values
    """

    # TODO: formatting? Typically had branch & commit on same line?
    repo = util.StringParameter("repo_{}".format(reponame),
                                label="{} repository".format(reponame),
                                default=config.repos[reponame][0])
    branch = util.StringParameter("branch_{}".format(reponame),
                                  label="Branch",
                                  default=config.repos[reponame][1])
    commit = util.StringParameter("commit_{}".format(reponame),
                                  label="Tag/Commit hash",
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
        parameters = parameters + inputs
    return parameters


def props_for_builder(builder):
    """
    Generate an appropriate list of properties to use on a builder-specific
    scheduler
    """

    props = []
    if builder == 'build-appliance':
        props.append(util.StringParameter(
            name="buildappsrcrev",
            # TODO: is this statement still true?
            label="""Build appliance src revision. Use DEFAULT to take the
 srcrev currently in the recipe:""",
            default="None",
        ))
    if builder in ['build-appliance', 'buildtools']:
        props.append(util.ChoiceStringParameter(
            name="deploy_artifacts",
            label="Do we want to deploy artifacts? ",
            choices=["False", "True"],
            default="False"
        ))

    props = props + repos_for_builder(builder)
    return props


for builder in config.triggered_builders:
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

# nightly builder triggers various other builders
wait = sched.Triggerable(name="wait",
                         builderNames=config.trigger_builders_wait)
schedulers.append(wait)

schedulers.append(sched.ForceScheduler(
    name="nightly",
    builderNames=["nightly"],
    buttonName="Start Nightly Build",
    codebases = [util.CodebaseParameter(codebase='', label="yocto-autobuilder-helper:", project=None)],
    reason=util.StringParameter(
        name="reason",
        label="""Reason (please note the reason for triggering the build and
 any expectations for the build's outcome:""",
        required=False),
    properties=[
        util.ChoiceStringParameter(
            name="is_release",
            label="Generate a release?",
            choices=["False", "True"],
            default="False"),
        util.ChoiceStringParameter(
            name="poky_name",  # possibly unused?
            label="Name of the Poky release.",
            choices=config.releases,
            default=""),
        util.ChoiceStringParameter(
            name="is_milestone",
            label="Is the release a milestone release?",
            choices=["False", "True"],
            default="False"),
        util.StringParameter(
            name="poky_number",  # possibly unused?
            label="Poky Release Number (10.0.0, 11.0.1 etc.)"),
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
        util.ChoiceStringParameter(
            name="send_email",
            label="Send QA alert emails?",
            choices=["False", "True"],
            default="False"),
        util.ChoiceStringParameter(
            name="deploy_artifacts",
            label="Do we want to deploy artifacts? ",
            choices=["False", "True"],
            default="False"),
        ReleaseSelector(
        name="branch",
            label="Release Shortcut Selector",
            choices=["master", "rocko", "sumo", "pyro", "morty"],
            selectors={
              'master': {
                'branch_poky': 'master',
                'branch_bitbake': 'master',
                'branch_eclipse-poky-neon': 'neon-master',
                'branch_eclipse-poky-oxygen': 'oxygen-master',
                'branch_meta-gplv2': 'master',
                'branch_meta-intel': 'master',
                'branch_meta-mingw': 'master',
                'branch_meta-qt3': 'master',
                'branch_meta-qt4': 'master',
                'branch_oecore': 'master',
              },
              'sumo': {
                'branch_poky': 'sumo',
                'branch_bitbake': '1.38',
                'branch_eclipse-poky-neon': 'neon/sumo',
                'branch_eclipse-poky-oxygen': 'oxygen/sumo',
                'branch_meta-gplv2': 'sumo',
                'branch_meta-intel': 'sumo',
                'branch_meta-mingw': 'sumo',
                'branch_meta-qt3': 'sumo',
                'branch_meta-qt4': 'sumo',
                'branch_oecore': 'sumo',
              },
              'rocko': {
                'branch_poky': 'rocko',
                'branch_bitbake': '1.36',
                'branch_eclipse-poky-neon': 'neon/rocko',
                'branch_eclipse-poky-oxygen': 'oxygen/rocko',
                'branch_meta-gplv2': 'rocko',
                'branch_meta-intel': 'rocko',
                'branch_meta-mingw': 'rocko',
                'branch_meta-qt3': 'rocko',
                'branch_meta-qt4': 'rocko',
                'branch_oecore': 'rocko',
              },
              'pyro': {
                'branch_poky': 'pyro',
                'branch_bitbake': '1.34',
                'branch_eclipse-poky-neon': 'neon/pyro',
                'branch_eclipse-poky-oxygen': 'oxygen/pyro',
                'branch_meta-gplv2': 'pyro',
                'branch_meta-intel': 'pyro',
                'branch_meta-mingw': 'pyro',
                'branch_meta-qt3': 'pyro',
                'branch_meta-qt4': 'pyro',
                'branch_oecore': 'pyro',
              },
              'morty': {
                'branch_poky': 'morty',
                'branch_bitbake': '1.32',
                'branch_eclipse-poky-neon': 'neon/morty',
                'branch_eclipse-poky-oxygen': 'oxygen/morty',
                'branch_meta-gplv2': 'master',
                'branch_meta-intel': 'morty',
                'branch_meta-mingw': 'morty',
                'branch_meta-qt3': 'morty',
                'branch_meta-qt4': 'morty',
                'branch_oecore': 'morty',
              }
            })
               
    ]+repos_for_builder("nightly")))
