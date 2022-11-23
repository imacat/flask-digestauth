# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/11/14

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

"""The Flask-Login integration.

"""

import typing as t

from flask import Response, abort, current_app, Request, g
from flask_login import LoginManager, login_user
from werkzeug.datastructures import Authorization

from flask_digest_auth.auth import DigestAuth, AuthState
from flask_digest_auth.exception import UnauthorizedException


def init_login_manager(auth: DigestAuth, login_manager: LoginManager) -> None:
    """Initialize the login manager.

    :param auth: The HTTP digest authentication.
    :param login_manager: The login manager from FlaskLogin.
    :return: None.
    """

    @login_manager.unauthorized_handler
    def unauthorized() -> None:
        """Handles when the user is unauthorized.

        :return: None.
        """
        response: Response = Response()
        response.status = 401
        response.headers["WWW-Authenticate"] = auth.make_response_header(
            g.digest_auth_state)
        abort(response)

    @login_manager.request_loader
    def load_user_from_request(request: Request) -> t.Optional[t.Any]:
        """Loads the user from the request header.

        :param request: The request.
        :return: The authenticated user, or None if the authentication fails
        """
        g.digest_auth_state = AuthState()
        authorization: Authorization = request.authorization
        try:
            if authorization is None:
                raise UnauthorizedException
            if authorization.type != "digest":
                raise UnauthorizedException(
                    "Not an HTTP digest authorization")
            auth.authenticate(g.digest_auth_state)
            user = login_manager.user_callback(authorization.username)
            login_user(user)
            return user
        except UnauthorizedException as e:
            if str(e) != "":
                current_app.logger.warning(str(e))
            return None
