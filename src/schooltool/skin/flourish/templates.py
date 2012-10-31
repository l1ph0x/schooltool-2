#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Common template class shorthands.
"""

from schooltool.common.inlinept import InlineViewPageTemplate as Inline
from schooltool.common.inlinept import InheritTemplate as Inherit
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile as File


class XMLFile(File):
    def __init__(self, *args, **kw):
        if 'content_type' not in kw:
            kw = dict(kw)
            kw['content_type'] = 'text/xml'
        File.__init__(self, *args, **kw)
