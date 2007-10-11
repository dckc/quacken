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

