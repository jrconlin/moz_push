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

import abc
import logging
from services.pluginreg import (PluginRegistry, load_and_configure)

# Use this logger for all MessageStorage plugins
logger = logging.getLogger('messagestorage')

class NotifStorageException (Exception):

    def __init(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class MessageStorage(PluginRegistry):
    """Abstract definition of all message store implementations."""
    plugin_type = 'messagestorage'

    @abc.abstractmethod
    def new_token(self):
        """Returns a new token consistent with the storage system index."""

    @abc.abstractmethod
    def get_name(self):
        """Returns the name of the plugin."""

    @abc.abstractmethod
    def create_client_queue(self, username):
        """Create a client queue for the specified user.

        Args:
            username: Name of user to create queue for.

        Returns:
            The queue name if successful;
            None otherwise.

        """

    @abc.abstractmethod
    def create_subscription(self, username, token):
        """Creates a subscription token.

        This will associate the token with the user so that
        any messages sent to it will be forwarded to the
        user's client queues.

        Args:
            username: Name of the user.
            token: Base64-encoded subscription token.

        Returns:
            True, if subscription was created successfully;
            False otherwise.

        """

    @abc.abstractmethod
    def delete_subscription(self, username, token):
        """Deletes a subscription token.

        This will remove any association between the token and
        the user.

        Args:
            username: Name of the user.
            token: Base64-encoded subscription token.

        Returns:
            True, if subscription was deleted;
            False otherwise.

        """

    @abc.abstractmethod
    def publish_message(self, message, token):
        """Publishes a message to a subscription token.

        This will forward the message to all clients registered with
        the user that created the token.

        Args:
            token: Base64-encoded subscription token.
            message: String message to send.

        Returns:
            True, if message was sent successfully;
            False otherwise.

        """

    @abc.abstractmethod
    def queue_message(self, message, queue_name):
        """Sends a message to a specified queue.

        Args:
            message: Message to put in the queue.
            queue_name: Name of the queue.

        Returns:
            True, if a message was sent successfully;
            False otherwise.

        """

    @abc.abstractmethod
    def send_broadcast(self, message, username):
        """Broadcasts a message to all clients registered to a user.

        Args:
            message: String message to send.
            username: Name of user to send messages to.


        Returns:
            True, if broadcast was sent successfully;
            False otherwise.

        """

def get_message_backend(config):
    return load_and_configure(config, cls_param = "notifserver.backend")
