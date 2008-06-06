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
Unit tests for the schooltool.timetable.model module.

$Id$
"""

import calendar
import unittest
import itertools
from datetime import date, time, timedelta, datetime
from pprint import pformat

from pytz import UTC
from zope.interface.verify import verifyObject
from zope.traversing.interfaces import IPhysicallyLocatable
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.app.testing import ztapi, setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.testing.util import NiceDiffsMixin
from schooltool.testing.util import diff
from schooltool.term.tests.test_term import TermStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences


class TimetablePhysicallyLocatableAdapterStub:
    def __init__(self, tt):
        self.tt = tt
    def getPath(self):
        return '/tt/%s' % id(self.tt)


class BaseTestTimetableModel:

    def extractCalendarEvents(self, cal, daterange):
        result = []
        for d in daterange:
            dt = datetime.combine(d, time(0, 0, tzinfo=UTC))
            dt1 = dt + d.resolution
            calday = cal.expand(dt, dt1)
            events = []
            for event in calday:
                events.append(event)
            result.append(dict([(event.dtstart, event.title)
                           for event in events]))
        return result


def createSimpleTimetable():
    """Create a simple timetable.

          Period | Day A    Day B
          ------ : -------  ---------
          Green  : English  Biology
          Blue   : Math     Geography

    """
    from schooltool.timetable import Timetable, TimetableDay
    from schooltool.timetable import TimetableActivity
    tt = Timetable(('A', 'B'))
    periods = ('Green', 'Blue')
    tt["A"] = TimetableDay(periods)
    tt["B"] = TimetableDay(periods)
    tt["A"].add("Green", TimetableActivity("English"))
    tt["A"].add("Blue", TimetableActivity("Math"))
    tt["B"].add("Green", TimetableActivity("Biology"))
    tt["B"].add("Blue", TimetableActivity("Geography"))
    return tt


class SequentialTestSetupMixin:
    createTimetable = staticmethod(createSimpleTimetable)


class ApplicationStub(object):
    implements(ISchoolToolApplication, IApplicationPreferences)
    def __init__(self, timezone='UTC'):
        self.timezone=timezone
    def __call__(self, context):
        return self


def doctest_BaseTimetableModel_createCalendar():
    """Tests for BaseTimetableModel.createCalendar

    We'll have to provide application configuration stub:

        >>> ztapi.provideAdapter(None, ISchoolToolApplication, ApplicationStub())

        >>> from schooltool.timetable.model import BaseTimetableModel
        >>> btm = BaseTimetableModel()

    We have a stub term that lasts from 2003-11-20 to 2003-11-26, and a simple
    timetable.

        >>> term = TermStub()
        >>> timetable = createSimpleTimetable()
        >>> from schooltool.timetable.interfaces import ITimetable
        >>> ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
        ...                      TimetablePhysicallyLocatableAdapterStub)

    BaseTimetableModel is a base class and needs concrete implementations for
    its abstract methods.

        >>> btm._dayGenerator = lambda: itertools.cycle(['A', 'B'])
        >>> btm.schooldayStrategy = lambda date, generator: generator.next()
        >>> from schooltool.timetable import SchooldayTemplate, SchooldaySlot
        >>> day_template = SchooldayTemplate()
        >>> t, td = time, timedelta
        >>> day_template.add(SchooldaySlot(t(9, 0), td(minutes=90)))
        >>> day_template.add(SchooldaySlot(t(11, 05), td(minutes=80)))
        >>> btm._getUsualTemplateForDay = lambda date, day_id: day_template

    Let us create a calendar.

        >>> from schooltool.timetable.interfaces import ITimetableCalendarEvent
        >>> cal = btm.createCalendar(term, timetable,
        ...                          first=date(2003, 11, 21),
        ...                          last=date(2003, 11, 25))

        >>> def print_cal(cal):
        ...     for e in cal:
        ...         print '%s %s--%s %s %-10s %s' % (
        ...                     e.dtstart.date(), e.dtstart.strftime('%H:%M'),
        ...                     (e.dtstart + e.duration).strftime('%H:%M'),
        ...                     e.dtstart.tzinfo,
        ...                     '(%s, %s)' % (e.day_id, e.period_id), e.title)
        ...         assert verifyObject(ITimetableCalendarEvent, e)
        ...         assert e.title == e.activity.title
        >>> print_cal(cal)
        2003-11-21 09:00--10:30 UTC (B, Green) Biology
        2003-11-21 11:05--12:25 UTC (B, Blue)  Geography
        2003-11-24 09:00--10:30 UTC (A, Green) English
        2003-11-24 11:05--12:25 UTC (A, Blue)  Math
        2003-11-25 09:00--10:30 UTC (B, Green) Biology
        2003-11-25 11:05--12:25 UTC (B, Blue)  Geography

    If school will get transported to Lithuania, lessons should still
    start at the same local time (9:00 in the morning), but the time
    should be stored in UTC:

        >>> timetable.timezone = 'Europe/Vilnius'
        >>> cal = btm.createCalendar(term, timetable,
        ...                          first=date(2003, 11, 21),
        ...                          last=date(2003, 11, 25))
        >>> print_cal(cal)
        2003-11-21 07:00--08:30 UTC (B, Green) Biology
        2003-11-21 09:05--10:25 UTC (B, Blue)  Geography
        2003-11-24 07:00--08:30 UTC (A, Green) English
        2003-11-24 09:05--10:25 UTC (A, Blue)  Math
        2003-11-25 07:00--08:30 UTC (B, Green) Biology
        2003-11-25 09:05--10:25 UTC (B, Blue)  Geography

    """


class TestSequentialDaysTimetableModel(PlacelessSetup,
                                       NiceDiffsMixin,
                                       unittest.TestCase,
                                       BaseTestTimetableModel,
                                       SequentialTestSetupMixin):

    def setUp(self):
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)

        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)
        ztapi.provideAdapter(None, ISchoolToolApplication, ApplicationStub())

    def createModel(self):
        """Create a simple sequential timetable model.

        Days A and B are alternated.

        Green period occurs at 9:00-10:30 on all days.
        Blue period occurs at 11:00-12:30 on all days except Fridays, when it
        occurs at 10:30-12:00.
        """
        from schooltool.timetable import SchooldayTemplate, SchooldaySlot
        from schooltool.timetable.model import SequentialDaysTimetableModel

        t, td = time, timedelta
        template1 = SchooldayTemplate()
        template1.add(SchooldaySlot(t(9, 0), td(minutes=90)))
        template1.add(SchooldaySlot(t(11, 0), td(minutes=90)))
        template2 = SchooldayTemplate()
        template2.add(SchooldaySlot(t(9, 0), td(minutes=90)))
        template2.add(SchooldaySlot(t(10, 30), td(minutes=90)))

        model = SequentialDaysTimetableModel(("A", "B"),
                                             {None: template1,
                                              calendar.FRIDAY: template2})
        return model

    def test_interface(self):
        from schooltool.timetable.model import SequentialDaysTimetableModel
        from schooltool.timetable.interfaces import IWeekdayBasedTimetableModel

        model = SequentialDaysTimetableModel(("A","B"), {None: 3})
        verifyObject(IWeekdayBasedTimetableModel, model)

    def test_eq(self):
        from schooltool.timetable.model import SequentialDaysTimetableModel
        from schooltool.timetable.model import WeeklyTimetableModel
        model = SequentialDaysTimetableModel(("A","B"), {1: 2, None: 3})
        model2 = SequentialDaysTimetableModel(("A","B"), {1: 2, None: 3})
        model3 = WeeklyTimetableModel(("A","B"), {1: 2, None: 3})
        model4 = SequentialDaysTimetableModel(("A"), {1: 2, None: 3})

        self.assertEqual(model, model2)
        self.assertNotEqual(model2, model3)
        self.assertNotEqual(model2, model4)
        self.assert_(not model2 != model)

        model.exceptionDays[date(2005, 7, 7)] = object()
        self.assertNotEqual(model, model2)

        del model.exceptionDays[date(2005, 7, 7)]
        self.assertEqual(model, model2)
        model.exceptionDayIds[date(2005, 7, 7)] = 'Monday'
        self.assertNotEqual(model, model2)

    def test_createCalendar(self):
        from schooltool.calendar.interfaces import ICalendar

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = TermStub()

        cal = model.createCalendar(schooldays, tt)
        verifyObject(ICalendar, cal)

        # The calendar is functionally derived, therefore everything
        # in it (including unique calendar event IDs) must not change
        # if it is regenerated.
        cal2 = model.createCalendar(schooldays, tt)
        self.assertEquals(list(cal), list(cal2))

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 10, 30, tzinfo=UTC): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Math"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_createCalendar_exceptionDays(self):
        from schooltool.term.term import Term
        from schooltool.timetable import SchooldaySlot

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = Term('Sample', date(2003, 11, 20), date(2003, 11, 26))
        schooldays.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        # Add an exception day
        t, td = time, timedelta
        exception = [("Green", SchooldaySlot(t(6, 0), td(minutes=90))),
                     ("Blue", SchooldaySlot(t(8, 0), td(minutes=90)))]
        model.exceptionDays[date(2003, 11, 22)] = exception

        # Run the calendar generation
        cal = model.createCalendar(schooldays, tt)

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 10, 30, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 22, 6, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 22, 8, 0, tzinfo=UTC): "Math"},
                    {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Geography"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_schooldayStrategy_getDayId(self):
        from schooltool.timetable.model import SequentialDaysTimetableModel
        from schooltool.term.term import Term
        from schooltool.timetable import SchooldayTemplate

        term = Term('Sample', date(2005, 6, 27), date(2005, 7, 10))
        term.addWeekdays(0, 1, 2, 3, 4)

        template = SchooldayTemplate()
        model = SequentialDaysTimetableModel(('A', 'B', 'C'), {None: template})

        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term
                if term.isSchoolday(d)]

        self.assertEqual(days, ['A', 'B', 'C', 'A', 'B',
                                'C', 'A', 'B', 'C', 'A'])

        self.assertEqual(model.getDayId(term, date(2005, 6, 27)), 'A')
        self.assertEqual(model.getDayId(term, date(2005, 6, 29)), 'C')
        self.assertEqual(model.getDayId(term, date(2005, 7, 1)), 'B')

        term.add(date(2005, 7, 2))
        model.exceptionDayIds[date(2005, 7, 2)] = "X"
        model.exceptionDayIds[date(2005, 7, 4)] = "Y"
        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen)
                for d in term
                if term.isSchoolday(d)]

        # Effectively, exception day ids get inserted into the normal
        # sequence of day ids, instead of replacing some day ids.
        self.assertEqual(days, ['A', 'B', 'C', 'A', 'B', 'X',
                                'Y', 'C', 'A', 'B', 'C'])


    def test_periodsInDay_originalPeriodsInDay(self):
        from schooltool.timetable import SchooldaySlot

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = TermStub()

        # Add an exception day
        t, td = time, timedelta
        exception = [
            ("Green", SchooldaySlot(t(6, 0), td(minutes=90))),
            ("Blue", SchooldaySlot(t(8, 0), td(minutes=90)))]
        model.exceptionDays[date(2003, 11, 21)] = exception

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 20)),
            [('Green', time(9, 0), timedelta(minutes=90)),
             ('Blue',  time(11, 0), timedelta(minutes=90))])

        self.assertEqual(
            model.originalPeriodsInDay(schooldays, tt, date(2003, 11, 21)),
            [('Green', time(9, 0), timedelta(minutes=90)),
             ('Blue', time(10, 30), timedelta(minutes=90))])

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 21)),
            [('Green', time(6, 0), timedelta(minutes=90)),
             ('Blue', time(8, 0), timedelta(minutes=90))])

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 22)),
            [])


class TestSequentialDayIdBasedTimetableModel(PlacelessSetup,
                                             unittest.TestCase,
                                             SequentialTestSetupMixin,
                                             BaseTestTimetableModel):

    def setUp(self):
        from zope.traversing.interfaces import IPhysicallyLocatable
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)

        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)
        ztapi.provideAdapter(None, ISchoolToolApplication, ApplicationStub())

    def createDayTemplates(self):
        from schooltool.timetable import SchooldayTemplate, SchooldaySlot
        t, td = time, timedelta
        template1 = SchooldayTemplate()
        template1.add(SchooldaySlot(t(9, 0), td(minutes=90)))
        template1.add(SchooldaySlot(t(11, 0), td(minutes=90)))
        template2 = SchooldayTemplate()
        template2.add(SchooldaySlot(t(11, 0), td(minutes=90)))
        template2.add(SchooldaySlot(t(13, 0), td(minutes=90)))
        return template1, template2

    def test_createCalendar(self):
        from schooltool.calendar.interfaces import ICalendar
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()

        model = SequentialDayIdBasedTimetableModel(('A', 'B'),
                                                   {'A': template1,
                                                    'B': template2})
        schooldays = TermStub()

        cal = model.createCalendar(schooldays, tt)
        verifyObject(ICalendar, cal)

        # The calendar is functionally derived, therefore everything
        # in it (including unique calendar event IDs) must not change
        # if it is regenerated.
        cal2 = model.createCalendar(schooldays, tt)
        self.assertEquals(list(cal), list(cal2))

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 13, 0, tzinfo=UTC): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 25, 13, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Math"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_createCalendar_date_range(self):
        from schooltool.timetable.model \
                import SequentialDayIdBasedTimetableModel
        template1, template2 = self.createDayTemplates()
        model = SequentialDayIdBasedTimetableModel(('A', 'B'),
                                                   {'A': template1,
                                                    'B': template2})
        schooldays = TermStub()
        tt = self.createTimetable()
        cal = model.createCalendar(schooldays, tt, first=date(2003, 11, 21),
                                   last=date(2003, 11, 25))
        result = self.extractCalendarEvents(cal, schooldays)
        expected = [{},
                    {datetime(2003, 11, 21, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 13, 0, tzinfo=UTC): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 25, 13, 0, tzinfo=UTC): "Geography"},
                    {}]
        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_verification(self):
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()

        self.assertRaises(AssertionError,
                          SequentialDayIdBasedTimetableModel,
                          ('A', 'B'),
                          {'A': template1,'Z': template2})

        SequentialDayIdBasedTimetableModel(
            ('A', 'Z'),
            {'A': template1, 'Z': template2})

    def test__getUsualTemplateForDay(self):
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()
        model = SequentialDayIdBasedTimetableModel(
            ('A', 'Z'),
            {'A': template1, 'Z': template2})
        self.assertEqual(model._getUsualTemplateForDay(date(2005, 7, 20), 'A'),
                         template1)
        self.assertEqual(model._getUsualTemplateForDay(date(2005, 7, 21), 'Z'),
                         template2)
        self.assertRaises(KeyError, model._getUsualTemplateForDay,
                          date(2005, 7, 21), 'B')


class TestWeeklyTimetableModel(PlacelessSetup,
                               unittest.TestCase,
                               BaseTestTimetableModel):

    def setUp(self):
        from zope.traversing.interfaces import IPhysicallyLocatable
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)
        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)
        ztapi.provideAdapter(None, ISchoolToolApplication, ApplicationStub())

    def test(self):
        from schooltool.timetable.model import WeeklyTimetableModel
        from schooltool.timetable import SchooldayTemplate, SchooldaySlot
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.timetable import TimetableActivity
        from schooltool.term.term import Term
        from schooltool.timetable.interfaces import IWeekdayBasedTimetableModel

        days = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
        tt = Timetable(days)

        periods = ('1', '2', '3', '4')
        for day_id in days:
            tt[day_id] = TimetableDay(periods)

        tt["Monday"].add("1", TimetableActivity("English"))
        tt["Monday"].add("2", TimetableActivity("History"))
        tt["Monday"].add("3", TimetableActivity("Biology"))
        tt["Monday"].add("4", TimetableActivity("Physics"))

        tt["Tuesday"].add("1", TimetableActivity("Geography"))
        tt["Tuesday"].add("2", TimetableActivity("Math"))
        tt["Tuesday"].add("3", TimetableActivity("English"))
        tt["Tuesday"].add("4", TimetableActivity("Music"))

        tt["Wednesday"].add("1", TimetableActivity("English"))
        tt["Wednesday"].add("2", TimetableActivity("History"))
        tt["Wednesday"].add("3", TimetableActivity("Biology"))
        tt["Wednesday"].add("4", TimetableActivity("Physics"))

        tt["Thursday"].add("1", TimetableActivity("Chemistry"))
        tt["Thursday"].add("2", TimetableActivity("English"))
        tt["Thursday"].add("3", TimetableActivity("English"))
        tt["Thursday"].add("4", TimetableActivity("Math"))

        tt["Friday"].add("1", TimetableActivity("Geography"))
        tt["Friday"].add("2", TimetableActivity("Drawing"))
        tt["Friday"].add("4", TimetableActivity("Math"))

        t, td = time, timedelta
        template = SchooldayTemplate()
        template.add(SchooldaySlot(t(9, 0), td(minutes=45)))
        template.add(SchooldaySlot(t(9, 50), td(minutes=45)))
        template.add(SchooldaySlot(t(10, 50), td(minutes=45)))
        template.add(SchooldaySlot(t(12, 0), td(minutes=45)))

        model = WeeklyTimetableModel(day_templates={None: template})
        verifyObject(IWeekdayBasedTimetableModel, model)

        # Add an exception day
        t, td = time, timedelta
        exception = [
            ('1', SchooldaySlot(t(6, 0), td(minutes=45))),
            ('2', SchooldaySlot(t(7, 0), td(minutes=45))),
            ('3', SchooldaySlot(t(8, 0), td(minutes=45))),
            ('4', SchooldaySlot(t(9, 0), td(minutes=45)))]
        model.exceptionDays[date(2003, 11, 22)] = exception
        model.exceptionDayIds[date(2003, 11, 22)] = "Monday"

        schooldays = Term('Sample', date(2003, 11, 20), date(2003, 11, 26))
        schooldays.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        cal = model.createCalendar(schooldays, tt)

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [
            {datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "Chemistry",
             datetime(2003, 11, 20, 9, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 20, 10, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 20, 12, 00, tzinfo=UTC): "Math"},
            {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Geography",
             datetime(2003, 11, 21, 9, 50, tzinfo=UTC): "Drawing",
             # skip! datetime(2003, 11, 21, 10, 50): "History",
             datetime(2003, 11, 21, 12, 00, tzinfo=UTC): "Math"},
            # An exceptional working Saturday, with a Monday's timetable
            {datetime(2003, 11, 22, 6, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 22, 7, 0, tzinfo=UTC): "History",
             datetime(2003, 11, 22, 8, 0, tzinfo=UTC): "Biology",
             datetime(2003, 11, 22, 9, 0, tzinfo=UTC): "Physics"},
            {},
            {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 24, 9, 50, tzinfo=UTC): "History",
             datetime(2003, 11, 24, 10, 50, tzinfo=UTC): "Biology",
             datetime(2003, 11, 24, 12, 00, tzinfo=UTC): "Physics"},
            {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "Geography",
             datetime(2003, 11, 25, 9, 50, tzinfo=UTC): "Math",
             datetime(2003, 11, 25, 10, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 25, 12, 00, tzinfo=UTC): "Music"},
            {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 26, 9, 50, tzinfo=UTC): "History",
             datetime(2003, 11, 26, 10, 50, tzinfo=UTC): "Biology",
             datetime(2003, 11, 26, 12, 00, tzinfo=UTC): "Physics"},
            ]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_not_enough_days(self):
        from schooltool.timetable.model import WeeklyTimetableModel
        from schooltool.timetable import SchooldayTemplate, SchooldaySlot
        from schooltool.timetable import Timetable, TimetableDay
        template = SchooldayTemplate()
        template.add(SchooldaySlot(time(8), timedelta(minutes=30)))
        days = ["Mon", "Tue"]
        model = WeeklyTimetableModel(days, {None: template})
        day = date(2003, 11, 20)    # 2003-11-20 is a Thursday
        self.assert_(model.schooldayStrategy(day, None) is None)

        tt = Timetable(days)
        for day_id in days:
            tt[day_id] = TimetableDay()
        schooldays = TermStub()
        self.assertEquals(model.periodsInDay(schooldays, tt, day), [])

        model.createCalendar(schooldays, tt)

    def test_schooldayStrategy(self):
        from schooltool.timetable.model import WeeklyTimetableModel
        from schooltool.term.term import Term
        from schooltool.timetable import SchooldayTemplate

        term = Term('Sample', date(2005, 6, 27), date(2005, 7, 10))
        term.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        template = SchooldayTemplate()
        model = WeeklyTimetableModel(day_templates={None: template})
        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term]

        self.assertEqual(days,
                         ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None,
                          'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None])

        model.exceptionDayIds[date(2005, 7, 2)] = "Wednesday"
        model.exceptionDayIds[date(2005, 7, 4)] = "Thursday"

        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term]

        self.assertEqual(days,
                         ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', 'Wednesday', None,
                          'Thursday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None])


class TestTimetableCalendarEvent(unittest.TestCase):

    def test(self):
        from schooltool.timetable.model import TimetableCalendarEvent
        from schooltool.timetable.interfaces import ITimetableCalendarEvent

        day_id = 'Day2'
        period_id = 'Mathematics'

        class ActivityStub(object):
            owner = None
            resources = []
        activity = ActivityStub()

        ev = TimetableCalendarEvent(datetime(2004, 10, 13, 12),
                                    timedelta(45), "Math",
                                    day_id=day_id, period_id=period_id,
                                    activity=activity)
        verifyObject(ITimetableCalendarEvent, ev)
        for attr in ['day_id', 'period_id', 'activity']:
            self.assertRaises(AttributeError, setattr, ev, attr, object())

    def test_owner_resources(self):
        from schooltool.timetable.model import TimetableCalendarEvent

        day_id = 'Day2'
        period_id = 'Mathematics'

        class ActivityStub(object):
            resources = ['cookie', 'parrot']
            owner = ['Long John']
        activity = ActivityStub()

        ev = TimetableCalendarEvent(datetime(2004, 10, 13, 12),
                                    timedelta(45), "Sailin mate",
                                    day_id=day_id, period_id=period_id,
                                    activity=activity)

        self.assertEqual(ev.owner, activity.owner)
        self.assertEqual(ev.resources, activity.resources)


def doctest_PersistentTimetableCalendarEvent():
    """Tests for PersistentTimetableCalendarEvent.

        >>> from schooltool.timetable.model import PersistentTimetableCalendarEvent
        >>> from schooltool.timetable.model import TimetableCalendarEvent
        >>> class TTStub(object):
        ...     timezone = 'utc'
        >>> class ActivityStub(object):
        ...     resources = ['cookie', 'parrot']
        ...     owner = ['Long John']
        ...     timetable = TTStub()
        >>> activity = ActivityStub()
        >>> ev = TimetableCalendarEvent(datetime(2004, 10, 13, 23, 0),
        ...                             timedelta(45), "Math",
        ...                             day_id='Day 2', period_id='Lesson 1',
        ...                             activity=activity)
        >>> class PTCEStub(PersistentTimetableCalendarEvent):
        ...     def bookResource(self, resource):
        ...         print "Booking %s" % resource
        >>> event = PTCEStub(ev)
        Booking cookie
        Booking parrot

        >>> event.schoolDay()
        datetime.date(2004, 10, 13)

        >>> event.activity.timetable.timezone = 'Europe/Vilnius'
        >>> event.schoolDay()
        datetime.date(2004, 10, 14)

    """

def doctest_timetableEventHandlers():
    """
        >>> class ApplicationStub(dict):
        ...     implements(ISchoolToolApplication, IApplicationPreferences)
        ...     def __call__(self, context):
        ...         return self

        >>> app = ApplicationStub()
        >>> app['terms'] = {'term': 'Term for Fall 2006'}
        >>> ztapi.provideAdapter(None, ISchoolToolApplication, app)
        >>> timetable_calendar = []
        >>> class ModelStub(object):
        ...     def createCalendar(self, term, timetable, first=None, last=None):
        ...         print "Creating calendar for %s" % term
        ...         return timetable_calendar
        >>> class TimetableStub(object):
        ...     __name__ = 'term.schema'
        ...     model = ModelStub()
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> class CalendarStub(list):
        ...     implements(ISchoolToolCalendar)
        ...     def addEvent(self, event):
        ...         print "Adding event %s to a calendar" % event.__name__
        ...     def removeEvent(self, event):
        ...         print "Removing event %s to a calendar" % event.__name__

        >>> section_calendar = CalendarStub()
        >>> class SectionStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ISchoolToolCalendar:
        ...             return section_calendar
        >>> class ActivityStub(object):
        ...     timetable = TimetableStub()
        ...     owner = SectionStub()
        ...     def __eq__(self, other):
        ...         return isinstance(other, ActivityStub)
        >>> class EventStub(object):
        ...     activity = ActivityStub()
        ...     period_id = 'Period 1'
        ...     day_id = 'Day 1'
        >>> from schooltool.timetable.model import addEventsToCalendar
        >>> event = EventStub()
        >>> addEventsToCalendar(event)
        Creating calendar for Term for Fall 2006

        >>> from schooltool.timetable.interfaces import ITimetableCalendarEvent
        >>> class TimetableEventStub(object):
        ...     implements(ITimetableCalendarEvent)
        ...     def __init__(self, name, activity, period_id, day_id):
        ...         self.activity = activity
        ...         self.period_id = period_id
        ...         self.day_id = day_id
        ...         self.unique_id = 'event'
        ...         self.__name__ = name
        ...         self.dtstart = None
        ...         self.duration = None
        ...         self.description = None
        ...         self.location = None
        ...         self.recurrence = None
        ...         self.allday = None
        ...         self.resources = []
        >>> timetable_calendar = [
        ...     TimetableEventStub('TTEvent1', ActivityStub(), 'Period 1', 'Day 1'),
        ...     TimetableEventStub('TTEvent2', ActivityStub(), 'Period 1', 'Day 2'),
        ...     TimetableEventStub('TTEvent3', ActivityStub(), 'Period 2', 'Day 2'),
        ...     TimetableEventStub('TTEvent4', object(), 'Period 2', 'Day 2')]
        >>> addEventsToCalendar(event)
        Creating calendar for Term for Fall 2006
        Adding event TTEvent1 to a calendar

        >>> section_calendar[:] = [
        ...     TimetableEventStub('TTEvent1', ActivityStub(), 'Period 1', 'Day 1'),
        ...     TimetableEventStub('TTEvent2', ActivityStub(), 'Period 1', 'Day 2'),
        ...     TimetableEventStub('TTEvent3', ActivityStub(), 'Period 2', 'Day 2'),
        ...     TimetableEventStub('TTEvent4', ActivityStub(), 'Period 2', 'Day 2')]
        >>> from schooltool.timetable.model import removeEventsFromCalendar
        >>> removeEventsFromCalendar(event)
        Removing event TTEvent1 to a calendar

        >>> from schooltool.timetable import TimetableReplacedEvent
        >>> from schooltool.timetable.model import handleTimetableRemovedEvent
        >>> section = SectionStub()
        >>> key = "term.schema"
        >>> event = TimetableReplacedEvent(section, key,
        ...                                old_timetable=ActivityStub.timetable,
        ...                                new_timetable=None)
        >>> handleTimetableRemovedEvent(event)
        Removing event TTEvent1 to a calendar
        Removing event TTEvent2 to a calendar
        Removing event TTEvent3 to a calendar
        Removing event TTEvent4 to a calendar

        >>> event = TimetableReplacedEvent(section, key,
        ...                                old_timetable=None,
        ...                                new_timetable=None)
        >>> handleTimetableRemovedEvent(event)

        >>> from schooltool.timetable.model import handleTimetableAddedEvent
        >>> event = TimetableReplacedEvent(section, key,
        ...                                old_timetable=None,
        ...                                new_timetable=ActivityStub.timetable)
        >>> handleTimetableAddedEvent(event)
        Creating calendar for Term for Fall 2006
        Adding event TTEvent1 to a calendar
        Adding event TTEvent2 to a calendar
        Adding event TTEvent3 to a calendar
        Adding event TTEvent4 to a calendar

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setup.placelessSetUp,
                             tearDown=setup.placelessTearDown),
        unittest.makeSuite(TestSequentialDaysTimetableModel),
        unittest.makeSuite(TestSequentialDayIdBasedTimetableModel),
        unittest.makeSuite(TestWeeklyTimetableModel),
        unittest.makeSuite(TestTimetableCalendarEvent),
    ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

