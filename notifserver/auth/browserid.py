import json

from cef import log_cef
from services.wsgiauth import Authentication
from webob.exc import (HTTPTemporaryRedirect, HTTPUnauthorized)
#from notifserver.controllers import BaseController
from notifserver.auth.jws import (JWS, JWSException)

# TODO: This needs to be integrated to the LDAP server (for end user control).

class NotifServerAuthentication(object):
    """ for this class, username = user's email address, password = assertion """

    def authenticate_user(self, user_name, password):
        """ Return a validated user id """

        try:
            import pdb; pdb.set_trace()
            raw_assertion = password;
            jws = JWS(config = self.config,
                      environ = {} )
            assertion = jws.parse(raw_assertion)
            return assertion

        except JWSException, e:
            log_cef("Error parsing assertion, %s" % e,
                    5,
                    environ = self.environ,
                    config = self.config)
            raise HTTPUnauthorized("Invalid assertion")
        except (ValueError, KeyError), e:
            log_cef("Unparsable request body %s" % str(e),
                    5, {}, {})
            raise HTTPUnauthorized("Invalid token")

    def get_user_id(self, user_name):
        return user_name

    def get_session_uid(self, request):
        return "1"

    def check(self, request, match):
        if self.get_session_uid(request) is not None:
            return
#        user_id = self.authenticate_user(request, self.config)
        user_id = "1"
        if user_id is None:
            data = request.method, request.path_info, {}
            request.environ['beaker.session']['redirect'] = data
            raise HTTPTemporaryRedirect(location='/login')
        match['user_id'] = user_id
