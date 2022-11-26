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

"""The HTTP Digest Authentication.
See RFC 2617 HTTP Authentication: Basic and Digest Access Authentication

"""
from __future__ import annotations

import sys
import typing as t
from functools import wraps
from random import random
from secrets import token_urlsafe

from flask import g, request, Response, session, abort, Flask, Request
from itsdangerous import URLSafeTimedSerializer, BadData
from werkzeug.datastructures import Authorization

from flask_digest_auth.algo import calc_response
from flask_digest_auth.exception import UnauthorizedException


class BasePasswordHashGetter:
    """The base password hash getter."""

    @staticmethod
    def __call__(username: str) -> t.Optional[str]:
        """Returns the password hash of a user.

        :param username: The username.
        :return: The password hash, or None if the user does not exist.
        :raise UnboundLocalError: When the password hash getter function is
            not registered yet.
        """
        raise UnboundLocalError("The function to return the password hash"
                                " was not registered yet.")


class BaseUserGetter:
    """The base user getter."""

    @staticmethod
    def __call__(username: str) -> t.Optional[t.Any]:
        """Returns a user.

        :param username: The username.
        :return: The user, or None if the user does not exist.
        :raise UnboundLocalError: When the user getter function is not
            registered yet.
        """
        raise UnboundLocalError("The function to return the user"
                                " was not registered yet.")


class BaseOnLogInCallback:
    """The base callback when the user logs in."""

    @staticmethod
    def __call__(user: t.Any) -> None:
        """Runs the callback when the user logs in.

        :param user: The logged-in user.
        :return: None.
        """


