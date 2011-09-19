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
# The Original Code is the Mozilla Push Notifications Server.
#
# The Initial Developer of the Original Code is
# Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Shane da Silva <sdasilva@mozilla.com>
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
import os
import unittest
import time

from webtest import TestApp

from services.tests.support import TestEnv
from services.config import Config
from notifserver.tests import FakeAuthTool
from notifserver import VERSION
from notifserver.wsgiapp import make_app
from notifserver.storage import get_message_backend


class ClientAgentTest(unittest.TestCase):
    """Test class for all Client Agent tests.

    This handles the creation of an in-process Client Agent server to run
    tests against.

    """

    def setUp(self):
        env = TestEnv(ini_dir = os.path.dirname(os.path.realpath(__file__)))
        test_cfg = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     'tests.conf')
        self.config = Config(cfgfile = test_cfg)
        #self.appdir = env.topdir
        self.app = TestApp(make_app(self.config))
        self.app.reset()

    def tearDown(self):
        pass

    def set_credentials(self, username=None, password=None):
        self.username = username
        self.password = password

    def create_queue(self):
        res = self.app.post("/%s/new_queue" % VERSION,
            extra_environ={'REMOTE_USER': self.username})
        assert res.status_int == 200

        return json.loads(res.body)

    def create_subscription(self, token):
        res = self.app.post("/%s/new_subscription" % VERSION,
            json.dumps({'token': token}),
            extra_environ={'REMOTE_USER': self.username})
        assert res.status_int == 200

    def remove_subscription(self, token):
        res = self.app.post("/%s/remove_subscription" % VERSION,
            json.dumps({'token': token}),
            extra_environ={'REMOTE_USER': self.username})

    def send_broadcast(self, message = None):
        if message is None:
            message = "'this is a broadcast message'"

        self.set_credentials("testuser", "mypassword")
        self.app.post("/%s/broadcast" % VERSION,
            message,
            extra_environ={'REMOTE_USER': self.username})


        # TODO: Figure out a way to extract messages from queues in tests
        # For now we assume all is well if "200 OK" returned

    def test_create_queue(self):
        self.set_credentials(self.config.get('tests.user', 'testuser'),
                             self.config.get('tests.password',"mypassword"))
        queue_info = self.create_queue()
        assert 'queue_id' in queue_info
        assert 'host' in queue_info
        assert 'port' in queue_info

        assert len(queue_info['queue_id']) > 0
        assert len(queue_info['host']) > 0
        assert queue_info['port']

    def test_subscriptions(self):
        self.set_credentials(self.config.get('tests.user', 'testuser'),
                             self.config.get('tests.password',"mypassword"))
        token = "TEST123456789"

        # Can't delete subscription if it doesn't exist
        try:
            self.remove_subscription(token)
            assert False
        except Exception, e:
            pass

        # Normal create and delete
        self.create_subscription(token)
        self.remove_subscription(token)

        # Can't delete subscription if already deleted
        try:
            self.remove_subscription(token)
            assert False
        except Exception, e:
            pass

    def test_broadcasts(self):
        self.set_credentials(self.config.get('tests.user',"testuser"),
                             self.config.get('tests.password', "mypassword"))
        queue_info = self.create_queue()
        ciphertext = 'test_12345'
        self.send_broadcast(
            json.dumps({"body":
                            json.dumps({"token": queue_info.get('queue_id'),
                                        "timestamp": int(time.time()),
                                        "ciphertext": ciphertext,
                                        "ttl": 1}),
                        "HMAC": ""}))
        backend = get_message_backend(self.config)
        messages = backend.get_pending_messages(self.config.get('tests.user'))
        self.assertEqual(json.loads(
                    json.loads(messages[0]).get('body')).get('ciphertext'),
                         ciphertext)
        #wait for the message to expire.
        time.sleep(2)
        messages = backend.get_pending_messages(self.config.get('tests.user'))
        self.assertEqual(len(messages), 0)
