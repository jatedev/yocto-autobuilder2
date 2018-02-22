from buildbot.reporters import utils
from buildbot.util import service
from twisted.internet import defer
from twisted.python import log

from yoctoab.lib.wiki import YPWiki


class WikiLog(service.BuildbotService):
    name = "WikiLog"
    wiki = None

    def checkConfig(self, wiki_uri, wiki_un, wiki_pass, wiki_page,
                    identifier=None, **kwargs):
        service.BuildbotService.checkConfig(self)

    @defer.inlineCallbacks
    def reconfigService(self, wiki_uri, wiki_un, wiki_pass, wiki_page,
                        identifier=None, **kwargs):
        yield service.BuildbotService.reconfigService(self)
        self.wiki_page = wiki_page
        tagfmt = " on {}"
        if identifier:
            self.tag = tagfmt(identifier)
        else:
            self.tag = ""
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

        # TODO: stepFinished? Or do we no longer need that now that the build
        # is much simpler?

    def stopService(self):
        self._buildCompleteConsumer.stopConsuming()
        self._buildStartedConsumer.stopConsuming()

    def buildStarted(self, key, build):
        yield utils.getDetailsForBuild(self.master, build,
                                       **self.needed)
        builderName = build['builder']['name']
        # TODO: this all seems a bit overly complex?
        if builderName != "nightly" and not self.isTriggered(build)\
           and not self.isNightlyRunning():
            # If a build has been started which isn't nightly and a nightly
            # build isn't running, chances are a single builder has been
            # started in order to test something and it just finished.
            if not self.logBuild(build):
                log.err("wkl: Failed to log build %s on %s" % (
                    build.getNumber(), builderName))
        elif builderName == "nightly":
            if not self.logBuild(build):
                log.err("wkl: Failed to log build %s on %s" % (
                    build.getNumber(), builderName))

    def stepFinished(self, key, build):
        blurb, content = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Couldn't get wiki content in stepFinished()")
            return
        update = self.updateBuildInfo(content, build)

        if not update:
            # log.msg("wkl: No update, nothing to POST")
            return

        if content == update:
            # log.msg("wkl: No update made, no need to make a POST")
            return

        cookies = self.wiki.login()
        if not cookies:
            log.err("wkl: Failed to login to wiki")
            return

        summary = "Updating branch and commitish for %s" %\
                  build.getNumber()
        if not self.wiki.post_entry(self.wiki_page, blurb+update, summary,
                                    cookies):
            # log.err("wkl: Failed to update wikilog with summary: '{}'".format
                # (summary))
            return

    def buildFinished(self, key, build):
        # TODO: we don't have a result var
        if result == SUCCESS:
            return

        if not self.updateBuild(build):
            log.err("wkl: Failed to update wikilog with build %s failure" %
                    build.getNumber())

    def logBuild(self, build):
        """
        Extract information about 'build' and post an entry to the wiki

        @type   build:  buildbot.status.build.BuildStatus
        """

        builder = build.getBuilder().getName()
        reason = build.getReason()
        buildid = str(build.getNumber())
        start, _ = build.getTimes()
        url = self.status.getURLForThing(build)
        buildbranch = build.getProperty('branch').strip()
        if not buildbranch or len(buildbranch) < 1:
            buildbranch = "YP_BUILDBRANCH"
        chash = build.getProperty('commit_poky').strip()
        if not chash or len(chash) < 1 or chash == "HEAD":
            chash = "YP_CHASH"

        reason_list = reason.split(':', 1)
        forcedby = reason_list[0].strip()
        description = 'No reason given.'
        if len(reason_list) > 1 and reason_list[1] != ' ':
            description = reason_list[1].strip()
        starttime = time.ctime(start)

        sectionfmt = '==[{} {} {} - {} {}]=='
        section_title = sectionfmt.format(url, builder, buildid, buildbranch,
                                          chash)
        summaryfmt = 'Adding new BuildLog entry for build %s (%s)'
        summary = summaryfmt % (buildid, chash)
        summary = summary + self.tag
        content = "* '''Build ID''' - %s" % chash
        content = content + self.tag + "\n"
        content = content + '* Started at: %s\n' % starttime
        content = content + '* ' + forcedby + '\n* ' + description + '\n'
        new_entry = '{}\n{}\n'.format(section_title, content).encode('utf-8')

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

    def updateEntryBuildInfo(self, entry, build):
        """
        Extract the branch and commit hash from the properties of the 'build'
        and update the 'entry' string with extracted values

        @type   entry: string
        @type   build:   buildbot.status.build.BuildStatus
        """
        # We only want to update the commit and branch info for the
        # primary poky build
        # FIXME: this is quite poky specific. Can we handle this in
        # a more generic manner?
        repo = build.getProperty("repourl_poky")
        if not repo:
            return entry
        buildbranch = build.getProperty('branch').strip()
        if not buildbranch or len(buildbranch) < 1:
            buildbranch = "YP_BUILDBRANCH"
        chash = build.getProperty('commit_poky').strip()
        if not chash or len(chash) < 1 or chash == "HEAD":
            chash = "YP_CHASH"

        new_entry = entry.replace("YP_BUILDBRANCH", buildbranch, 1)
        new_entry = new_entry.replace("YP_CHASH", chash, 2)

        return new_entry

    def updateBuildInfo(self, content, build):
        """
        Extract the branch and commit hash from the properties of the 'build'
        and update the 'content' string with extracted values

        @type   content: string
        @type   build:   buildbot.status.build.BuildStatus
        """

        # Try to find an entry that matches this build, rather than blindly
        # updating all instances of the template value in the content
        buildid = build.getProperty('buildnumber', '0')
        builder = build.getProperty('buildername', 'nobuilder')
        entry_list = re.split('\=\=\[(.+)\]\=\=', content)
        title_idx = -1
        # Start at the beginning of entry list and keep iterating until we find
        # a title which looks ~right
        for idx, ent in enumerate(entry_list):
            # The matched title contents should always start with a http*
            # schemed URI
            if ent.startswith('http'):
                # format of the title is:
                # ==[url builder buildid - buildbranch commit_hash]==
                title_components = ent.split(None, 6)
                if builder == title_components[1] and \
                   str(buildid) == title_components[2]:
                    title_idx = idx
                    break

        if title_idx < 0:
            errmsg = ("wkl: Failed to update entry for {0} couldn't find a "
                      "matching title with builder {1}")
            log.err(errmsg.format(buildid, builder))
            return content

        entry = entry_list[title_idx + 1]
        title = entry_list[title_idx]

        combined = "==[{0}]=={1}".format(title, entry)
        new_entry = self.updateEntryBuildInfo(combined, build)
        new_entry = new_entry.encode('utf-8')

        it = re.finditer('\=\=\[(.+)\]\=\=', content)
        entry_title = it.next()
        while entry_title.group(1) != title:
            entry_title = it.next()
        next_title = it.next()
        head = content[:entry_title.start()]
        tail = content[next_title.start():]
        update = head + new_entry + tail

        # log.msg("wkl: Updating commit info YP_BUILDBRANCH=%s YP_CHASH=%s" %
        #         (buildbranch, chash))

        return update

    def updateBuild(self, build):
        """
        Extract information about 'build' and update an entry in the wiki

        @type   build:  buildbot.status.build.BuildStatus
        """
        builder = build.getBuilder().getName()
        buildid = str(build.getNumber())
        reason = build.getReason()
        blurb, entries = self.wiki.get_content(self.wiki_page)
        if not blurb:
            log.err("wkl: Unexpected content retrieved from wiki!")
            return False

        url = self.status.getURLForThing(build)
        log_entries = []
        logfmt = '[%s %s]'
        for l in build.getLogs():
            # Ignore logs for steps which succeeded
            result, _ = l.getStep().getResults()
            if result == SUCCESS:
                continue

            step_name = l.getStep().getName()
            log_url = '%s/steps/%s/logs/%s' % (url,
                                               step_name,
                                               l.getName())
            log_url = log_url.replace(' ', '%20')
            log_entry = logfmt % (log_url, step_name)
            log_entries.append(log_entry)
        buildbranch = build.getProperty('branch').strip()
        if not buildbranch or len(buildbranch) < 1:
            buildbranch = "YP_BUILDBRANCH"
        chash = build.getProperty('commit_poky').strip()
        if not chash or len(chash) < 1 or chash == "HEAD":
            chash = "YP_CHASH"

        entry_list = re.split('\=\=\[(.+)\]\=\=', entries)
        entry = ''
        title = ''
        # Start at the beginning of entry list and keep iterating until we find
        # a title which looks ~right
        trigger = "Triggerable(trigger_main-build"
        for idx, entry in enumerate(entry_list):
            # The matched title contents should always start with a http*
            # schemed URI
            if entry.startswith('http'):
                # format of the title is:
                # ==[url builder buildid - buildbranch commit_hash]==
                title_components = entry.split(None, 6)

                # For the primary, nightly, builder we can match on chash and
                # buildbranch, otherwise we have to hope that the first
                # triggered build with matching chash and tag
                foundmatch = False
                if buildbranch == title_components[4] \
                   and chash == title_components[5] \
                   and self.tag in entry_list[idx+1]:
                    foundmatch = True
                elif trigger in reason \
                   and chash == title_components[5] \
                   and self.tag in entry_list[idx+1]:
                    foundmatch = True

                if foundmatch:
                    entry = entry_list[idx+1]
                    title = entry_list[idx]
                    break

        if not entry or not title:
            errmsg = ("wkl: Failed to update entry for {0} couldn't find a "
                      "matching title for branch: {1} or hash: {2} "
                      "(reason was '{3}')")
            log.err(errmsg.format(buildid, buildbranch, chash, reason))
            return False

        log_fmt = ''
        logs = ''
        new_entry = ''
        if builder == 'nightly':
            # for failures in nightly we just append extra entries to the
            # bullet list pointing to the failure logs
            if len(log_entries) > 0:
                logs = '\n* '.join(log_entries) + '\n'
                new_entry = '\n' + entry.strip() + '\n* ' + logs
            else:
                # We only update the buildlog for a nightly build if there
                # are additional items to append to the log list.
                return True
        else:
            # for non-nightly failures we create an entry in the list linking
            # to the failed builder and indent the logs as a child bullet list
            log_fmt = '\n* '
            builderfmt = log_fmt
            if self.isTriggered(build) or self.isNightlyRunning():
                log_fmt = '\n** '
                builderfmt = '\n* [%s %s] failed' % (url, builder)

            if len(log_entries) > 0:
                if self.isTriggered(build) or self.isNightlyRunning():
                    builderfmt = builderfmt + ': ' + log_fmt
                logs = log_fmt.join(log_entries)
            logs = logs + '\n'
            new_entry = '\n' + entry.strip() + builderfmt + logs

        summary = 'Updating entry with failures in %s' % builder
        summary = summary + self.tag

        new_entry = self.updateEntryBuildInfo(new_entry, build)
        new_entry = new_entry.encode('utf-8')

        # Find the point where the first entry's title starts and the second
        # entry's title begins, then replace the text between those points
        # with the newly generated entry.
        it = re.finditer('\=\=\[(.+)\]\=\=', entries)
        entry_title = it.next()
        while entry_title.group(1) != title:
            entry_title = it.next()
        next_title = it.next()
        head = entries[:entry_title.end()]
        tail = entries[next_title.start():]
        update = head + new_entry + tail

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

    def isNightlyRunning(self):
        """
        Determine whether there's a nightly build in progress
        """
        nightly = self.master.getBuilder("nightly")
        if not nightly:
            return False
        build = nightly.getBuild(-1)  # the most recent build
        if not build:
            return False
        running = not build.isFinished()
        return running

    def isTriggered(self, build):
        """
        build.isFinished() can return True when buildsteps triggered by
        nightly are still running, therefore we provide a method to check
        whether the 'build' was triggered by a nightly build.

        @type   build:  buildbot.status.build.BuildStatus
        """
        reason = build.getReason()
        reason_list = reason.split(':', 1)
        forcedby = reason_list[0].strip()
        if forcedby.startswith("Triggerable"):
            return True
        return False
