import pytz
import datetime
from zope import event
from zope.formlib import form
from zope.lifecycleevent import ObjectModifiedEvent
from zope.interface.common import idatetime
from zope.browserpage import ViewPageTemplateFile
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.common import SchoolToolMessage as _

class BasicForm(form.FormBase):
    """Simple non-edit form in schooltool style.

    Pass render_context=False to form.Fields() in subclasses to
    make sure it doesn't try to render fields from the context object.
    """
    template = ViewPageTemplateFile('templates/edit_form.pt')

    def title(self):
        # optional
        return None

    def legend(self):
        # optional
        return None

    def getMenu(self):
        # optional
        return None


class EditForm(form.PageEditForm):
    """Formlib-based edit form in schooltool style.
    """
    template = ViewPageTemplateFile('templates/edit_form.pt')

    def title(self):
        # optional
        return None

    def legend(self):
        # optional
        return None

    def getMenu(self):
        # optional
        return None

    def actualContext(self):
        # subclass could turn this into self.context.__parent__ for
        # attribute editing
        return self.context

    @form.action(_("Apply"), condition=form.haveInputWidgets)
    def handle_edit_action(self, action, data):
        self.edit_action(action, data)

    # a separate method so it can be called by actions on subclasses as well
    # or, alternatively, be overridden by subclasses
    def edit_action(self, action, data):
        if not form.applyChanges(self.context, self.form_fields, data,
                                 self.adapters):
            self.status = 'No changes'
            return

        event.notify(ObjectModifiedEvent(self.context))
        formatter = self.request.locale.dates.getFormatter(
            'dateTime', 'medium')

        try:
            time_zone = idatetime.ITZInfo(self.request)
        except TypeError:
            time_zone = pytz.UTC

        self.status = _(
            "Updated on ${date_time}",
            mapping={
              'date_time':
              formatter.format(datetime.datetime.now(time_zone))
              }
            )

    @form.action(_("Cancel"), condition=form.haveInputWidgets)
    def handle_cancel_action(self, action, data):
        self.cancel_action(action, data)

    def cancel_action(self, action, data):
        # redirect to parent
        url = absoluteURL(self.actualContext(), self.request)
        self.request.response.redirect(url)
        return ''


class AttributeEditForm(EditForm):
    """A form that can be used when editing an attribute of the actual
    content object.
    """
    def actualContext(self):
        return self.context.__parent__
