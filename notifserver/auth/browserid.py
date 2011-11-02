import json

from cef import log_cef
from services.wsgiauth import Authentication
from webob.exc import (HTTPTemporaryRedirect, HTTPUnauthorized)
#from notifserver.controllers import BaseController
from notifserver.auth.jws import (JWS, JWSException)

# TODO: This needs to be integrated to the LDAP server (for end user control).

class NotifServerAuthentication(object):
    """ for this class, username = user's email address, password = assertion """

    def __init__(self, *args, **kw):
        self.config = kw.get('config', {})
        self.environ = kw.get('environ', {})
        self.username = None
        self.assertion = None
        self.raw_assertion = None

    def authenticate_user(self, user_name, password, request = None):
        """ Return a validated user id """
        if password is None:
            # Perhaps the UI folks messed up. Try to get the 
            # assertion from the arguments.
            if request.params.get('assertion', None) is None:
               return None
            password = request.params.get('assertion')
        try:
            if request:
                self.environ = request.environ
            raw_assertion = password;
            jws = JWS(config = self.config,
                      environ = request.environ)
            assertion = jws.parse(raw_assertion)
            # get the latest id name, fail to old id name 
            email = assertion.get('certificates')[0]\
                .get('payload').get('principal').get('email')
            #email = assertion.get('moz-vep-id', assertion.get('email'))
            self.username = email
            self.assertion = assertion
            self.raw_assertion = raw_assertion
            return self.username

        except JWSException, e:
            log_cef("Error parsing assertion, %s" % e,
                    5,
                    environ = request.environ,
                    config = self.config)
            raise HTTPUnauthorized("Invalid assertion")
        except (ValueError, KeyError), e:
            import pdb; pdb.set_trace()
            log_cef("Unparsable request body %s" % str(e),
                    5, {}, {})
            raise HTTPUnauthorized("Invalid token")

    def get_user_id(self, user_name):
        return self.username

    def get_session_uid(self, request):
        return self.username

    def get_assertion(self):
        return self.raw_assertion

    def check(self, request, match):
        if self.get_session_uid(request) is not None:
            return
        user_id = self.authenticate_user(request, self.config)
        user_id = "1"
        if user_id is None:
            data = request.method, request.path_info, {}
            request.environ['beaker.session']['redirect'] = data
            raise HTTPTemporaryRedirect(location='/login')
        match['user_id'] = user_id
