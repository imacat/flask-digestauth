================================
Flask HTTP Digest Authentication
================================


Description
===========

*Flask-Digest-Auth* is an HTTP Digest Authentication implementation
for Flask_ applications.  It authenticates the user for the protected
views.  It works with Flask-Login_, so that log in protection can be
separated with the authentication mechanism.  You can write Flask
modules that work with different authentication mechanisms.

.. _Flask: https://flask.palletsprojects.com
.. _Flask-Login: https://flask-login.readthedocs.io


Installation
============

It's suggested that you install with ``pip``:

::

    pip install flask-digest-auth

You may also install from the latest source from the
`flask-digest-auth Github repository`_.

::

    git clone git@github.com:imacat/flask-digest-auth.git
    cd flask-digest-auth
    pip install .

.. _flask-digest-auth Github repository: https://github.com/imacat/flask-digest-auth


Flask-Digest-Auth Alone
=======================

Flask-Digest-Auth can authenticate the users alone.


Example for Simple Applications with Flask-Digest-Auth Alone
------------------------------------------------------------

In your ``my_app.py``:

::

    from flask import Flask
    from flask_digest_auth import DigestAuth

    app: flask = Flask(__name__)
    ... (Configure the Flask application) ...

    auth: DigestAuth = DigestAuth(realm="Admin")

    @auth.register_get_password
    def get_password_hash(username: str) -> t.Optional[str]:
        ... (Load the password hash) ...

    @auth.register_get_user
    def get_user(username: str) -> t.Optional[t.Any]:
        ... (Load the user) ...

    @app.get("/admin")
    @auth.login_required
    def admin():
        ... (Process the view) ...


Example for Larger Applications with ``create_app()`` with Flask-Digest-Auth Alone
----------------------------------------------------------------------------------

In your ``my_app/__init__.py``:

:::

    from flask import Flask
    from flask_digest_auth import DigestAuth

    auth: DigestAuth = DigestAuth()

    def create_app(test_config = None) -> Flask:
        app: flask = Flask(__name__)
        ... (Configure the Flask application) ...

        auth.realm = app.config["REALM"]

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
    from flask import Flask, Blueprint

    bp = Blueprint("admin", __name__, url_prefix="/admin")

    @bp.get("/")
    @auth.login_required
    def admin():
        ... (Process the view) ...

    def init_app(app: Flask) -> None:
        app.register_blueprint(bp)


Flask-Login Integration
=======================

Flask-Digest-Auth can work with Flask-Login.  You can write a Flask
module that requires log in, without specifying the authentication
mechanism.  The Flask application can specify the actual
authentication mechanism as it sees fit.


Example for Simple Applications with Flask-Login Integration
------------------------------------------------------------

In your ``my_app.py``:

::

    from flask import Flask
    from flask_digest_auth import DigestAuth
    from flask_login import LoginManager

    app: flask = Flask(__name__)
    ... (Configure the Flask application) ...

    login_manager: LoginManager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> t.Optional[User]:
        ... (Load the user with the username) ...

    auth: DigestAuth = DigestAuth(realm="Admin")
    auth.init_app(app)

    @auth.register_get_password
    def get_password_hash(username: str) -> t.Optional[str]:
        ... (Load the password hash) ...

    @app.get("/admin")
    @login_manager.login_required
    def admin():
        ... (Process the view) ...


Example for Larger Applications with ``create_app()`` with Flask-Login Integration
----------------------------------------------------------------------------------

In your ``my_app/__init__.py``:

:::

    from flask import Flask
    from flask_digest_auth import DigestAuth
    from flask_login import LoginManager

    def create_app(test_config = None) -> Flask:
        app: flask = Flask(__name__)
        ... (Configure the Flask application) ...

        login_manager: LoginManager = LoginManager()
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id: str) -> t.Optional[User]:
            ... (Load the user with the username) ...

        auth: DigestAuth = DigestAuth(realm=app.config["REALM"])
        auth.init_app(app)

        @auth.register_get_password
        def get_password_hash(username: str) -> t.Optional[str]:
            ... (Load the password hash) ...

        return app

In your ``my_app/views.py``:

::

    import flask_login
    from flask import Flask, Blueprint

    bp = Blueprint("admin", __name__, url_prefix="/admin")

    @bp.get("/")
    @flask_login.login_required
    def admin():
        ... (Process the view) ...

    def init_app(app: Flask) -> None:
        app.register_blueprint(bp)

The views only depend on Flask-Login, but not its underlying
authentication mechanism.  You can always change the
authentication mechanism without changing the views, or release a
protected Flask module without specifying the authentication
mechanism.


Writing Tests
=============

You can write tests with our test client that handles HTTP Digest
Authentication.  Example for a unittest testcase:

::

    from flask_digest_auth import Client
    from flask_testing import TestCase
    from my_app import create_app

    class MyTestCase(TestCase):

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
                "/admin", digest_auth=("my_name", "my_pass"))
            self.assertEqual(response.status_code, 200)


Copyright
=========

 Copyright (c) 2022 imacat.

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
