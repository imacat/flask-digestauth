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

"""The HTTP Digest Authentication.
See `RFC 2617`_ HTTP Authentication: Basic and Digest Access Authentication

.. _RFC 2617: https://www.rfc-editor.org/rfc/rfc2617
"""
from __future__ import annotations

import sys
import typing as t
from functools import wraps
from secrets import token_urlsafe, randbits

from flask import g, request, Response, session, abort, Flask, Request, \
    current_app
from itsdangerous import URLSafeTimedSerializer, BadData
from werkzeug.datastructures import Authorization

from flask_digest_auth.algo import calc_response


class DigestAuth:
    """The HTTP digest authentication."""

    def __init__(self, realm: t.Optional[str] = None):
        """Constructs the HTTP digest authentication.

        :param realm: The realm.
        """
        self.__serializer: URLSafeTimedSerializer \
            = URLSafeTimedSerializer(token_urlsafe(32))
        """The serializer to generate and validate the nonce and opaque."""
        self.realm: str = "Login Required" if realm is None else realm
        """The realm.  Default is "Login Required"."""
        self.algorithm: t.Optional[t.Literal["MD5", "MD5-sess"]] = None
        """The algorithm, either None, ``MD5``, or ``MD5-sess``.  Default is
        None."""
        self.use_opaque: bool = True
        """Whether to use an opaque.  Default is True."""
        self.__domain: t.List[str] = []
        """A list of directories that this username and password applies to.
        Default is empty."""
        self.__qop: t.List[t.Literal["auth", "auth-int"]] \
            = ["auth", "auth-int"]
        """A list of supported quality of protection supported, either
        ``qop``, ``auth-int``, both, or empty.  Default is both."""
        self.__get_password_hash: BasePasswordHashGetter \
            = BasePasswordHashGetter()
        """The callback to return the password hash."""
        self.__get_user: BaseUserGetter = BaseUserGetter()
        """The callback to return the user."""
        self.__on_login: BaseOnLogInCallback = BaseOnLogInCallback()
        """The callback to run when the user logs in."""

    def login_required(self, view) -> t.Callable:
        """The view decorator for the HTTP digest authentication.

        :Example:

        ::

            @app.get("/admin")
            @auth.login_required
            def admin():
                return f"Hello, {g.user.username}!"

        The logged-in user can be retrieved at ``g.user``.

        :param view: The view.
        :return: The login-protected view.
        """

        class NoLogInException(Exception):
            """The exception thrown when the user is not authorized."""

        def get_logged_in_user() -> t.Any:
            """Returns the currently logged-in user.

            :return: The currently logged-in user.
            :raise NoLogInException: When the user is not logged in.
            """
            if "user" not in session:
                raise NoLogInException
            user: t.Optional[t.Any] = self.__get_user(session["user"])
            if user is None:
                del session["user"]
                raise NoLogInException
            return user

        def auth_user(state: AuthState) -> t.Any:
            """Authenticates a user.

            :param state: The authentication state.
            :return: The user.
            :raise UnauthorizedException: When the authentication fails.
            """
            authorization: Authorization = request.authorization
            if authorization is None:
                raise UnauthorizedException
            if authorization.type != "digest":
                raise UnauthorizedException(
                    "Not an HTTP digest authorization")
            self.__authenticate(state)
            session["user"] = authorization.username
            return self.__get_user(authorization.username)

        @wraps(view)
        def login_required_view(*args, **kwargs) -> t.Any:
            """The login-protected view.

            :param args: The positional arguments of the view.
            :param kwargs: The keyword arguments of the view.
            :return: The response.
            """
            try:
                g.user = get_logged_in_user()
                return view(*args, **kwargs)
            except NoLogInException:
                pass

            state: AuthState = AuthState()
            try:
                g.user = auth_user(state)
                self.__on_login(g.user)
                return view(*args, **kwargs)
            except UnauthorizedException as e:
                if len(e.args) > 0:
                    sys.stderr.write(e.args[0] + "\n")
                response: Response = Response()
                response.status = 401
                response.headers["WWW-Authenticate"] \
                    = self.__make_response_header(state)
                abort(response)

        return login_required_view

    def __authenticate(self, state: AuthState) -> None:
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
                self.__serializer.loads(
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
            self.__serializer.loads(
                authorization.nonce,
                salt="nonce" if authorization.opaque is None
                else f"nonce-{authorization.opaque}")
        except BadData:
            state.stale = True
            raise UnauthorizedException("Invalid nonce")

    def __make_response_header(self, state: AuthState) -> str:
        """Composes and returns the ``WWW-Authenticate`` response header.

        :param state: The authorization state.
        :return: The ``WWW-Authenticate`` response header.
        """

        def get_opaque() -> t.Optional[str]:
            """Returns the opaque value.

            :return: The opaque value.
            """
            if not self.use_opaque:
                return None
            if state.opaque is not None:
                return state.opaque
            return self.__serializer.dumps(randbits(32), salt="opaque")

        opaque: t.Optional[str] = get_opaque()
        nonce: str = self.__serializer.dumps(
            randbits(32),
            salt="nonce" if opaque is None else f"nonce-{opaque}")

        header: str = f"Digest realm=\"{self.realm}\""
        if len(self.__domain) > 0:
            domain_list: str = ",".join(self.__domain)
            header += f", domain=\"{domain_list}\""
        header += f", nonce=\"{nonce}\""
        if opaque is not None:
            header += f", opaque=\"{opaque}\""
        if state.stale is not None:
            header += f", stale=TRUE" if state.stale else f", stale=FALSE"
        if self.algorithm is not None:
            header += f", algorithm=\"{self.algorithm}\""
        if len(self.__qop) > 0:
            qop_list: str = ",".join(self.__qop)
            header += f", qop=\"{qop_list}\""
        return header

    def register_get_password(self, func: t.Callable[[str], t.Optional[str]])\
            -> None:
        """The decorator to register the callback to obtain the password hash.

        :Example:

        ::

            @auth.register_get_password
            def get_password_hash(username: str) -> Optional[str]:
                user = User.query.filter(User.username == username).first()
                return None if user is None else user.password

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
        """The decorator to register the callback to obtain the user.

        :Example:

        ::

            @auth.register_get_user
            def get_user(username: str) -> Optional[User]:
                return User.query.filter(User.username == username).first()

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
        """The decorator to register the callback to run when the user logs in.

        :Example:

        ::

            @auth.register_on_login
            def on_login(user: User) -> None:
                user.visits = user.visits + 1

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
        """Initializes the Flask application.  The DigestAuth instance will
        be stored in ``app.extensions["digest_auth"]``.

        :Example:

        ::

            app: flask = Flask(__name__)
            auth: DigestAuth = DigestAuth()
            auth.realm = "My Admin"
            auth.init_app(app)

        :param app: The Flask application.
        :return: None.
        """
        app.extensions["digest_auth"] = self
        if "DIGEST_AUTH_REALM" in app.config:
            self.realm = app.config["DIGEST_AUTH_REALM"]

        if hasattr(app, "login_manager"):
            from flask_login import LoginManager, login_user

            login_manager: LoginManager = getattr(app, "login_manager")

            @login_manager.unauthorized_handler
            def unauthorized() -> None:
                """Handles when the user is unauthorized.

                :return: None.
                """
                state: AuthState = getattr(request, "_digest_auth_state") \
                    if hasattr(request, "_digest_auth_state") \
                    else AuthState()
                response: Response = Response()
                response.status = 401
                response.headers["WWW-Authenticate"] \
                    = self.__make_response_header(state)
                abort(response)

            @login_manager.request_loader
            def load_user_from_request(req: Request) -> t.Optional[t.Any]:
                """Loads the user from the request header.

                :param req: The request.
                :return: The authenticated user, or None if the
                    authentication fails
                """
                request._digest_auth_state = AuthState()
                authorization: Authorization = req.authorization
                try:
                    if authorization is None:
                        raise UnauthorizedException
                    if authorization.type != "digest":
                        raise UnauthorizedException(
                            "Not an HTTP digest authorization")
                    self.__authenticate(request._digest_auth_state)
                    user = login_manager.user_callback(authorization.username)
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

        :Example:

        ::

            @app.post("/logout")
            @auth.login_required
            def logout():
                auth.logout()
                return redirect(request.form.get("next"))

        :return: None.
        """
        if "user" in session:
            del session["user"]
        try:
            if hasattr(current_app, "login_manager"):
                from flask_login import logout_user
                logout_user()
        except ModuleNotFoundError:
            pass
        session["digest_auth_logout"] = True


class AuthState:
    """The authentication state.  It keeps the status in the earlier
    authentication stage, so that the latter response stage knows how to
    response.
    """

    def __init__(self):
        """Constructs the authorization state."""
        self.opaque: t.Optional[str] = None
        """The opaque value specified by the client, if valid."""
        self.stale: t.Optional[bool] = None
        """The stale value, if there is a previous log in attempt."""


class UnauthorizedException(Exception):
    """The exception thrown when the authentication fails."""


class BasePasswordHashGetter:
    """The base callback that given the username, returns the password hash,
    or None if the user does not exist.  The default is to raise an
    :class:`UnboundLocalError` if the callback is not registered yet.

    See :meth:`flask_digest_auth.auth.DigestAuth.register_get_password`
    """

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
    """The base callback that given the username, returns the user, or None if
    the user does not exist.  The default is to raise an
    :class:`UnboundLocalError` if the callback is not registered yet.

    See :meth:`flask_digest_auth.auth.DigestAuth.register_get_user`
    """

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
    """The base callback to run when the user logs in, given the logged-in
    user.  The default does nothing.

    See :meth:`flask_digest_auth.auth.DigestAuth.register_on_login`
    """

    @staticmethod
    def __call__(user: t.Any) -> None:
        """Runs the callback when the user logs in.

        :param user: The logged-in user.
        :return: None.
        """
