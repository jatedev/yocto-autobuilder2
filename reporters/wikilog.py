from buildbot.reporters import utils
from buildbot.util import service
from twisted.internet import defer
from twisted.python import log
from buildbot.process.results import SUCCESS

from yoctoabb.lib.wiki import YPWiki

import time
import pprint
import re

class WikiLog(service.BuildbotService):
    name = "WikiLog"
    wiki = None
    # wantPreviousBuilds wantLogs
    neededDetails = dict(wantProperties=True, wantSteps=True)

    def checkConfig(self, wiki_uri, wiki_un, wiki_pass, wiki_page,
                    identifier=None, **kwargs):
        service.BuildbotService.checkConfig(self)

    @defer.inlineCallbacks
    def reconfigService(self, wiki_uri, wiki_un, wiki_pass, wiki_page,
                        identifier=None, **kwargs):
        yield service.BuildbotService.reconfigService(self)
        self.wiki_page = wiki_page
        self.identifier = None
        self.idstring = ""
        if identifier:
            self.identifier = identifier.replace(" ", "-")
            self.idstring = " on " + self.identifier
        self.wiki = YPWiki(wiki_uri, wiki_un, wiki_pass)

    @defer.inlineCallbacks
    def startService(self):
        yield service.BuildbotService.startService(self)

        startConsuming = self.master.mq.startConsuming
        self._buildCompleteConsumer = yield startConsuming(
            self.buildFinished,
            ('builds', None, 'finished'))

        self._buildStartedConsumer = yield startConsuming(
            self.buildStarted,
            ('builds', None, 'new'))

    def stopService(self):
        self._buildCompleteConsumer.stopConsuming()
        self._buildStartedConsumer.stopConsuming()

    @defer.inlineCallbacks
    def buildStarted(self, key, build):
        yield utils.getDetailsForBuild(self.master, build, **self.neededDetails)
        #log.err("wkl: buildStarted %s %s" % (key, pprint.pformat(build)))

        # Only place initial entries in the wiki for builds with no parents
        if not build['buildset']['parent_buildid']:
            if not self.logBuild(build):
                log.err("wkl: Failed to log build %s on %s" % (
                    build['buildid'], build['builder']['name']))

    # Assume we only have a parent, doesn't handle builds nested more than one level.
    @defer.inlineCallbacks
    def buildFinished(self, key, build):
        yield utils.getDetailsForBuild(self.master, build, **self.neededDetails)
        #log.err("wkl: buildFinished %s %s" % (key, pprint.pformat(build)))

        parent = None
        if build['buildset']['parent_buildid']:
            parent = yield self.master.data.get(("builds", build['buildset']['parent_buildid']))
            yield utils.getDetailsForBuild(self.master, parent, **self.neededDetails)

        if not self.updateBuild(build, parent):
            log.err("wkl: Failed to update wikilog with build %s failure" %
                    build['buildid'])

    def logBuild(self, build):
        """
        Extract information about 'build' and post an entry to the wiki

        @type   build:  buildbot.status.build.BuildStatus
        """

        log.err("wkl: logbuild %s" % (build))

        builder = build['builder']['name']
        reason = "No reason given"
        if 'reason' in build['properties'] and build['properties']['reason'][0]:
            reason = build['properties']['reason'][0]
        buildid = build['buildid']
        start = build['started_at']
        url = build['url']
        buildbranch = build['properties']['branch_poky'][0]

        chash = build['properties']['commit_poky'][0]
        if not chash or len(chash) < 1 or chash == "HEAD":
            chash = "YP_CHASH"

        forcedby = "Unknown"
        if 'owner' in build['properties']:
            forcedby = build['properties']['owner'][0]
        starttime = start.ctime()

        sectionfmt = '==[{} {} {} - {} {}{}]=='
        section_title = sectionfmt.format(url, builder, buildid, buildbranch, chash, self.idstring)
        summaryfmt = 'Adding new BuildLog entry for build %s (%s)'
        summary = summaryfmt % (buildid, chash)
        summary = summary + self.idstring
        content = "* '''Build ID''' - %s" % chash
        content = content + self.idstring
        content = content + '\n* Started at: %s\n' % starttime
        content = content + '* ' + forcedby + '\n* ' + reason + '\n'
        new_entry = '{}\n{}\n'.format(section_title, content)

        blurb, entries = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Unexpected content retrieved from wiki!")
            return False

        entries = new_entry + entries
        cookies = self.wiki.login()

        if not cookies:
            log.err("wkl: Failed to login to wiki")
            return False

        if not self.wiki.post_entry(self.wiki_page, blurb+entries,
                                    summary, cookies):
            log.err("wkl: Failed to post entry for %s" % buildid)
            return False

        log.msg("wkl: Posting wikilog entry for %s" % buildid)
        return True

    def updateEntryBuildInfo(self, entry, title, build):
        """
        Extract the branch and commit hash from the properties of the 'build'
        and update the 'entry' string with extracted values

        @type   entry: string
        @type   build:   buildbot.status.build.BuildStatus
        """

        chash = None
        if "yp_build_revision" in build['properties']:
            chash = build['properties']['yp_build_revision'][0]
        if not chash or len(chash) < 1 or chash == "HEAD":
            chash = "YP_CHASH"

        new_entry = entry.replace("YP_CHASH", chash, 2)
        new_title = title.replace("YP_CHASH", chash, 2)

        return new_entry, new_title

    @defer.inlineCallbacks
    def updateBuild(self, build, parent):
        """
        Extract information about 'build' and update an entry in the wiki

        @type   build:  buildbot.status.build.BuildStatus
        """
        if not parent:
            parent = build

        url = build['url']
        log_entries = []
        logfmt = '[%s %s]'
        for s in build['steps']:

            # Ignore logs for steps which succeeded
            result = s['results']
            if result == SUCCESS:
                continue

            step_name = s['name']
            step_number = s['number']
            logs = yield self.master.data.get(("steps", s['stepid'], 'logs'))
            logs = list(logs)
            for l in logs:
                log_url = '%s/steps/%s/logs/%s' % (url, step_number, l['name'])
                log_entry = logfmt % (log_url, step_name)
                log_entries.append(log_entry)

        blurb, entries = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Unexpected content retrieved from wiki!")
            return False

        entry_list = re.split('\=\=\[(.+)\]\=\=', entries)
        entry = ''
        title = ''
        foundmatch = False
        # Start at the beginning of entry list and keep iterating until we find
        # a title which contains our url/identifier
        for idx, entry in enumerate(entry_list):
            # The matched title contents should always start with a http*
            # schemed URI
            if entry.startswith('http'):
                # format of the title is:
                # ==[url builder buildid - buildbranch commit_hash on identifier]==
                title_components = entry.split(None, 8)

                if title_components[0] == parent['url']:
                    if self.identifier and title_components[7] == self.identifier:
                        foundmatch = True
                    elif not self.identifier:
                        foundmatch = True

                if foundmatch:
                    entry = entry_list[idx+1]
                    title = entry_list[idx]
                    break

        if not entry or not title:
            errmsg = ("wkl: Failed to update entry for {0} couldn't find a matching title containing url: {1}")
            log.err(errmsg.format(buildid, parent['url']))
            return False

        logs = ''
        new_entry = ''
        log_fmt = '\n** '
        buildid = build['buildid']
        builder = build['builder']['name']
        builderfmt = '\n* [%s %s] failed' % (url, builder)

        if len(log_entries) > 0:
            builderfmt = builderfmt + ': ' + log_fmt
            logs = log_fmt.join(log_entries)
        logs = logs + '\n'
        new_entry = '\n' + entry.strip() + builderfmt + logs

        summary = 'Updating entry with failures in %s' % builder
        summary = summary + self.idstring

        new_entry, new_title = self.updateEntryBuildInfo(new_entry, title, parent)

        # Find the point where the first entry's title starts and the second
        # entry's title begins, then replace the text between those points
        # with the newly generated entry.
        it = re.finditer('\=\=\[(.+)\]\=\=', entries)
        entry_title = next(it)
        while entry_title.group(1) != title:
            entry_title = next(it)
        next_title = next(it)
        head = entries[:entry_title.start()]
        tail = entries[next_title.start():]
        update = head + "==[" + new_title + "]==\n" + new_entry + tail

        cookies = self.wiki.login()
        if not cookies:
            log.err("wkl: Failed to login to wiki")
            return False

        if not self.wiki.post_entry(self.wiki_page, blurb+update, summary,
                                    cookies):
            log.err("wkl: Failed to update entry for %s" % buildid)
            return False

        log.msg("wkl: Updating wikilog entry for %s" % buildid)
        return True

