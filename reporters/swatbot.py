#
# SPDX-License-Identifier: GPL-2.0-only
#

from buildbot.reporters import utils
from buildbot.util import service
from twisted.internet import defer, threads
from twisted.python import log
from buildbot.process.results import SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED

import requests
import time
import pprint
import re
import json

#monitored_parents = ['a-full', 'a-quick']

class SwatBotURI(object):
    TIMEOUT = 10

    def __init__(self, uri, user, passwd):
        self.uri = uri
        self.user = user
        self.passwd = passwd

        self.login()

    def login(self):
        self.client = requests.session()
        self.headers = {'Content-type':'application/vnd.api+json'}

        req = self.client.get(self.uri + "accounts/login/", timeout=self.TIMEOUT, headers=self.headers)
        login_data = {
            'username': self.user,
            'password': self.passwd, 
            'csrfmiddlewaretoken': req.cookies['csrftoken'],
        }
        req2 = self.client.post(self.uri + "accounts/login/", data=login_data, allow_redirects=False)
        csrftoken = req2.cookies['csrftoken']
        self.headers = {'Content-type':'application/vnd.api+json', 'X-CSRFToken': csrftoken}

    def query_with_login(self, query):
        req = self.client.get(query, timeout=self.TIMEOUT, headers=self.headers, allow_redirects=False)
        # A 302 status means we probably need to renew the login
        if req.status_code == requests.codes.found and "login" in req.headers['Location']:
            log.err("SwatBot: Attempting to renew login")
            self.login()
            return self.client.get(query, timeout=self.TIMEOUT, headers=self.headers, allow_redirects=False)
        return req

    def find_build_collection(self, build):
        dbid = None

        url = self.uri + "rest/buildcollection/"

        collection_build_id = build['buildid']
        if build['buildset']['parent_buildid']:
            collection_build_id = build['buildset']['parent_buildid']

        req = self.query_with_login(url + "?buildid=" + str(collection_build_id))
        if req.status_code == requests.codes.ok:
            try:
                data = req.json()['data']
                if len(data) > 1:
                    log.err("SwatBot: More than one buildid matches?: %s" % str(data))
                    return None
                elif len(data) == 1:
                    return data[0]['id']
            except (json.decoder.JSONDecodeError, KeyError, IndexError) as e:
                log.err("SwatBot: Couldn't decode json data: %s (ret code %s)" % (req.text, req.status_code))
                return None
        if req.status_code == requests.codes.not_found or not dbid:
            payload = {
                'data': {
                    'type': 'BuildCollection',
                    'attributes': {
                        "buildid": collection_build_id,
                        "targetname": build['builder']['name'],
                        "branch": build['properties']['branch_poky'][0],
                    }
                }
            }

            # We should only get here when a DB entry doesn't exist which means we're the triggering build
            # and should have reason/owner
            if 'reason' in build['properties'] and build['properties']['reason'][0]:
                payload['data']['attributes']['reason'] = build['properties']['reason'][0]
            if 'owner' in build['properties'] and build['properties']['owner'][0]:
                payload['data']['attributes']['owner'] = build['properties']['owner'][0]
            if 'swat_monitor' in build['properties'] and build['properties']['swat_monitor'][0]:
                payload['data']['attributes']['forswat'] = True
            else:
                payload['data']['attributes']['forswat'] = False

            try:
                req = self.client.post(url, json=payload, timeout=self.TIMEOUT, headers=self.headers)
            except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                log.err("SwatBot: Unexpected server response exception")
                return None
            if req.status_code != requests.codes.created:
                log.err("SwatBot: Couldn't create: %s (%s)" % (str(req.status_code), str(req.json())))
                return None
            data = req.json()['data']
            return data['id']
        if not dbid:
            log.err("SwatBot: Unexpected server response: %s (%s)" % (str(req.status_code), str(req.json())))
            return None

        return dbid

    def add_build(self, build):
        url = self.uri + "rest/build/"

        dbid = None
        collectionid = self.find_build_collection(build)
        if not collectionid:
            log.err("SwatBot: Couldn't find BuildCollection database ID")
            return False

        req = self.query_with_login(url + "?buildid=" + str(build['buildid']))
        if req.status_code == requests.codes.ok:
            data = req.json()['data']
            if len(data) > 1:
                log.err("SwatBot: More than one buildid matches?: %s" % str(data))
                return False
            elif len(data) == 1:
                log.err("SwatBot: Build already exists?: %s" % str(data))
                return False

        payload = {
            'data': {
                'type': 'Build',
                'attributes': {
                    "buildid": build['buildid'],
                    "url": build['url'],
                    "targetname": build['builder']['name'],
                    "started": build['started_at'].isoformat(),
                    "workername": build['properties']['workername'][0],
                    "buildcollection": {
                        "type": "BuildCollection",
                        "id" :int(collectionid)
                    }
                }
            }
        }

        req = self.client.post(url, json=payload, timeout=self.TIMEOUT, headers=self.headers)
        if req.status_code != requests.codes.created:
            log.err("SwatBot: Couldn't create: %s (%s)" % (str(req.status_code), str(req.json())))
            return False
        return True

    @defer.inlineCallbacks
    def update_build(self, build, master):
        req = self.query_with_login(self.uri + "rest/build/?buildid=" + str(build['buildid']))
        if req.status_code != requests.codes.ok:
            log.err("SwatBot: Couldn't find build to update: %s (%s)" % (str(req.status_code), str(req.json())))
            return False

        try:
            data = req.json()['data']
        except (json.decoder.JSONDecodeError, KeyError, IndexError) as e:
            log.err("SwatBot: Couldn't decode json data: %s (ret code %s)" % (req.text, req.status_code))
            return False

        if len(data) != 1:
            log.err("SwatBot: More than one buildid matches?: %s" % str(data))
            return False

        dbid = data[0]['id']
        url = self.uri + "rest/build/" + str(dbid) + "/"

        payload = {
            'data': {
                'id': int(dbid),
                'type': 'Build',
                'attributes': data[0]['attributes'],
            }
        }

        payload['data']['attributes']['status'] = build['results']
        payload['data']['attributes']['completed'] = build['complete_at'].isoformat()
        if "yp_build_revision" in build['properties']:
            payload['data']['attributes']['revision'] = build['properties']['yp_build_revision'][0]

        req = self.client.put(url, json=payload, timeout=self.TIMEOUT, headers=self.headers)
        if req.status_code != requests.codes.ok:
            log.err("SwatBot: Couldn't update record: %s %s (%s)" % (str(build), str(req.status_code), str(req.json())))
            return False

        for s in build['steps']:
            # Ignore logs for steps which succeeded/cancelled
            result = s['results']
            if result in (SUCCESS, RETRY, CANCELLED, SKIPPED):
                continue

            # Log for FAILURE, EXCEPTION, WARNING
            step_name = s['name']
            step_number = s['number']
            logs = yield master.data.get(("steps", s['stepid'], 'logs'))
            logs = list(logs)
            urls = []
            for l in logs:
                urls.append('%s/steps/%s/logs/%s' % (build['url'], step_number, l['name'].replace(" ", "_")))
            if urls:
                urls = " ".join(urls)
            else:
                urls = ""
            payload = {
                'data': {
                    'type': 'StepFailure',
                    'attributes': {
                        "urls": urls,
                        "status": s['results'],
                        "stepname": s['name'],
                        "stepnumber": s['number'],
                        "build": {
                            "type": "Build",
                            "id": int(dbid),
                        }
                    }
                }
            }

            req = self.client.post(self.uri + "rest/stepfailure/", json=payload, timeout=self.TIMEOUT, headers=self.headers)
            if req.status_code != requests.codes.created:
                log.err("SwatBot: Couldn't create failure entry: Step data: %s" % (str(s)))
                log.err("SwatBot: Couldn't create failure entry: Payload: %s" % (str(payload)))
                log.err("SwatBot: Couldn't create failure entry: %s %s" % (str(req.status_code), str(req.headers)))
        return True


class SwatBot(service.BuildbotService):
    name = "SwatBot"

    neededDetails = dict(wantProperties=True, wantSteps=True)
    # wantPreviousBuilds wantLogs

    def checkConfig(self, bot_uri, user, password, **kwargs):
        service.BuildbotService.checkConfig(self)

    @defer.inlineCallbacks
    def reconfigService(self, bot_uri, user, password, **kwargs):
        yield service.BuildbotService.reconfigService(self)
        self.uri = bot_uri
        self.user = user
        self.passwd = password
        self.helper = SwatBotURI(self.uri, self.user, self.passwd)

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
        #log.err("SwatBot: buildStarted %s %s" % (key, pprint.pformat(build)))
        self.helper.add_build(build)

    # Assume we only have a parent, doesn't handle builds nested more than one level.
    @defer.inlineCallbacks
    def buildFinished(self, key, build):
        yield utils.getDetailsForBuild(self.master, build, **self.neededDetails)
        #log.err("SwatBot: buildFinished %s %s" % (key, pprint.pformat(build)))
        yield self.helper.update_build(build, self.master)

