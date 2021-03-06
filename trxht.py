#!/usr/bin/python # http://www.python.org/
"""
trxht -- format personal finance transactions as hCalendar
----------------------------------------------------------

Usage
-----

Run a transaction report over *all* of your data in some date range
and print it to a tab-separated file, say, ``2004qtrx.txt``. Then
invoke a la::

  $ python trxht.py transactions.xml 2004qtrx.txt  >,x.html
  $ xmlwf ,x.html
  $ firefox ,x.html

You can give multiple files, as long as the ending balance
of one matches the starting balance of the next::

  $ python trxht.py tpl.xml 2002qtrx.txt 2004qtrx.txt  >,x.html

Support for SPARQL-style filtering is in progress. Try::

  $ python trxht.py --class myclass tpl.xml myqtrx.txt  >myclass.html

to simulate::

  describe ?TRX where { ?TRX qt:split [ qs:class "9912mit-misc"] }.


Future Work
-----------

 - migrate hCard markup to genshi
 
 - web access to accounts, categories, classes, payees

   - django integration in progress; see qdbload.py

 - add hCards for payees (in progress)

  - pick out phone numbers, city/state names

  - support a form of payee smushing on label

 - support the "num is local time" idiom as a transforming filter
 
 - support round-trip with QIF; sync back up with RDF export work in grokTrx.py

 - publish hg log stuff in a _scm/ subpath; serve the current version
    at the top


Colophon
--------

This module is documented in rst_ format for use with epydoc_.

.. _epydoc: http://epydoc.sourceforge.net/
.. _rst: http://docutils.sourceforge.net/docs/user/rst/quickstart.html

The examples in the docstrings below are executable doctest_ unit
tests.  Check them a la::

  $ python trxht.py --test

.. _doctest: http://www.python.org/doc/lib/module-doctest.html

"""
__docformat__ = "restructuredtext en"

import re
import itertools
import getopt
from decimal import Decimal

from xml.sax.saxutils import escape as xmldata
from genshi.template import MarkupTemplate # http://genshi.edgewall.org/

import trxtsv
from trxtsv import isoDate, numField, TestData

from places import Regions, Localities

def main(argv):
    import sys
    opts, args = getopt.getopt(argv[1:],
			       "a:",
			       ["account=",
				"class=",
				"cat=",
				"search=",
				"after=",
				])

    filter = None
    tpl = MarkupTemplate(file(args[0]), filename=args[0])
    criteria = {}
    
    for o, a in opts:
        if o in ("-a", "--account"):
	    criteria['account'] = a
	    f = PathFilter(a, ('trx', 'acct'))
	    if filter: filter = AndFilter(filter, f)
	    else: filter = f
	elif o in ("--class",):
	    criteria['class'] = a
	    f = PathFilter(a, ('splits', '*', 'class'))
	    if filter: filter = AndFilter(filter, f)
	    else: filter = f
	elif o in ("--cat",):
	    criteria['category'] = a
	    f = PathFilter(a, ('splits', '*', 'cat'))
	    if filter: filter = AndFilter(filter, f)
	    else: filter = f
	elif o in ("--search",):
	    criteria['search'] = a
	    f = SearchFilter(a)
	    if filter: filter = AndFilter(filter, f)
	    else: filter = f
	elif o in ("--after",):
	    criteria['after'] = a
	    f = DateFilter(a)
	    if filter: filter = AndFilter(filter, f)
	    else: filter = f

    kb = FileKB(args[1:])
    for s in kb.generate(template=tpl, criteria=criteria, filter=filter):
	sys.stdout.write(s.encode('utf-8'))
    


class AndFilter:
    def __init__(self, a, b):
	self._parts = (a, b)

    def __call__(self, arg):
	for p in self._parts:
	    if not p(arg):
		return False
	return True

class OrFilter:
    def __init__(self, *args):
	self._parts = args

    def __call__(self, arg):
	for p in self._parts:
	    if p(arg):
		return True
	return False

