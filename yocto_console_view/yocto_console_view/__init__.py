from buildbot.www.plugin import Application
from buildbot.schedulers.forcesched import ChoiceStringParameter

# create the interface for the setuptools entry point
ep = Application(__name__, "Yocto Console View UI")

class ReleaseSelector(ChoiceStringParameter):

    spec_attributes = ["selectors"]
    type = "releaseselector"
    selectors = None
