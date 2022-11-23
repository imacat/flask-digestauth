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

"""The algorithm.

"""
from __future__ import annotations

import typing as t
from hashlib import md5

from flask_digest_auth.exception import UnauthorizedException


def make_password_hash(realm: str, username: str, password: str) -> str:
    """Calculates the password hash for the HTTP digest authentication.

    :param realm: The realm.
    :param username: The username.
    :param password: The cleartext password.
    :return: The password hash for the HTTP digest authentication.
    """
    return md5(f"{username}:{realm}:{password}".encode("utf8")).hexdigest()


def calc_response(
        method: str, uri: str, password_hash: str,
        nonce: str, qop: t.Optional[t.Literal["auth", "auth-int"]] = None,
        algorithm: t.Optional[t.Literal["MD5", "MD5-sess"]] = "MD5-sess",
        cnonce: t.Optional[str] = None, nc: t.Optional[str] = None,
        body: t.Optional[bytes] = None) -> str:
    """Calculates the response value of the HTTP digest authentication.

    :param method: The request method.
    :param uri: The request URI.
    :param password_hash: The password hash for the HTTP digest authentication.
    :param nonce: The nonce.
    :param qop: the quality of protection.
    :param algorithm: The algorithm, either "MD5" or "MD5-sess".
    :param cnonce: The client nonce, which must exists when qop exists or
        algorithm="MD5-sess".
    :param nc: The request counter, which must exists when qop exists.
    :param body: The request body, which must exists when qop="auth-int".
    :return: The response value.
    :raise UnauthorizedException: When the cnonce is missing with the MD5-sess
        algorithm, when the body is missing with the auth-int qop, or when the
        cnonce or nc is missing with the auth or auth-int qop.
    """

    def calc_ha1() -> str:
        """Calculates and returns the first hash.

        :return: The first hash.
        :raise UnauthorizedException: When the cnonce is missing with the MD5-sess
            algorithm.
        """
        if algorithm is None or algorithm == "MD5":
            return password_hash
        if algorithm == "MD5-sess":
            if cnonce is None:
                raise UnauthorizedException(
                    f"Missing \"cnonce\" with algorithm=\"{algorithm}\"")
            return md5(f"{password_hash}:{nonce}:{cnonce}".encode("utf8")) \
                .hexdigest()
        raise UnauthorizedException(
            f"Unsupported algorithm=\"{algorithm}\"")

    def calc_ha2() -> str:
        """Calculates the second hash.

        :return: The second hash.
        :raise UnauthorizedException: When the body is missing with
            qop="auth-int".
        """
        if qop is None or qop == "auth":
            return md5(f"{method}:{uri}".encode("utf8")).hexdigest()
        if qop == "auth-int":
            if body is None:
                raise UnauthorizedException(
                    f"Missing \"body\" with qop=\"{qop}\"")
            return md5(
                f"{method}:{uri}:{md5(body).hexdigest()}".encode("utf8")) \
                .hexdigest()
        raise UnauthorizedException(f"Unsupported qop=\"{qop}\"")

    ha1: str = calc_ha1()
    ha2: str = calc_ha2()
    if qop is None:
        return md5(f"{ha1}:{nonce}:{ha2}".encode("utf8")).hexdigest()
    if qop == "auth" or qop == "auth-int":
        if cnonce is None:
            raise UnauthorizedException(
                f"Missing \"cnonce\" with the qop=\"{qop}\"")
        if nc is None:
            raise UnauthorizedException(
                f"Missing \"nc\" with the qop=\"{qop}\"")
        return md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode("utf8"))\
            .hexdigest()
    if cnonce is None:
        raise UnauthorizedException(
            f"Unsupported qop=\"{qop}\"")
