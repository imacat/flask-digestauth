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
        self.__get_password_hash: t.Callable[[str], t.Optional[str]] \
            = lambda x: None
        self.__get_user: t.Callable[[str], t.Optional] = lambda x: None

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
                    g.user = self.__get_user(authorization.username)
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
        password_hash: t.Optional[str] = self.__get_password_hash(
            authorization.username)
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
        self.__get_password_hash = func

    def register_get_user(self, func: t.Callable[[str], t.Optional[t.Any]])\
            -> None:
        """Registers the callback to obtain the user.

        :param func: The callback that given the username, returns the user,
            or None if the user does not exist.
        :return: None.
        """
        self.__get_user = func

    def init_app(self, app: Flask) -> None:
        """Initializes the Flask application.

        :param app: The Flask application.
        :return: None.
        """

        try:
            from flask_login import LoginManager, login_user

            if not hasattr(app, "login_manager"):
                raise AttributeError(
                    "Please run the Flask-Login init-app() first")
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
                    return user
                except UnauthorizedException as e:
                    if str(e) != "":
                        app.logger.warning(str(e))
                    return None

        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "init_app() is only for Flask-Login integration")


class AuthState:
    """The authorization state."""

    def __init__(self):
        """Constructs the authorization state."""
        self.opaque: t.Optional[str] = None
        self.stale: t.Optional[bool] = None
