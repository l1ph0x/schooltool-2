import pytz
import datetime
from zope.app import zapi
from zope.interface import implements
from zope import event
from zope.formlib import form, namedtemplate
from zope.formlib.interfaces import IAction
from zope.lifecycleevent import ObjectModifiedEvent
from zope.interface.common import idatetime
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.form.browser.interfaces import ITerms
from zope.app.publisher.browser.menu import getMenu, BrowserMenu

from schooltool.skin.form import AttributeEditForm
from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.person.browser.person import PersonAddView as PersonAddViewBase
from schooltool.person.interfaces import IReadPerson
from schooltool.demographics.person import Person
from schooltool.demographics import interfaces
from schooltool.demographics.browser.widget import FancyDateWidget
from schooltool import SchoolToolMessage as _

class PersonDisplayForm(form.PageDisplayForm):
    template = ViewPageTemplateFile('display_form.pt')

    def getMenu(self):
        return getMenu('person_display_menu', self.context, self.request)

class AttributeMenu(BrowserMenu):
    def getMenuItems(self, object, request):
        # all rather hackish, but functional
        obj_url = zapi.absoluteURL(object.__parent__, request)
        items = super(AttributeMenu, self).getMenuItems(object, request)
        for item in items:
            action = item['action']
            if action.startswith('/'):
                # determine which attribute we're viewing by looking at
                # the action supplied..
                attribute_name = action.split('/')[1]
                if attribute_name == object.__name__:
                    item['selected'] = True
                item['action'] = '%s%s' % (obj_url, item['action'])
        return items
    
class PersonEditForm(AttributeEditForm):

    def getMenu(self):
        return getMenu('person_edit_menu', self.context, self.request)

    def fullname(self):
        return IReadPerson(self.context.__parent__).title
        
nameinfo_traverser = SingleAttributeTraverserPlugin('nameinfo')

class NameInfoEdit(PersonEditForm):
    def title(self):
        return _(u'Change name information for ${fullname}',
                 mapping={'fullname':self.fullname()})

    def legend(self):
        return _(u'Name information')
    
    form_fields = form.Fields(interfaces.INameInfo)

class NameInfoDisplay(PersonDisplayForm):
    form_fields = form.Fields(interfaces.INameInfo)

demographics_traverser = SingleAttributeTraverserPlugin('demographics')

class DemographicsEdit(PersonEditForm):
    def title(self):
        return _(u'Change demographics for ${fullname}',
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.IDemographics)
    form_fields["birth_date"].custom_widget = FancyDateWidget    
    
class DemographicsDisplay(PersonDisplayForm):
    form_fields = form.Fields(interfaces.IDemographics)

schooldata_traverser = SingleAttributeTraverserPlugin('schooldata')

class SchoolDataEdit(PersonEditForm):
    def title(self):
        return _(u'Change school data for ${fullname}',
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.ISchoolData)
    form_fields["enrollment_date"].custom_widget = FancyDateWidget
    
class SchoolDataDisplay(PersonDisplayForm):
    form_fields = form.Fields(interfaces.ISchoolData)

parent1_traverser = SingleAttributeTraverserPlugin('parent1')
parent2_traverser = SingleAttributeTraverserPlugin('parent2')
emergency1_traverser = SingleAttributeTraverserPlugin('emergency1')
emergency2_traverser = SingleAttributeTraverserPlugin('emergency2')
emergency3_traverser = SingleAttributeTraverserPlugin('emergency3')

class ContactInfoEdit(PersonEditForm):
    # XXX need to distinguish between the different contact informations
    # somehow. Is there a sane way to do this without introducing an
    # abundance of views *and* interfaces *and* change the content
    # model?
    def title(self):
        return _(u"Change contact information for ${fullname}",
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.IContactInfo)

class ContactInfoDisplay(PersonDisplayForm):
    form_fields = form.Fields(interfaces.IContactInfo)
    
class PersonAddView(PersonAddViewBase):
    _factory = Person

class Term(object):
    def __init__(self, title, value):
        self.title = title
        self.token = value
        self.value = value
        
class Terms(object):
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def getTerm(self, value):
        return Term(value, value)

    def getValue(self, token):
        return token

@namedtemplate.implementation(IAction)
def render_submit_button(self):
    if not self.available():
        return ''
    label = self.label
    if isinstance(label, zope.i18nmessageid.Message):
        label = zope.i18n.translate(self.label, context=self.form.request)
    return ('<input type="submit" id="%s" name="%s" value="%s"'
            ' class="button-ok" />' %
            (self.__name__, self.__name__, label)
            )
