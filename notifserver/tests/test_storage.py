# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Push Notification Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   JR Conlin (jrconlin@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
import json
import unittest
import time
import os

from services.config import Config
from notifserver.storage import get_message_backend
from notifserver.wsgiapp import make_app
from webtest import TestApp


class TestStorage(unittest.TestCase):

    def setUp(self):
        test_cfg = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     'tests.conf')
        self.config = Config(cfgfile = test_cfg)

        self.app = TestApp(make_app(self.config))
        self.app.reset()

    def tearDown(self):
        pass

    def test_all(self):
        storage = get_message_backend(self.config)
        username = 'testuser'
        test_token = 'unit_test_token_123'
        origin = 'nowhere'
        test_message = json.dumps({"body": json.dumps({
                                                "token": test_token,
                                                "timestamp": int(time.time()),
                                                "ciphertext": "test",
                                                "ttl": 100}),
                                   "HMAC": "123abc"})
        queue_info = storage.create_client_queue(username)
        subs = storage.create_subscription(username, test_token)

        #Send a message to the user.
        storage.send_broadcast(test_message, username, origin = origin)
        msgs = storage.get_pending_messages(username)
        storage._purge(username = username)

        #Send a message to a user based on their queue id (most common path)
        storage.publish_message(test_message,
                                queue_info.get('queue_id'),
                                origin = origin)
        msgs = storage.get_pending_messages(username)
        self.failUnless(test_token in msgs[0])
        storage._purge(username = username)

        # Add a message to a subscription queue
        storage.queue_message(test_message,
                subs.get('queue_id'),
                origin = origin)
        msgs = storage.get_pending_messages(username)
        # clean all the messages out of the user queue
        storage._purge(username = username)

        # drop the subscription.
        storage.delete_subscription(username, test_token)
        # Should not be able to add message to a deleted queue
        self.failIf(storage.queue_message(test_message,
                              subs.get('queue_id'),
                              origin = origin))
        # Should not be able to read messages from an empty queue
        msgs = storage.get_pending_messages(username)
        self.failIf(len(msgs))
