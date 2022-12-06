Introduction
============


*Flask-Digest-Auth* is an `HTTP Digest Authentication`_ implementation
for Flask_ applications.  It authenticates the user for the protected
views.

HTTP Digest Authentication is specified in `RFC 2617`_.

See :ref:`example-alone-simple` and :ref:`example-alone-large`.


Why HTTP Digest Authentication?
-------------------------------

HTTP Digest Authentication has the advantage that it does not send the
actual password to the server, which greatly enhances the security.
It uses the challenge-response authentication scheme.  The client
returns the response calculated from the challenge and the password,
but not the original password.

Log in forms has the advantage of freedom, in the senses of both the
visual design and the actual implementation.  You may implement your
own challenge-response log in form, but then you are reinventing the
wheels.  If a pretty log in form is not critical to your project, HTTP
Digest Authentication should be a good choice.

Flask-Digest-Auth works with Flask-Login_.  Log in protection can be
separated with the authentication mechanism.  You can create protected
Flask modules without knowing the actual authentication mechanisms.


Features
--------

There are a couple of Flask HTTP digest authentication
implementations.  Flask-Digest-Auth has the following features:


Flask-Login Integration
#######################

Flask-Digest-Auth features Flask-Login integration.  The views
can be totally independent with the actual authentication mechanism.
You can write a Flask module that requires log in, without specify
the actual authentication mechanism.  The application can specify
either HTTP Digest Authentication, or the log in forms, as needed.

See :ref:`example-flask-login-simple` and
:ref:`example-flask-login-large`.


Session Integration
###################

Flask-Digest-Auth features session integration.  The user log in
is remembered in the session.  The authentication information is not
requested again.  This is different to the practice of the HTTP Digest
Authentication, but is convenient for the log in accounting.


Log In Bookkeeping
##################

You can register a callback to run when the user logs in.
See :meth:`flask_digest_auth.DigestAuth.register_on_login`.


Log Out
#######

Flask-Digest-Auth supports log out.  The user will be prompted for the
new username and password.
See :meth:`flask_digest_auth.DigestAuth.logout`.


Test Client
###########

Flask-Digest-Auth comes with a test client that supports HTTP digest
authentication.
See :class:`flask_digest_auth.Client`.

Also see :ref:`example-unittest` and :ref:`example-pytest`.


.. _HTTP Digest Authentication: https://en.wikipedia.org/wiki/Digest_access_authentication
.. _RFC 2617: https://www.rfc-editor.org/rfc/rfc2617
.. _Flask: https://flask.palletsprojects.com
.. _Flask-Login: https://flask-login.readthedocs.io
