# ***** BEGIN LICENSE BLOCK *****   msgs = storage.get_pen
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
# The Original Code is Mozilla Push
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

import base64
import json
import random
import time
import redis
import os

from notifserver.storage import (logger, NotifStorageException)


class RedisStorage(object):

    is_connected = False
    connection = None

    def __init__(self, **config):
        self.config = config
        self.db_host = self.config.get('redis.host', 'localhost')
        self.db_port = int(self.config.get('redis.port', '6379'))
        self.redis = redis.Redis(host = self.db_host,
                                port = self.db_port)

        """ schemas:
            mapping:
            u2t: username to user token
            t2u: user token to username
            s2u: subscription token to username
            u2s: username to subscription tokens (list)
            u2m: username to all messages (list of objects)
                um_object={file: path to message storage
                            expry: freshness date
                            id: message sequence number}
        """

    @classmethod
    def get_name(cls):
        return 'redis'

    def _user_storage_path(self, username):
        """ Return a path constructed from the username's token """
        doc_path = self.config.get('redis.data_path', '/tmp')
        user_queue = self.create_client_queue(username)
        user_token = user_queue.get('queue_id')
        return os.path.join(doc_path,
                                user_token[0:4],
                                user_token[4:8],
                                user_token[8:])

    def new_token(self):
        return "%x" % random.getrandbits(256)

    def create_client_queue(self, username):
        logger.info("Creating incoming queue for %s for user %s")
        try:
            # Check to see if the user already has a token.
            # ut: user -> token
            user_token = self.redis.get('u2t:%s' % username)
            if user_token is None:
                user_token = self.new_token()
                self.redis.set('u2t:%s' % username, user_token)
                self.redis.set('t2u:%s' % user_token, username)
            return {'queue_id': user_token,
                    'port': self.config.get('notifserver.port', 80),
                    'host': self.config.get('notifserver.host')}
        except Exception, ex:
            logger.error("Could not create user queue %s" % str(ex))

    def create_subscription(self, username, token):
        """ Map a token to a username """
        # s2u: subscription to user
        # u2s: user subscriptions
        retObj = {'queue_id': token,
                'port': self.config.get('notifserver.port', 80),
                'host': self.config.get('notifserver.host')}
        if self.redis.get("s2u:%s" % token):
            if self.redis.get("s2u:%s" % token) == username:
                return retObj
            logger.error("Token collision! %s" % token)
            return False
        self.redis.set("s2u:%s" % token, username)
        user_tokens = self.redis.lrange("u2s:%s" % username, 0, -1)
        if token not in user_tokens:
            self.redis.lpush("u2s:%s" % username, token)
        return retObj

    def delete_subscription(self, username, token):
        """ remove a subscription """
        tuser = self.redis.get("s2u:%s" % token)
        if tuser != username:
            raise NotifStorageException(("Attempted to remove token %s not " +
                                        "for username %s") %
                         (token, username))
        self.redis.delete("s2u:%s" % token)
        # remove all instances of the token from the user's list
        # note, python redis reverses the lrem arguments, which is Awesome ._.
        self.redis.lrem('u2s:%s' % username, token, 1)
        # remove pending messages of that subscription:
        message_list = self.redis.lrange('u2m:%s' % username, 0, -1)
        for message in message_list:
            redStore = json.loads(message)
            origin = redStore.get('origin', None)
            if origin is not None and origin == token:
                self._cleanMessage(username, message)

    def publish_message(self, message, token, origin = None):
        """ add message to a user queue """
        # resolve token to user
        username = self.redis.get("t2u:%s" % token)
        if username:
            return self.send_broadcast(message, username, origin = origin)
        return False

    def _cleanMessage(self, username, message):
        """ """
        dead_file = os.path.join(self._user_storage_path(username),
                                 json.loads(message).get('file'))
        logger.info("Removing expired msg file %s" % dead_file)
        try:
            os.remove(dead_file)
        except OSError:
            pass
        self.redis.lrem('u2m:%s' % username, message, 0)

    def queue_message(self, message, queue_name, origin = None):
        # resolve queue to user
        username = self.redis.get("s2u:%s" % queue_name)
        if username:
            self.send_broadcast(message, username, origin = origin)
        return False

    def send_broadcast(self, message, username, origin = None):
        """ append message to user's out queue
            queue = user/_tok/en_as_path/new_message_token
        """
        max_msgs = int(self.config.get('redis.max_msgs_per_user', '200'))
        file_ok = False
        doc_path = self._user_storage_path(username)

        if not os.path.exists(doc_path):
            os.makedirs(doc_path)
        try:
            while (not file_ok):
                doc_file = base64.urlsafe_b64encode(self.new_token())
                file_ok = not os.path.isfile(os.path.join(doc_path, doc_file))
            file_path = os.path.join(doc_path, doc_file)
            file = os.open(file_path, os.O_WRONLY | os.O_CREAT)
            os.write(file, message)
            os.close(file)
        except IOError, e:
            logger.error("Could not write message file %s" % str(e))
            raise NotifStorageException("Error storing message content")
        top_index = 0
        index_record = self.redis.lindex("u2m:%s" % username, 0)
        if index_record is not None:
            top_index = json.loads(index_record).get("id", 0)
        parsed_message = json.loads(message)
        message_body = json.loads(parsed_message.get('body'))
        now = int(time.time())
        timestamp = parsed_message.get('timestamp', int(time.time()))
        if timestamp > now:
            timestamp == now
        redStore = {'file': doc_file,
                    'origin': origin,
                    'expry': int(timestamp + message_body.get('ttl',
                        self.config.get('notifserver.max_ttl_seconds',
                                        259200))),
                    'id': top_index + 1}
        logger.debug('Adding message for %s' % username)
        self.redis.lpush("u2m:%s" % username, json.dumps(redStore))
        old = self.redis.lrange("u2m:%s" % username, 0, 0-max_msgs)
        if len(old):
            for message in old:
                self._cleanMessage(username, message)
            self.redis.ltrim("u2m:%s" % username, 0, max_msgs)
        return {"id": top_index + 1}

    def get_pending_messages(self, username, since = None):
        """ send messages to user """
        doc_path = self._user_storage_path(username)
        message_list = self.redis.lrange('u2m:%s' % username, 0, -1)
        result = []
        buffer = None
        for message in message_list:
            mstruct = json.loads(message)
            if since is not None:
                if mstruct.get('id') < since:
                    continue
            if mstruct.get('expry', int(time.time())) < int(time.time()):
                self._cleanMessage(username, message)
                continue
            try:
                file_path = os.path.join(doc_path, mstruct.get('file'))
                stat = os.lstat(file_path)
                file = os.open(file_path, os.O_RDONLY)
                buffer = os.read(file, stat.st_size)
                os.close(file)
            except OSError, e:
                logger.warn("Message missing %s [e]" % (file_path, str(e)))
                self._cleanMessage(username, message)
                continue
            result.append(json.loads(buffer))
        return result

    def _purge(self, username = None):
        """ purge old/expired messages """
        old = self.redis.lrange("u2m:%s" % username, 0, -1)
        if len(old):
            for message in old:
                self._cleanMessage(username, message)
            self.redis.ltrim("u2m:%s" % username, 0, -1)
        pass
