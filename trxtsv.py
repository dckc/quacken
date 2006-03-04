"""
trxtsv -- read quicken transactions

The Quicken Interchange Format (QIF_) is notoriously inadequate for
clean import/export. The instructions_ for migrating Quicken data
across platforms say:

  1. From the old platform, dump it out as QIF
  2. On the new platform, read in the QIF data
  3. Review the results for duplicate transfers

I have not migrated my data from Windows98 to OS X because of this mess.
I use win4lin as life-support for Quicken 2001 on my debian linux box.

Meanwhile, quicken supports printing any report to a tab-separated
file, and I found that an exhaustive transaction report represents
transfers unambiguously. Since October 2000, when my testing showed
that I could re-create various balances and reports from these
tab-separated reports, I have been maintaining a CVS history of
my exported Quicken data, splitting it every few years::

   $ wc *qtrx.txt
    4785   38141  276520 1990-1996qtrx.txt
    6193   61973  432107 1997-1999qtrx.txt
    4307   46419  335592 2000qtrx.txt
    5063   54562  396610 2002qtrx.txt
    5748   59941  437710 2004qtrx.txt
   26096  261036 1878539 total

I switched from CVS to mercurial_ a few months ago, carrying the
history over. I seem to have 189 commits/changesets, of which
154 are on the qtrx files (others are on the makefile and
related scripts). So that's about one commit every two weeks.


.. QIF_: @@
.. instructions_: @@
.. mercurial_: Mercurial Distributed SCM (version 414e81ae971f)
               Copyright (C) 2005 Matt Mackall <mpm@selenic.com>

Usage
-----

The main methods are is eachFile() and eachTrx().

Future Work
-----------

  - support some SPARQL: date range, text matching
   - the sink.transaction method is like a SPARQL describe hit
    - how about a python datastructure to mirror turtle?
     - how does that relate to JSON?
      - and how does JSON relate to python pickles?
  - investigate diff/patch, sync with mysql DB; flag ambiguous transactions
  - QA
   - get back to pychecker happiness
   - check rst out, add Colophon

"""

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

def eachFile(files, sink):
    """Iterate over transactions in the files and send them to the sink.

    @param files: a list of files containing reports as above
    @param sink: something with a transaction() method.

    The transaction method gets called a la: sink.transaction(trxdata, splits).
    See eachTrx() for the structure of trxdata and splits.
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
	    sink.transaction(trx[0], trx[1])
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
    """Turn an iterator over lines into an interator over transactions

    >>> r=[]; d=iter(_TestLines); dummy=readHeader(d); \
    t=eachTrx(d, r); len(list(t))
    11

    >>> r=[]; d=iter(_TestLines); dummy=readHeader(d); \
    t=eachTrx(d, r); t.next()
    (['1/7/94', 'Texans Checks', '1237', 'Albertsons'], [['', '', '', '', '', 'Home', 'R', '-17.70']])
    """

    trx = None
    splits = []
    
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
                yield (trx, splits)
            splits = []
            trx = fields[:-4]
	    splits = [['', '', '', ''] + fields[-4:]]
        else:
            if fields[3].startswith("TOTAL"):
                if trx: yield (trx, splits)
                result.append(ln)
		return
            else:
                splits.append(fields)


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
    """@@ print statements should be replaced by unit tests
    """
    import sys
    for a in args:
        sys.stderr.write(str(a) + ' ')
    sys.stderr.write("\n")


def _test():
    import doctest
    return doctest.testmod()

if __name__ == '__main__':
    _test()
