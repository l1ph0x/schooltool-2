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
Views for calendaring.

$Id$
"""

import libxml2
import datetime
import operator
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ISchooldayModel, ICalendar
from schooltool.interfaces import IApplicationObject
from schooltool.rest import View, Template, absoluteURL
from schooltool.rest import textErrorPage, notFoundPage
from schooltool.rest import read_file
from schooltool.rest.auth import PublicAccess, PrivateAccess, TeacherAccess
from schooltool.rest.auth import isManager
from schooltool.cal import ICalReader, ICalParseError, CalendarEvent
from schooltool.cal import ical_text, ical_duration, Period
from schooltool.common import parse_date, parse_datetime, to_unicode
from schooltool.component import getPath, traverse
from schooltool.component import registerView
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


complex_prop_names = ('RRULE', 'RDATE', 'EXRULE', 'EXDATE')


class SchooldayModelCalendarView(View):
    """iCalendar view for ISchooldayModel."""

    authorization = PublicAccess

    datetime_hook = datetime.datetime

    schema = read_file("../schema/schooldays.rng")
    _dow_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6}

    def do_GET(self, request):
        end_date = self.context.last + datetime.date.resolution
        uid_suffix = "%s@%s" % (getPath(self.context),
                                request.getRequestHostname())
        dtstamp = self.datetime_hook.utcnow().strftime("%Y%m%dT%H%M%SZ")
        result = [
            "BEGIN:VCALENDAR",
            "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:school-period-%s" % uid_suffix,
            "SUMMARY:School Period",
            "DTSTART;VALUE=DATE:%s" % self.context.first.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:%s" % end_date.strftime("%Y%m%d"),
            "DTSTAMP:%s" % dtstamp,
            "END:VEVENT",
        ]
        for date in self.context:
            if self.context.isSchoolday(date):
                s = date.strftime("%Y%m%d")
                result += [
                    "BEGIN:VEVENT",
                    "UID:schoolday-%s-%s" % (s, uid_suffix),
                    "SUMMARY:Schoolday",
                    "DTSTART;VALUE=DATE:%s" % s,
                    "DTSTAMP:%s" % dtstamp,
                    "END:VEVENT",
                ]
        result.append("END:VCALENDAR")
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
        return "\r\n".join(result)

    def do_PUT(self, request):
        ctype = request.getContentType()
        if ctype == 'text/calendar':
            return self.do_PUT_text_calendar(request)
        elif ctype == 'text/xml':
            return self.do_PUT_text_xml(request)
        else:
            return textErrorPage(request,
                                 _("Unsupported content type: %s") % ctype)

    def do_PUT_text_calendar(self, request):
        first = last = None
        days = []
        reader = ICalReader(request.content)
        try:
            for event in reader.iterEvents():
                summary = event.getOne('SUMMARY', '').lower()
                if summary not in ('school period', 'schoolday'):
                    continue # ignore boring events

                if not event.all_day_event:
                    return textErrorPage(request,
                             _("All-day event should be used"))

                has_complex_props = reduce(operator.or_,
                                      map(event.hasProp, complex_prop_names))

                if has_complex_props:
                    return textErrorPage(request,
                         _("Repeating events/exceptions not yet supported"))

                if summary == 'school period':
                    if (first is not None and
                        (first, last) != (event.dtstart, event.dtend)):
                        return textErrorPage(request,
                                    _("Multiple definitions of school period"))
                    else:
                        first, last = event.dtstart, event.dtend
                elif summary == 'schoolday':
                    if event.duration != datetime.date.resolution:
                        return textErrorPage(request,
                                    _("Schoolday longer than one day"))
                    days.append(event.dtstart)
        except ICalParseError, e:
            return textErrorPage(request, str(e))
        else:
            if first is None:
                return textErrorPage(request, _("School period not defined"))
            for day in days:
                if not first <= day < last:
                    return textErrorPage(request,
                                         _("Schoolday outside school period"))
            self.context.reset(first, last - datetime.date.resolution)
            for day in days:
                self.context.add(day)
        self.log_PUT(request)
        request.setHeader('Content-Type', 'text/plain')
        return _("Calendar imported")

    def do_PUT_text_xml(self, request):
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                            _("Schoolday model not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request,
                            _("Schoolday model is not valid XML"))
        doc = libxml2.parseDoc(xml)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/schooldays/0.1'
            xpathctx.xpathRegisterNs('tt', ns)
            schooldays = xpathctx.xpathEval('/tt:schooldays')[0]
            first_attr = to_unicode(schooldays.nsProp('first', None))
            last_attr = to_unicode(schooldays.nsProp('last', None))
            try:
                first = parse_date(first_attr)
                last = parse_date(last_attr)
                holidays = [parse_date(to_unicode(node.content))
                            for node in xpathctx.xpathEval(
                                            '/tt:schooldays/tt:holiday/@date')]
            except ValueError, e:
                return textErrorPage(request, str(e))
            try:
                node = xpathctx.xpathEval('/tt:schooldays/tt:daysofweek')[0]
                dows = [self._dow_map[d]
                        for d in to_unicode(node.content).split()]
            except KeyError, e:
                return textErrorPage(request, str(e))
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        self.context.reset(first, last)
        self.context.addWeekdays(*dows)
        for holiday in holidays:
            if holiday in self.context and self.context.isSchoolday(holiday):
                self.context.remove(holiday)
        self.log_PUT(request)
        request.setHeader('Content-Type', 'text/plain')
        return _("Calendar imported")

    def log_PUT(self, request):
        """Add an entry to the application log.

        This method is overriden by subclasses of SchooldayModelCalendarView.
        """
        request.appLog(_("Schoolday Calendar %s updated")
                       % getPath(self.context))


class CalendarReadView(View):
    """iCalendar read only view for ICalendar."""

    authorization = PublicAccess

    datetime_hook = datetime.datetime

    def do_GET(self, request):
        dtstamp = self.datetime_hook.utcnow().strftime("%Y%m%dT%H%M%SZ")
        result = [
            "BEGIN:VCALENDAR",
            "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
            "VERSION:2.0",
        ]
        events = list(self.context)
        events.sort()
        for event in events:
            result += [
                "BEGIN:VEVENT",
                "UID:%s" % ical_text(event.unique_id),
                "SUMMARY:%s" % ical_text(event.title)]
            if event.location is not None:
                result.append("LOCATION:%s" % ical_text(event.location))
            result += [
                "DTSTART:%s" % event.dtstart.strftime('%Y%m%dT%H%M%S'),
                "DURATION:%s" % ical_duration(event.duration),
                "DTSTAMP:%s" % dtstamp,
                "END:VEVENT",
            ]
        if not events:
            # There were no events.  iCalendar spec (RFC 2445) requires
            # VCALENDAR to have at least one subcomponent.  Let's create
            # a fake event.
            # NB Mozilla Calendar produces a 0-length file when publishing
            # empty calendars.  Sadly it does not then accept them
            # (http://bugzilla.mozilla.org/show_bug.cgi?id=229266).
            result += [
                "BEGIN:VEVENT",
                "UID:placeholder-%s@%s" % (getPath(self.context),
                                           request.getRequestHostname()),
                "SUMMARY:%s" % ical_text("Empty calendar"),
                "DTSTART;VALUE=DATE:%s" % dtstamp[:8],
                "DTSTAMP:%s" % dtstamp,
                "END:VEVENT",
            ]
        result.append("END:VCALENDAR")
        request.setHeader('Content-Type', 'text/calendar; charset=UTF-8')
        return "\r\n".join(result)


class CalendarView(CalendarReadView):
    """iCalendar r/w view for ICalendar."""

    authorization = PrivateAccess

    def do_PUT(self, request):
        ctype = request.getContentType()
        if ctype != 'text/calendar':
            return textErrorPage(request,
                                 _("Unsupported content type: %s") % ctype)
        events = []
        reader = ICalReader(request.content)
        try:
            for event in reader.iterEvents():
                if (event.summary == 'Empty calendar'
                    and event.getOne('UID').startswith('placeholder')):
                    continue
                has_complex_props = reduce(operator.or_,
                                      map(event.hasProp, complex_prop_names))
                if has_complex_props:
                    return textErrorPage(request,
                         _("Repeating events/exceptions not yet supported"))
                events.append(CalendarEvent(event.dtstart, event.duration,
                                            event.summary,
                                            location=event.location,
                                            unique_id=event.uid))
        except ICalParseError, e:
            return textErrorPage(request, str(e))
        else:
            for event in list(self.context):
                if event in events:
                    # old events
                    events.remove(event)
                elif event.owner or event.context:
                    # XXX: This business logic should be in an event
                    #      handler, not in a view.

                    # owner and context are not represented in the
                    # iCalendar representation
                    e = CalendarEvent(event.dtstart, event.duration,
                                      event.title, unique_id=event.unique_id)
                    if e in events:
                        # old event
                        events.remove(e)
                    else:
                        if event.owner is not None:
                            event.owner.calendar.removeEvent(event)
                        if event.context is not None:
                            event.context.calendar.removeEvent(event)
                else:
                    # deleted event
                    self.context.removeEvent(event)

            for event in events:
                # newly added events
                self.context.addEvent(event)
            request.appLog(
                _("Calendar %s for %s imported")
                % (getPath(self.context), self.context.__parent__.title))
            request.setHeader('Content-Type', 'text/plain')
            return _("Calendar imported")


class BookingView(View):
    """Resource booking (...object/booking)"""

    schema = read_file("../schema/booking.rng")
    authorization = TeacherAccess

    do_GET = staticmethod(notFoundPage)

    def do_POST(self, request):
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     _("Input not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Not valid XML"))
        doc = libxml2.parseDoc(xml)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/calendar/0.1'
            xpathctx.xpathRegisterNs('cal', ns)

            owner_node = xpathctx.xpathEval('/cal:booking/cal:owner')[0]
            owner_path = to_unicode(owner_node.nsProp('path', None))
            try:
                owner = traverse(self.context, owner_path)
            except KeyError:
                return textErrorPage(request,
                                     _("Invalid path: %r") % owner_path)
            if not IApplicationObject.providedBy(owner):
                return textErrorPage(request,
                                     _("'owner' in not an ApplicationObject."))
            if (owner is not request.authenticated_user
                    and not isManager(request.authenticated_user)):
                return textErrorPage(request, _("You can only book resources "
                                                "for yourself"))

            resource_node = xpathctx.xpathEval('/cal:booking/cal:slot')[0]
            start_str = to_unicode(resource_node.nsProp('start', None))
            dur_str = to_unicode(resource_node.nsProp('duration', None))
            try:
                arg = 'start'
                start = parse_datetime(start_str)
                arg = 'duration'
                duration = datetime.timedelta(minutes=int(dur_str))
            except ValueError:
                return textErrorPage(request, _("%r argument incorrect") % arg)
            booking_node = xpathctx.xpathEval('/cal:booking')[0]
            if to_unicode(booking_node.nsProp('conflicts', None)) != 'ignore':
                p = Period(start, duration)
                for e in self.context.calendar:
                    if p.overlaps(Period(e.dtstart, e.duration)):
                        return textErrorPage(request, _("The resource is "
                                             "busy at specified time"))
            title = _('%s booked by %s') % (self.context.title, owner.title)
            ev = CalendarEvent(start, duration, title, owner, self.context)
            self.context.calendar.addEvent(ev)
            owner.calendar.addEvent(ev)
            request.appLog(_("%s (%s) booked by %s (%s) at %s for %s") %
                           (getPath(self.context), self.context.title,
                            getPath(owner), owner.title, start, duration))
            request.setHeader('Content-Type', 'text/plain')
            return _("OK")
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()


class AllCalendarsView(View):
    """List of all calendars (/calendars.html).

    This is a  view on the top-level application object that generates an HTML
    page with links to the calendars of all groups, persons and resources.
    """

    template = Template("www/all_calendars.pt")
    authorization = PublicAccess

    def groups(self):
        return self._list('groups')

    def persons(self):
        return self._list('persons')

    def resources(self):
        return self._list('resources')

    def _list(self, name):
        items = [(item.title, absoluteURL(self.request, item.calendar),
                  absoluteURL(self.request, item, 'timetable-calendar'))
                 for item in self.context[name].itervalues()]
        items.sort()
        return [{'title': title,
                 'href': href,
                 'tthref': tthref,
                } for title, href, tthref in items]


def setUp():
    """See IModuleSetup."""
    registerView(ISchooldayModel, SchooldayModelCalendarView)
    registerView(ICalendar, CalendarView)

