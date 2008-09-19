"""
trxtsv -- read quicken transaction reports
==========================================

Usage
-----

The main methods are is trxiter() and eachTrx().
See qdbload.py for normalization and SQL integration.

A transaction is a JSON_-like dict:

  - trx

    - date, payee, num, memo

  - splits array

    - cat, clr, subtot, memo
        
.. _JSON: http://www.json.org/

See isoDate(), num(), and amt() for some of the field formats.


Future Work
-----------

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
1/3/00	Citi Visa HI		3Com/Palm Computing 888-956-7256	reciept?Palm IIIx replacement (phone order 3 Jan)	[MIT 97]/9912mit-misc	R	-100.00
1/3/00	Discover HI		ALBERTSON'S #40 391401 AUSTIN TX		Home	R	-14.46
1/3/00	MIT 97		3Com/Palm Computing 888-956-7256	Palm IIIx replacement (phone order 3 Jan)	[Citi Visa HI]/9912mit-misc		100.00
2/25/08	MIT 2000	515	McCracken Shuttle	05:15 shuttle home  to	MCI	[D Wallet]/200802tag-yvr	c	50.00
							
			TOTAL 1/1/90 - 12/31/96				51,488.91
							
			BALANCE 12/31/96				51,488.91
							
							
			TOTAL INFLOWS				728,052.11
			TOTAL OUTFLOWS				-676,563.20
							
			NET TOTAL				51,488.91

"""
_TestLines = TestString.split("\n")
_TestEncoding = ['1/4/08	Visa2773		APL*ITUNES 866-712-7753 CA	C\xe9line	Fun:Media	R	-0.99',
'			TOTAL 1/1/90 - 12/31/96				51,488.91'
]

def TestData():
    d = iter(_TestLines)
    readHeader(d)
    return eachTrx(d, [])

def trxiter(files, filter=None):
    """Iterate over selected transactions in the files,
    a bit like SPARQL describe.

    :param files: a list of files containing reports as above

    :param filter: a function from (trxdata, splits) to t/f

    yields (trxdata, splits) for each transaction;
    See `eachTrx()` for the structure of trxdata and splits.

    """
    
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

	r = []
	for trx in eachTrx(lines, r):
	    if filter is None or filter(trx):
		yield trx
        ln = r[0]
        foot = readFooter(lines, ln)
        progress("footer: ", fn, foot)
        dummy, (rdate, rtot), dummy, dummy, dummy = foot


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


def eachTrx(lines, result, encoding="iso8859-1"):
    """Turn an iterator over lines into an interator over transactions.

    >>> d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); len(list(t))
    12

    >>> from pprint import pformat as _pf; \
    d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); \
    print _pf(_sr(t.next()))
    [('splits',
      [[('L', u'Home'), ('cat', u'Home'), ('clr', u'R'), ('subtot', u'-17.70')]]),
     ('trx',
      [('acct', u'Texans Checks'),
       ('date', u'1/7/94'),
       ('num', u'1237'),
       ('payee', u'Albertsons')])]


    >>> from pprint import pformat as _pf; \
    d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); \
    print _pf(_sr(list(t)[8]))
    [('splits',
      [[('L', u'[MIT 97]/9912mit-misc'),
        ('acct', u'MIT 97'),
        ('class', u'9912mit-misc'),
        ('clr', u'R'),
        ('memo', u'reciept?Palm IIIx replacement (phone order 3 Jan)'),
        ('subtot', u'-100.00')]]),
     ('trx',
      [('acct', u'Citi Visa HI'),
       ('date', u'1/3/00'),
       ('memo', u'reciept?Palm IIIx replacement (phone order 3 Jan)'),
       ('payee', u'3Com/Palm Computing 888-956-7256')])]


    # grok tabs in memo; normalize spaces
    >>> d=iter(_TestLines); dummy=readHeader(d); t=eachTrx(d, []); \
    list(t)[11]['trx']['memo']
    u'05:15 shuttle home  to\\tMCI'

    # quicken encodes &eacute; as \xe9
    >>> d=iter(_TestEncoding); t=eachTrx(d, []); \
    len(list(t)[0]['trx']['memo'])
    6

    """

    trx = None
    
    while 1:
	try:
	    ln = lines.next()
	except StopIteration:
            raise IOError, 'unexpected end-of-lines'
        if ln.endswith("\r\n"): ln = ln[:-2]
        elif ln.endswith("\n"): ln = ln[:-1]
        ln = ln.decode(encoding)
        fields = splitline(ln)

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
                if ln.strip():
                    trx['splits'].append(fixSplit(mkRecord(SplitCols,
                                                           fields[4:])))


TestLine='2/25/08	MIT 2000	515	McCracken Shuttle	05:15 shuttle home  to	MCI	[D Wallet]/200802tag-yvr	c	50.00'

def splitline(ln):
    """handle tabs in memo

    >>> len(splitline(TestLine))
    8
    """

    p1 = ln.split('\t', 4)
    p2 = p1[-1].rsplit('\t', 3)
    return p1[:-1] + p2

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
    >>> _sr(fixSplit({'L': '[N/A]'}))
    [('L', '[N/A]'), ('acct', 'N/A')]
    """

    if not 'L' in rec: return rec

    s = rec['L']
    if s.startswith('['):
        acct, s = s[1:].split("]")
	rec['acct'] = acct
    if '/' in s:
	s, cls = s.split('/')
	rec['class'] = cls
    if s:
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
