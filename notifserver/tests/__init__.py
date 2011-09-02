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

from services.auth.dummy import DummyAuth

class FakeRequest(object):
    """
     Fake request object for testing only
    """

    def __init__(self,
                 path="/",
                 environ=None,
                 post=None,
                 get=None,
                 host="localhost:80",  # match UnitTest's fake localhost
                 **kw):
        self.path_info = path
        self.environ = environ or {}
        self.POST = post or {}
        self.params = get or {}
        self.params.update({'audience': 'test.example.org'})
        self.host = host


class FakeAuthTool(DummyAuth):
    """
    Fake Auth tool returns invalid for any password containing "bad"
    The username is hashed by this point.
    """

    def authenticate_user(self, *userpass):
        if "bad" in userpass[1]:
            return None
        return 'test_api_1'
