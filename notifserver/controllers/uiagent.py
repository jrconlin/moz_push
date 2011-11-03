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
#  JR Conlin <jrconlin@mozilla.com>
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

from services.formatters import json_response
from webob import Response
from webob.exc import (HTTPOk, HTTPBadRequest, 
            HTTPInternalServerError, HTTPUnauthorized,
            HTTPFound)
from notifserver.controllers import BaseController
from notifserver.controllers.clientagent import ClientAgent
from notifserver.storage import (get_message_backend,
                                 new_token,
                                 NotifStorageException)

logger = logging.getLogger('uiagent')


class UIAgent(BaseController):
    """Carries out actions on behalf of clients.

    Handles all user/client registration with the server, as well as
    exchange/queue creation with the message broker.

    """

    def _init(self, config):
        self.msg_backend = get_message_backend(config)
        self.auth = self.app.auth.backend
        self.auth.__init__(config = config)
        self.client_agent = ClientAgent(self.app)

    def _auth(self, request):
        if request.params.get('paste.testing', False):
            username = request.environ.get('test_session.uid')
            password = request.environ.get('test_session.password')
        else:
            username = request.params.get('username')
            password = request.params.get('password')
            user_id = self.auth.authenticate_user(username, password, 
                    request = request)
        session = request.environ['beaker.session']
        logging.debug("Setting user_id to %s" % user_id)
        session['uid'] = user_id
        session.save()
        return user_id

    def _get_uid(self, request, doAuth = True):
        """ Get the cached UID, or authenticate the user.
        """
        uid = self.get_session_uid(request)
        if uid is None:
            if doAuth == False:
                return None
            self._auth(request)
            return request.environ.get('beaker.session', {}).get('uid', None)
        return uid

    def _get_params(self, request):
        params = dict(request.GET)
        str_params = {}
        for key, value in params:
            str_params[str(key)] = str(value);
        return str_params

    def index(self, request, **kw):
        self._init(self.app.config)
        doAuth = len(kw) != 0
        logger.debug('session.beaker.uid = %s' % 
                request.environ.get('session.beaker',{}).get('uid','None'))
        username = self._get_uid(request, doAuth = doAuth)
        logger.debug('username = %s' % username)
        response = {'username': username }
        if username is None:
            # display login page
           template = self.get_template("not_logged_in")
        else:
            # Create the user queue if necessary.
            self.client_agent.user_queue(request)
            template = self.get_template("logged_in")
            response['user_info'] = self.msg_backend.user_info(username)
            response['subscriptions'] = self.msg_backend.get_queues(username)
        content_type = "text/html"  # it's always text/html
        body = template.render(request = request,
                                config = self.app.config,
                                response = response
                                )
        return Response(str(body),
                        content_type = content_type)

    def logout(self, request, **kv):
        try:
            session = request.environ['beaker.session']
            session['uid']=None
            session.save()
        except KeyError:
            pass
        raise HTTPFound(location = '/')
            
