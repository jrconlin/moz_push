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

from Queue import Queue
import random
import threading

from notifserver.storage import logger


class MemoryStorage(object):
    """Manages message storage with an in-memory store.

    This is useful for testing purposes only.
    """

    def __init__(self, **config):
        self.broker_host = config['host']
        self.broker_port = config['amqp_port']

        self.mutex = threading.Lock()
        self.subToUser = {}
        self.userToQueues = {} 
        self.queues = {}

    @classmethod
    def get_name(cls):
        return 'memory'

    def create_client_queue(self, username):
        self.mutex.acquire()

        self._ensure_user_exists(username)

        # TODO: Probably unnecessary, but make sure the queue name isn't taken
        queue_name = "%x" % random.getrandbits(256)

        logger.info("Creating queue %s for user %s", queue_name, username)

        self.userToQueues[username].append(queue_name) 
        self.queues[queue_name] = Queue()

        self.mutex.release()

        return {
            'queue_id': queue_name,
            'host': self.broker_host,
            'port': self.broker_port,
        }

    def _ensure_user_exists(self, username):
        if username not in self.userToQueues:
            self.userToQueues[username] = [] 

    def create_subscription(self, username, token):
        logger.info("Creating subscription '%s' for user '%s'" % (token, username))

        with self.mutex:
            self._ensure_user_exists(username)

            if token in self.subToUser:
                if self.subToUser[token] != username:
                    raise Exception("Subscription token '%s' is already taken" % token)
                else:
                    pass # Don't care if same user registers token twice

            self.subToUser[token] = username

    def delete_subscription(self, username, token):
        logger.info("Deleting subscription '%s' for user '%s'" % (token, username))

        with self.mutex:
            self._ensure_user_exists(username) 

            if token not in self.subToUser:
                raise Exception("Subscription token '%s' does not exist" % token) 

            del self.subToUser[token]

    def publish_message(self, message, token):
        logger.info("Publishing message to subscription token '%s'" % token)

        with self.mutex:
            if token not in self.subToUser:
                raise Exception("Subscription token '%s' does not exist" % token)

            username = self.subToUser[token]

            self._ensure_user_exists(username)
            
            # Deliver message to each of the user's queues
            for queue_name in self.userToQueues[username]:
                self.queues[queue_name].put(message)

    def queue_message(self, message, queue_name):
        logger.info("Sending message to queue '%s'" % queue_name)

        with self.mutex:
            if queue_name not in self.queues:
                raise Exception("Queue '%s' does not exist" % queue_name)

            self.queues[queue_name].put(message)

    def send_broadcast(self, message, username):
        logger.info("Sending broadcast to user '%s'" % username)

        with self.mutex:
            if username not in self.userToQueues:
                raise Exception("User '%s' has no queues" % username)
            
            # Deliver message to each of the user's queues
            for queue_name in self.userToQueues[username]:
                self.queues[queue_name].put(message)

    def get_message(self, queue_name):
        logger.info("Consuming message from queue '%s'" % queue_name)

        queue = None
        with self.mutex:
            if queue_name not in self.queues:
                raise Exception("Queue '%s' does not exist")

            queue = self.queues[queue_name]

        # NOTE: In theory, a queue can be deleted with other storage plugins.
        # This is not a case we worry about with in-memory storage
        return queue.get() # Blocks until queue gets item

