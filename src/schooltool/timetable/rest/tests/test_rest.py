#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Unit tests for schooltool.timetable.rest.

$Id$
"""

import unittest
import datetime
from StringIO import StringIO

from zope.component import provideAdapter
from zope.component import adapts
from zope.app.testing import placelesssetup
from zope.app.testing import ztapi, setup
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.component.testing import PlacefulSetup
from zope.testing.doctest import DocTestSuite, ELLIPSIS, NORMALIZE_WHITESPACE
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.http import IHTTPRequest
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.term.interfaces import ITermContainer
from schooltool.testing.util import XMLCompareMixin
from schooltool.testing import setup as sbsetup
from schooltool.timetable import TimetablesAdapter
from schooltool.timetable.interfaces import ITimetables


def setUp(test=None):
    placelesssetup.setUp(test)
    setup.setUpAnnotations()
    ztapi.provideAdapter(IAttributeAnnotatable, ITimetables,
                         TimetablesAdapter)


class TimetableTestMixin(PlacefulSetup, XMLCompareMixin):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <timezone name="UTC"/>
          <term id="2003 fall"/>
          <schooltt id="schema1"/>
          <day id="Day 1">
            <period id="A" homeroom="">
            </period>
            <period id="B" homeroom="">
            </period>
          </day>
          <day id="Day 2">
            <period id="C" homeroom="">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    full_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <timezone name="Europe/Vilnius"/>
          <term id="2003 fall"/>
          <schooltt id="schema1"/>
          <day id="Day 1">
            <period id="A" homeroom="">
              <activity title="Maths" />
            </period>
            <period id="B" homeroom="">
              <activity title="English" />
              <activity title="French" />
            </period>
          </day>
          <day id="Day 2">
            <period id="C" homeroom="">
              <activity title="CompSci" />
            </period>
            <period id="D">
              <activity title="CompSci" />
            </period>
          </day>
        </timetable>
        """

    def setUp(self):
        PlacefulSetup.setUp(self)
        self.app = sbsetup.setUpSchoolToolSite()
        from schooltool.term.term import getTermContainer
        from zope.interface import Interface
        provideAdapter(getTermContainer, [Interface], ITermContainer)
        from schooltool.schoolyear.schoolyear import getSchoolYearContainer
        provideAdapter(getSchoolYearContainer)

        from schooltool.course.section import Section
        from schooltool.resource.resource import Resource
        self.app["sections"]["history"] = self.section = Section("History")
        self.app["resources"]['room1'] = Resource("Room1")
        self.app["resources"]['lab1'] = Resource("Lab1")
        self.app["resources"]['lab2'] = Resource("Lab2")
        self.app["resources"][u'\u017eabas'] = Resource("Zabas")

        from schooltool.schoolyear.schoolyear import SchoolYear
        from schooltool.schoolyear.interfaces import ISchoolYearContainer
        schoolyears = ISchoolYearContainer(self.app)
        schoolyears['2003'] = SchoolYear("2003",
                                         datetime.date(2003, 1, 1),
                                         datetime.date(2003, 12, 31))

        terms = ITermContainer(self.app)
        self.schema = self.app["ttschemas"]["schema1"] = self.createSchema()
        self.term = terms["2003 fall"] = self.createTerm(9)
        self.term2 = terms["2004 fall"] = self.createTerm(10)

        provideAdapter(lambda x: self.app, [None], ISchoolToolApplication)

        from schooltool.app.rest.interfaces import ITimetableFileFactory
        from schooltool.timetable.rest import TimetableFileFactory
        from schooltool.timetable import TimetablesAdapter
        from schooltool.timetable.interfaces import ITimetableDict
        provideAdapter(TimetableFileFactory,
                       [ITimetableDict, IHTTPRequest],
                       ITimetableFileFactory)
        provideAdapter(TimetablesAdapter, [IAttributeAnnotatable],
                       ITimetables)

    def createTerm(self, month=9):
        from schooltool.term.term import Term
        return Term("2003 fall",
                    datetime.date(2003, month, 1),
                    datetime.date(2003, month, 30))

    def createSchema(self):
        from schooltool.timetable.schema import TimetableSchemaDay
        from schooltool.timetable.schema import TimetableSchema
        tt = TimetableSchema(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableSchemaDay(['A', 'B'], ['A', 'B'])
        tt['Day 2'] = TimetableSchemaDay(['C', 'D'], ['C'])
        return tt

    def createEmpty(self, term=None):
        return self.schema.createTimetable(term)

    def createFull(self, owner=None, term=None):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty(term)
        room1 = self.app["resources"]['room1']
        lab1 = self.app["resources"]['lab1']
        lab2 = self.app["resources"]['lab2']
        zab = self.app["resources"][u'\u017eabas']
        tt['Day 1'].add('A', TimetableActivity('Maths', owner, [room1]))
        tt['Day 1'].add('B', TimetableActivity('English', owner))
        tt['Day 1'].add('B', TimetableActivity('French', owner))
        tt['Day 2'].add('C', TimetableActivity('CompSci', owner, [lab1, lab2]))
        tt['Day 2'].add('D', TimetableActivity('CompSci', owner, [zab]))
        tt.timezone = "Europe/Vilnius"
        return tt


class TestTimetableReadView(TimetableTestMixin, unittest.TestCase):

    def createView(self, context, request):
        from schooltool.timetable.rest import TimetableReadView
        return TimetableReadView(context, request)

    def do_test_get(self, context, expected, ctype="text/xml"):
        request = TestRequest()
        view = self.createView(context, request)
        result = view.GET()
        self.assertEquals(request.response.getHeader('content-type'),
                          "%s; charset=UTF-8" % ctype)
        self.assertEqualsXML(result, expected, recursively_sort=['timetable'])

    def test_get(self):
        self.do_test_get(self.createEmpty(self.term), self.empty_xml)
        self.do_test_get(self.createFull(term=self.term), self.full_xml)


class TestTimetableFileFactory(TimetableTestMixin, unittest.TestCase):

    namespaces = {'tt': 'http://schooltool.org/ns/timetable/0.1',
                  'xlink': 'http://www.w3.org/1999/xlink'}

    def test(self):
        from schooltool.app.rest.interfaces import ITimetableFileFactory
        from schooltool.timetable.rest import TimetableFileFactory
        verifyObject(ITimetableFileFactory,
                     TimetableFileFactory(ITimetables(self.section).timetables,
                                          TestRequest()))

    def test_call(self):
        from schooltool.timetable.rest import TimetableFileFactory

        factory = TimetableFileFactory(ITimetables(self.section).timetables,
                                       TestRequest())
        timetable = factory("2003 fall.schema1", "text/xml", self.full_xml)
        self.assertEquals(timetable, self.createFull(self.section))

        timetable = factory("2003 fall.schema1", "text/xml", self.empty_xml)
        self.assertEquals(timetable, self.createEmpty())


class TestTimetablePUT(TimetableTestMixin, unittest.TestCase):

    def setUp(self):
        TimetableTestMixin.setUp(self)
        self.timetable = self.createEmpty()
        timetables = ITimetables(self.section).timetables
        timetables["2003 fall.schema1"] = self.timetable

    def test_put(self):
        from schooltool.timetable.rest import TimetablePUT
        request = TestRequest(StringIO(self.full_xml))
        view = TimetablePUT(self.timetable, request)
        view.PUT()
        self.assertEquals(
            ITimetables(self.section).timetables["2003 fall.schema1"],
            self.createFull(self.section))


def doctest_TimetableDictPublishTraverse():
    """Unit tests for TimetableDictPublishTraverse

    Some setup is needed:

        >>> setup.placefulSetUp()
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> from schooltool.term.term import getTermContainer
        >>> from zope.interface import Interface
        >>> provideAdapter(getTermContainer, [Interface], ITermContainer)
        >>> from schooltool.schoolyear.schoolyear import getSchoolYearContainer
        >>> provideAdapter(getSchoolYearContainer)

        >>> from datetime import date

        >>> from schooltool.schoolyear.schoolyear import SchoolYear
        >>> from schooltool.schoolyear.interfaces import ISchoolYearContainer
        >>> schoolyears = ISchoolYearContainer(app)
        >>> schoolyears['2005-2006'] = SchoolYear("2005-2006",
        ...                                       date(2005, 9, 1),
        ...                                       date(2006, 6, 30))

        >>> from schooltool.term.term import Term
        >>> from schooltool.timetable.schema import TimetableSchema
        >>> ITermContainer(app)['2005-fall'] = Term('2005 Fall',
        ...         date(2005, 9, 1), date(2005, 12, 31))
        >>> ITermContainer(app)['2006-spring'] = Term('2006 Spring',
        ...         date(2006, 2, 1), date(2006, 6, 30))
        >>> app['ttschemas']['default'] = TimetableSchema([])

    TimetableDictPublishTraverse adapts (ITimetableDict, IHTTPRequest)
    pair

        >>> from schooltool.timetable import TimetableDict
        >>> from schooltool.timetable.rest import TimetableDictPublishTraverse
        >>> context = TimetableDict()
        >>> request = TestRequest()
        >>> pt = TimetableDictPublishTraverse(context, request)

    There are three cases.

    1. Existing timetable

        >>> from schooltool.timetable import Timetable
        >>> context['2005-fall.default'] = tt = Timetable([])
        >>> obj = pt.publishTraverse(request, '2005-fall.default')
        >>> obj
        <Timetable: ...>
        >>> obj is tt
        True

    2. Nonexisting timetable

        >>> obj = pt.publishTraverse(request, '2006-spring.default')
        >>> obj
        <...NullTimetable object at ...>
        >>> obj.container is context
        True
        >>> obj.name
        '2006-spring.default'

    Cleanup:

        >>> setup.placefulTearDown()

    """


def doctest_NullTimetablePUT():
    """Unit tests for NullTimetablePUT

    Setup: there should be an adapter from ITimetableDict to
    ITimetableFileFactory.

        >>> setup.placelessSetUp()
        >>> from schooltool.timetable.interfaces import ITimetableDict
        >>> from schooltool.app.rest.interfaces import ITimetableFileFactory
        >>> from schooltool.timetable import Timetable
        >>> class TimetableFileFactoryStub(object):
        ...     adapts(ITimetableDict)
        ...     implements(ITimetableFileFactory)
        ...     def __init__(self, context, request):
        ...         self.context = context
        ...         self.request = request
        ...     def __call__(self, name, ctype, data):
        ...         print "*** Creating a timetable called %s" % name
        ...         print "    from a %s entity containing %s" % (ctype, data)
        ...         return Timetable([])
        >>> ztapi.provideAdapter((ITimetableDict, IHTTPRequest),
        ...                      ITimetableFileFactory,
        ...                      TimetableFileFactoryStub)

    Also we want to see what events are sent out

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> def handler(event):
        ...     print "*** Event: %r" % event
        >>> zope.event.subscribers.append(handler)

    NullTimetablePUT is a view on NullTimetable, which in turn knows
    where the new timetable is to be placed, and how it should be
    named.

        >>> from schooltool.timetable.rest import NullTimetablePUT
        >>> from schooltool.timetable.rest import NullTimetable
        >>> from schooltool.timetable import TimetableDict
        >>> container = TimetableDict()
        >>> name = '2005-fall.default'
        >>> context = NullTimetable(container, name)
        >>> request = TestRequest(StringIO('<timetable data>'),
        ...                       environ={'CONTENT_TYPE': 'text/xml'})
        >>> view = NullTimetablePUT(context, request)

        >>> view.PUT()
        *** Creating a timetable called 2005-fall.default
            from a text/xml entity containing <timetable data>
        *** Event: <...ObjectCreatedEvent...>
        ''
        >>> request.response.getStatus()
        201

        >>> container[name]
        <Timetable: ...>

    As per the HTTP spec, NullTimetablePUT barfs if the request contains
    unrecognized Content-* headers.

        >>> request = TestRequest(StringIO('<timetable data>'),
        ...                       environ={'CONTENT_TYPE': 'text/xml',
        ...                                'HTTP_CONTENT_RANGE': 'blah'})
        >>> view = NullTimetablePUT(context, request)
        >>> view.PUT()
        ''
        >>> request.response.getStatus()
        501

    Cleanup:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> setup.placelessTearDown()

    """


class TestTimetableDictView(TimetableTestMixin, unittest.TestCase):

    def createView(self, context, request):
        from schooltool.timetable.rest import TimetableDictView
        return TimetableDictView(context, request)

    def setUp(self):
        TimetableTestMixin.setUp(self)
        self.tt = ITimetables(self.section).timetables["2003 fall.schema1"] \
                = self.createEmpty(ITermContainer(self.app)['2003 fall'])

    def test_getTimetables(self):
        view = self.createView(ITimetables(self.section).timetables,
                               TestRequest())
        timetables = view.getTimetables()
        self.assertEquals(len(timetables), 1)
        self.assert_(timetables[0] is self.tt)

    def test_timetables(self):
        view = self.createView(ITimetables(self.section).timetables,
                               TestRequest())
        self.assertEquals(view.timetables, [{
          'url': "http://127.0.0.1/sections/history/timetables/2003%20fall.schema1",
          'term': u'2003 fall',
          'schema': u'schema1'}])

    def test_get(self):
        view = self.createView(ITimetables(self.section).timetables,
                               TestRequest())
        self.assertEqualsXML(
            view.GET(),
            """<timetables xmlns:xlink="http://www.w3.org/1999/xlink">
                 <timetable xlink:type="simple" term="2003 fall"
                            xlink:href="http://127.0.0.1/sections/history/timetables/2003%20fall.schema1"
                            schema="schema1"/>
               </timetables>""")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableReadView))
    suite.addTest(unittest.makeSuite(TestTimetableFileFactory))
    suite.addTest(unittest.makeSuite(TestTimetablePUT))
    suite.addTest(unittest.makeSuite(TestTimetableDictView))
    suite.addTest(DocTestSuite(optionflags=ELLIPSIS))
    suite.addTest(DocTestSuite('schooltool.timetable.rest',
                               setUp=setUp, tearDown=placelesssetup.tearDown,
                               optionflags=ELLIPSIS|NORMALIZE_WHITESPACE))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
