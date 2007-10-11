"""financial - currency filter for django

This is quick-n-dirty; works with floats.

For a more complete implementation, see...
http://www.satchmoproject.com/trac/browser/satchmo/trunk/satchmo/shop/templatetags/currency_filter.py?rev=689
and
http://docs.python.org/lib/decimal-recipes.html

Note also
  Currency Fields with newforms
  http://www.djangosnippets.org/snippets/176/

and decimal support in django
 http://code.djangoproject.com/ticket/200 fixed 2007-05-20
 http://code.djangoproject.com/changeset/5302
"""

def currency(value, args=""):
    """
    >>> currency(-11400.01)
    '-11,400.01'

    >>> currency(10)
    '10.00'
    >>> currency(2.3)
    '2.30'
    """
    s = "%.2f" % value
    n = value < 0 and 1 or 0
    i = 6
    while i < len(s) - n:
        s = s[:-i] + "," + s[-i:]
        i += 4
    return s

def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()
else:
    from django import template
    register = template.Library()

    register.filter('currency', currency)

