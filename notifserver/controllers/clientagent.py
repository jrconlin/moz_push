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

import base64
import json
import logging

from services.util import convert_config, json_response
from webob.dec import wsgify
from webob.exc import HTTPOk, HTTPBadRequest, HTTPInternalServerError

from notifserver.storage import get_message_backend


logger = logging.getLogger('clientagent')


class ClientAgent(object):
    """Carries out actions on behalf of clients.

    Handles all user/client registration with the server, as well as
    exchange/queue creation with the message broker.

    """

    def __init__(self, config):
        self.msg_backend = get_message_backend(config)
        self.post_urls = {
            '/1.0/new_queue': self.new_queue,
            '/1.0/new_subscription': self.new_subscription,
            '/1.0/remove_subscription': self.remove_subscription,
            '/1.0/broadcast': self.broadcast,
        }

    @wsgify
    def __call__(self, request):
        path = request.path
        verb = request.method

        # TODO: Use routes (although the utility would be very small given the
        # few number of paths we actually support)
        if verb == 'POST':
            if path in self.post_urls:
                return self.post_urls[path](request)

        raise HTTPBadRequest("API request %s %s not supported" % (verb, path))

    def new_queue(self, request):
        username = request.environ['REMOTE_USER']

        try:
            result = self.msg_backend.create_client_queue(username)
            return json_response(result)
        except:
            logger.error("Error creating client queue")
            raise

    def new_subscription(self, request):
        username = request.environ['REMOTE_USER']

        try:
            logger.debug("New subscription request: '%s'", request.body)
            subscription = json.loads(request.body)
        except ValueError as verr:
            logger.error("Error parsing subscription JSON")
            raise HTTPBadRequest("Invalid JSON")

        if 'token' not in subscription or not subscription['token']:
            logger.error("Token not specified")
            raise HTTPBadRequest("Need to specify token to create")

        # Extract the token as ASCII (Pika doesn't work with Unicode)
        token = subscription['token'].encode('ascii')
        logger.info("Subscribing user '%s' to token '%s'", username, token)

        try:
            self.msg_backend.create_subscription(username, token)
            return HTTPOk()
        except:
            logger.error("Error creating subscription.")
            raise

    def remove_subscription(self, request):
        username = request.environ['REMOTE_USER']

        try:
            logger.debug("Remove subscription request: '%s'", request.body)
            subscription = json.loads(request.body)
        except ValueError as verr:
            logger.error("Error parsing subscription JSON")
            raise HTTPBadRequest("Invalid JSON")

        if 'token' not in subscription or not subscription['token']:
            logger.error("Token not specified")
            raise HTTPBadRequest("Need to specify a token to cancel")

        # Fetch token as ASCII (Pika doesn't work with Unicode)
        token = subscription['token'].encode('ascii')
        logger.info("Unsubscribing user '%s' from token '%s'", username, token)

        try:
            self.msg_backend.delete_subscription(username, token)
            return HTTPOk()
        except:
            logger.error("Error deleting subscription")
            raise

    def broadcast(self, request):
        username = request.environ['REMOTE_USER']

        try:
            logger.debug("Broadcast request: '%s'", request.body)
            logger.debug("Broadcast Message length: %s", len(request.body))
            broadcast_msg = json.loads(request.body)
        except ValueError as verr:
            logger.error("Error parsing broadcast JSON")
            raise HTTPBadRequest("Invalid JSON")

        if 'body' not in broadcast_msg:
            logger.error("Body not specified")
            raise HTTPBadRequest("Need to include body with broadcast")

        if 'HMAC' not in broadcast_msg:
            logger.error("HMAC not specified")
            raise HTTPBadRequest("Need to include HMAC with broadcast")

        logger.info("Broadcasting message for user '%s'", username)

        try:
            self.msg_backend.send_broadcast(request.body, username)
        except:
            logger.error("Error sending broadcast message to user '%s'", username)
            raise


def make_client_agent(global_config, **local_config):
    config = global_config.copy()
    config.update(local_config)
    params = convert_config(config)
    return ClientAgent(params)
