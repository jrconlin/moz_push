import json
import urllib
import pycurl
import StringIO

from notifserver.notify import (Notify, NotifyException, logger)
from webob.response import Response

class Android(Notify):

    SEND_OK = 0
    SEND_BAD_USER = 1
    SEND_TIMEOUT = 2

    def __init__(self, config=None):
        if config is None:
            self.config['publish.android_url'] = \
                'https://android.apis.google.com/c2dm'
        else:
            self.config = config


    def register(self, user):
        # Get a token for the user and store it into the user's data.
        pass

    def send (self, user, notification):
        #Send the notification tickler to the Google Cloud
        publish_message = {
            "registration_id": user.get('droid_registration_id'),
            "collapse_key": 'mozilla_notify_push'
        }
        #Semi-arbitrary content not displayed.
        publish_message['data.alert'] = "You've got notifications"
        # publish_message['data.url'] = "fetch url?"

        http_headers = {}
        http_headers['Authorization'] = \
                    self.config.get('publish.android_auth_token')
        if http_headers.get("Authorization", None) is None:
            raise NotifyException(NotifyException.SERVER,
                                  "No auth_token specified")

        try:
            buffer = StringIO.StringIO()

            """ Why pycurl instead of liburl? pycurl checks https certs,
            provides timeouts, and other things. """
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, self.config.get('publish.android_url'))
            curl.setopt(pycurl.FOLLOWLOCATION, 1)
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDS, publish_message)
            curl.setopt(pycurl.HTTPHEADER,  http_headers)
            curl.setopt(pycurl.WRITEFUNCTION, buffer.write)
            curl.setopt(pycurl.HEADER, 1)
            curl.perform()
            curl.close()
            return_code = curl.getinfo(pycurl.HTTP_CODE)
            [raw_header, raw_body] = buffer.getvalue().split("\r\n\r\n",2)
            response = Response(buffer.getvalue())
            if return_code != 200:
                if return_code == 401:
                    raise NotifyException(return_code,
                                          "Invalid user specified")
                if return_code == 503:
                    #pull the back-off value
                    self.backoff = response.headers.get('Retry-After')
                    #sleep(self.backoff)
                    #self.send(user, notification)
                raise NotifyException(return_code,
                                      "Unclassified Error")
            else:  #Check the body.
                reply = json.loads(response.body)
        except Exception, e:
            import pdb; pdb.set_trace();
            logger.error("failure to send post %s" % str(e))
            raise NotifyException("Notificfation not sent")