class PathFilter:
    """Make a filter function from a class name.

    We're simulating::

      describe ?TRX where { ... ?TRX qt:split [ qs:class "9912mit-misc"] }.

   where the ... is another filter, given by the f param.

    >>> f=PathFilter('9912mit-misc', ('splits', '*', 'class')); \
    trx={'trx': {'date': '1/7/94', 'acct': 'Texans Checks', 'num': '1237', \
    'memo': 'Albertsons'}, \
    'splits': [{'cat': 'Home', 'clr': 'R', 'amt': '-17.70'}]}; \
    f(trx)
    False

    >>> f=PathFilter('9912mit-misc', ('splits', '*', 'class')); \
    trx={'trx': {'date': '1/3/00', 'acct': 'Citi Visa HI', \
    'memo': '3Com/Palm Computing 888-956-7256'}, \
    'splits': [{'memo': '@@reciept?Palm IIIx replacement (phone order 3 Jan)',\
    'acct': 'MIT 97', 'class': '9912mit-misc', 'clr': 'R', \
    'amt': '-100.00'}]}; \
    f(trx)
    True

    >>> f=PathFilter('Citi Visa HI', ('trx', 'acct')); \
    trx={'trx': {'date': '1/3/00', 'acct': 'Citi Visa HI', \
    'memo': '3Com/Palm Computing 888-956-7256'}, \
    'splits': [{'memo': '@@reciept?Palm IIIx replacement (phone order 3 Jan)',\
    'acct': 'MIT 97', 'class': '9912mit-misc', 'clr': 'R', \
    'amt': '-100.00'}]}; \
    f(trx)
    True

    """
    def __init__(self, v, path):
	self._v = v
	self._path = path

    def __call__(self, trx):
        v = self._v

        def pathTest(r, path):
            if len(path) == 1:
                return r.get(path[0], None) == v
            else:
                if path[0] == '*':
                    for i in r:
                        if pathTest(i, path[1:]):
                            return True
                else:
                    r = r.get(path[0], None)
                    if r:
                        return pathTest(r, path[1:])
                return False

	return pathTest(trx, self._path)


class SearchFilter(object):
    """Make a filter for text searching.

    >>> s = SearchFilter("Tex")
    >>> t = trxtsv.TestData()
    >>> [tx['trx']['date'] for tx in t if s(tx)]
    ['1/7/94', '1/7/94', '1/1/00', '1/2/00', '1/3/00']
    """
    def __init__(self, q):
        self._q = q

    def __call__(self, trx):
        q = self._q
        
        def search(d):
            for k, v in d.iteritems():
                if type(v) is type({}):
                    if search(v): return True
                elif type(v) is type([]):
                    if [vv for vv in v if search(vv)]: return True
                elif type(v) is type(''):
                    if q in v: return True
            return False
        return search(trx)


class DateFilter(object):
    """Make a filter for text searching.

    >>> s = DateFilter("1994-12-31")
    >>> t = trxtsv.TestData()
    >>> [tx['trx']['date'] for tx in t if s(tx)]
    ['1/1/00', '1/1/00', '1/2/00', '1/3/00', '1/3/00', '1/3/00', '1/3/00']
    """
    def __init__(self, when):
        self._when = when

    def __call__(self, trx):
        return isoDate(trx['trx']['date']) > self._when


class FileKB(object):
    def __init__(self, filenames):
        self._filenames = filenames

    def generate(self, template, criteria, filter):
        txs = trxtsv.trxiter(self._filenames)
        details = trxdetails(itertools.ifilter(filter, txs))
        return template.generate(output='xml', encoding='utf-8',
                                 transactions = details,
                                 criteria = criteria
                                 ).serialize()


def trxdetails(txs):
    for t in txs:
        tx = t["trx"]

        # change amounts from string to decimal
        for s in t["splits"]:
            s["subtot"] = Decimal(s["subtot"].replace(",", ""))


        dtstart = isoDate(tx["date"])
        memo = tx.get("memo", "")

        # local convention: put time in memo field
        m = re.match(r'(\d\d:\d\d)\b\s*', memo)
        if m:
            dtstart = "%sT%s" % (dtstart, m.group(1))
            memo = memo[m.end(0):]
            tx["memo"] = memo

        tx["dtstart"] = dtstart

        tx['num'], tx['s'], tx['ty'] = numField(tx.get('num', ''))

        yield t

