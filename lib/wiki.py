#
# SPDX-License-Identifier: GPL-2.0-only
#

'''
Created on Dec 13, 2016

__author__ = "Joshua Lock"
__copyright__ = "Copyright 2016, Intel Corp."
__credits__ = ["Joshua Lock"]
'''

import codecs
import hashlib
import time
import requests
from twisted.python import log


class YPWiki(object):
    MAX_TRIES = 5
    TIMEOUT = 60

    def __init__(self, wiki_uri, wiki_un, wiki_pass):
        self.wiki_uri = wiki_uri
        self.wiki_un = wiki_un
        self.wiki_pass = wiki_pass

    @staticmethod
    def retry_request(requesturl, **kwargs):
        """
        Rather than failing when a request to a 'requesturl' throws an
        exception retry again a minute later. Perform this retry no more than
        5 times.

        @type   requesturl:  string
        """
        kwargs['timeout'] = YPWiki.TIMEOUT

        def try_request():
            try:
                req = requests.get(requesturl, **kwargs)
                return req
            except (requests.exceptions.RequestException,
                    requests.exceptions.Timeout):
                return None

        tries = 0
        req = None
        while not req and tries < YPWiki.MAX_TRIES:
            if tries > 0:
                time.sleep(60)
            req = try_request()
            tries = tries + 1

        return req

    @staticmethod
    def parse_json(response):
        """
        This method handles stripping UTF-8 BOM from the beginning of responses
        from the Yocto Project wiki.

        http://en.wikipedia.org/wiki/Byte_Order_Mark
        http://bugs.python.org/issue18958

        @type   response:   requests.Response
        """
        bom = codecs.BOM_UTF8
        text = ''

        # In Requests 0.8.2 (Ubuntu 12.04) Response.content has type unicode,
        # whereas in requests 2.1.10 (Fedora 23) Response.content is a str
        # Ensure that bom is the same type as the content, codecs.BOM_UTF8 is
        # a str

        # If we discover a BOM set the encoding appropriately so that the
        # built in decoding routines in requests work correctly.
        if response.content.startswith(bom):
            response.encoding = 'utf-8-sig'

        return response.json()

    def login(self):
        """
        Login to the wiki and return cookies for the logged in session
        """
        payload = {
            'action': 'login',
            'lgname': self.wiki_un,
            'lgpassword': self.wiki_pass,
            'utf8': '',
            'format': 'json'
        }

        try:
            req1 = requests.post(self.wiki_uri, data=payload,
                                 timeout=self.TIMEOUT)
        except (requests.exceptions.RequestException,
                requests.exceptions.Timeout):
            return None

        parsed = self.parse_json(req1)
        login_token = parsed['login']['token'].encode('utf-8')

        payload['lgtoken'] = login_token
        try:
            req2 = requests.post(self.wiki_uri, data=payload,
                                 cookies=req1.cookies, timeout=self.TIMEOUT)
        except (requests.exceptions.RequestException,
                requests.exceptions.Timeout):
            return None

        return req2.cookies.copy()

    def get_content(self, wiki_page):
        """
        Get the current content of the 'wiki_page' -- to make the wiki page
        as useful as possible the most recent log entry should be at the top,
        to that end we need to edit the whole page so that we can insert the
        new entry after the log but before the other entries.

        This method fetches the current page content, splits out the blurb and
        returns a pair:
        1) the blurb
        2) the current entries

        @type   wiki_page:  string
        """

        pm = '?format=json&action=query&prop=revisions&rvprop=content&titles='

        req = self.retry_request(self.wiki_uri+pm+wiki_page)
        if not req:
            return None, None

        parsed = self.parse_json(req)
        pageid = sorted(parsed['query']['pages'].keys())[-1]
        blurb, entries, footer = "\n", "", "\n==Archived Logs=="
        if 'revisions' in parsed['query']['pages'][pageid]:
            content = parsed['query']['pages'][pageid]['revisions'][0]['*']
            blurb, entries = content.split('==', 1)
            # ensure we keep only a single newline after the blurb
            blurb = blurb.strip() + "\n"
            entries = '==' + entries
            try:
                entries, footer = entries.rsplit('\n==Archived Logs==', 1)
                footer = '\n==Archived Logs==' + footer
            except ValueError:
                pass

        return blurb, entries, footer

    def post_entry(self, wiki_page, content, summary, cookies):
        """
        Post the new page contents 'content' to  the page title 'wiki_page'
        with a 'summary' using the login credentials from 'cookies'

        @type   wiki_page:  string
        @type   content:    string
        @type   summary:    string
        @type   cookies:    CookieJar
        """

        params = ("?format=json&action=query&prop=info|revisions"
                  "&intoken=edit&rvprop=timestamp&titles=")
        req = self.retry_request(self.wiki_uri+params+wiki_page,
                                 cookies=cookies)
        if not req:
            return False

        parsed = self.parse_json(req)
        pageid = sorted(parsed['query']['pages'].keys())[-1]
        edit_token = parsed['query']['pages'][pageid]['edittoken']
        edit_cookie = cookies.copy()
        edit_cookie.update(req.cookies)

        content = content.encode('utf-8')

        content_hash = hashlib.md5(content).hexdigest()

        payload = {
            'action': 'edit',
            'assert': 'user',
            'title': wiki_page,
            'summary': summary,
            'text': content,
            'md5': content_hash,
            'token': edit_token,
            'utf8': '',
            'format': 'json'
        }

        try:
            req = requests.post(self.wiki_uri, data=payload,
                                cookies=edit_cookie, timeout=self.TIMEOUT)
        except (requests.exceptions.RequestException,
                requests.exceptions.Timeout):
            return False

        if not req.status_code == requests.codes.ok:
            log.err("Unexpected status code %s received when trying to post"
                    " an entry to the wiki." % req.status_code)
            return False
        else:
            result = self.parse_json(req)
            status = result.get('edit', {}).get('result', '')
            if status == 'Success':
                return True
            return False
