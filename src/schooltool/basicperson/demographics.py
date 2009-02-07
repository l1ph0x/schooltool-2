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
Demographics fields and storage
"""
from persistent.dict import PersistentDict
from persistent import Persistent

from zope.schema._field import Choice
from zope.schema._field import Date
from zope.schema import TextLine
from zope.location.location import locate
from zope.interface import Interface
from zope.interface import implements
from zope.interface import implementer
from zope.component import adapts
from zope.component import adapter
from zope.app.container.btree import BTreeContainer
from zope.app.container.ordered import OrderedContainer

from z3c.form import field

from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.app.app import InitBase
from schooltool.app.interfaces import IApplicationStartUpEvent
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.basicperson.interfaces import IDemographics


class IDemographicsForm(Interface):
    """Interface for fields that are supposed to get stored in person demographics."""


class PersonDemographicsDataContainer(BTreeContainer):
    """Storage for demographics information for all persons."""


class InvalidKeyError(Exception):
    """Key is not in demographics fields."""


class PersonDemographicsData(PersistentDict):
    """Storage for demographics information for a person."""

    def isValidKey(self, key):
        app = ISchoolToolApplication(None)
        demographics_fields = IDemographicsFields(app)
        return key in demographics_fields

    def __setitem__(self, key, v):
        if not self.isValidKey(key):
            raise InvalidKeyError(key)
        super(PersonDemographicsData, self).__setitem__(key, v)

    def __getitem__(self, key):
        if key not in self and self.isValidKey(key):
            self[key] = None
        return super(PersonDemographicsData, self).__getitem__(key)


@adapter(IBasicPerson)
@implementer(IDemographics)
def getPersonDemographics(person):
    app = ISchoolToolApplication(None)
    pdc = app['schooltool.basicperson.demographics_data']
    demographics = pdc.get(person.username, None)
    if demographics is None:
        pdc[person.username] = demographics = PersonDemographicsData()
    return demographics


class DemographicsFormAdapter(object):
    implements(IDemographicsForm)
    adapts(IBasicPerson)

    def __init__(self, context):
        self.__dict__['context'] = context
        self.__dict__['demographics'] = IDemographics(self.context)

    def __setattr__(self, name, value):
        self.demographics[name] = value

    def __getattr__(self, name):
        return self.demographics.get(name, None)


class DemographicsFields(OrderedContainer):
    implements(IDemographicsFields)


def setUpDefaultDemographics(app):
    dfs = DemographicsFields()
    app['schooltool.basicperson.demographics_fields'] = dfs
    locate(dfs, app, 'schooltool.basicperson.demographics_fields')
    dfs['ID'] = TextFieldDescription('ID', 'ID')
    dfs['ethnicity'] = EnumFieldDescription('ethnicity', 'Ethnicity')
    dfs['ethnicity'].items = [u'American Indian or Alaska Native',
                              u'Asian',
                              u'Black or African American',
                              u'Native Hawaiian or Other Pasific Islander',
                              u'White']
    dfs['language'] = TextFieldDescription('language', 'Language')
    dfs['placeofbirth'] = TextFieldDescription('placeofbirth', 'Place of birth')
    dfs['citizenship'] = TextFieldDescription('citizenship', 'Citizenship')


class DemographicsAppStartup(ObjectEventAdapterSubscriber):
    adapts(IApplicationStartUpEvent, ISchoolToolApplication)

    def __call__(self):
        if 'schooltool.basicperson.demographics_fields' not in self.object:
            setUpDefaultDemographics(self.object)
        if 'schooltool.basicperson.demographics_data' not in self.object:
            self.object['schooltool.basicperson.demographics_data'] = PersonDemographicsDataContainer()


class DemographicsInit(InitBase):
    def __call__(self):
        setUpDefaultDemographics(self.app)
        self.app['schooltool.basicperson.demographics_data'] = PersonDemographicsDataContainer()


@implementer(IDemographicsFields)
@adapter(ISchoolToolApplication)
def getDemographicsFields(app):
    return app['schooltool.basicperson.demographics_fields']


class FieldDescription(Persistent):

    def __init__(self, name, title):
        self.name, self.title = name, title
        self.required = False


class EnumFieldDescription(FieldDescription):

    items = []

    def makeField(self):
        form_field = Choice(
            title=unicode(self.title),
            values=self.items
            )
        form_field.required = self.required
        form_field.__name__ = self.name
        form_field.interface = IDemographicsForm
        return field.Fields(form_field)


class DateFieldDescription(FieldDescription):

    def makeField(self):
        form_field = Date(title=unicode(self.title))
        form_field.required = self.required
        form_field.__name__ = self.name
        form_field.interface = IDemographicsForm
        return field.Fields(form_field)


class TextFieldDescription(FieldDescription):

    def makeField(self):
        form_field = TextLine(title=unicode(self.title))
        form_field.required = self.required
        form_field.__name__ = self.name
        form_field.interface = IDemographicsForm
        return field.Fields(form_field)
