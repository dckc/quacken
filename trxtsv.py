"""
trxtsv -- read quicken transaction reports
==========================================

Usage
-----

The main methods are is eachFile() and eachTrx().

A transaction is a JSON_-like dict:

  - trx

    - date, payee, num, memo

  - splits array

    - cat, clr, subtot, memo
        
.. _JSON: http://www.json.org/

See isoDate(), num(), and amt() for some of the field formats.


Future Work
-----------

  - support database loading, a la normalizeQData.py

  - investigate diff/patch, sync with DB; flag ambiguous transactions

  - how about a python datastructure to mirror turtle?

    - and how does JSON relate to python pickles?


Colophon
--------

This module is documented in rst_ format for use with epydoc_.

.. _epydoc: http://epydoc.sourceforge.net/
.. _rst: http://docutils.sourceforge.net/rst.html

"""

__docformat__ = "restructuredtext en"


TestString = """							
Date	Account	Num	Description	Memo	Category	Clr	Amount
							
			BALANCE 12/31/99				1000.00
							
1/7/94	Texans Checks	1237	Albertsons		Home	R	-17.70
1/7/94	Texans Checks	ATM         S	N/A		Loss	R	-1.00
					Home	R	-31.01
				haircut	Stuff:Personal	R	-10.00
					Fun:Cash	R	-8.99
1/7/94	VISA 4339		Dallas	w/Susan	Fun:Entertainment	R	-25.75
1/9/94	Discover HI		Exxon	14.838gal	Auto:Fuel	R	-16.75
1/1/00	Texans Checks		Interest Earned		Interest	R	4.20
1/1/00	Discover HI		Pizza Hut		Fun:Dining	R	-22.58
1/2/00	Texans Checks	4196	Northwest Fellowship		Charity	R	-125.00
1/3/00	Texans Checks	EFT	Nationwide	prepared DEC 08	Auto:Insurance	R	-66.09
1/3/00	Citi Visa HI		3Com/Palm Computing 888-956-7256	@@reciept?Palm IIIx replacement (phone order 3 Jan)	[MIT 97]/9912mit-misc	R	-100.00
1/3/00	Discover HI		ALBERTSON'S #40 391401 AUSTIN TX		Home	R	-14.46
1/3/00	MIT 97		3Com/Palm Computing 888-956-7256	Palm IIIx replacement (phone order 3 Jan)	[Citi Visa HI]/9912mit-misc		100.00
							
			TOTAL 1/1/90 - 12/31/96				51,488.91
							
			BALANCE 12/31/96				51,488.91
							
							
			TOTAL INFLOWS				728,052.11
			TOTAL OUTFLOWS				-676,563.20
							
			NET TOTAL				51,488.91

"""
_TestLines = TestString.split("\n")

def eachFile(files, sink, filter=None):
    """Iterate over selected transactions in the files and send them to
    the sink.

    :param files: a list of files containing reports as above

    :param sink: something with header(), transaction(), and close() methods.

    :param filter: a function from (trxdata, splits) to t/f

    The transaction method gets called a la: sink.transaction(trxdata, splits).
    See eachTrx() for the structure of trxdata and splits.

    The sink.transaction method is like a SPARQL describe hit.

    @@TODO: document header() method.
    """
    sink.startDoc()
    
    rtot = None
    rdate = None
    
    for fn in files:
        lines = file(fn)

        fieldNames, dt, bal = readHeader(lines)
        progress("header:" , fn, fieldNames, dt, bal)
        if rdate and dt <> rdate:
            raise IOError, "expected date " + rdate + " but got " + dt
        if rtot and bal <> rtot:
            raise IOError, "expected balance " + rtot + " but got " + bal
        sink.header(fieldNames, fn, dt, bal)
	r = []
	for trx in eachTrx(lines, r):
	    if filter is None or filter(trx):
		sink.transaction(trx['trx'], trx['splits'])
        ln = r[0]
        foot = readFooter(lines, ln)
        progress("footer: ", fn, foot)
        dummy, (rdate, rtot), dummy, dummy, dummy = foot
    
    sink.close()

def readHeader(lines):
    """
    >>> readHeader(iter(_TestLines))
    (['Date', 'Account', 'Num', 'Description', 'Memo', 'Category', 'Clr', 'Amount'], '1999-12-31', '1000.00')
    """
    while 1:
        # skip blank line at top
        hd = lines.next().strip()
        if hd: break
    fieldNames = hd.split('\t')

    while 1:
        bal = lines.next().strip()
        if bal: break
    dummy, dt, a = bal.split()
    dt = isoDate(dt)
    a = amt(a)

    hd = lines.next().strip() # skip blank line
    if hd: raise IOError, "expected blank line; got" + hd
    
    return fieldNames, dt, a