class TrxDocSink:
    """Write transactions as XHTML using microformats
    """

    def __init__(self, w):
	""":param w: a writer function, such as f.write
	"""
	self._w = w
	self._args = []

    def startDoc(self):
	w = self._w
	w("""<?xml version="1.0" encoding="utf-8"?><!--*- nxml -*-->
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
       "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head profile="http://www.w3.org/2003/g/data-view
		 http://purl.org/NET/erdf/profile">
  <link rel="transformation" href="http://www.w3.org/2002/12/cal/glean-hcal.xsl"/>
  <style type="text/css">
tbody.vevent tr.trx td { border-top: 1px solid }
tbody.vevent td { padding: 3px; margin: 0}
.amt { text-align: right }
.even { background: grey }
</style>

""")
	w(" <title>@@</title>\n")
	w("</head>\n<body>\n")

    def addArg(self, arg, v):
	self._args.append((arg, v))

    def header(self, fn, fieldNames, dt, bal):
	w = self._w
	w(" <h1>Transactions</h1>\n")
	if self._args:
	    w("<div>Filter info: %s</div>" % self._args)
	w(" <p>Input file starting date: %s bal: %s</p>" % (dt, bal))
	w(" <table>\n")
	self._row = 0 # don't let tables grow without bound

    def transaction(self, trx, splits):
	w = self._w

	if self._row > 100:
	    w("</table>\n<table>\n")
	    self._row = 0
	else:
	    self._row += 1

	datei = isoDate(trx['date'])
	w("<tbody class='vevent'>\n")
	w(" <tr class='trx'><td><abbr class='dtstart %s' title='%s'>%s</abbr>"
	  "</td>\n" % (_parity(datei), datei, trx['date']))

	num, splitflag, trxty = numField(trx.get('num', ''))

	descElt(w, 'td', trx.get('payee', ''))
	w("<td>%s</td> <td>%s</td></tr>\n" %
	  (num or trxty or '', trx['acct']))

        for split in splits:
	    w("<tr class='split description'><td></td><td>%s</td><td>%s</td>"
	      "<td>%s</td><td class='amt'>%s</td></tr>\n" %
	      (xmldata(split.get('memo', '')),
	       split.get('clr', ''),
	       xmldata(split.get('L', '')),
	       split.get('subtot', '')))
	w("</tbody>\n\n")

    def close(self):
	w = self._w
	w(" </table>\n</body>\n</html>")


def descElt(w, elt, desc):
    """Write transaction description element, including hCard if possible.

    >>> x=[]; descElt(lambda(s): x.append(s), 'td', \
    'KCI SHUTTLE'); ''.join(x)
    "<td class='summary'>KCI SHUTTLE</td>"

    Hmm... currently, we use python lists at one level,
    and XHTML markup at another, just like we used to
    for transactions. Better to use a JSON-style
    dict again, as a mini RDF store. JSON doesn't
    allow sharing, though. Hmm...


    """

    try:
	fn, teli, tel, region = telRegion(desc)
    except IndexError:
	try:
	    fn, locality, region, postcode = citySt(desc)
	except IndexError:
	    w("<%s class='summary'>%s</%s>" % (elt, xmldata(desc), elt))
	else:
	    w('<td class="location vcard"><b class="summary fn org">%s</b> ' %
              xmldata(fn))
	    w('<span class="adr">' \
	      '<span class="locality">%s</span> ' \
	      '<abbr class="region" title="%s">%s</abbr>' % \
	      (locality, Regions[region], region))
	    if postcode:
		w(' <u class="postal-code">%s</u>' % postcode)
	    w('</span>')
	    w('</td>')
    else:
	w('<td class="location vcard"><b class="summary fn org">%s</b> ' % xmldata(fn))
	w('<a class="tel" href="tel:%s">%s</a> ' % (teli, tel))
	if region:
	    w('<span class="adr"><span class="region">%s</span></span>' % \
	      region)
	w('</td>')

