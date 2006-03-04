"""
trxht -- format personal finance transactions as hCalendar

Usage
-----

Run a transaction report over *all* of your data in some date range
and put it in, say, _2004qtrx.txt_. Then invoke a la::

  $ python trxht.py 2004qtrx.txt  >,x.html
  $ xmlwf ,x.html
  $ firefox ,x.html

Future Work
-----------

 - add hCard support
  - pick out phone numbers, city/state names
  - support a form of payee smushing on label
 - make URIs for accounts, categories, classses

Colophon
--------

This document is (supposed to be) written in ReStructuredText_ (I
haven't tested it@@). The examples in the docstrings below are
executable doctest_ unit tests.  Check them a la::

  $ python trxht.py --test

.. _ReStructuredText: http://docutils.sourceforge.net/docs/user/rst/quickstart.html
.. _doctest: http://www.python.org/doc/lib/module-doctest.html

"""

from xml.sax.saxutils import escape as xmldata

from trxtsv import eachFile, isoDate, numField

def main(argv):
    sink = TrxDocSink(sys.stdout.write)
    eachFile(argv[1:], sink)

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
  <style type="text/css">
tbody.vevent tr.trx td { border-top: 1px solid }
tbody.vevent td { padding: 3px; margin: 0}
.amt { text-align: right }
.even { background: grey }
</style>

""")
	w(" <title>@@</title>\n")
	w("</head>\n<body>\n")

    def header(self, fn, fieldNames, dt, bal):
	w = self._w
	w(" <h1>Transactions</h1>\n")
	w(" <p>starting date: %s bal: %s</p>" % (dt, bal))
	w(" <table>\n")
	self._row = 0 # don't let tables grow without bound

    def transaction(self, trx, splits):
	w = self._w

	if self._row > 100:
	    w("</table>\n<table>\n")
	    self._row = 0
	else:
	    self._row += 1

	date, acct, num, desc = trx[:4]
	datei = isoDate(date)
	w("<tbody class='vevent'>\n")
	w(" <tr class='trx'><td><abbr class='dtstart %s' title='%s'>%s</abbr>"
	  "</td>\n" % (parity(datei), datei, date))

	num, splitflag, trxty = numField(num)
	w("<td>%s</td> <td>%s</td> <td>%s</td></tr>\n" %
	  (xmldata(desc), num or trxty or '', acct))
        splits.insert(0, ['', '', '', ''] + trx[-4:])
        for d1, d2, d3, d4, memo, category, clr, a in splits:
	    w("<tr class='split'><td></td><td>%s</td><td>%s</td>"
	      "<td>%s</td><td class='amt'>%s</td></tr>\n" %
	      (xmldata(memo), clr, xmldata(category), a))
	w("</tbody>\n\n")

    def close(self):
	w = self._w
	w(" </table>\n</body>\n</html>")


def parity(ymd):
    """
    >>> parity("2005-11-12")
    'even'
    >>> parity("2005-11-13")
    'odd'
    """
    parity = int(ymd[-1]) % 2
    return ("even", "odd")[parity]


def _test():
    import doctest
    return doctest.testmod()

if __name__ == '__main__':
    import sys
    if sys.argv[1:] and sys.argv[1] == '--test': _test()
    else: main(sys.argv)
