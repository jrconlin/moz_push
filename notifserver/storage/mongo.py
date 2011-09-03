import base64
import json
import random
import urllib
import pymongo
import time

import pdb

from notifserver.storage import (logger, NotifStorageException)
from pymongo.errors import OperationFailure

class MongoStorage(object):

    is_connected = False
    connection = None

    def __init__(self, **config):
        self.config = config
        self.db_host = self.config.get('host', 'localhost')
        self.db_port = int(self.config.get('port', '27017'))
        self.db_name = self.config.get('database', 'notif')
        self.mongo = pymongo.Connection(host = self.db_host,
                                     port = self.db_port
                                     )
        self.db = self.mongo[self.db_name]
        """ schemas:
        mapping:
        _id : unique post id
        user_id: user's id.
        """
        """
        messages:
        _id :
        user_id :   user's id
        origin : origin ID
        expry : Expiration (TTL for message + current time)
        """

    @classmethod
    def get_name(cls):
        return 'mongo'

    def create_client_queue(self, username):
        # create the mapping record

        channel_info = {u'_id': username,
                        u'created': int(time.time())
                        }

        logger.info("Creating incoming queue %s for user %s",
                    channel_info.get('_id'),
                    username)
        try:
            self.db.user.insert(channel_info, safe=True)
            return { 'queue_id': channel_info['_id']}

        except OperationFailure:
            logger.error('Could not create mapping: %s' % str(e))
            return False

    def create_subscription(self, username, token):
        """Map token to username"""
        mapping_info = {'_id': token,
                        'user': username}

        try:
            self.db.mapping.insert(mapping_info, safe=True)
            return True
        except OperationFailure:
            logger.error('Could not create subscription: %s' % str(e))
            return False

    def delete_subscription(self, username, token):

        try:
            self.db.mapping.remove({u'_id': token})
            self.db.user.remove({'user_id': username,
                                 'origin': token})
            return True
        except OperationFailure:
            logger.error('Could not remove mappning for subscription %s'
                         % str(e))
            return False

    def _resolve_token(self, token):
        try:
            mapping = self.db.mapping.get(token)
            if mapping is None or mapping.get('user', None) is None:
                return None
            return mapping.get('user')
        except OperationalError, e:
            logger.error('Could not find mapping to user for token %s, %s',
                         token, str(e))
            return None

    def publish_message(self, message, token):
        # This really should push to a single device.
        user = self._resolve_token(token)
        if user is None:
            return False

        return self.send_broadcast(message, user)

    def queue_message(self, message, queue_name):
        return self.publish_message(message, queue_name)

    def send_broadcast(self, message, username):
        msg_content = {}
        ttl = int(self.config.get('max_ttl_seconds', '259200')) # 3 days
        try:
            msg_content = json.loads(message)
            ttl = msg_content.get('ttl', ttl)
            self.db.user.save({u'user_id': mapping.get('user'),
                           'origin': token,
                           'expry': int(time.time() + ttl)})
            #TODO:: Add in notification to tickle listening clients (if desired)
        except OperationError, e:
            logger.error("Could not save message to %s from %s " %(
                mapping.get('user'), token
            ))
        except ValueError, e:
            logger.error("message is not valid JSON, ignoring %s" %
                         str(e))
            return False

    def get_pending_messages(self, username = None, since = None):
        result = []
        if username is None:
            return result
        query = {u'user_id': username}
        # TODO: set a default 'since' ?
        if since is not None:
            query['ttl'] = {'$gt': since}
        return list(self.db.user.find(query))

    def purge(self):
        try:
            self.db.remove({'expry': {'$lt': int(time.time())}})
        except OperationError, e:
            logger.error("Could not purge old messages: %s", str(e))