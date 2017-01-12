# Preparing an eReuse Workbench release

This document enumerates the steps needed for releasing a new version of the eReuse Workbench tools.

## 1. Increase the version in source code

Let ``SOURCE`` be a Git checkout of the ``master`` branch of the Workbench source code.

Edit ``erwb/__init__.py`` and update the value of the ``VERSION`` variable according to [Semantic Versioning][] and the [Python Packaging User Guide][].

[Semantic Versioning]: http://semver.org/
[Python Packaging User Guide]: https://packaging.python.org/distributing/#choosing-a-versioning-scheme

Then commit the change with a message like:

> Bump version to VERSION

Where ``VERSION`` is the compact version number of the package, which you may obtain by running:

    ( cd erwb \
      && python -c 'from __init__ import get_version; print get_version()' )

Finally, push changes upstream:

    $ git push

## 2. Tag the current commit

Add an annotated tag to the current commit with the name ``vVERSION`` (using the same value of ``VERSION`` as in the previous point), e.g. by running:

> $ git tag -a vVERSION

Describe in the tag notes the main changes of the new major or minor release, along with fixes in this patch release, in [Markdown syntax][].  This is a possible template for the notes:

```markdown
Version X.Y(.Z) (alpha|beta|rc N)

Some introductory notes...

Release news
============

  - One new feature of this major or minor release compared to the previous one (reference to related #issue).
  - Another new feature (#issue).

Release fixes
=============

  - One bug fixed by this major or minor release compared to the previous one (reference to related #issue).
  - Another bug fix (#issue)

Guides
======

  - Link to a guide.
  - Link to another guide.

--------

Fixes
=====

  - A fix in this particular patch release (#issue).

New features
============

  - A new feature added in this particular patch release (#issue).

```

[Markdown syntax]: https://daringfireball.net/projects/markdown/syntax

Finally, push the tag upstream:

    $ git push --tags

## 3. Create a Python source package

Use the following command:

    $ python setup.py sdist

This will create the ``dist/ereuse-workbench-VERSION.tar.gz`` file.

## 4. Create the eReuseOS ISO

You need to run the ``build_ereuse_iso.sh`` script as root from the ``SOURCE`` directory:

    $ sudo scripts/build_ereuse_iso.sh

After a while, the file ``dist/iso/eReuseOS-VERSION.iso`` will be created, including an installation of the Python package generated above.

## 5. Create the data archive

From the ``SOURCE`` directory, run:

    $ scripts/build_ereuse_data.sh

This will create the ``dist/ereuse-data-VERSION.tar.gz`` file, which includes the previously generated ISO, a default configuration file, and others.

## 6. Create the PXE server OVA

To perform this step you must first make sure that there are no VirtualBox virtual machines running, since a KVM VM needs to be launched during the process.

You need to run the ``build_ereuse_ova.sh`` script as root from the ``SOURCE`` directory:

    $ sudo scripts/build_ereuse_ova.sh

After a while, the file ``dist/ereuse-server-VERSION.ova`` will be created.

**Note:** The PXE server is independent from the package, ISO and data archive created above, so as long as new releases of the Workbench do not change the way they interact with the PXE server, there is no need to release a new OVA.  In a similar manner, if a fix to the server does not imply changes to the interaction with the Workbench, there is no need to release a new data archive.

## 7. Publish the new release

If using GitHub, follow the *releases* link under the *Code* tab, then click on the *Draft a new release* button.  Choose tag version ``vVERSION`` of the ``master`` branch.  As the release title enter the first, title line of the version tag note, and the rest of it as the release description.  You may get the tag note with:

    $ git show vVERSION

Then attach the ``dist/ereuse-data-VERSION.tar.gz`` and ``dist/ereuse-server-VERSION.ova`` files as needed for this particular release.

Enable the pre-release check box if convenient.

Finally, click on the *Publish release* button.  Congratulations!  A new release of the eReuse Workbench is out!`:)`
