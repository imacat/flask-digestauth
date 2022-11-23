# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/11/23

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

"""The test case for the Flask-Login integration.

"""
import typing as t
from secrets import token_urlsafe

from flask import Response, Flask
from flask_testing import TestCase

from flask_digest_auth import DigestAuth, make_password_hash, Client

_REALM: str = "testrealm@host.com"
_USERNAME: str = "Mufasa"
_PASSWORD: str = "Circle Of Life"


class User:
    def __init__(self, username: str):
        self.username: str = username
        self.is_authenticated: bool = True
        self.is_active: bool = True
        self.is_anonymous: bool = False

    def get_id(self) -> str:
        """Returns the username.
        This is required by Flask-Login.

        :return: The username.
        """
        return self.username


class FlaskLoginTestCase(TestCase):
    """The test case with the Flask-Login integration."""

    def create_app(self) -> Flask:
        """Creates the Flask application.

        :return: The Flask application.
        """
        app: Flask = Flask(__name__)
        app.config.from_mapping({
            "SECRET_KEY": token_urlsafe(32),
            "TESTING": True
        })
        app.test_client_class = Client

        self.has_flask_login: bool = True
        try:
            import flask_login
        except ModuleNotFoundError:
            self.has_flask_login = False
            return app

        login_manager: flask_login.LoginManager = flask_login.LoginManager()
        login_manager.init_app(app)

        auth: DigestAuth = DigestAuth(realm=_REALM)
        auth.init_app(app)

        user_db: t.Dict[str, str] \
            = {_USERNAME: make_password_hash(_REALM, _USERNAME, _PASSWORD)}

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            """Returns the password hash of a user.

            :param username: The username.
            :return: The password hash, or None if the user does not exist.
            """
            return user_db[username] if username in user_db else None

        @login_manager.user_loader
        def load_user(user_id: str) -> t.Optional[User]:
            """Loads a user.

            :param user_id: The username.
            :return: The user, or None if the user does not exist.
            """
            return User(user_id) if user_id in user_db else None

        @app.get("/login-required-1/auth", endpoint="auth-1")
        @flask_login.login_required
        def login_required_1() -> str:
            """The first dummy view.

            :return: The response.
            """
            return f"Hello, {flask_login.current_user.username}! #1"

        @app.get("/login-required-2/auth", endpoint="auth-2")
        @flask_login.login_required
        def login_required_2() -> str:
            """The second dummy view.

            :return: The response.
            """
            return f"Hello, {flask_login.current_user.username}! #2"

        return app

    def test_auth(self) -> None:
        """Tests the authentication.

        :return: None.
        """
        if not self.has_flask_login:
            self.skipTest("Skipped testing Flask-Login integration without it.")

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
