import base64
import json
import random
import cPickle
import time
import redis
import os

import pdb

from notifserver.storage import (logger, NotifStorageException)

class RedisStorage(object):

    is_connected = False
    connection = None

    def __init__(self, **config):
        self.config = config
        self.db_host = self.config.get('host', 'localhost')
        self.db_port = int(self.config.get('port', '6379'))
        self.redis = redis.Redis(host = self.db_host,
                                port = self.db_port)

        """ schemas:
            mapping:
            t:### => u:###  incoming token to user

            u:### => [t:###, t:###]     user to tokens

            u:##/##/###.. token lists as files using cPickle to store the data.
        """

    @classmethod
    def get_name(cls):
        return 'redis'

    def new_token(self):
        return "%x" % random.getrandbits(256)

    def create_client_queue(self, username):
        logger.info("Creating incoming queue for %s for user %s")
        channel_info = {'queue_id': self.new_token()}
        try:
            user_token_list = self.redis.get("u:%s" % username)
            # add token to user list
            # add mapping for token to user.
            return channel_info
        except Exception, e:
            logger.error("Could not create user queue")

    def create_subscription(self, username, token):
        """ Map a token to a username """
        # get user list
        # add token to list (if not already present)
        # add mapping to user (if not already present)

    def delete_subscription(self, username, token):
        """ remove a subscription """
        # delete mapping to user
        # get user token map
        # remove token from user map

    def publish_message(self, message, token):
        """ add message to a user queue """
        # resolve token to user
        self.send_broadcast(message, username)

    def queue_message(self, message, queue_name):
        # resolve queue to user
        self.send_braodcast(message, username)

    def send_broadcast(self, message, username):
        """ append message to user's out queue """
        # lock/open file, read file
        # clear expired, old
        # append message
        # write and return

    def get_pending_messages(self, username, since = None):
        """ send messages to user """
        # open file, read file, close file
        # unpickle list
        # add valid messages to out list

    def purge(self):
        """ purge old/expired messages """
       
