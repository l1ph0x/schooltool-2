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
Web-application views for the schooltool.model objects.

$Id$
"""

import datetime
import PIL.Image
from StringIO import StringIO

from schooltool.browser import View, Template
from schooltool.browser import absoluteURL
from schooltool.browser import notFoundPage
from schooltool.browser.auth import AuthenticatedAccess, ManagerAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.browser.auth import isManager
from schooltool.browser.timetable import TimetableTraverseView
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects, getPath, traverse
from schooltool.interfaces import IPerson, IGroup, IResource
from schooltool.membership import Membership
from schooltool.rest.infofacets import maxspect
from schooltool.translation import ugettext as _
from schooltool.uris import URIMember, URIGroup, URITeacher
from schooltool.teaching import Teaching

__metaclass__ = type


class GetParentsMixin:
    """A helper for Person and Group views."""

    def getParentGroups(self):
        """Return groups that context is a member of."""
        return getRelatedObjects(self.context, URIGroup)


class PersonInfoMixin:
    """A helper for Person views."""

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def photoURL(self):
        if self.info().photo is None:
            return u''
        else:
            return absoluteURL(self.request, self.context) + '/photo.jpg'


class TimetabledViewMixin:
    """A helper for views for ITimetabled objects."""

    def timetables(self):
        """Return a sorted list of all composite timetables on self.context.

        The list contains dicts with 'title' and 'url' in them.
        """
        path = absoluteURL(self.request, self.context)
        keys = list(self.context.listCompositeTimetables())
        keys.sort()
        return [{'title': '%s, %s' % (period, schema),
                 'url': '%s/timetables/%s/%s' % (path, period, schema)}
                for period, schema in keys]


class PersonView(View, GetParentsMixin, PersonInfoMixin, TimetabledViewMixin):
    """Person information view (/persons/id)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        elif name == 'edit.html':
            return PersonEditView(self.context)
        elif name == 'password.html':
            return PersonPasswordView(self.context)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        raise KeyError(name)

    def canEdit(self):
        return isManager(self.request.authenticated_user)

    def editURL(self):
        return absoluteURL(self.request, self.context) + '/edit.html'

    def canChangePassword(self):
        user = self.request.authenticated_user
        return isManager(user) or user is self.context

    def passwordURL(self):
        return absoluteURL(self.request, self.context) + '/password.html'


class PersonPasswordView(View):
    """Page for changing a person's password (/persons/id/password.html)."""

    __used_for__ = IPerson

    authorization = PrivateAccess

    template = Template('www/password.pt')

    error = None

    message = None

    back = True

    def do_POST(self, request):
        old_password = request.args['old_password'][0]
        user = request.authenticated_user
        if not user.checkPassword(old_password):
            self.error = _("Incorrect password for %s." % user.title)
        else:
            if 'DISABLE' in request.args:
                self.message = _('Account disabled.')
                self.context.setPassword(None)
                request.appLog(_("Account disabled for %s (%s)") %
                               (self.context.title, getPath(self.context)))
            elif 'CHANGE' in request.args:
                new_password = request.args['new_password'][0]
                verify_password = request.args['verify_password'][0]
                if new_password != verify_password:
                    self.error = _('Passwords do not match.')
                else:
                    self.message = _('Password changed.')
                    self.context.setPassword(new_password)
                    request.appLog(_("Password changed for %s (%s)") %
                                   (self.context.title, getPath(self.context)))
        return self.do_GET(request)


class PersonEditView(View, PersonInfoMixin):
    """Page for changing information about a person (/persons/id/edit.html)."""

    __used_for__ = IPerson

    authorization = ManagerAccess

    template = Template('www/person_edit.pt')

    error = None

    canonical_photo_size = (240, 240)

    back = True

    def do_POST(self, request):
        first_name = unicode(request.args['first_name'][0], 'utf-8')
        last_name = unicode(request.args['last_name'][0], 'utf-8')
        dob_string = request.args['date_of_birth'][0]
        comment = unicode(request.args['comment'][0], 'utf-8')
        photo = request.args['photo'][0]

        if not dob_string:
            dob = None
        else:
            try:
                # XXX The format of the date is too strict
                date_elements = [int(el) for el in dob_string.split('-')]
                dob = datetime.date(*date_elements)
            except (TypeError, ValueError):
                self.error = _('Invalid date')
                return self.do_GET(request)

        if photo:
            try:
                photo = self.processPhoto(photo)
            except IOError:
                self.error = _('Invalid photo')
                return self.do_GET(request)
            else:
                request.appLog(_("Photo added on %s (%s)") %
                               (self.context.title, getPath(self.context)))

        infofacet = self.info()
        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.date_of_birth = dob
        infofacet.comment = comment
        if photo:
            infofacet.photo = photo

        request.appLog(_("Person info updated on %s (%s)") %
                       (self.context.title, getPath(self.context)))

        url = absoluteURL(request, self.context)
        return self.redirect(url, request)

    def processPhoto(self, photo):
        # XXX The code has been copy&pasted from
        #     schooltool.rest.infofacets.PhotoView.do_PUT().
        #     It does not have tests.
        photo_file = StringIO(photo)
        img = PIL.Image.open(photo_file)
        size = maxspect(img.size, self.canonical_photo_size)
        img2 = img.resize(size, PIL.Image.ANTIALIAS)
        buf = StringIO()
        img2.save(buf, 'JPEG')
        return buf.getvalue()


