# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/10/5

#  Copyright (c) 2023 imacat.
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

"""The common test libraries.

"""
from secrets import token_urlsafe
from typing import Optional, Literal, Dict

from werkzeug.datastructures import Authorization, WWWAuthenticate
from werkzeug.http import parse_set_header

from flask_digest_auth import calc_response, make_password_hash

REALM: str = "testrealm@host.com"
"""The realm."""
USERNAME: str = "Mufasa"
"""The username."""
PASSWORD: str = "Circle Of Life"
"""The password."""
ADMIN_1_URI: str = "/admin-1/auth"
"""The first administration URI."""
ADMIN_2_URI: str = "/admin-2/auth"
"""The first administration URI."""
LOGOUT_URI: str = "/logout"
"""The log out URI."""


def make_authorization(www_authenticate: WWWAuthenticate, uri: str,
                       username: str, password: str) -> str:
    """Composes and returns the request authorization.

    :param www_authenticate: The ``WWW-Authenticate`` response.
    :param uri: The request URI.
    :param username: The username.
    :param password: The password.
    :return: The request authorization header.
    """
    qop: Optional[Literal["auth", "auth-int"]] = None
    if "auth" in parse_set_header(www_authenticate.get("qop")):
        qop = "auth"

    cnonce: Optional[str] = None
    if qop is not None or www_authenticate.algorithm == "MD5-sess":
        cnonce = token_urlsafe(8)
    nc: Optional[str] = None
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

    data: Dict[str, str] = {
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

    return str(Authorization("digest", data=data))
