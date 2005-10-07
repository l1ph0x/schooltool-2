#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Backend for the SchoolTool GUI client.  This module abstracts all communication
with the SchoolTool server.

Note that all strings used in data objects are Unicode strings.
"""

import httplib
import socket
import libxml2
import datetime
import urllib
import base64
import cgi

from schooltool.common import parse_datetime, parse_date, to_unicode
from schooltool.common import UnicodeAwareException
from schooltool.common import looks_like_a_uri
from schooltool import SchoolToolMessageID as _

__metaclass__ = type


#
# Client/server communication
#


def make_basic_auth(username, password):
    r"""Generate HTTP basic authentication credentials.

    Example:

        >>> make_basic_auth('myusername', 'secret')
        'Basic bXl1c2VybmFtZTpzZWNyZXQ='

    Usernames and passwords that contain non-ASCII characters are converted to
    UTF-8 before encoding.

        >>> make_basic_auth('myusername', '\u263B')
        'Basic bXl1c2VybmFtZTpcdTI2M0I='

    """
    creds = "%s:%s" % (username, password)
    return "Basic " + base64.encodestring(creds.encode('UTF-8')).strip()


def to_xml(s):
    r"""Prepare `s` for inclusion into XML (convert to UTF-8 and escape).

        >>> to_xml('foo')
        'foo'
        >>> to_xml(u'\u263B')
        '\xe2\x98\xbb'
        >>> to_xml('<brackets> & "quotes"')
        '&lt;brackets&gt; &amp; &quot;quotes&quot;'
        >>> to_xml(42)
        '42'

    """
    return cgi.escape(unicode(s).encode('UTF-8'), True)


class SchoolToolClient:
    """Client for the SchoolTool HTTP server.

    Every method that communicates with the server sets the status and version
    attributes.

    All URIs used to identify objects are relative and contain the absolute
    path within the server.
    """

    # Hooks for unit tests.
    connectionFactory = httplib.HTTPConnection
    secureConnectionFactory = httplib.HTTPSConnection

    def __init__(self, server='localhost', port=7001, ssl=False,
                 user=None, password=''):
        self.server = server
        self.port = port
        self.ssl = ssl
        self.user = user
        self.password = password
        self.status = ''
        self.version = ''


    # Generic HTTP methods

    def setServer(self, server, port, ssl=False):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message.
        """
        self.server = server
        self.port = port
        self.ssl = ssl
        self.tryToConnect()

    def setUser(self, user, password):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message.
        """
        if user:
            self.user = user
            self.password = password
        else:
            self.user = None
            self.password = ""

    def tryToConnect(self):
        """Try to connect to the server and set the status message.

        If connection is successful, try to update the URI list."""
        try:
            self.get('/')
        except SchoolToolError, e:
            # self.status has been set and will be shown on the status bar
            pass

    def get(self, path, headers=None):
        """Perform an HTTP GET request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('GET', path, headers=headers)

    def post(self, path, body, headers=None):
        """Perform an HTTP POST request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('POST', path, body, headers=headers)

    def put(self, path, body, headers=None):
        """Perform an HTTP PUT request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('PUT', path, body, headers=headers)

    def delete(self, path, headers=None):
        """Perform an HTTP DELETE request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('DELETE', path, '', headers=headers)

    def _request(self, method, path, body=None, headers=None):
        """Perform an HTTP request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        if self.ssl:
            conn = self.secureConnectionFactory(self.server, self.port)
        else:
            conn = self.connectionFactory(self.server, self.port)
        try:
            hdrs = {}
            if body:
                hdrs['Content-Type'] = 'text/xml'
                # Do *not* specify a Content-Length header here.  It will
                # be provided by httplib automatically.  In fact, if you do
                # specify it here, httplib will happily send out a request
                # with two Content-Type headers and confuse proxies such as
                # Apache.
            if self.user is not None:
                creds = make_basic_auth(self.user, self.password)
                hdrs['Authorization'] = creds
            if headers:
                hdrs.update(headers)
            conn.request(method, path, body, hdrs)
            response = Response(conn.getresponse())
            conn.close()
            self.status = "%d %s" % (response.status, response.reason)
            self.version = response.getheader('Server')
            return response
        except socket.error, e:
            conn.close()
            errno, message = e.args
            self.status = "%s (%d)" % (message, errno)
            self.version = ""
            raise SchoolToolError(self.status)

    # SchoolTool specific methods

    def getListOfPersons(self):
        """Return the list of all persons.

        Returns a sequence of tuples (person_title, person_path).
        """
        response = self.get('/persons')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getListOfGroups(self):
        """Return the list of all groups.

        Returns a sequence of tuples (group_title, group_path).
        """
        response = self.get('/groups')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getListOfResources(self):
        """Return the list of all resources.

        Returns a sequence of tuples (resource_title, resource_path).
        """
        response = self.get('/resources')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getGroupInfo(self, group_path):
        """Return information page about a group.

        Returns a GroupInfo object.
        """
        relationships = self.getObjectRelationships(group_path)
        member_relationships = [relationship for relationship in relationships
                                if relationship.role.uri == URIMember_uri]
        members = [MemberInfo(member_relationship.target_path)
                   for member_relationship in member_relationships]
        return GroupInfo(members)

    def getPersonInfo(self, person_path):
        """Return information about a person.

        Returns a PersonInfo object.
        """
        response = self.get(person_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parsePersonInfo(response.read())

    def savePersonInfo(self, person_path, person_info):
        """Put a PersonInfo object."""
        path = person_path
        body = """
            <object xmlns:xlink="http://www.w3.org/1999/xlink"
                    xmlns="http://schooltool.org/ns/model/0.1"
                    title="%s" />
        """ % to_xml(person_info.title)

        response = self.put(path, body)
        if response.status / 100 != 2:
            raise ResponseStatusError(response)

    def getPersonPhoto(self, person_path):
        """Return the photo of a person.

        Returns an 8-bit string with JPEG data.

        Returns None if the person does not have a photo.
        """
        response = self.get(person_path + '/photo')
        if response.status == 404:
            return None
        elif response.status != 200:
            raise ResponseStatusError(response)
        else:
            return response.read()

    def savePersonPhoto(self, person_path, person_photo):
        """Upload a photo for a person.

        photo should be an 8-bit string with image data.
        """
        path = person_path + '/photo'
        response = self.put(path, person_photo,
                        headers={'Content-Type': 'application/octet-stream'})
        if response.status / 100 != 2:
            raise ResponseStatusError(response)

    def removePersonPhoto(self, person_path):
        """Remove a person's photo."""
        path = person_path + '/photo'
        response = self.delete(path)
        if response.status / 100 != 2:
            raise ResponseStatusError(response)

    def getObjectRelationships(self, object_path):
        """Return relationships of an application object (group or person).

        Returns a list of RelationshipInfo objects.
        """
        response = self.get('%s/relationships' % object_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseRelationships(response.read())

    def getTerms(self):
        """Return a list of terms.

        Returns a sequence of tuples (term_title, term_path).
        """
        response = self.get("/terms")
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getTimetableSchemas(self):
        """Return a list of timetable schemas.

        Returns a sequence of tuples (term_title, term_path).
        """
        response = self.get("/ttschemas")
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def createPerson(self, person_title, name, password=None):
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"/>' % to_xml(person_title))

        path = '/persons/' + name
        response = self.put(path, body)

        if response.status != 201:
            raise ResponseStatusError(response)

        if password is not None:
            response = self.put(path + '/password', password)
            if response.status != 200:
                raise ResponseStatusError(response)
        return path

    def changePassword(self, username, new_password):
        """Change the password for a persons."""
        response = self.put('/persons/%s/password' % username, new_password,
                            headers={'Content-Type': 'text/plain'})
        if response.status != 200:
            raise ResponseStatusError(response)

    def createGroup(self, title, description=""):
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"'
                ' description="%s"/>' % (to_xml(title), to_xml(description)))
        response = self.post('/groups', body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def createRelationship(self, obj1_path, obj2_path, reltype, obj2_role):
        """Create a relationship between two objects.

        reltype and obj2_role are simple string URIs, not URIObjects.

        Example:
          client.createRelationship('/persons/john', '/groups/teachers',
                                    URIMembership_uri, URIMember_uri)
        """
        body = ('<relationship xmlns="http://schooltool.org/ns/model/0.1"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xlink:type="simple"'
                ' xlink:href="%s" xlink:arcrole="%s" xlink:role="%s"/>'
                % tuple(map(to_xml, [obj2_path, reltype, obj2_role])))
        response = self.post('%s/relationships' % obj1_path, body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def _pathFromResponse(self, response):
        """Return the path portion of the Location header in the response."""
        location = response.getheader('Location')
        slashslash = location.index('//')
        slash = location.index('/', slashslash + 2)
        return location[slash:]

    def deleteObject(self, object_path):
        """Delete an object."""
        response = self.delete(object_path)
        if response.status != 200:
            raise ResponseStatusError(response)


class Response:
    """HTTP response.

    Wraps httplib.HTTPResponse and stores the response body as a string.
    The whole point of this class is that you can get the response body
    after the connection has been closed.
    """

    def __init__(self, response):
        self.status = response.status
        self.reason = response.reason
        self.body = response.read()
        self._response = response

    def getheader(self, header):
        return self._response.getheader(header)

    def read(self):
        return self.body

    __str__ = read


#
# Parsing utilities
#

def _parseContainer(body):
    """Parse the contents of a container.

    Returns a list of tuples (object_title, object_href).
    """
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError(_("Could not parse item list"))
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/container/items/item[@xlink:href]")
        items = []
        for node in res:
            href = to_unicode(node.nsProp('href', xlink))
            title = to_unicode(node.nsProp('title', xlink))
            if title is None:
                title = href.split('/')[-1]
            items.append((title, href))
        return items
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()


def _parseRelationships(body, uriobjects=None):
    """Parse the list of relationships.

    uriobjects is a mapping from URIs to URIObjects.  Note that new keys
    may be added to this mapping, to register unknown URIs.
    """
    if uriobjects is None:
        uriobjects = {}

    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError(_("Could not parse relationship list"))
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        xmlns = "http://schooltool.org/ns/model/0.1"
        ctx.xpathRegisterNs("m", xmlns)
        res = ctx.xpathEval("/m:relationships/m:existing/m:relationship")
        relationships = []
        for node in res:
            href = to_unicode(node.nsProp('href', xlink))
            role_uri = to_unicode(node.nsProp('role', xlink))
            arcrole_uri = to_unicode(node.nsProp('arcrole', xlink))
            if (not href
                or not looks_like_a_uri(role_uri)
                or not looks_like_a_uri(arcrole_uri)):
                continue
            title = to_unicode(node.nsProp('title', xlink))
            if title is None:
                title = href.split('/')[-1]
            try:
                role = uriobjects[role_uri]
            except KeyError:
                role = uriobjects[role_uri] = URIObject(role_uri)
            try:
                arcrole = uriobjects[arcrole_uri]
            except KeyError:
                arcrole = uriobjects[arcrole_uri] = URIObject(arcrole_uri)
            ctx.setContextNode(node)
            manage_nodes = ctx.xpathEval("m:manage/@xlink:href")
            if len(manage_nodes) != 1:
                raise SchoolToolError(_("Could not parse relationship list"))
            link_href = to_unicode(manage_nodes[0].content)
            relationships.append(RelationshipInfo(arcrole, role, title,
                                                  href, link_href))
        return relationships
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()


def _parsePersonInfo(body):
    """Parse the data provided by the person XML representation."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError(_("Could not parse person info"))
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        xmlns = "http://schooltool.org/ns/model/0.1"
        ctx.xpathRegisterNs("m", xmlns)
        try:
            node = ctx.xpathEval("/m:person/m:title")[0]
            title = to_unicode(node.content)
        except IndexError:
            raise SchoolToolError(_("Insufficient data in person info"))

        return PersonInfo(title)
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()


#
# Application object representation
#


Unchanged = "Unchanged"


class URIObject:
    """An object that represents an URI."""

    def __init__(self, uri, name=None, description=''):
        assert looks_like_a_uri(uri)
        self.uri = uri
        if name is None:
            name = uri
        self.name = name
        self.description = description


URIMembership_uri = 'http://schooltool.org/ns/membership'
URIMember_uri = 'http://schooltool.org/ns/membership/member'
URIGroup_uri = 'http://schooltool.org/ns/membership/group'

URIInstruction_uri = 'http://schooltool.org/ns/instruction'
URISection_uri = 'http://schooltool.org/ns/instruction/section'
URIInstructor_uri = 'http://schooltool.org/ns/instruction/instructor'

URICourseSections_uri = 'http://schooltool.org/ns/coursesections'
URICourse_uri = 'http://schooltool.org/ns/coursesections/course'
URISectionOfCourse_uri = 'http://schooltool.org/ns/coursesections/section'


class PersonInfo:
    """An object containing the data for a person"""

    def __init__(self, title=None):
        self.title = title


class GroupInfo:
    """Information about a group."""

    # List of group members
    members = None

    def __init__(self, members):
        self.members = members


class MemberInfo:
    """Information about a group member."""

    person_path = None

    def __init__(self, path):
        self.person_path = path

    def __cmp__(self, other):
        if not isinstance(other, MemberInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp(self.person_path, other.person_path)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.person_path)


class RelationshipInfo:
    """Information about a relationship."""

    arcrole = None              # Role of the target (URIObject)
    role = None                 # Role of the relationship (URIObject)
    target_title = None         # Title of the target
    target_path = None          # Path of the target
    link_path = None            # Path of the link

    def __init__(self, arcrole, role, title, path, link_path):
        self.arcrole = arcrole
        self.role = role
        self.target_title = title
        self.target_path = path
        self.link_path = link_path

    def __cmp__(self, other):
        if not isinstance(other, RelationshipInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.arcrole, self.role, self.target_title,
                    self.target_path, self.link_path),
                   (other.arcrole, other.role, other.target_title,
                    other.target_path, other.link_path))

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r)" % (self.__class__.__name__,
                   self.arcrole, self.role, self.target_title,
                   self.target_path, self.link_path)


#
# Exceptions
#

class SchoolToolError(UnicodeAwareException):
    """Communication error"""


class ResponseStatusError(SchoolToolError):
    """The server returned an unexpected HTTP status code."""

    def __init__(self, response):
        errmsg = "%d %s" % (response.status, response.reason)
        if response.getheader('Content-Type') == 'text/plain':
            errmsg += '\n%s' % response.read()
        SchoolToolError.__init__(self, errmsg)
        self.status = response.status
        self.reason = response.reason

