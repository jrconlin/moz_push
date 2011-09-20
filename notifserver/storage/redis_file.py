import base64
import json
import random
import cPickle
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
        self
        # s2u: subscription to user
        # u2s: user subscriptions
        if self.redis.get("s2u:%s" % token):
            logger.error("Token collision! %s" % token)
            return False
        self.redis.set("s2u:%s" % token, username)
        user_tokens = self.redis.lrange("u2s:%s" % username, 0, -1)
        if token not in user_tokens:
            self.redis.lpush("u2s:%s" % username, token)
        return {'queue_id': token,
                'port': self.config.get('notifserver.port', 80),
                'host': self.config.get('notifserver.host')}

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
            origin =redStore.get('origin', None)
            if origin is not None and origin == token:
                self._cleanMessage(username, message)

    def publish_message(self, message, token):
        """ add message to a user queue """
        # resolve token to user
        username = self.redis.get("t2u:%s" % token)
        if username:
            return self.send_broadcast(message, username, origin = token)
        return False

    def _cleanMessage(self, username, message):
        """ """
        dead_file = json.loads(message).get('file')
        logger.info("Removing expired msg file %s" % dead_file)
        try:
            os.remove(dead_file)
        except OSError:
            pass
        self.redis.lrem('u2m:%s' % username, message, 0)

    def queue_message(self, message, queue_name):
        # resolve queue to user
        username = self.redis.get("s2u:%s" % queue_name)
        if username:
            self.send_braodcast(message, username)
        return False

    def send_broadcast(self, message, username, origin = None):
        """ append message to user's out queue
            queue = user/_tok/en_as_path/new_message_token
        """
        user_queue = self.create_client_queue(username)
        user_token = user_queue.get('queue_id')
        max_msgs = int(self.config.get('redis.max_msgs_per_user', '200'))
        file_ok = False
        doc_path = self._user_storage_path(username)
        if not os.path.exists(doc_path):
            os.makedirs(doc_path)
        while (not file_ok):
            doc_file = base64.urlsafe_b64encode(self.new_token())
            file_ok = not os.path.isfile(os.path.join(doc_path, doc_file))
        file_path = os.path.join(doc_path, doc_file)
        file = os.open(file_path, os.O_WRONLY | os.O_CREAT)
        os.write(file, message)
        os.close(file)
        top_index = 0
        index_record = self.redis.lindex("u2m:%s" % username, 0)
        if index_record is not None:
            top_index = json.loads(index_record).get("id", 0)
        parsed_message = json.loads(message)
        message_body = json.loads(parsed_message.get('body'))
        redStore = {'file': doc_file,
                    'origin': origin,
                    'expry': int(time.time() + message_body.get('ttl',
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
                logger.warn("Message missing %s" % file_path)
                self._cleanMessage(username, message)
                continue
            result.append(buffer)
        return result

    def purge(self):
        """ purge old/expired messages """
        pass
