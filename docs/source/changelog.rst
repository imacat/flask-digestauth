Change Log
==========


Version 0.6.0
-------------

Released 2023/4/26

* Updated the minimal Python version to 3.8.
* Switched from ``setup.cfg`` to ``pyproject.toml``.
* Added the change log.
* Simplified ``README.rst``.


Version 0.5.0
-------------

Released 2023/1/6

* Added the ``DIGEST_AUTH_REALM`` configuration variable as the
  recommended way to set the authentication realm.
* Changed the default realm from an empty string to
  ``Login Required``.


Version 0.4.0
-------------

Released 2023/1/4

* Changed the package name from ``flask-digest-auth`` to
  ``Flask-DigestAuth``, according to the Flask recommended extension
  guidelines
  https://flask.palletsprojects.com/en/latest/extensiondev/ .
* Replaced ``app.digest_auth`` with ``app.extensions["digest-auth"]``
  to store the ``DigestAuth`` instance.
* Replaced ``auth.app`` with ``current_app``, to prevent circular
  imports.


Version 0.3.1
-------------

Released 2022/12/29

Fixed the missing authentication state with disabled users.


Version 0.3.0
-------------

Released 2022/12/7

Changed the visibility of several methods and properties of the
DigestAuth class that should be private to private.


Version 0.2.4
-------------

Released 2022/12/6

Fixed the pytest example in the documentation.


Version 0.2.3
-------------

Released 2022/12/6

Fixed the dependencies for the documentation hosted on Read the Docs.


Version 0.2.2
-------------

Released 2022/12/6

Added the Sphinx documentation, and hosted the documentation on
Read the Docs.


Version 0.2.1
-------------

Released 2022/12/6

Various fixes, with the help from SonarQube.


Version 0.2.0
-------------

Released 2022/11/27

* Added log out support.  User can log out.
* Added on-login event handler.  You can do some accounting when the
  user logs in.

This release is written in Sydney and on the international flight,
and released in Taipei.


Version 0.1.1
-------------

Released 2022/11/24

Changed the minimal Python version to 3.7.

Released at Sydney, Australia on vacation.


Version 0.1.0
-------------

Released 2022/11/24

The initial release.

Released at Sydney, Australia on vacation.
