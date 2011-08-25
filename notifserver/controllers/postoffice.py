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
import logging

from mako.template import Template
from services.util import convert_config
from services.pluginreg import _resolve_name
from webob import Response
from webob.dec import wsgify
from webob.exc import HTTPAccepted, HTTPBadRequest
from notifserver.controllers import BaseController
from notifserver.storage import get_message_backend


logger = logging.getLogger('postoffice')


class PostOfficeController(BaseController):
    """Forwards messages on behalf of web apps.

    The POST Office (named so due to the fact that it only accepts POST
    requests) simply takes messages and forwards them to the message
    broker for routing.

    If run in a development environment, the POST Office can perform
    validation of incoming messages itself. For production environments
    however, this does not scale, so it simply dumps any messages into
    a queue in the broker which are validated and routed to their
    destination by another worker.

    """

    def _init(self, config, validator = None):
        self.msg_backend = get_message_backend(config)
        self.msg_queue_name = config.get('notifs_queue_name')
        if validator is None:
            validator = config.get('validator', None)
            if validator is not None:
                try:
                    self.validator = _resolve_name(validator)
                except ImportError:
                    raise KeyError('Validator class not found %s' % validator)
        else:
            self.validator = validator

    def handlePost(self, request, **kw):
        pdb.set_trace()
        if not self.msg_backend:
            self._init(self.app.config)
        logger.info("Message received: %s", request.body)

        if self.validator:
            logger.info("self validating")
            # If we're validating ourselves route message directly
            return self.route_message(request)
        else:
            # Otherwise forward message to be validated later
            logger.info("no local validator")
            return self.forward_message(request)

    def route_message(self, request):
        """Validates and routes message to recipient."""
        if not self.msg_backend:
            self._init(self.app.config)
        try:
            msg = json.loads(request.body)
            body = json.loads(msg['body'])

            self.validator.validate(msg, body)
        except ValueError, e:
            raise HTTPBadRequest("Invalid post; missing body")

        try:
            self.msg_backend.publish_message(json.dumps(msg), body['token'])
            return HTTPAccepted()
        except:
            logger.error("Error publishing message with token '%s'" % body['token'])
            raise

    def forward_message(self, request):
        """Queues messages in the message broker to be validated at a later time."""
        try:
            self.msg_backend.queue_message(request, self.msg_queue_name)
            return HTTPAccepted()
        except:
            logger.error("Error queueing message in message broker")
            raise


    def index(self, request, **kw):
        template = self.get_template("index")
        content_type = "text/html"      #it's always text/html
        response = {}

        import pdb;pdb.set_trace();
        body = template.render(request = request,
                                config = self.app.config,
                                response = response)
        return Response(str(body),
                        content_type = content_type)
#
#def make_post_office(global_config, **local_config):
#    """Creates a POST Office that simply queues messages in the broker.
#
#    This is a factory function for integration with Paste.
#    """
#    config = global_config.copy()
#    config.update(local_config)
#    params = convert_config(config)
#    return PostOfficeController(params)
#
#
#def make_post_office_router(global_config, **local_config):
#    """Creates a POST Office that validates and routes messages.
#
#    This is useful for development environments where running
#    a separate validation/routing server is inconvenient.
#
#    This is a factory function for integration with Paste.
#    """
#    config = global_config.copy()
#    config.update(local_config)
#    params = convert_config(config)
#    return PostOfficeController(params, NotificationValidator())
