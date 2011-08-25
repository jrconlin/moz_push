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
#  Paul Sawaya <me@paulsawaya.com>
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

"""TODO: convert this to async handlers for pika.
    How are sse channels broken?
    How do we requeue a message that may go to a broken pipe.
"""
import json

from notifserver.storage import get_message_backend
from notifserver.controllers import BaseController
from services.config import Config
from pika.adapters.blocking_connection import BlockingConnection
from webob.response import Response
from services.pluginreg import _resolve_name

class ServerEventController(BaseController):
    connection = None

    def _connect(self, config):
        self.config = config

        self.msg_backend = get_message_backend(config)
        self.msg_queue_name = self.config.get('notifs_queue_name')

        self.validator = self.config.get('validator', None)
        if self.validator is not None:
            self.validator

    def handlefeed(self, request, **kw):
        connection = self._connect(self.app.config)

    def on_connected(self, connection):
        """ Fully connected to Rabbit """


    def makeAMQPConnection(self, token='', callback=None):
        def notifsCallback(msg):
            if callback:
                callback(msg)
            print " [x] Received %r \n \n for token %s" % (msg.body, token)

        def on_connect():
            print "on_connect for token %s" % token
            ch = self.conn.channel()
            ch.queue_declare(queue=token, durable=True, exclusive=False, auto_delete=False)
            ch.consume(token, notifsCallback, no_ack=True)
            ch.qos(prefetch_count=1)

        self.conn = Connection()
        self.conn.connect(on_connect)

    def handle_feed(self, request, **kw):

        self._connect(self.app.config)

        import pdb; pdb.set_trace()
        items =self.msg_backend.get_pending_messages(
                    request.sync_info.get('usertoken'))
        body= '/*' + json.dumps(items)
        response = Response(str(body))
        response.headers.add('Content-Type', 'application/json')

        return response

        #thisSSE = self

        #class NotificationsWebHandler(tornado.web.RequestHandler):
        #    @tornado.web.asynchronous
        #    def get(self, token):
        #        self.set_header("Content-Type","text/event-stream")
        #        self.set_header("Cache-Control","no-cache")
        #        self.set_header("Connection","keep-alive")

        #        self.notifID = 0

        #        self.flush()

        #        def callbackFunc(msg):
        #            print "about to publish %s" % msg.body
        #            self.publishNotification(msg.body)

        #        thisSSE.makeAMQPConnection(token, callbackFunc)

        #    @tornado.web.asynchronous
        #    def publishNotification(self, notifData):
        #        self.write("id: %i\n" % self.notifID)
        #        self.write("data:")
        #        self.write(notifData)
        #        self.write("\n\n")
        #        self.flush()

        #        self.notifID+=1

        #        print "published: %s" % notifData


def make_sse_server(config_filename):
    configItems = ['configuration', 'broker_host', 'broker_amqp_port', 'broker_username', 'broker_password', 'broker_virtual_host', 'incoming_exchange_name', 'notifs_queue_name']
    SSEConfig = Config(config_filename)
    configMap = dict([(item, SSEConfig.get("app:post_office", item)) for item in configItems])

    return SSEServer(configMap)

if __name__ == "__main__":
    SSE = make_sse_server("../development.ini")
