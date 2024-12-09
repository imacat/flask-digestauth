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
import logging
import unittest
from secrets import token_urlsafe
from typing import Any, Optional, Dict

import httpx
from flask import Flask, g, redirect, request
from werkzeug.datastructures import WWWAuthenticate

from flask_digest_auth import DigestAuth, make_password_hash
from testlib import REALM, USERNAME, PASSWORD, ADMIN_1_URI, ADMIN_2_URI, \
    LOGOUT_URI, make_authorization


class User:
    """A dummy user"""

    def __init__(self, username: str, password: str):
        """Constructs a dummy user.

        :param username: The username.
        :param password: The clear-text password.
        """
        self.username: str = username
        """The username."""
        self.password_hash: str = make_password_hash(REALM, username, password)
        """The password hash."""
        self.visits: int = 0
        """The number of visits."""


class AuthenticationTestCase(unittest.TestCase):
    """The test case for the HTTP digest authentication."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        logging.getLogger("test_auth").addHandler(logging.NullHandler())
        app: Flask = Flask(__name__)
        app.config.from_mapping({
            "TESTING": True,
            "SECRET_KEY": token_urlsafe(32),
            "DIGEST_AUTH_REALM": REALM,
        })
        self.__client: httpx.Client = httpx.Client(
            transport=httpx.WSGITransport(app=app),
            base_url="https://testserver")
        """The testing client."""

        auth: DigestAuth = DigestAuth()
        auth.init_app(app)
        self.__user: User = User(USERNAME, PASSWORD)
        """The user account."""
        user_db: Dict[str, User] = {USERNAME: self.__user}

        @auth.register_get_password
        def get_password_hash(username: str) -> Optional[str]:
            """Returns the password hash of a user.

            :param username: The username.
            :return: The password hash, or None if the user does not exist.
            """
            return user_db[username].password_hash if username in user_db \
                else None

        @auth.register_get_user
        def get_user(username: str) -> Optional[Any]:
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

        @app.get(ADMIN_1_URI, endpoint="admin-1")
        @auth.login_required
        def admin_1() -> str:
            """The first administration section.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #1"

        @app.get(ADMIN_2_URI, endpoint="admin-2")
        @auth.login_required
        def admin_2() -> str:
            """The second administration section.

            :return: The response.
            """
            return f"Hello, {g.user.username}! #2"

        @app.post(LOGOUT_URI, endpoint="logout")
        @auth.login_required
        def logout() -> redirect:
            """Logs out the user.

            :return: The response.
            """
            auth.logout()
            return redirect(request.form.get("next"))

    def test_auth(self) -> None:
        """Tests the authentication.

        :return: None.
        """
        response: httpx.Response
        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)
        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, f"Hello, {USERNAME}! #1")
        response = self.__client.get(ADMIN_2_URI)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, f"Hello, {USERNAME}! #2")
        self.assertEqual(self.__user.visits, 1)

    def test_stale_opaque(self) -> None:
        """Tests the stale and opaque value.

        :return: None.
        """
        response: httpx.Response
        www_authenticate: WWWAuthenticate
        auth_header: str

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)
        www_authenticate = WWWAuthenticate.from_header(
            response.headers["WWW-Authenticate"])
        self.assertEqual(www_authenticate.type, "digest")
        self.assertIsNone(www_authenticate.get("stale"))
        opaque: str = www_authenticate.opaque

        www_authenticate.nonce = "bad"
        auth_header = make_authorization(
            www_authenticate, ADMIN_1_URI, USERNAME, PASSWORD)
        response = self.__client.get(ADMIN_1_URI,
                                     headers={"Authorization": auth_header})
        self.assertEqual(response.status_code, 401)
        www_authenticate = WWWAuthenticate.from_header(
            response.headers["WWW-Authenticate"])
        self.assertEqual(www_authenticate.get("stale"), "TRUE")
        self.assertEqual(www_authenticate.opaque, opaque)

        auth_header = make_authorization(
            www_authenticate, ADMIN_1_URI, USERNAME, PASSWORD + "2")
        response = self.__client.get(ADMIN_1_URI,
                                     headers={"Authorization": auth_header})
        self.assertEqual(response.status_code, 401)
        www_authenticate = WWWAuthenticate.from_header(
            response.headers["WWW-Authenticate"])
        self.assertEqual(www_authenticate.get("stale"), "FALSE")
        self.assertEqual(www_authenticate.opaque, opaque)

        auth_header = make_authorization(
            www_authenticate, ADMIN_1_URI, USERNAME, PASSWORD)
        response = self.__client.get(ADMIN_1_URI,
                                     headers={"Authorization": auth_header})
        self.assertEqual(response.status_code, 200)

    def test_logout(self) -> None:
        """Tests the logging out.

        :return: None.
        """
        logout_uri: str = LOGOUT_URI
        response: httpx.Response

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)

        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 200)

        response = self.__client.post(logout_uri, data={"next": ADMIN_1_URI})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], ADMIN_1_URI)

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)

        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 401)

        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.__user.visits, 2)
