# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/11/3

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

"""The test client with HTTP digest authentication enabled.

"""
import typing as t
from secrets import token_urlsafe

from flask import g
from werkzeug.datastructures import Authorization, WWWAuthenticate
from werkzeug.test import TestResponse, Client as WerkzeugClient

from flask_digest_auth.algo import calc_response, make_password_hash


class Client(WerkzeugClient):
    """The test client with HTTP digest authentication enabled.

    :Example:

    For unittest_:

    ::

        class MyTestCase(flask_testing.TestCase):

            def create_app(self):
                app: Flask = create_app({
                    "SECRET_KEY": token_urlsafe(32),
                    "TESTING": True
                })
                app.test_client_class = Client
                return app

            def test_admin(self):
                response = self.client.get("/admin")
                self.assertEqual(response.status_code, 401)
                response = self.client.get(
                    "/admin", digest_auth=(USERNAME, PASSWORD))
                self.assertEqual(response.status_code, 200)

    For pytest_:

    ::

        @pytest.fixture()
        def app():
            app: Flask = create_app({
                "SECRET_KEY": token_urlsafe(32),
                "TESTING": True
            })
            app.test_client_class = Client
            yield app

        @pytest.fixture()
        def client(app):
            return app.test_client()

        def test_admin(app: Flask, client: Client):
            with app.app_context():
                response = client.get("/admin")
                assert response.status_code == 401
                response = client.get(
                    "/admin", digest_auth=(USERNAME, PASSWORD))
                assert response.status_code == 200

    .. _unittest: https://docs.python.org/3/library/unittest.html
    .. _pytest: https://pytest.org
    """

    def open(self, *args, digest_auth: t.Optional[t.Tuple[str, str]] = None,
             **kwargs) -> TestResponse:
        """Opens a request.

        :param args: The arguments.
        :param digest_auth: The (*username*, *password*) tuple for the HTTP
            digest authentication.
        :param kwargs: The keyword arguments.
        :return: The response.
        """
        response: TestResponse = super(Client, self).open(*args, **kwargs)
        www_authenticate: WWWAuthenticate = response.www_authenticate
        if not (response.status_code == 401
                and www_authenticate.type == "digest"
                and digest_auth is not None):
            return response
        if hasattr(g, "_login_user"):
            delattr(g, "_login_user")
        auth_data: Authorization = self.__class__.make_authorization(
            www_authenticate, args[0], digest_auth[0], digest_auth[1])
        response = super(Client, self).open(*args, auth=auth_data, **kwargs)
        return response

    @staticmethod
    def make_authorization(www_authenticate: WWWAuthenticate, uri: str,
                           username: str, password: str) -> Authorization:
        """Composes and returns the request authorization.

        :param www_authenticate: The ``WWW-Authenticate`` response.
        :param uri: The request URI.
        :param username: The username.
        :param password: The password.
        :return: The request authorization.
        """
        qop: t.Optional[t.Literal["auth", "auth-int"]] = None
        if www_authenticate.qop is not None and "auth" in www_authenticate.qop:
            qop = "auth"

        cnonce: t.Optional[str] = None
        if qop is not None or www_authenticate.algorithm == "MD5-sess":
            cnonce = token_urlsafe(8)
        nc: t.Optional[str] = None
        count: int = 1
        if qop is not None:
            nc: str = hex(count)[2:].zfill(8)

        expected: str = calc_response(
            method="GET", uri=uri,
            password_hash=make_password_hash(www_authenticate.realm,
                                             username, password),
            nonce=www_authenticate.nonce, qop=qop,
            algorithm=www_authenticate.algorithm, cnonce=cnonce, nc=nc,
            body=None)

        data: t.Dict[str, str] = {
            "username": username, "realm": www_authenticate.realm,
            "nonce": www_authenticate.nonce, "uri": uri, "response": expected}
        if www_authenticate.algorithm is not None:
            data["algorithm"] = www_authenticate.algorithm
        if cnonce is not None:
            data["cnonce"] = cnonce
        if www_authenticate.opaque is not None:
            data["opaque"] = www_authenticate.opaque
        if qop is not None:
            data["qop"] = qop
        if nc is not None:
            data["nc"] = nc

        return Authorization("digest", data=data)