def eachTrx(lines, result):
    """Turn an iterator over lines into an interator over transactions.

    >>> d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); len(list(t))
    11

    >>> from pprint import pformat as _pf; \
    d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); \
    print _pf(_sr(t.next()))
    [('splits',
      [[('L', 'Home'), ('cat', 'Home'), ('clr', 'R'), ('subtot', '-17.70')]]),
     ('trx',
      [('acct', 'Texans Checks'),
       ('date', '1/7/94'),
       ('num', '1237'),
       ('payee', 'Albertsons')])]


    >>> from pprint import pformat as _pf; \
    d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); \
    print _pf(_sr(list(t)[8]))
    [('splits',
      [[('L', '[MIT 97]/9912mit-misc'),
        ('acct', 'MIT 97'),
        ('class', '9912mit-misc'),
        ('clr', 'R'),
        ('memo', '@@reciept?Palm IIIx replacement (phone order 3 Jan)'),
        ('subtot', '-100.00')]]),
     ('trx',
      [('acct', 'Citi Visa HI'),
       ('date', '1/3/00'),
       ('memo', '@@reciept?Palm IIIx replacement (phone order 3 Jan)'),
       ('payee', '3Com/Palm Computing 888-956-7256')])]



    """

    trx = None
    
    while 1:
	try:
	    ln = lines.next()
	except StopIteration:
            raise IOError, 'unexpected end-of-lines'
        if ln.endswith("\r\n"): ln = ln[:-2]
        elif ln.endswith("\n"): ln = ln[:-1]
        fields = ln.split('\t')

	#progress("fields", fields)
        if fields[0]:
            if trx:
                yield trx
	    trx = mkRecord(('trx','splits'),
			   (mkRecord(TrxCols, fields),
			    [fixSplit(mkRecord(SplitCols, fields[4:]))]))
        else:
            if fields[3].startswith("TOTAL"):
                if trx: yield trx
                result.append(ln)
		return
            else:
                trx['splits'].append(fixSplit(mkRecord(SplitCols, fields[4:])))


def mkRecord(keys, fields):
    """
    >>> mkRecord(('date', 'acct', 'num', 'payee'), \
    ['1/7/94', 'Texans Checks', '1237' 'Albertsons'])
    {'date': '1/7/94', 'acct': 'Texans Checks', 'num': '1237Albertsons'}
    """
    d = {}
    for k, v in zip(keys, fields):
	if v: d[k] = v
    return d

def _sr(r):
    """just for testing
    """
    if type(r) is type({}):
	it=r.items()
	it.sort()
	return [(k, _sr(v) ) for k, v in it]
    elif type(r) is type([]):
	return [_sr(v) for v in r]
    else:
	return r

TrxCols = ('date', 'acct', 'num', 'payee', 'memo')
SplitCols = ('memo', 'L', 'clr', 'subtot')

def fixSplit(rec):
    """
    >>> _sr(fixSplit({'L': 'Home'}))
    [('L', 'Home'), ('cat', 'Home')]

    >>> _sr(fixSplit({'L': '[MIT 97]/9912mit-misc'}))
    [('L', '[MIT 97]/9912mit-misc'), ('acct', 'MIT 97'), ('class', '9912mit-misc')]

    >>> _sr(fixSplit({'L': 'xyz/9912mit-misc'}))
    [('L', 'xyz/9912mit-misc'), ('cat', 'xyz'), ('class', '9912mit-misc')]
    """

    if not 'L' in rec: return rec

    s = rec['L']
    if '/' in s:
	s, cls = s.split('/')
	rec['class'] = cls
    if '[' in s:
	rec['acct'] = s[1:-1]
    else:
	rec['cat'] = s
    return rec


def readFooter(lines, ln):
    while 1:
        words = ln.split()
        if words:
            k = words[0]
            if k == 'TOTAL':
                if words[1] == 'INFLOWS':
                    inflows = amt(words[2])
                elif words[1] == 'OUTFLOWS':
                    outflows = amt(words[2])
                else:
                    total = (isoDate(words[1]), isoDate(words[3]),
                             amt(words[4]))
            elif k == 'BALANCE':
                balance = (isoDate(words[1]), amt(words[2]))
            elif k == 'NET':
                nettot = amt(words[2])
            else:
                raise IOError, "unexpected data: " + ln

	try:
	    ln = lines.next()
	except StopIteration:
	    break
        
    return total, balance, inflows, outflows, nettot


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
    >>> d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, [])
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
    >>> d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, [])
    >>> [tx['trx']['date'] for tx in t if s(tx)]
    ['1/1/00', '1/1/00', '1/2/00', '1/3/00', '1/3/00', '1/3/00', '1/3/00']
    """
    def __init__(self, when):
        self._when = when

    def __call__(self, trx):
        return isoDate(trx['trx']['date']) > self._when

def isoDate(dt):
    """convert quicken date format to XML date format
    assume date between 1950 and 2050

    >>> isoDate("12/31/02")
    '2002-12-31'

    >>> isoDate("12/31/96")
    '1996-12-31'

    """

    mm, dd, yy = dt.split("/")
    yy = int(yy)
    if yy > 50:
        yy = 1900 + yy
    else:
        yy = 2000 + yy
    return "%04d-%02d-%02d" % (yy, int(mm), int(dd))

def amt(s):
    """grok amount

    don't convert to float due to rounding

    >>> amt("728,052.11")
    '728052.11'

    """
    s = s.replace(',', '')
    assert float(s) is not None
    return s

def numField(num):
    if num.endswith(' S'):
	# ah... this just means split transaction. redundant.
	num=num[:-1].strip()
	split = 'S'
    else:
	split = None

    if num in ('ATM', 'DEP', 'Deposit', 'EFT', 'TXFR'):
	trxty = num
	num = None
    else:
	trxty = None
    return (num, split, trxty)


def progress(*args):
    """@@ print statements should be replaced by unit tests
    """
    import sys
    for a in args:
        sys.stderr.write(str(a) + ' ')
    sys.stderr.write("\n")


def _test():
    import doctest
    assert(_TestLines) # tell pychecker we _do_ use this.
    return doctest.testmod()

if __name__ == '__main__':
    _test()
