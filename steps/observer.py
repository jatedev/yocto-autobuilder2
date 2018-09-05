from twisted.python import log

from buildbot.process import logobserver
from buildbot.process.results import FAILURE
from buildbot.process.results import SKIPPED
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.steps.shell import ShellCommand

#
# Monitor the step 1-X logs and stdio, collecting up any warnings and errors seen
# and publish them at the end in their own 'logfile' for ease of access to the user
#
class RunConfigLogObserver(ShellCommand):

    warnOnWarnings = True
    warnOnFailure = True
    warnings = 0
    errors = 0

    def __init__(self, python=None, maxsteps=10, *args, **kwargs):
        ShellCommand.__init__(self, *args, **kwargs)
        self.python = python
        self.warningLines = []
        self.errorLines = []
        self.addLogObserver('stdio', logobserver.LineConsumerLogObserver(self.logConsumer))
        for i in range(1, maxsteps):
            for j in ['a', 'b', 'c', 'd']:
                self.addLogObserver('step' + str(i) + str(j), logobserver.LineConsumerLogObserver(self.logConsumer))

    def logConsumer(self):
        while True:
            stream, line = yield
            if line.startswith("WARNING:"):
                self.warnings += 1
                self.warningLines.append(line)
            if line.startswith("ERROR:"):
                self.errors += 1
                self.errorLines.append(line)

    def commandComplete(self, cmd):
        self.addCompleteLog('warnings', '\n'.join(self.warningLines))
        self.addCompleteLog('errors', '\n'.join(self.errorLines))

    def evaluateCommand(self, cmd):
        if cmd.didFail() or self.errors:
            return FAILURE
        if self.warnings:
            return WARNINGS
        return SUCCESS
