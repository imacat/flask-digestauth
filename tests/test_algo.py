# The Flask HTTP Digest Authentication Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2022/10/30

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

"""The test case for the HTTP digest authentication algorithm.

"""
import typing as t
import unittest

from flask_digest_auth import make_password_hash, calc_response


class AlgorithmTestCase(unittest.TestCase):
    """The test case for the HTTP digest authentication algorithm."""

    def test_response_value(self) -> None:
        """Tests the response value.
        See https://en.wikipedia.org/wiki/Digest_access_authentication.

        :return: None.
        """
        realm: str = "testrealm@host.com"
        username: str = "Mufasa"
        password: str = "Circle Of Life"
        method: str = "GET"
        uri: str = "/dir/index.html"
        nonce: str = "dcd98b7102dd2f0e8b11d0f600bfb0c093"
        qop: t.Optional[t.Literal["auth", "auth-int"]] = "auth"
        algorithm: t.Optional[t.Literal["MD5", "MD5-sess"]] = None
        cnonce: t.Optional[str] = "0a4f113b"
        nc: t.Optional[str] = "00000001"
        body: t.Optional[bytes] = None

        password_hash: str = make_password_hash(realm, username, password)
        response: str = calc_response(method, uri, password_hash, nonce, qop,
                                      algorithm, cnonce, nc, body)
        self.assertEqual(response, "6629fae49393a05397450978507c4ef1")
