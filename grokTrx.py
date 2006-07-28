#!/usr/bin/python
""" grokTrx.py -- Quicken transaction report to RDF

Unlike previous approaches, we're not doing any
normalization here.

TODO:
 - reconcile namespace/schema with other quicken stuff; e.g.
   - dngr2qif
   - timbl's quicken/tax stuff.
 - capture test cases for current functionality:
  - checking balances across multiple files
  - building dm93.rdf (and down-stream XSLT-based expense reporting)
 - restructured text a la flightCal.py, bnf2turtle.py


"""

__version__ = '$Id: grokTrx.py,v 1.15 2006/03/06 05:40:45 connolly Exp $'

    
import XMLWriter # from swap http://www.w3.org/2002/12/cal/
from trxtsv import eachFile, isoDate, numField, amt


def main(argv):
    xwr = XMLWriter.T(sys.stdout)
    sink = TrxSink(xwr)
    eachFile(argv[1:], sink)


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
        xwr.characters(isoDate(trx['date']))
        xwr.endElement()

        xwr.startElement(Quacken.Account, {})
        xwr.characters(trx['acct'])
        xwr.endElement()

        num, splitmark, trxty = numField(trx.get('num', ''))
        if splitmark:
            xwr.startElement(Quacken.NumS, {})
            xwr.characters('S')
            xwr.endElement()
        if trxty:
            xwr.startElement(Quacken.NumT, {})
            xwr.characters(trxty)
            xwr.endElement()
        else:
            if num:
                xwr.startElement(Quacken.Num, {})
                xwr.characters(num)
                xwr.endElement()

        memo = trx.get('memo', None)
        if memo:
            xwr.startElement(Quacken.Description, {})
            xwr.characters(memo)
            xwr.endElement()

        xwr.startElement(Quacken.splits,
                         {'r:parseType': 'Collection'})
        for split in splits:
            #@@ redundant processing of the 'L' field
            memo, category, clr, a = split.get('memo', None), \
                                     split.get('L', ''), \
                                     split.get('clr', ''), \
                                     split.get('subtot', None)
            if a is None: continue # skip empty splits
            xwr.startElement(Quacken.Split, {})

            if memo:
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

	   
def _test():
    import doctest, grokTrx
    return doctest.testmod()

if __name__ == '__main__':
    import sys
    if sys.argv[1:] and sys.argv[1] == '--test': _test()
    else: main(sys.argv)
