# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/10/22

#  Copyright (c) 2022-2023 imacat.
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

from flask import Response, Flask, g, redirect, request
from flask_testing import TestCase
from werkzeug.datastructures import WWWAuthenticate, Authorization

from flask_digest_auth import DigestAuth, make_password_hash, Client

_REALM: str = "testrealm@host.com"
_USERNAME: str = "Mufasa"
_PASSWORD: str = "Circle Of Life"


class User:
    """A dummy user"""

    def __init__(self, username: str, password: str):
        """Constructs a dummy user.

        :param username: The username.
        :param password: The clear-text password.
        """
        self.username: str = username
        self.password_hash: str = make_password_hash(
            _REALM, username, password)
        self.visits: int = 0


class AuthenticationTestCase(TestCase):
    """The test case for the HTTP digest authentication."""

    def create_app(self):
        """Creates the Flask application.

        :return: The Flask application.
        """
        app: Flask = Flask(__name__)
        app.config.from_mapping({
            "TESTING": True,
            "SECRET_KEY": token_urlsafe(32),
            "DIGEST_AUTH_REALM": _REALM,
        })
        app.test_client_class = Client

        auth: DigestAuth = DigestAuth()
        auth.init_app(app)
        self.user: User = User(_USERNAME, _PASSWORD)
        user_db: t.Dict[str, User] = {_USERNAME: self.user}

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            """Returns the password hash of a user.

            :param username: The username.
            :return: The password hash, or None if the user does not exist.
            """
            return user_db[username].password_hash if username in user_db \
                else None

        @auth.register_get_user
        def get_user(username: str) -> t.Optional[t.Any]:
            """Returns a user.

            :param username: The username.
            :return: The user, or None if the user does not exist.
            """
            return user_db[username] if username in user_db else None

        @auth.register_on_login
        def on_login(user: User):
            """The callback when the user logs in.

            :param user: The logged-in user.
            :return: None.
            """
            user.visits = user.visits + 1

        @app.get("/admin-1/auth", endpoint="admin-1")
        @auth.login_required
        def admin_1() -> str:
            """The first administration section.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #1"

        @app.get("/admin-2/auth", endpoint="admin-2")
        @auth.login_required
        def admin_2() -> str:
            """The second administration section.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #2"

        @app.post("/logout", endpoint="logout")
        @auth.login_required
        def logout() -> redirect:
            """Logs out the user.

            :return: The response.
            """
            auth.logout()
            return redirect(request.form.get("next"))

        return app

    def test_auth(self) -> None:
        """Tests the authentication.

        :return: None.
        """
        response: Response = self.client.get(self.app.url_for("admin-1"))
        self.assertEqual(response.status_code, 401)
        response = self.client.get(
            self.app.url_for("admin-1"), digest_auth=(_USERNAME, _PASSWORD))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         f"Hello, {_USERNAME}! #1")
        response: Response = self.client.get(self.app.url_for("admin-2"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("UTF-8"),
                         f"Hello, {_USERNAME}! #2")
        self.assertEqual(self.user.visits, 1)

    def test_stale_opaque(self) -> None:
        """Tests the stale and opaque value.

        :return: None.
        """
        admin_uri: str = self.app.url_for("admin-1")
        response: Response
        www_authenticate: WWWAuthenticate
        auth_data: Authorization

        response = super(Client, self.client).get(admin_uri)
        self.assertEqual(response.status_code, 401)
        www_authenticate = response.www_authenticate
        self.assertEqual(www_authenticate.type, "digest")
        self.assertEqual(www_authenticate.stale, None)
        opaque: str = www_authenticate.opaque

        www_authenticate.nonce = "bad"
        auth_data = Client.make_authorization(
            www_authenticate, admin_uri, _USERNAME, _PASSWORD)
        response = super(Client, self.client).get(admin_uri, auth=auth_data)
        self.assertEqual(response.status_code, 401)
        www_authenticate = response.www_authenticate
        self.assertEqual(www_authenticate.stale, True)
        self.assertEqual(www_authenticate.opaque, opaque)

        auth_data = Client.make_authorization(
            www_authenticate, admin_uri, _USERNAME, _PASSWORD + "2")
        response = super(Client, self.client).get(admin_uri, auth=auth_data)
        self.assertEqual(response.status_code, 401)
        www_authenticate = response.www_authenticate
        self.assertEqual(www_authenticate.stale, False)
        self.assertEqual(www_authenticate.opaque, opaque)

        auth_data = Client.make_authorization(
            www_authenticate, admin_uri, _USERNAME, _PASSWORD)
        response = super(Client, self.client).get(admin_uri, auth=auth_data)
        self.assertEqual(response.status_code, 200)

    def test_logout(self) -> None:
        """Tests the logging out.

        :return: None.
        """
        admin_uri: str = self.app.url_for("admin-1")
        logout_uri: str = self.app.url_for("logout")
        response: Response

        response = self.client.get(admin_uri)
        self.assertEqual(response.status_code, 401)

        response = self.client.get(admin_uri,
                                   digest_auth=(_USERNAME, _PASSWORD))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(admin_uri)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(logout_uri, data={"next": admin_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, admin_uri)

        response = self.client.get(admin_uri)
        self.assertEqual(response.status_code, 401)

        response = self.client.get(admin_uri,
                                   digest_auth=(_USERNAME, _PASSWORD))
        self.assertEqual(response.status_code, 401)

        response = self.client.get(admin_uri,
                                   digest_auth=(_USERNAME, _PASSWORD))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(admin_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.visits, 2)