class GroupView(View, GetParentsMixin, TimetabledViewMixin):
    """Group information view (/group/id)."""

    __used_for__ = IGroup

    authorization = AuthenticatedAccess

    template = Template("www/group.pt")

    def _traverse(self, name, request):
        if name == "edit.html":
            return GroupEditView(self.context)
        elif name == "teachers.html":
            return GroupTeachersView(self.context)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        raise KeyError(name)

    def getOtherMembers(self):
        """Return members that are not groups."""
        return [g for g in getRelatedObjects(self.context, URIMember)
                if not IGroup.providedBy(g)]

    def getSubGroups(self):
        """Return members that are groups."""
        return [g for g in getRelatedObjects(self.context, URIMember)
                if IGroup.providedBy(g)]

    def teachersList(self):
        """Lists teachers of this group"""
        result = [(obj.title, obj)
                  for obj in getRelatedObjects(self.context, URITeacher)]
        result.sort()
        return [obj for title, obj in result]

    def canEdit(self):
        return isManager(self.request.authenticated_user)


class RelationshipViewMixin:
    """A mixin for views that manage relationships on groups.

    Subclasses must define:

      linkrole = Attribute('URI of the role of the related object.')

      relname = Attribute('Relationship name')

      def createRelationship(self, other):
          'Create the relationship between self.context and other'
    """

    def list(self):
        """Return a list of related objects"""
        result = [(obj.title, obj)
                  for obj in getRelatedObjects(self.context,
                                               self.linkrole)]
        result.sort()
        return [obj for title, obj in result]

    def update(self):
        request = self.request
        if "DELETE" in request.args:
            paths = []
            if "CHECK" in request.args:
                paths += request.args["CHECK"]
            for link in self.context.listLinks(self.linkrole):
                if getPath(link.traverse()) in paths:
                    link.unlink()
                    request.appLog(_("Relationship '%s' between %s and %s"
                                     " removed")
                                   % (self.relname, getPath(link.traverse()),
                                      getPath(self.context)))
        if "FINISH_ADD" in request.args:
            paths = []
            if "toadd" in request.args:
                paths += request.args["toadd"]
            for path in paths:
                obj = traverse(self.context, path)
                self.createRelationship(obj)
                request.appLog(_("Relationship '%s' between %s and %s created")
                               % (self.relname, getPath(obj),
                                  getPath(self.context)))


class GroupEditView(View, RelationshipViewMixin):
    """Page for "editing" a Group (/group/id/edit.html)."""

    __used_for__ = IGroup

    authorization = ManagerAccess

    template = Template('www/group_edit.pt')

    linkrole = URIMember

    relname = _('Membership')

    back = True

    def addList(self):
        """Return a list of objects available for addition"""
        result = []

        searchstr = self.request.args['SEARCH'][0].lower()
        members = getRelatedObjects(self.context, URIMember)

        for path in ('/groups', '/persons', '/resources'):
            for obj in traverse(self.context, path).itervalues():
                if (searchstr in obj.title.lower() and
                    obj not in members):
                    result.append((obj.__class__.__name__, obj.title, obj))
        result.sort()
        return [obj for cls, title, obj in result]

    def createRelationship(self, other):
        Membership(group=self.context, member=other)


class GroupTeachersView(View, RelationshipViewMixin):

    __used_for__ = IGroup

    authorization = ManagerAccess

    template = Template('www/group_teachers.pt')

    linkrole = URITeacher

    relname = _('Teaching')

    back = True

    def addList(self):
        """List all members of the Teachers group except current teachers."""
        result = []
        request = self.request
        current_teachers = getRelatedObjects(self.context, URITeacher)
        teachers = traverse(self.context, '/groups/teachers')
        for obj in getRelatedObjects(teachers, URIMember):
            if obj not in current_teachers:
                result.append((obj.title, obj))
        result.sort()
        return [obj for title, obj in result]

    def createRelationship(self, other):
        Teaching(taught=self.context, teacher=other)


class ResourceView(View):
    """View for displaying a resource."""

    __used_for__ = IResource

    authorization = AuthenticatedAccess

    template = Template("www/resource.pt")

    def canEdit(self):
        return isManager(self.request.authenticated_user)

    def editURL(self):
        return absoluteURL(self.request, self.context) + '/edit.html'

    def _traverse(self, name, request):
        if name == "edit.html":
            return ResourceEditView(self.context)
        else:
            raise KeyError(name)


class ResourceEditView(View):
    """View for displaying a resource."""

    __used_for__ = IResource

    authorization = ManagerAccess

    template = Template("www/resource_edit.pt")

    back = True

    def do_POST(self, request):
        title = unicode(request.args['title'][0], 'utf-8')
        self.context.title = title

        request.appLog(_("Resource %s modified") % getPath(self.context))
        url = absoluteURL(request, self.context)
        return self.redirect(url, request)


class PhotoView(View):
    """View for displaying a person's photo (/persons/id/photo.jpg)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    def do_GET(self, request):
        facet = FacetManager(self.context).facetByName('person_info')
        if facet.photo is None:
            return notFoundPage(request)
        else:
            request.setHeader('Content-Type', 'image/jpeg')
            return facet.photo

