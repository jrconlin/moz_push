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

import logging

from services.auth import get_auth 
from services.util import convert_config
from webob.dec import wsgify
from webob.exc import HTTPUnauthorized 

logger = logging.getLogger('auth')

class BasicAuthMiddleware(object):
    """Wraps a WSGI app so that authentication is required."""

    def __init__(self, app, realm, config):
        self.app = app 
        self.auth = get_auth(config)
        self.realm = realm

    @wsgify
    def __call__(self, request):
        if not self.authorized(request):
            logger.error("User not authorized")
            headers = [('WWW-Authenticate', 'Basic realm="%s"' % self.realm)]
            raise HTTPUnauthorized(headerlist=headers)
        else:
            logger.debug("Authorized user '%s'", request.environ['REMOTE_USER'])
            return self.app 

    def authorized(self, request):
        if 'authorization' not in request.headers:
            logger.error("HTTP request lacks 'Authorization' header")
            return False

        auth_header = request.headers['authorization']
        auth_type, encoded = auth_header.split(None, 1)
        if not auth_type.lower() == 'basic':
            logger.error("Invalid 'Authorization' header: %s", auth_header)
            return False

        username, password = encoded.decode('base64').split(':', 1)
        request.environ['REMOTE_USER'] = username

        logger.debug("Checking credentials of user '%s'", username)
        return self.auth.authenticate_user(username, password)


def make_basic_auth(app, global_config, realm, **local_config):
    """App factory function for integration with Paste."""
    config = global_config.copy()
    config.update(local_config)
    params = convert_config(config)
    return BasicAuthMiddleware(app, realm, params)

