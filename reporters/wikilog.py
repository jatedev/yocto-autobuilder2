#
# SPDX-License-Identifier: GPL-2.0-only
#

from buildbot.reporters import utils
from buildbot.util import service
from twisted.internet import defer, threads
from twisted.python import log
from buildbot.process.results import SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED

from yoctoabb.lib.wiki import YPWiki

import time
import pprint
import re

monitored_parents = ['a-full', 'a-quick']

class WikiLog(service.BuildbotService):
    name = "WikiLog"
    wiki = None
    # wantPreviousBuilds wantLogs
    neededDetails = dict(wantProperties=True, wantSteps=True)
    wikiLock = None

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
        self.wikiLock = defer.DeferredLock()

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
            # Only log full/quick builds on the wiki log
            if build['builder']['name'] not in monitored_parents:
                return
            yield self.wikiLock.acquire()
            try:
                result = yield threads.deferToThread(self.logBuild, build)
            finally:
                self.wikiLock.release()

            if not result:
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

        # Only run the logging code for builds in the monitored_parents list, or builds with
        # failures (to try and cut down on wiki noise)
        havelog = False
        headerpresent = False
        if build['results'] in [FAILURE, EXCEPTION, WARNINGS]:
            havelog = True
        if (parent and parent['builder']['name'] in monitored_parents) or \
                (build['builder']['name'] in monitored_parents):
            havelog = True
            headerpresent = True

        if not havelog:
            return

        if not headerpresent:
            yield self.wikiLock.acquire()
            try:
                result = yield threads.deferToThread(self.logBuild, build)
            finally:
                self.wikiLock.release()

            if not result:
                log.err("wkl: Failed to log build failure %s on %s" % (
                    build['buildid'], build['builder']['name']))
                return

        entry = yield self.getEntry(build, parent)
        yield self.wikiLock.acquire()
        try:
            update = yield threads.deferToThread(self.updateBuild, build, parent, entry)
        finally:
            self.wikiLock.release()
        if not update:
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
        content = '<div id="' + str(buildid) + '"></div>\n'
        content = content + "* '''Build ID''' - %s" % chash
        content = content + self.idstring
        content = content + '\n* Started at: %s\n' % starttime
        content = content + '* ' + forcedby + '\n* ' + reason + '\n'
        new_entry = '{}\n{}\n'.format(section_title, content)

        blurb, entries, footer = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Unexpected content retrieved from wiki!")
            return False

        content = blurb + new_entry + entries + footer
        cookies = self.wiki.login()

        if not cookies:
            log.err("wkl: Failed to login to wiki")
            return False

        post = self.wiki.post_entry(self.wiki_page, content, summary, cookies)
        if not post:
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
    def getEntry(self, build, parent):
        """
        Extract information about 'build' and update an entry in the wiki

        @type   build:  buildbot.status.build.BuildStatus
        """
        if not parent:
            parent = build

        url = build['url']
        buildid = build['buildid']
        builder = build['builder']['name']
        log_entries = []
        logentry = ""
        for s in build['steps']:

            # Ignore logs for steps which succeeded/cancelled
            result = s['results']
            if result in (SUCCESS, RETRY, CANCELLED, SKIPPED):
                continue
            #if result == WARNINGS:
            #    # ignore warnings for log purposes for now
            #    continue

            # Log for FAILURE, EXCEPTION

            step_name = s['name']
            step_number = s['number']
            logs = yield self.master.data.get(("steps", s['stepid'], 'logs'))
            logs = list(logs)
            logstring = []
            for l in logs:
                log_url = '%s/steps/%s/logs/%s' % (url, step_number, l['name'])
                logstring.append('[%s %s]' % (log_url, l['name']))

            logs = ' '.join(logstring)
            logentry = logentry + '\n* [%s %s] %s failed: %s' % (url, builder, step_name, logs)
        return logentry

    def updateBuild(self, build, parent, logentry):

        if not parent:
            parent = build
        buildid = build['buildid']
        builder = build['builder']['name']

        log.err("wkl: Starting to update entry for %s(%s)" % (buildid, parent['buildid']))

        blurb, entries, footer = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Unexpected content retrieved from wiki!")
            return False

        entry_list = re.split('\=\=\[(.+)\]\=\=.*', entries)

        # [1::2] selects only the odd entries, i.e. separators/titles
        titles = entry_list[1::2]
        if len(titles) > 200:
            # Archive off entries when the log becomes too long

            log.err("wkl: Archiving off entries from %s (size %s)" % (titles[50], len(titles)))

            sep = '==[' + titles[50] + ']=='
            head, archive = entries.split(sep, 1)
            archive = sep + archive


            archivenum = int(max(re.findall(r'\[%s/Archive/([0-9]+)\]' % self.wiki_page, footer)))
            nextnum = str(archivenum + 1).zfill(4)

            cookies = self.wiki.login()
            if not cookies:
                log.err("wkl: Failed to login to wiki")
                return False

            post = self.wiki.post_entry(self.wiki_page + "/Archive/" + nextnum, archive, "Archive out older buildlog entries", cookies)
            if not post:
                log.err("wkl: Failed to save new archive page %s" % (nextnum))
                return False

            entries = head
            entry_list = re.split('\=\=\[(.+)\]\=\=.*', entries)

            footer = footer + "\n* [[" + self.wiki_page + "/Archive/" + nextnum + "]]"

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

        new_entry = '\n' + entry.strip() + logentry + '\n\n'

        summary = 'Updating entry with failures in %s' % builder
        summary = summary + self.idstring

        new_entry, new_title = self.updateEntryBuildInfo(new_entry, title, parent)

        # If unchanged, skip the update
        if entry == new_entry and title == new_title:
            log.msg("wkl: Entry unchanged for wikilog entry %s" % buildid)
            return True

        # Find the point where the first entry's title starts and the second
        # entry's title begins, then replace the text between those points
        # with the newly generated entry.
        it = re.finditer('\=\=\[(.+)\]\=\=', entries)
        entry_title = next(it)
        while entry_title.group(1) != title:
            entry_title = next(it)
        head = entries[:entry_title.start()]
        try:
            next_title = next(it)
            tail = entries[next_title.start():]
        except StopIteration:
            # There was no following entry
            tail = ""

        update = blurb + head + "==[" + new_title + "]==\n" + new_entry + tail + footer

        cookies = self.wiki.login()
        if not cookies:
            log.err("wkl: Failed to login to wiki")
            return False

        post = self.wiki.post_entry(self.wiki_page, update, summary, cookies)
        if not post:
            log.err("wkl: Failed to update entry for %s(%s)" % (buildid, parent['buildid']))
            return False

        log.msg("wkl: Updating wikilog entry for %s(%s)" % (buildid, parent['buildid']))
        return True
