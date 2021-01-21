#
# SPDX-License-Identifier: GPL-2.0-only
#

from buildbot.plugins import reporters

from yoctoabb import config


services = []

# TODO: we'll replace this with functionality in yocto-autobuilder-helpers
# to mail the error reports to the list
# services.append(
#     reporters.MailNotifier(fromaddr="yocto-builds@yoctoproject.org",
#                            sendToInterestedUsers=False,
#                            extraRecipients=["yocto-builds@yoctoproject.org"],
#                            mode=('failing',))
# )

# services.append(
#     reporters.IRC(host="irc.freenode.net",
#                   nick="YoctoAutobuilderBot",
#                   password=""
#                   notify_events={
#                     'successToFailure': 1,
#                     'failureToSuccess': 0
#                   },
#                   channels=["yocto"],
#                   noticeOnChannel=True))

# from yoctoabb.reporters import wikilog
# services.append(
#     wikilog.WikiLog("https://wiki.yoctoproject.org/wiki/api.php",
#                     "User", "password", "LogPage",
#                     "Production Cluster")
# )

# from yoctoabb.reporters import swatbot
# services.append(
#     swatbot.SwatBot("http://localhost:8000/", "buildbot-notifier", "password")
# )