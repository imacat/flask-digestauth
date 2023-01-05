================================
Flask HTTP Digest Authentication
================================


Description
===========

*Flask-DigestAuth* is an `HTTP Digest Authentication`_ implementation
for Flask_ applications.  It authenticates the user for the protected
views.

HTTP Digest Authentication is specified in `RFC 2617`_.

Refer to the full `Flask-DigestAuth readthedocs documentation`_.


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


Configuration
=============

Flask-DigestAuth takes the configuration ``DIGEST_AUTH_REALM`` as the
realm.  The default realm is ``Login Required``.


Setting the Password
====================

The password hash of the HTTP Digest Authentication is composed of the
realm, the username, and the password.  Example for setting the
password:

::

    from flask_digest_auth import make_password_hash

    user.password = make_password_hash(realm, username, password)

The username is part of the hash.  If the user changes their username,
you need to ask their password, to generate and store the new password
hash.


Flask-DigestAuth Alone
======================

Flask-DigestAuth can authenticate the users alone.


Simple Applications with Flask-DigestAuth Alone
-----------------------------------------------

In your ``my_app.py``:

::

    from flask import Flask, request, redirect
    from flask_digest_auth import DigestAuth

    app: flask = Flask(__name__)
    ... (Configure the Flask application) ...

    auth: DigestAuth = DigestAuth()
    auth.init_app(app)

    @auth.register_get_password
    def get_password_hash(username: str) -> t.Optional[str]:
        ... (Load the password hash) ...

    @auth.register_get_user
    def get_user(username: str) -> t.Optional[t.Any]:
        ... (Load the user) ...

    @app.get("/admin")
    @auth.login_required
    def admin():
        return f"Hello, {g.user.username}!"

    @app.post("/logout")
    @auth.login_required
    def logout():
        auth.logout()
        return redirect(request.form.get("next"))


Larger Applications with ``create_app()`` with Flask-DigestAuth Alone
---------------------------------------------------------------------

In your ``my_app/__init__.py``:

::

    from flask import Flask
    from flask_digest_auth import DigestAuth

    auth: DigestAuth = DigestAuth()

    def create_app(test_config = None) -> Flask:
        app: flask = Flask(__name__)
        ... (Configure the Flask application) ...

        auth.init_app(app)

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            ... (Load the password hash) ...

        @auth.register_get_user
        def get_user(username: str) -> t.Optional[t.Any]:
            ... (Load the user) ...

        return app

In your ``my_app/views.py``:

::

    from my_app import auth
    from flask import Flask, Blueprint, request, redirect

    bp = Blueprint("admin", __name__, url_prefix="/admin")

    @bp.get("/admin")
    @auth.login_required
    def admin():
        return f"Hello, {g.user.username}!"

    @app.post("/logout")
    @auth.login_required
    def logout():
        auth.logout()
        return redirect(request.form.get("next"))

    def init_app(app: Flask) -> None:
        app.register_blueprint(bp)



Flask-Login Integration
=======================

Flask-DigestAuth works with Flask-Login_.  You can write a Flask
module that requires log in, without specifying how to log in.  The
application can use either HTTP Digest Authentication, or the log in
forms, as needed.

To use Flask-Login with Flask-DigestAuth,
``login_manager.init_app(app)`` must be called before
``auth.init_app(app)``.

The currently logged-in user can be retrieved at
``flask_login.current_user``, if any.

The views only depend on Flask-Login, but not the Flask-DigestAuth.
You can change the actual authentication mechanism without changing
the views.


Simple Applications with Flask-Login Integration
------------------------------------------------

In your ``my_app.py``:

::

    import flask_login
    from flask import Flask, request, redirect
    from flask_digest_auth import DigestAuth

    app: flask = Flask(__name__)
    ... (Configure the Flask application) ...

    login_manager: flask_login.LoginManager = flask_login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> t.Optional[User]:
        ... (Load the user with the username) ...

    auth: DigestAuth = DigestAuth()
    auth.init_app(app)

    @auth.register_get_password
    def get_password_hash(username: str) -> t.Optional[str]:
        ... (Load the password hash) ...

    @app.get("/admin")
    @flask_login.login_required
    def admin():
        return f"Hello, {flask_login.current_user.get_id()}!"

    @app.post("/logout")
    @flask_login.login_required
    def logout():
        auth.logout()
        # Do not call flask_login.logout_user()
        return redirect(request.form.get("next"))


Larger Applications with ``create_app()`` with Flask-Login Integration
----------------------------------------------------------------------

In your ``my_app/__init__.py``:

::

    from flask import Flask
    from flask_digest_auth import DigestAuth
    from flask_login import LoginManager

    auth: DigestAuth = DigestAuth()

    def create_app(test_config = None) -> Flask:
        app: flask = Flask(__name__)
        ... (Configure the Flask application) ...

        login_manager: LoginManager = LoginManager()
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id: str) -> t.Optional[User]:
            ... (Load the user with the username) ...

        auth.init_app(app)

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            ... (Load the password hash) ...

        return app

In your ``my_app/views.py``:

::

    import flask_login
    from flask import Flask, Blueprint, request, redirect
    from my_app import auth

    bp = Blueprint("admin", __name__, url_prefix="/admin")

    @bp.get("/admin")
    @flask_login.login_required
    def admin():
        return f"Hello, {flask_login.current_user.get_id()}!"

    @app.post("/logout")
    @flask_login.login_required
    def logout():
        auth.logout()
        # Do not call flask_login.logout_user()
        return redirect(request.form.get("next"))

    def init_app(app: Flask) -> None:
        app.register_blueprint(bp)

The views only depend on Flask-Login, but not the actual
authentication mechanism.  You can change the actual authentication
mechanism without changing the views.


Session Integration
===================

Flask-DigestAuth features session integration.  The user log in
is remembered in the session.  The authentication information is not
requested again.  This is different to the practice of the HTTP Digest
Authentication, but is convenient for the log in accounting.


Log In Bookkeeping
==================

You can register a callback to run when the user logs in, for ex.,
logging the log in event, adding the log in counter, etc.

::

    @auth.register_on_login
    def on_login(user: User) -> None:
        user.visits = user.visits + 1


Log Out
=======

Flask-DigestAuth supports log out.  The user will be prompted for the
new username and password.


Test Client
===========

Flask-DigestAuth comes with a test client that supports HTTP digest
authentication.


A unittest Test Case
--------------------

::

    from flask import Flask
    from flask_digest_auth import Client
    from flask_testing import TestCase
    from my_app import create_app

    class MyTestCase(TestCase):

        def create_app(self):
            app: Flask = create_app({
                "TESTING": True,
                "SECRET_KEY": token_urlsafe(32),
                "DIGEST_AUTH_REALM": "admin",
            })
            app.test_client_class = Client
            return app

        def test_admin(self):
            response = self.client.get("/admin")
            self.assertEqual(response.status_code, 401)
            response = self.client.get(
                "/admin", digest_auth=(USERNAME, PASSWORD))
            self.assertEqual(response.status_code, 200)


A pytest Test
-------------

::

    import pytest
    from flask import Flask
    from flask_digest_auth import Client
    from my_app import create_app

    @pytest.fixture()
    def app():
        app: Flask = create_app({
            "TESTING": True,
            "SECRET_KEY": token_urlsafe(32),
            "DIGEST_AUTH_REALM": "admin",
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
.. _Flask-DigestAuth readthedocs documentation: https://flask-digestauth.readthedocs.io
.. _Flask-Login: https://flask-login.readthedocs.io
