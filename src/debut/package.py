# Debian packaging tools: Package manipulation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 25, 2018
# URL: https://github.com/xolox/python-deb-pkg-tools
#
# Copyright (c) 2018 Peter Odding
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# Debian packaging tools: Relationship parsing and evaluation.
#

"""
Functions to build and inspect Debian binary package archives (``*.deb``
files)."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import itertools
from os import path
import sys

if sys.version_info[:2] >= (3, 6):
    OrderedDict = dict
else:
    from collections import OrderedDict

from attr import attrs
from attr import attrib
from attr import Factory

from debut.version import Version


# The names of control file fields that specify dependencies.
DEPENDENCY_FIELDS = ('Depends', 'Pre-Depends')


@attrs
class DebArchive(object):
    """
    A .deb binary package archive.
    """
    name = attrib()
    version = attrib()
    architecture = attrib()
    original_filename = attrib(default=None)

    @classmethod
    def from_filename(cls, filename):
        """
        Parse the filename of a Debian binary package archive and return a DebArchive instance.
        Raise ValueError if the `filename` is not valid.

        For example::

        >>> from debut import package
        >>> components = packageDevArchive.from_filename('/var/cache/apt/archives/python2.7_2.7.3-0ubuntu3.4_amd64.deb')
        >>> print(repr(components))
        DebArchive(name='python2.7',
                   version='2.7.3-0ubuntu3.4',
                   architecture='amd64',
                   original_filename='/var/cache/apt/archives/python2.7_2.7.3-0ubuntu3.4_amd64.deb')

        """
        if isinstance(filename, DebArchive):
            return filename
        original_filename = filename
        filename = path.basename(filename)
        basename, extension = path.splitext(filename)
        if extension not in ('.deb', '.udeb'):
            raise ValueError(
                'Unknown Debian binary package filename extension: {}'.format(filename))
        components = basename.split('_')
        if len(components) != 3:
            raise ValueError(
                'Unknown Debian binary package filename format. '
                'Should have three underscore: {}'.format(filename))
        name, evr, architecture = components
        version = Version.from_string(evr)
        return cls(
            name=name,
            version=version,
            architecture=architecture,
            original_filename=original_filename)

    def to_dict(self):
        data = OrderedDict()
        data['name'] = self.name
        data['version'] = self.version
        data['architecture'] = self.architecture
        data['original_filename'] = self.original_filename
        return data

    def to_tuple(self):
        """
        Return a tuple of name, Vresion, architecture suitable for sorting.
        This tuple does not contain the original_filename values.
        """
        return tuple(v for v in self.to_dict().values() if v != 'original_filename')


# TODO: simplify me
def match_relationships(package_archive, relationship_sets):
    """
    Validate that `package_archive` DebArchive satisfies all the relationships
    of a `relationship_sets`. Return True if valid and False otherwise.
    """
    archive_matches = None
    for relationships in relationship_sets:
        status = relationships.matches(package_archive.name, package_archive.version)
        if status is True and archive_matches is not False:
            archive_matches = True
        elif status is False:
            # This package archive specifically conflicts with (at least) one
            # of the given relationship sets.
            archive_matches = False
            # Short circuit the evaluation of further relationship sets because
            # we've already found our answer.
            break
    return archive_matches


def find_latest_version(packages):
    """
    Return the DebArchive package archive with the highest version number given
    a `packages` list of  package filename strings or DebArchive instances.
    All package items must have the same package name

    Raise ValueError if a package filename is invalid or if the packages do not
    have all the same package name.
    """
    if not packages:
        return
    packages = [DebArchive.from_filename(fn) for fn in packages]
    packages = sorted(packages, key=lambda p: p.to_tuple())
    names = set(p.name for p in packages)
    if len(names) > 1:
        msg = 'Cannot compare versions of different package names'
        raise ValueError(msg.format(' '.join(sorted(names))))
    return packages[-1]


def find_latest_versions(packages):
    """
    Return a mapping {name: DebArchive} where DebArchive is the package archive
    with the highest version number for a given package name given a `packages`
    list of  package filename strings or DebArchive instances.
    """
    if not packages:
        return
    packages = sorted([DebArchive.from_filename(fn) for fn in packages])
    latests = {}
    for name, packages_group in itertools.groupby(packages, key=lambda p: p.name):
        latest = find_latest_version(packages_group)
        latests[name] = latest
    return latests
