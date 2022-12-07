#
# SPDX-License-Identifier: GPL-2.0-only
#

from twisted.python import log

from buildbot.process import logobserver
from buildbot.process.results import FAILURE
from buildbot.process.results import SKIPPED
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.steps.shell import ShellCommand

from functools import partial

#
# Monitor the step 1-X logs and stdio, collecting up any warnings and errors seen
# and publish them at the end in their own 'logfile' for ease of access to the user
#
class SimpleLogObserver(ShellCommand):

    warnOnWarnings = True
    warnOnFailure = True
    warnings = 0
    errors = 0

    def __init__(self, maxsteps=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.warningLines = []
        self.errorLines = []
        if "description" in kwargs:
            self.description = kwargs["description"]
        else:
            self.description = "run-config"
        self.addLogObserver('stdio', logobserver.LineConsumerLogObserver(partial(self.logConsumer, 'stdio')))

    def describe(self, done=False):
        return self.description

    def logConsumer(self, logname):
        while True:
            stream, line = yield
            if line.startswith("WARNING:"):
                self.warnings += 1
                self.warningLines.append(logname + ": " + line)
            if line.startswith("ERROR:"):
                self.errors += 1
                self.errorLines.append(logname + ": " + line)

    def commandComplete(self, cmd):
        if self.warningLines:
            self.addCompleteLog('warnings', '\n'.join(self.warningLines))
        if self.errorLines:
            self.addCompleteLog('errors', '\n'.join(self.errorLines))

    def evaluateCommand(self, cmd):
        if cmd.didFail() or self.errors:
            return FAILURE
        if self.warnings:
            return WARNINGS
        return SUCCESS

class RunConfigLogObserver(SimpleLogObserver):

    def __init__(self, maxsteps=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, maxsteps):
            for j in ['a', 'b', 'c', 'd']:
                name = 'step' + str(i) + str(j)
                self.addLogObserver(name, logobserver.LineConsumerLogObserver(partial(self.logConsumer, name)))