class DigestAuth:
    """The HTTP digest authentication."""

    def __init__(self, realm: t.Optional[str] = None):
        """Constructs the HTTP digest authentication.

        :param realm: The realm.
        """
        self.secret_key: str = token_urlsafe(32)
        self.serializer: URLSafeTimedSerializer \
            = URLSafeTimedSerializer(self.secret_key)
        self.realm: str = "" if realm is None else realm
        self.algorithm: t.Optional[str] = None
        self.use_opaque: bool = True
        self.domain: t.List[str] = []
        self.qop: t.List[str] = ["auth", "auth-int"]
        self.app: t.Optional[Flask] = None
        self.__get_password_hash: BasePasswordHashGetter \
            = BasePasswordHashGetter()
        self.__get_user: BaseUserGetter = BaseUserGetter()
        self.__on_login: BaseOnLogInCallback = BaseOnLogInCallback()

    def login_required(self, view) -> t.Callable:
        """The view decorator for HTTP digest authentication.

        :param view:
        :return: The login-protected view.
        """

        class NoLogInException(Exception):
            """The exception thrown when the user is not authorized."""

        @wraps(view)
        def login_required_view(*args, **kwargs) -> t.Any:
            """The login-protected view.

            :param args: The positional arguments of the view.
            :param kwargs: The keyword arguments of the view.
            :return: The response.
            """
            try:
                if "user" not in session:
                    raise NoLogInException
                user: t.Optional[t.Any] = self.__get_user(session["user"])
                if user is None:
                    raise NoLogInException
                g.user = user
                return view(*args, **kwargs)
            except NoLogInException:
                state: AuthState = AuthState()
                authorization: Authorization = request.authorization
                try:
                    if authorization is None:
                        raise UnauthorizedException
                    if authorization.type != "digest":
                        raise UnauthorizedException(
                            "Not an HTTP digest authorization")
                    self.authenticate(state)
                    session["user"] = authorization.username
                    user = self.__get_user(authorization.username)
                    g.user = user
                    self.__on_login(user)
                    return view(*args, **kwargs)
                except UnauthorizedException as e:
                    if len(e.args) > 0:
                        sys.stderr.write(e.args[0] + "\n")
                    response: Response = Response()
                    response.status = 401
                    response.headers["WWW-Authenticate"] \
                        = self.make_response_header(state)
                    abort(response)

        return login_required_view

    def authenticate(self, state: AuthState) -> None:
        """Authenticate a user.

        :param state: The authorization state.
        :return: None.
        :raise UnauthorizedException: When the authentication failed.
        """
        if "digest_auth_logout" in session:
            del session["digest_auth_logout"]
            raise UnauthorizedException("Logging out")
        authorization: Authorization = request.authorization
        if self.use_opaque:
            if authorization.opaque is None:
                raise UnauthorizedException(
                    "Missing \"opaque\" in the Authorization header")
            try:
                self.serializer.loads(
                    authorization.opaque, salt="opaque", max_age=1800)
            except BadData:
                raise UnauthorizedException("Invalid opaque")
            state.opaque = authorization.opaque
        password_hash: t.Optional[str] \
            = self.__get_password_hash(authorization.username)
        if password_hash is None:
            raise UnauthorizedException(
                f"No such user \"{authorization.username}\"")
        expected: str = calc_response(
            method=request.method, uri=authorization.uri,
            password_hash=password_hash, nonce=authorization.nonce,
            qop=authorization.qop,
            algorithm=authorization.get("algorithm"),
            cnonce=authorization.cnonce, nc=authorization.nc,
            body=request.data)
        if authorization.response != expected:
            state.stale = False
            raise UnauthorizedException("Incorrect response value")
        try:
            self.serializer.loads(
                authorization.nonce,
                salt="nonce" if authorization.opaque is None
                else f"nonce-{authorization.opaque}")
        except BadData:
            state.stale = True
            raise UnauthorizedException("Invalid nonce")

    def make_response_header(self, state: AuthState) -> str:
        """Composes and returns the WWW-Authenticate response header.

        :param state: The authorization state.
        :return: The WWW-Authenticate response header.
        """
        opaque: t.Optional[str] = None if not self.use_opaque else \
            (state.opaque if state.opaque is not None
             else self.serializer.dumps(random(), salt="opaque"))
        nonce: str = self.serializer.dumps(
            random(), salt="nonce" if opaque is None else f"nonce-{opaque}")

        header: str = f"Digest realm=\"{self.realm}\""
        if len(self.domain) > 0:
            domain_list: str = ",".join(self.domain)
            header += f", domain=\"{domain_list}\""
        header += f", nonce=\"{nonce}\""
        if opaque is not None:
            header += f", opaque=\"{opaque}\""
        if state.stale is not None:
            header += f", stale=TRUE" if state.stale else f", stale=FALSE"
        if self.algorithm is not None:
            header += f", algorithm=\"{self.algorithm}\""
        if len(self.qop) > 0:
            qop_list: str = ",".join(self.qop)
            header += f", qop=\"{qop_list}\""
        return header

    def register_get_password(self, func: t.Callable[[str], t.Optional[str]])\
            -> None:
        """Registers the callback to obtain the password hash.

        :param func: The callback that given the username, returns the password
            hash, or None if the user does not exist.
        :return: None.
        """

        class PasswordHashGetter(BasePasswordHashGetter):
            """The base password hash getter."""

            @staticmethod
            def __call__(username: str) -> t.Optional[str]:
                """Returns the password hash of a user.

                :param username: The username.
                :return: The password hash, or None if the user does not exist.
                """
                return func(username)

        self.__get_password_hash = PasswordHashGetter()

    def register_get_user(self, func: t.Callable[[str], t.Optional[t.Any]])\
            -> None:
        """Registers the callback to obtain the user.

        :param func: The callback that given the username, returns the user,
            or None if the user does not exist.
        :return: None.
        """

        class UserGetter(BaseUserGetter):
            """The user getter."""

            @staticmethod
            def __call__(username: str) -> t.Optional[t.Any]:
                """Returns a user.

                :param username: The username.
                :return: The user, or None if the user does not exist.
                """
                return func(username)

        self.__get_user = UserGetter()

    def register_on_login(self, func: t.Callable[[t.Any], None]) -> None:
        """Registers the callback when the user logs in.

        :param func: The callback given the logged-in user.
        :return: None.
        """

        class OnLogInCallback:
            """The callback when the user logs in."""

            @staticmethod
            def __call__(user: t.Any) -> None:
                """Runs the callback when the user logs in.

                :param user: The logged-in user.
                :return: None.
                """
                func(user)

        self.__on_login = OnLogInCallback()

    def init_app(self, app: Flask) -> None:
        """Initializes the Flask application.

        :param app: The Flask application.
        :return: None.
        """
        app.digest_auth = self
        self.app = app

        if hasattr(app, "login_manager"):
            from flask_login import LoginManager, login_user

            login_manager: LoginManager = getattr(app, "login_manager")

            @login_manager.unauthorized_handler
            def unauthorized() -> None:
                """Handles when the user is unauthorized.

                :return: None.
                """
                response: Response = Response()
                response.status = 401
                response.headers["WWW-Authenticate"] \
                    = self.make_response_header(g.digest_auth_state)
                abort(response)

            @login_manager.request_loader
            def load_user_from_request(req: Request) -> t.Optional[t.Any]:
                """Loads the user from the request header.

                :param req: The request.
                :return: The authenticated user, or None if the
                    authentication fails
                """
                g.digest_auth_state = AuthState()
                authorization: Authorization = req.authorization
                try:
                    if authorization is None:
                        raise UnauthorizedException
                    if authorization.type != "digest":
                        raise UnauthorizedException(
                            "Not an HTTP digest authorization")
                    self.authenticate(g.digest_auth_state)
                    user = login_manager.user_callback(
                        authorization.username)
                    login_user(user)
                    self.__on_login(user)
                    return user
                except UnauthorizedException as e:
                    if str(e) != "":
                        app.logger.warning(str(e))
                    return None

    def logout(self) -> None:
        """Logs out the user.
        This actually causes the next authentication to fail, which forces
        the browser to ask the user for the username and password again.

        :return: None.
        """
        if "user" in session:
            del session["user"]
        try:
            if hasattr(self.app, "login_manager"):
                from flask_login import logout_user
                logout_user()
        except ModuleNotFoundError:
            pass
        session["digest_auth_logout"] = True


class AuthState:
    """The authorization state."""

    def __init__(self):
        """Constructs the authorization state."""
        self.opaque: t.Optional[str] = None
        self.stale: t.Optional[bool] = None
