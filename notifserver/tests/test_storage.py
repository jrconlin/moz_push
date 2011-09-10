import json
import unittest
import time
import os

from services.tests.support import TestEnv
from notifserver.storage import get_message_backend
from notifserver.wsgiapp import make_app
from webtest import TestApp

class TestStoreage(unittest.TestCase):

    def setUp(self):
        env = TestEnv(os.path.realpath(__file__))
        self.config = env.config

        self.appdir = env.topdir
        self.app = TestApp(make_app(self.config))
        self.app.reset()

    def tearDown(self):
        pass

    def test_all(self):
        storage = get_message_backend(self.config)
        username = 'testuser'
        test_token = 'unit_test_token_123'
        test_message = json.dumps({"body": json.dumps({
                                                "token": test_token,
                                                "timestamp": int(time.time()),
                                                "ciphertext": "test",
                                                "ttl": 1}),
                                   "HMAC": "123abc"})

        import pdb; pdb.set_trace()
        queue_info = storage.create_client_queue(username)
        create_subscription(username, test_token)
        storage.send_broadcast(test_message, username)
        msgs = storage.get_pending_messages(username)
        storage.purge()
        storage.publish_message(test_message,
                                test_token)
        msgs = storage.get_pending_messages(username)
        storage.delete_subscription(username, test_token)
        print 'yay!'