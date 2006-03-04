#!/usr/bin/python
""" grokTrx.py -- Quicken transaction report to RDF

Unlike previous approaches, we're not doing any
normalization here.

TODO: reconcile namespace/schema with other
quicken stuff; e.g.
 - dngr2qif
 - timbl's quicken/tax stuff.

$Id: grokTrx.py,v 1.14 2004/06/11 00:52:05 connolly Exp $
"""

from xml.sax.saxutils import escape as xmldata

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

def amt(s):
    """grok amount

    don't convert to float due to rounding

    >>> amt("728,052.11")
    '728052.11'

    """
    s = s.replace(',', '')
    assert float(s) is not None
    return s

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


class Namespace:
    def __init__(self, n):
        self._n = n

    def setPrefix(self, p):
        #KLUDGE
        self._p = p

    def __getattr__(self, ln):
        if ln.startswith("__"):
            raise AttributeError
        return self._p + ':' + ln

    def __str__(self):
        return self._n

    def attr(self, ln):
        return self._p + ':' + ln

    def decl(self, pfx):
        return {self._n: pfx}

RDF = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
Quacken = Namespace('http://dev.w3.org/cvsweb/2000/quacken/vocab#')

RDF.setPrefix('r')
Quacken.setPrefix('q')

class TrxSink:

    def __init__(self, xwr):
        self._wr = xwr

    def startDoc(self):
        xwr = self._wr
        xwr.startElement(RDF.RDF,
                         {'xmlns:r': str(RDF),
                          'xmlns:q': str(Quacken)})

    def header(self, fn, fieldNames, dt, bal):
        self._fieldNames = fieldNames
        xwr = self._wr

        xwr.startElement(RDF.Description,
                         {'r:about': ""})
        xwr.startElement(Quacken.startingDate, {}) #@@ add to schema
        xwr.characters(dt)
        xwr.endElement()
        xwr.startElement(Quacken.startingBalance, {})
        xwr.characters(str(bal))
        xwr.endElement()
        xwr.endElement()

    def transaction(self, trx, splits):
        xwr = self._wr
        xwr.startElement(Quacken.Trx, {})

        #@@use self._fieldNames
        xwr.startElement(Quacken.Date, {})
        xwr.characters(isoDate(trx[0]))
        xwr.endElement()

        xwr.startElement(Quacken.Account, {})
        xwr.characters(trx[1])
        xwr.endElement()

        num = trx[2]
        if num.endswith(' S'):
            # ah... this just means split transaction. redundant.
            num=num[:-1].strip()
            xwr.startElement(Quacken.NumS, {})
            xwr.characters('S')
            xwr.endElement()
        if num in ('ATM', 'DEP', 'Deposit', 'EFT', 'TXFR'):
            xwr.startElement(Quacken.NumT, {})
            xwr.characters(num)
            xwr.endElement()
        else:
            if num:
                xwr.startElement(Quacken.Num, {})
                xwr.characters(num)
                xwr.endElement()

        xwr.startElement(Quacken.Description, {})
        xwr.characters(trx[3])
        xwr.endElement()

        splits.insert(0, ['', '', '', ''] + trx[-4:])

        xwr.startElement(Quacken.splits,
                         {'r:parseType': 'Collection'})
        for d1, d2, d3, d4, memo, category, clr, a in splits:
            if a == '': continue # skip empty splits
            xwr.startElement(Quacken.Split, {})

            xwr.startElement(Quacken.Memo, {})
            xwr.characters(memo)
            xwr.endElement()

            xwr.startElement(Quacken.Class, {})
            if category.find('/') >= 0:
                category, cls = category.split('/')
                xwr.characters(cls)
            else:
                xwr.characters('')
            xwr.endElement()
            if category.startswith('['):
                xwr.startElement(Quacken.Account, {})
                xwr.characters(category[1:-1])
                xwr.endElement()
            else:
                xwr.startElement(Quacken.Category, {})
                xwr.characters(category)
                xwr.endElement()
            
            xwr.startElement(Quacken.Clr, {})
            xwr.characters(clr)
            xwr.endElement()

            xwr.startElement(Quacken.Amount, {})
            xwr.characters(amt(a))
            xwr.endElement()

            xwr.endElement()

        xwr.endElement()

        xwr.endElement()


    def close(self):
        xwr = self._wr
        xwr.endElement() # close r:RDF


class TrxDocSink:
    """Write transactions as XHTML using microformats
    """

    def __init__(self, w):
	"""@param : a writer function, such as f.write
	"""
	self._w = w

    def startDoc(self):
	w = self._w
	w("""<?xml version="1.0" encoding="utf-8"?><!--*- nxml -*-->
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
       "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head profile="http://www.w3.org/2003/g/data-view
		 http://purl.org/NET/erdf/profile">
  <link rel="transformation" href="http://www.w3.org/2002/12/cal/glean-hcal.xsl"/>
""")
	w(" <title>@@</title>\n")
	w("</head>\n<body>\n")

    def header(self, fn, fieldNames, dt, bal):
	w = self._w
	w(" <h1>Transactions</h1>\n")
	w(" <p>starting date: %s bal: %s</p>" % (dt, bal))
	w(" <ul>\n")

    def transaction(self, trx, splits):
	w = self._w
	w("  <li class='vevent'>")
	date, acct, num, desc = trx[:4]
	w("<abbr class='dtstart' title='%s'>%s</abbr>\n" % (isoDate(date), date))
	w("<em>%s</em> <tt>%s</tt> <b>%s</b>\n" % (acct, num, xmldata(desc)))
        splits.insert(0, ['', '', '', ''] + trx[-4:])
	w("<ul>")
        for d1, d2, d3, d4, memo, category, clr, a in splits:
	    w("<li>@@%s</li>\n" % (xmldata(str((memo, category, clr, a),))))
	w("</ul>")
	w("</li>")

    def close(self):
	w = self._w
	w(" </ul>\n</body>\n</html>")

	   
def progress(*args):
    import sys
    for a in args:
        sys.stderr.write(str(a) + ' ')
    sys.stderr.write("\n")


def main(argv):
    """open 1st arg as input
    (we don't use stdin for the sake of debugging)
    """

    import sys
    if len(argv) > 1 and argv[1] == '--mf':
	sink = TrxDocSink(sys.stdout.write)
	del argv[1]
    else:
	# from swap http://www.w3.org/2002/12/cal/
	import XMLWriter
	xwr = XMLWriter.T(sys.stdout)
	sink = TrxSink(xwr)
    sink.startDoc()
    
    rtot = None
    rdate = None
    
    for fn in argv[1:]:
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

def _test():
    import doctest, grokTrx
    return doctest.testmod(grokTrx)

if __name__ == '__main__':
    import sys
    if sys.argv[1:] and sys.argv[1] == '--test': _test()
    else: main(sys.argv)
