#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum specific security code.

$Id$

"""
from zope.traversing.api import getParent

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.common import SchoolToolMessage as _
from schooltool.group.interfaces import IGroupContainer
from schooltool.person.interfaces import IPerson
from schooltool.securitypolicy.crowds import Crowd, ConfigurableCrowd


class PersonAdvisorsCrowd(Crowd):
    """Crowd of advisors of a person."""

    title = _(u'Advisors')
    description = _(u'Advisors of a person.')

    def contains(self, principal):
        user = IPerson(principal, None)
        person = self.context
        if not IBasicPerson.providedBy(person):
            return False
        return user in person.advisors

