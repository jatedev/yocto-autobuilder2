from buildbot.plugins import schedulers as sched
from buildbot.plugins import util
from yoctoabb import config

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
nowait = sched.Triggerable(name="nowait",
                           builderNames=config.trigger_builders_nowait)
schedulers.append(nowait)

schedulers.append(sched.ForceScheduler(
    name="nightly",
    builderNames=["nightly"],
    buttonName="Start Nightly Build",
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
            default="False")
    ]+repos_for_builder("nightly")))
