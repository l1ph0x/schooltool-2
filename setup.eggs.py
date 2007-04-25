#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation,
#                       Brian Sutherland
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool setup script.
"""


# Check python version
import sys
if sys.version_info < (2, 4):
    print >> sys.stderr, '%s: need Python 2.4 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import site
site.addsitedir('eggs')

import pkg_resources
pkg_resources.require("setuptools>=0.6a11")

import os
from setuptools import setup, find_packages

def get_version():
    version_file = os.path.join('src', 'schooltool', 'version.txt')
    f = open(version_file, 'r')
    result = f.read()
    f.close()
    return result

# Setup SchoolTool
setup(
    name="schooltool",
    description="A common information systems platform for school administration.",
    long_description="""
SchoolTool is an open source school management information system.  It is
a distributed client/server system.  The SchoolTool server presents two
interfaces to clients:

  - a traditional web application interface, usable with an ordinary browser.

  - HTTP-based programming interface suitable for fat clients, adhering to
    the Representational State Transfer (REST) architectural style (see
    http://rest.blueoxen.net/).

The web application interface is the primary one.  The RESTive interface is
there for potential interoperability with other systems and fat clients to
perform data entry that is inconvenient to do via the web application
interface.

Any modern web browser is suitable for the web application interface.  The
interface degrades gracefully, so a browser that does not support CSS or
Javascript will be usable, although perhaps not very nice or convenient.""",
    version=get_version(),
    url='http://www.schooltool.org',
    license="GPL",
    maintainer="SchoolTool development team",
    maintainer_email="schooltool-dev@schooltool.org",
    platforms=["any"],
    classifiers=["Development Status :: 5 - Production/Stable",
    "Environment :: Web Environment",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Zope",
    "Topic :: Education",
    "Topic :: Office/Business :: Scheduling"],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=['pytz >= 2007c',
                      'zc.resourcelibrary >= 0.7dev_r72506',
                      'zc.table >= 0.7dev_r72459', 'zc.catalog >= 1.2dev',
                      'hurry.query >= 0.9.2',
                      'zc.datetimewidget >= 0.6.1dev_r72453',
                      'zope.ucol >= 1.0.2', 'zope.html >= 0.1dev_r72429',
                      'zope.file >= 0.1dev_r72428',
                      'zope.mimetype >= 1.1dev_r72462',
                      'z3c.javascript.mochikit >= 0.0.1',
                      'zope.i18nmessageid',
                      'zope.app.catalog',
                      'zope.viewlet',
                      'zope.app.file',
                      'zope.app.onlinehelp',
                      'zope.app.apidoc',
                      'zope.optionstorage',
                      'zope.wfmc',
                      'zope.app.wfmc',
                      'zope.server',
                      'zope.app.wsgi',
                      'zope.app.server',
                      'zope.app.generations',
                      'zope.app.securitypolicy',
                      'zope.app.zcmlfiles'],
    dependency_links=['http://ftp.schooltool.org/schooltool/eggs/',
                      'http://download.zope.org/distribution/',
                      'http://eggs.carduner.net/'],
    )
