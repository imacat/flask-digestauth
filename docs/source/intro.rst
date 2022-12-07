Introduction
============


*Flask-Digest-Auth* is an `HTTP Digest Authentication`_ implementation
for Flask_ applications.  It authenticates the user for the protected
views.

HTTP Digest Authentication is specified in `RFC 2617`_.


Why HTTP Digest Authentication?
-------------------------------

*HTTP Digest Authentication* has the advantage that it does not send
the actual password to the server, which greatly enhances the
security.  It uses the challenge-response authentication scheme.  The
client returns the response calculated from the challenge and the
password, but not the original password.

Log in forms has the advantage of freedom, in the senses of both the
visual design and the actual implementation.  You may implement your
own challenge-response log in form, but then you are reinventing the
wheels.  If a pretty log in form is not critical to your project, HTTP
Digest Authentication should be a good choice.

Flask-Digest-Auth works with Flask-Login_.  Log in protection can be
separated with the authentication mechanism.  You can create protected
Flask modules without knowing the actual authentication mechanisms.


Installation
------------

You can install Flask-Digest-Auth with ``pip``:

::

    pip install Flask-Digest-Auth

You may also install the latest source from the
`Flask-Digest-Auth GitHub repository`_.

::

    pip install git+https://github.com/imacat/flask-digest-auth.git


Setting the Password
--------------------

The password hash of the HTTP Digest Authentication is composed of the
realm, the username, and the password.  Example for setting the
password:

::

    from flask_digest_auth import make_password_hash

    user.password = make_password_hash(realm, username, password)

The username is part of the hash.  If the user changes their username,
you need to ask their password, to generate and store the new password
hash.

See :func:`flask_digest_auth.algo.make_password_hash`.


Flask-Digest-Auth Alone
-----------------------

Flask-Digest-Auth can authenticate the users alone.

See :ref:`example-alone-simple` and :ref:`example-alone-large`.


Flask-Login Integration
-----------------------

Flask-Digest-Auth works with Flask-Login_.  You can write a Flask
module that requires log in, without specifying how to log in.  The
application can use either HTTP Digest Authentication, or the log in
forms, as needed.

To use Flask-Login with Flask-Digest-Auth,
``login_manager.init_app(app)`` must be called before
``auth.init_app(app)``.

The currently logged-in user can be retrieved at
``flask_login.current_user``, if any.

See :ref:`example-flask-login-simple` and
:ref:`example-flask-login-large`.

The views only depend on Flask-Login, but not the Flask-Digest-Auth.
You can change the actual authentication mechanism without changing
the views.


Session Integration
-------------------

Flask-Digest-Auth features session integration.  The user log in
is remembered in the session.  The authentication information is not
requested again.  This is different to the practice of the HTTP Digest
Authentication, but is convenient for the log in accounting.


Log In Bookkeeping
------------------

You can register a callback to run when the user logs in, for ex.,
logging the log in event, adding the log in counter, etc.

::

    @auth.register_on_login
    def on_login(user: User) -> None:
        user.visits = user.visits + 1

See :meth:`flask_digest_auth.auth.DigestAuth.register_on_login`.


Log Out
-------

Flask-Digest-Auth supports log out.  The user will be prompted for the
new username and password.

See :meth:`flask_digest_auth.auth.DigestAuth.logout`.


Test Client
-----------

Flask-Digest-Auth comes with a test client that supports HTTP digest
authentication.

See :class:`flask_digest_auth.test.Client`.

Also see :ref:`example-unittest` and :ref:`example-pytest`.


.. _HTTP Digest Authentication: https://en.wikipedia.org/wiki/Digest_access_authentication
.. _RFC 2617: https://www.rfc-editor.org/rfc/rfc2617
.. _Flask: https://flask.palletsprojects.com
.. _Flask-Login: https://flask-login.readthedocs.io
.. _Flask-Digest-Auth GitHub repository: https://github.com/imacat/flask-digest-auth
