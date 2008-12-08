# cribbed from
# YUI Autocomplete
# August 27, 2007
# http://www.djangosnippets.org/snippets/392/

from django import newforms as forms
from django.newforms.util import smart_unicode
from django.newforms.widgets import TextInput,flatatt
from django.utils.html import escape

class AutoCompleteField(TextInput):
    """http://www.djangosnippets.org/snippets/253/
    """
    def __init__(self, url='', options='{paramName: "text"}', attrs=None):
        self.url = url
        self.options = options
        if attrs is None:
            attrs = {}
        self.attrs = attrs
            
    def render(self, name, value=None, attrs=None):
        final_attrs = self.build_attrs(attrs, name=name)
        if value:
            value = smart_unicode(value)
            final_attrs['value'] = escape(value)
        if not self.attrs.has_key('id'):
            final_attrs['id'] = 'id_%s' % name
        return (u'<input type="text" name="%(name)s" id="%(id)s"/> <div class="autocomplete" id="box_%(name)s"></div>'
                '<script type="text/javascript">'
                'new Ajax.Autocompleter(\'%(id)s\', \'box_%(name)s\', \'%(url)s\', %(options)s);'
                '</script>') % {'attrs'	: flatatt(final_attrs),
                                'name'	: name,
                                'id'	: final_attrs['id'],
                                'url'	: self.url,
                                'options' : self.options}



class AutoCompleteWidget(forms.widgets.TextInput):
    """ widget autocomplete dla zwyklych pol tekstowych (nie FK)
    http://www.djangosnippets.org/snippets/392/
    """
    # YUI schema
    schema = None
    # url for YUI XHR Datasource
    lookup_url = None

    def render(self, name, value, attrs={}):
        html_id = attrs.get('id', name)

        if value: value = smart_unicode(value)
        else: value = ''
        
        return AC_SNIPPET % {'id': html_id,
                             'name': name,
                             'value': escape(value),
                             'url': self.lookup_url,
                             'schema': self.schema}
    

def _test():
    print AutoCompleteWidget().render('field_name', '')

if __name__ == '__main__':
    _test()
