================================
Flask HTTP Digest Authentication
================================


Description
===========

*Flask-DigestAuth* is an `HTTP Digest Authentication`_ implementation
for Flask_ applications.  It authenticates the user for the protected
views.

HTTP Digest Authentication is specified in `RFC 2617`_.


Why HTTP Digest Authentication?
-------------------------------

*HTTP Digest Authentication* has the advantage that it does not send
thee actual password to the server, which greatly enhances the
security.  It uses the challenge-response authentication scheme.  The
client returns the response calculated from the challenge and the
password, but not the original password.

Log in forms has the advantage of freedom, in the senses of both the
visual design and the actual implementation.  You may implement your
own challenge-response log in form, but then you are reinventing the
wheels.  If a pretty log in form is not critical to your project, HTTP
Digest Authentication should be a good choice.

Flask-DigestAuth works with Flask-Login_.  Log in protection can be
separated with the authentication mechanism.  You can create protected
Flask modules without knowing the actual authentication mechanisms.


Installation
============

You can install Flask-DigestAuth with ``pip``:

::

    pip install Flask-DigestAuth

You may also install the latest source from the
`Flask-DigestAuth GitHub repository`_.

::

    pip install git+https://github.com/imacat/flask-digestauth.git


Documentation
=============

Refer to the `documentation on Read the Docs`_.


Change Log
==========

Refer to the `change log`_.


Copyright
=========

 Copyright (c) 2022-2023 imacat.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.


Authors
=======

| imacat
| imacat@mail.imacat.idv.tw
| 2022/11/23

.. _HTTP Digest Authentication: https://en.wikipedia.org/wiki/Digest_access_authentication
.. _RFC 2617: https://www.rfc-editor.org/rfc/rfc2617
.. _Flask: https://flask.palletsprojects.com
.. _Flask-DigestAuth GitHub repository: https://github.com/imacat/flask-digestauth
.. _Flask-Login: https://flask-login.readthedocs.io
.. _documentation on Read the Docs: https://flask-digestauth.readthedocs.io
.. _change log: https://flask-digestauth.readthedocs.io/en/latest/changelog.html
