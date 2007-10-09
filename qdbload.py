"""qdbload.py -- normalize quicken data and load into SQL DB

Usage
-----

Run a transaction report over *all* of your data in some date range
and print it to a tab-separated file, say, ``2004qtrx.txt``. Then
invoke a la::

  $ python qdbload.py 2004qtrx.txt

to produce normalized data in csv files: accounts, transactions, splits,
and classes.

Using qdb.sql (derived from qdb.html; see Makefile for details)
you can load it into a sqlite databse::

  $ python qdbload.py --sqlite qdb1 --schema qdb.sql 2004qtrx.txt

As with trxht.py, you may give multiple files, as long as the ending
balance of one matches the starting balance of the next.


"""

from trxtsv import trxiter, isoDate
from trxht import trxdetails

from UserDict import DictMixin

import csv

def main(args):
    import getopt

    db = CSVDB()
    opts, args = getopt.getopt(args[1:], "", ["sqlite=", "schema=", "prefix="])
    for o, a in opts:
        if o == '--sqlite':
            db = SQLiteDB(a)
        elif o == '--prefix':
            db.prefix(a)
        elif o == '--schema':
            db.loadSchema(a)

    print "normalizing data from files:", args

    txs = trxiter(args)
    normalize(txs, db)


def normalize(txs, db):
    # running ids for transactions, splits
    tid = 1
    sid = 1

    txw = db.mktable("Transaction")
    splits = db.mktable("Split")
    accounts = NameTable("Account")
    accounts.open(db)
    classes = NameTable("Job")
    classes.open(db)

    for trx in trxdetails(txs):
        tx = trx['trx']
        db.insert(txw,
                  # django adds _id to ref fields
                  ('id', 'acct_id', 'date', 'payee', 'num', 'ty', 'memo'),
                  (tid, accounts[tx['acct']],
                   isoDate(tx['date']),
                   tx.get('payee', None),
                   tx.get('num', None),
                   tx.get('ty', None),
                   tx.get('memo', None)
                   ))
        
        for split in trx['splits']:

            # combine categories and transfer accounts
            a2 = split.get('acct', split.get('cat'))
            if a2: a2 = accounts[a2]
            if 'class' in split:
                cls = classes[split['class']]
            else:
                cls = None
            db.insert(splits,
                      ('id', 'trx_id', 'acct_id',
                       'job_id', 'clr', 'memo', 'subtot'),
                      (sid, tid,
                       a2, cls,
                       split.get('clr', None),
                       split.get('memo', None),
                       split['subtot']))
            sid += 1
        tid += 1
    db.commit()


class NameTable(object, DictMixin):
    def __init__(self, name):
        self._name = name
        self._d = {}
        self._i = 1

    def open(self, db):
        self._db = db
        self._t = db.mktable(self._name)

    def __getitem__(self, k):
        assert k is not None
        d = self._d
        try:
            return d[k]
        except KeyError:
            v = self._i
            d[k] = v
            self._db.insert(self._t, ('id', 'name'), (v, k))
            self._i += 1
            return v

    def keys(self):
        return self._d.keys()

    def __setitem__(self, k, v):
        raise RuntimeError

    def __delitem__(self, k):
        raise RuntimeError


class CSVDB(object):
    def mktable(self, name):
        return csv.writer(open(name + ".csv", "wb"))

    def insert(self, t, fields, row):
        t.writerow(row)

    def commit(self):
        pass

class SQLiteDB(object):
    
    def __init__(self, name):
        import sqlite3
        self._cx = sqlite3.connect(name)
        self._pfx = ''

        from decimal import Decimal
        sqlite3.register_adapter(Decimal, str)

        
    def prefix(self, pfx):
        self._pfx = pfx
        
    def loadSchema(self, schemafn):
        cur = self._cx.cursor()
        for stmt in open(schemafn).read().split(";"):
            cur.execute(stmt)
        self._cx.commit()
        
    def mktable(self, name):
        return self._pfx + name

    def insert(self, t, fields, row):
        cur = self._cx.cursor()
        cur.execute(asSQL(t, fields), row)

    def commit(self):
        self._cx.commit()

def asSQL(t, fields):
    """
    >>> asSQL("things", ('size', 'weight', 'length'))
    'insert into things (size, weight, length) values (?, ?, ?)'
    """
    return "insert into %s (%s) values (%s)" % \
                    (t,
                     ", ".join(fields),
                     ", ".join(['?'] * len(fields)))

def _test():
    import doctest
    doctest.testmod()
    
if __name__ == '__main__':
    import sys
    if '--test' in sys.argv: _test()
    else: main(sys.argv)
