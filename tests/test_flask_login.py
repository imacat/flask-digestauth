# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/11/23

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

"""The test case for the Flask-Login integration.

"""
import logging
import unittest
from secrets import token_urlsafe
from typing import Optional, Dict

import httpx
from flask import Flask, g, redirect, request
from werkzeug.datastructures import WWWAuthenticate

from flask_digest_auth import DigestAuth, make_password_hash
from testlib import REALM, USERNAME, PASSWORD, ADMIN_1_URI, ADMIN_2_URI, \
    LOGOUT_URI, make_authorization

SKIPPED_NO_FLASK_LOGIN: str = "Skipped without Flask-Login."
"""The message that a test is skipped when Flask-Login is not installed."""


class User:
    """A dummy user."""

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
        self.is_active: bool = True
        """True if the account is active, or False otherwise."""
        self.is_anonymous: bool = False
        """True if the account is anonymous, or False otherwise."""

    def get_id(self) -> str:
        """Returns the username.
        This is required by Flask-Login.

        :return: The username.
        """
        return self.username

    @property
    def is_authenticated(self) -> bool:
        """Returns whether the user is authenticated.
        This is required by Flask-Login.
        This should return self.is_active.

        :return: True if the user is active, or False otherwise.
        """
        return self.is_active


class FlaskLoginTestCase(unittest.TestCase):
    """The test case with the Flask-Login integration."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        logging.getLogger("test_flask_login").addHandler(logging.NullHandler())
        self.app: Flask = Flask(__name__)
        self.app.config.from_mapping({
            "TESTING": True,
            "SECRET_KEY": token_urlsafe(32),
            "DIGEST_AUTH_REALM": REALM,
        })
        self.__client: httpx.Client = httpx.Client(
            transport=httpx.WSGITransport(app=self.app),
            base_url="https://testserver")
        """The testing client."""

        self.__has_flask_login: bool = True
        """Whether the Flask-Login package is installed."""
        try:
            import flask_login
        except ModuleNotFoundError:
            self.__has_flask_login = False
            return
        except ImportError:
            self.__has_flask_login = False
            return

        login_manager: flask_login.LoginManager = flask_login.LoginManager()
        login_manager.init_app(self.app)

        auth: DigestAuth = DigestAuth()
        auth.init_app(self.app)

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

        @auth.register_on_login
        def on_login(user: User):
            """The callback when the user logs in.

            :param user: The logged-in user.
            :return: None.
            """
            user.visits = user.visits + 1

        @login_manager.user_loader
        def load_user(user_id: str) -> Optional[User]:
            """Loads a user.

            :param user_id: The username.
            :return: The user, or None if the user does not exist.
            """
            return user_db[user_id] if user_id in user_db else None

        @self.app.get(ADMIN_1_URI)
        @flask_login.login_required
        def admin_1() -> str:
            """The first administration section.

            :return: The response.
            """
            return f"Hello, {flask_login.current_user.get_id()}! #1"

        @self.app.get(ADMIN_2_URI)
        @flask_login.login_required
        def admin_2() -> str:
            """The second administration section.

            :return: The response.
            """
            return f"Hello, {flask_login.current_user.get_id()}! #2"

        @self.app.post(LOGOUT_URI)
        @flask_login.login_required
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
        if not self.__has_flask_login:
            self.skipTest(SKIPPED_NO_FLASK_LOGIN)

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
        if not self.__has_flask_login:
            self.skipTest(SKIPPED_NO_FLASK_LOGIN)

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

        with self.app.app_context():
            if hasattr(g, "_login_user"):
                delattr(g, "_login_user")
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

        with self.app.app_context():
            if hasattr(g, "_login_user"):
                delattr(g, "_login_user")
        auth_header = make_authorization(
            www_authenticate, ADMIN_1_URI, USERNAME, PASSWORD + "2")
        response = self.__client.get(ADMIN_1_URI,
                                     headers={"Authorization": auth_header})
        self.assertEqual(response.status_code, 401)
        www_authenticate = WWWAuthenticate.from_header(
            response.headers["WWW-Authenticate"])
        self.assertEqual(www_authenticate.get("stale"), "FALSE")
        self.assertEqual(www_authenticate.opaque, opaque)

        with self.app.app_context():
            if hasattr(g, "_login_user"):
                delattr(g, "_login_user")
        auth_header = make_authorization(
            www_authenticate, ADMIN_1_URI, USERNAME, PASSWORD)
        response = self.__client.get(ADMIN_1_URI,
                                     headers={"Authorization": auth_header})
        self.assertEqual(response.status_code, 200)

    def test_logout(self) -> None:
        """Tests the logging out.

        :return: None.
        """
        if not self.__has_flask_login:
            self.skipTest(SKIPPED_NO_FLASK_LOGIN)

        response: httpx.Response

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)

        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 200)

        response = self.__client.post(LOGOUT_URI, data={"next": ADMIN_1_URI})
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

    def test_disabled(self) -> None:
        """Tests the disabled user.

        :return: None.
        """
        if not self.__has_flask_login:
            self.skipTest(SKIPPED_NO_FLASK_LOGIN)

        response: httpx.Response

        self.__user.is_active = False
        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)
        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 401)

        self.__user.is_active = True
        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 200)
        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 200)

        self.__user.is_active = False
        response = self.__client.get(ADMIN_1_URI)
        self.assertEqual(response.status_code, 401)
        response = self.__client.get(ADMIN_1_URI,
                                     auth=httpx.DigestAuth(USERNAME, PASSWORD))
        self.assertEqual(response.status_code, 401)
