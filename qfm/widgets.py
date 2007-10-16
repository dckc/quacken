# cribbed from
# YUI Autocomplete
# August 27, 2007
# http://www.djangosnippets.org/snippets/392/

from django import newforms as forms
from django.newforms.util import smart_unicode
from django.utils.html import escape

AC_SNIPPET = """
<div class="ac_container yui-skin-sam">
    <input class="autocomplete_widget" id="%(id)s" name="%(name)s" type="text" value="%(value)s" />
    <div id="%(id)s_container"></div>

    <script type="text/javascript">
        var acDataSource_%(id)s = new YAHOO.widget.DS_XHR("%(url)s", %(schema)s);
        var acAutoComp_%(id)s = new YAHOO.widget.AutoComplete("%(id)s","%(id)s_container", acDataSource_%(id)s);
        acAutoComp_%(id)s.useIFrame = true;
        acAutoComp_%(id)s.typeAhead = true; 
    </script>
</div>
"""

class AutoCompleteWidget(forms.widgets.TextInput):
    """ widget autocomplete dla zwyklych pol tekstowych (nie FK)
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