def telRegion(desc):
    """Pick out phone numbers and state names from U.S. places.

    >>> telRegion('KCI SHUTTLE +1-816-471-2015 MO')
    ('KCI SHUTTLE', '+1-816-471-2015', '+1-816-471-2015', 'MO')

    >>> telRegion('WAYPORT 5125196115 TX')
    ('WAYPORT', '+1-512-519-6115', '5125196115', 'TX')

    >>> telRegion('VONAGE DIGITAL VOICE 732-528-2600 NJ')
    ('VONAGE DIGITAL VOICE', '+1-732-528-2600', '732-528-2600', 'NJ')

    >>> telRegion('MICRO CENTER #191 +1-913-652-6000')
    ('MICRO CENTER #191', '+1-913-652-6000', '+1-913-652-6000', None)
    """

    if '+' in desc: # international phone number; state optional
	p = r'(?P<fn>[^\+]+)' \
	    r'(?P<tel>(?P<teli>\+[\d\-\.]+))' \
	    r'\s*(?P<region>[A-Z][A-Z])?$'
    else: # us phone number; state required
	p = r'(?P<fn>[^\+]+)' \
	    r'(?P<tel>(?P<ac>\d\d\d)-?(?P<ex>\d\d\d)-?(?P<ln>\d\d\d\d))' \
	    r'\s*(?P<region>[A-Z][A-Z])$'
    m = re.match(p, desc)
    if m:
	tel = m.group('tel')
	try:
	    teli = m.group('teli')
	except IndexError:
	    teli = "+1-%s-%s-%s" % (m.group('ac'), m.group('ex'), m.group('ln'))
	return m.group('fn').strip(), teli, tel, m.group('region') or None

    raise IndexError




def mkregex(state, cities):
    r"""Make a regex from city/state data.
    
    We assume no regex chars in the data.

    >>> mkregex('KS', ['STANLEY', 'OVERLAND PARK', 'SHAWNEE MISSION'])
    '((?P<locality>STANLEY|OVERLAND PARK|SHAWNEE MISSION))\\s*(?P<region>KS)'

    """

    expc = '(?P<locality>%s)' % ('|'.join([ v for v in cities]), )

    return '(' + expc + (')\s*(?P<region>%s)' % state)


PlaceExp = dict([(st, re.compile(mkregex(st, cities))) \
		 for st, cities in Localities])

def citySt(desc):
    """Parse payee/description into formatted name, locality, region, postcode.

    Data comes from credit card statements, typically.
    
    :raises IndexError: if we can't find a region
    
    >>> citySt('COLLEGE PARK FAMILY STANLEY KS')
    ('COLLEGE PARK FAMILY', 'STANLEY', 'KS', None)

    >>> citySt('COMFORT INN@PLAINFIELD, IN')
    ('COMFORT INN', 'PLAINFIELD', 'IN', None)

    >>> citySt('BP OIL@DUBLIN, OH 43016')
    ('BP OIL', 'DUBLIN', 'OH', '43016')

    >>> citySt('@@listing fees???')
    Traceback (most recent call last):
        ...
    IndexError: no city/state found

    todo: 'USPS 1983579556 SHAWNEE MISSI KS'
    """

    postcode = None

    if '@' in desc and '@@' not in desc:
	fn, where = desc.split('@')

	# 3 letter code: airport
	if re.match(r'^[A-Z][A-Z][A-Z]$', where):
	    raise IndexError, "airport code not expected"

	fn = fn.strip()
	city, st = where.split(',')
	if st[-1].isdigit() and ' ' in st:
	    st, postcode = st.split()
	st = st.strip()
	return fn, city, st, postcode

    for st, exp in PlaceExp.items():
	m = exp.search(desc)
	if m:
	    return desc[:m.start(0)].strip(), \
		m.group('locality'), st, postcode

    raise IndexError, "no city/state found"



def _parity(ymd):
    """
    >>> _parity("2005-11-12")
    'even'
    >>> _parity("2005-11-13")
    'odd'
    """
    parity = int(ymd[-1]) % 2
    return ("even", "odd")[parity]


def _test():
    import doctest
    return doctest.testmod()

if __name__ == '__main__':
    import sys

    if sys.argv[1:] and sys.argv[1] == '--test':
	_test()
    else:
	try:
	    main(sys.argv)
	except getopt.GetoptError:
	    print >>sys.stderr, __doc__
	    sys.exit(2)



