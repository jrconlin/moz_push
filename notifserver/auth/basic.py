from services.wsgiauth import Authentication
from webob.exc import HTTPTemporaryRedirect
from notifserver.controllers import BaseController


class NotifServerAuthentication(Authentication, BaseController):

    def get_session_uid(self, request):
        return "1"

    def check(self, request, match):
        if self.get_session_uid(request) is not None:
            return
#        user_id = self.authenticate_user(request, self.config)
        user_id = "1"
        if user_id is None:
            data = request.method, request.path_info, params
            request.environ['beaker.session']['redirect'] = data
            raise HTTPTemporaryRedirect(location='/login')
        match['user_id'] = user_id
