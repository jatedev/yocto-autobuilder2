#
# SPDX-License-Identifier: GPL-2.0-only
#

from twisted.internet import defer
from buildbot.process import buildstep
import json
import os

from yoctoabb import config


class WriteLayerInfo(buildstep.ShellMixin, buildstep.BuildStep):
    name = "WriteLayerInfo"

    def __init__(self, **kwargs):
        buildstep.BuildStep.__init__(self, **kwargs)

    def generateLayerInfo(self):
        layerinfo = {}
        writerepos = config.buildertorepos.get(self.getProperty("buildername"))
        if not writerepos:
            writerepos = config.buildertorepos["default"]

        for repo in writerepos:
            repodict = {}
            repodict["url"] = self.getProperty("repo_{}".format(repo))
            repodict["branch"] = self.getProperty("branch_{}".format(repo))
            repodict["revision"] = self.getProperty("commit_{}".format(repo))
            layerinfo[repo] = repodict

        return json.dumps(layerinfo, sort_keys=True, indent=4,
                          separators=(',', ': '))

    @defer.inlineCallbacks
    def run(self):
        repojson = self.generateLayerInfo()
        layerinfo = os.path.join(self.getProperty("builddir"),
                                 "layerinfo.json")
        writerepos = "printf '%s' >> %s" % (repojson, layerinfo)
        cmd = yield self.makeRemoteShellCommand(
            command=writerepos)
        yield self.runCommand(cmd)
        defer.returnValue(cmd.results())


@defer.inlineCallbacks
def run(self):
    cmd = RemoteCommand(args)
    log = yield self.addLog('output')
    cmd.useLog(log, closeWhenFinished=True)
    yield self.runCommand(cmd)
