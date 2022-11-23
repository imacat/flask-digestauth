# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/10/22

#  Copyright (c) 2022 imacat.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""The test case for the HTTP digest authentication.

"""
import typing as t
from secrets import token_urlsafe
from types import SimpleNamespace

from flask import Response, Flask, g
from flask_testing import TestCase

from flask_digest_auth import DigestAuth, make_password_hash, Client

_REALM: str = "testrealm@host.com"
_USERNAME: str = "Mufasa"
_PASSWORD: str = "Circle Of Life"


class AuthenticationTestCase(TestCase):
    """The test case for the HTTP digest authentication."""

    def create_app(self):
        """Creates the Flask application.

        :return: The Flask application.
        """
        app: Flask = Flask(__name__)
        app.config.from_mapping({
            "SECRET_KEY": token_urlsafe(32),
            "TESTING": True
        })
        app.test_client_class = Client

        auth: DigestAuth = DigestAuth(realm=_REALM)
        user_db: t.Dict[str, str] \
            = {_USERNAME: make_password_hash(_REALM, _USERNAME, _PASSWORD)}

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            """Returns the password hash of a user.

            :param username: The username.
            :return: The password hash, or None if the user does not exist.
            """
            return user_db[username] if username in user_db else None

        @auth.register_get_user
        def get_user(username: str) -> t.Optional[t.Any]:
            """Returns a user.

            :param username: The username.
            :return: The user, or None if the user does not exist.
            """
            return SimpleNamespace(username=username) if username in user_db \
                else None

        @app.get("/login-required-1/auth", endpoint="auth-1")
        @auth.login_required
        def login_required_1() -> str:
            """The first dummy view.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #1"

        @app.get("/login-required-2/auth", endpoint="auth-2")
        @auth.login_required
        def login_required_2() -> str:
            """The second dummy view.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #2"

        return app

    def test_auth(self) -> None:
        """Tests the authentication.

        :return: None.
        """
        response: Response = self.client.get(self.app.url_for("auth-1"))
        self.assertEqual(response.status_code, 401)
        response = self.client.get(
            self.app.url_for("auth-1"), digest_auth=(_USERNAME, _PASSWORD))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         f"Hello, {_USERNAME}! #1")
        response: Response = self.client.get(self.app.url_for("auth-2"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         f"Hello, {_USERNAME}! #2")
