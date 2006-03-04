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
my exported Quicken data, splitting it every few years:

    4785   38141  276520 1990-1996qtrx.txt
    6193   61973  432107 1997-1999qtrx.txt
    4307   46419  335592 2000qtrx.txt
    5063   54562  396610 2002qtrx.txt
    5748   59941  437710 2004qtrx.txt
   26096  261036 1878539 total

I switched from CVS to mercurial a few months ago, carrying the
history over. In total, I seem to have 189 commits/changesets.


.. QIF_: @@
.. instructions_: @@

Future Work
-----------

  - support some SPARQL: date range, text matching
  - investigate diff/patch, sync with mysql DB; flag ambiguous transactions

"""


def eachFile(files, sink):
    sink.startDoc()
    
    rtot = None
    rdate = None
    
    for fn in files:
        fp = open(fn)

        fieldNames, dt, bal = readHeader(fp)
        progress("header:" , fn, fieldNames, dt, bal)
        if rdate and dt <> rdate:
            raise IOError, "expected date " + rdate + " but got " + dt
        if rtot and bal <> rtot:
            raise IOError, "expected balance " + rtot + " but got " + bal
        sink.header(fieldNames, fn, dt, bal)
        ln = grokTransactions(fp, sink)
        foot = readFooter(fp, ln)
        progress("footer: ", fn, foot)
        dummy, (rdate, rtot), dummy, dummy, dummy = foot
    
    sink.close()

def readHeader(fp):
    while 1:
        # skip blank line at top
        hd = fp.readline().strip()
        if hd: break
    fieldNames = hd.split('\t')

    while 1:
        bal = fp.readline().strip()
        if bal: break
    dummy, dt, a = bal.split()
    dt = isoDate(dt)
    a = amt(a)

    hd = fp.readline().strip() # skip blank line
    if hd: raise IOError, "expected blank line; got" + hd
    
    return fieldNames, dt, a


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

def grokTransactions(fp, sink):
    trx = None
    splits = []
    
    while 1:
        ln = fp.readline()
        if not ln:
            raise IOError, 'unexpected end-of-file'
        if ln.endswith("\r\n"): ln = ln[:-2]
        elif ln.endswith("\n"): ln = ln[:-1]
        fields = ln.split('\t')

        #progress ("fields: ", fields)
        if fields[0]:
            if trx:
                sink.transaction(trx, splits)
            splits = []
            trx = fields
        else:
            if fields[3].startswith("TOTAL"):
                if trx: sink.transaction(trx, splits)
                return ln
            else:
                splits.append(fields)

    return None # is there a better way to make pychecker happy?

def readFooter(fp, ln):
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
            
        ln = fp.readline()
        if not ln: break
        

    return total, balance, inflows, outflows, nettot

    
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
