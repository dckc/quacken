from trxtsv import trxiter
from trxht import trxdetails

from UserDict import DictMixin

import csv

def main(args):
    fnames = args[1:]
    txs = trxiter(fnames)
    normalize(txs, CSVDB())

def normalize(txs, db):
    # running ids for transactions, splits
    tid = 1
    sid = 1

    txw = db.mktable("transactions")
    splits = db.mktable("splits")
    accounts = NameTable("accounts")
    accounts.open(db)
    classes = NameTable("classes")
    classes.open(db)

    for trx in trxdetails(txs):
        tx = trx['trx']
        db.insert(txw,
                  (tid, accounts[tx['acct']],
                   tx['date'],
                   tx.get('payee', None),
                   tx.get('num', None),
                   tx.get('ty', None),
                   tx.get('memo', None)
                   ))
        
        for split in trx['splits']:

            # combine categories and transfer accounts
            a2 = split.get('acct', split.get('cat'))
            if 'class' in split:
                cls = classes[split['class']]
                if split['class'] == 'A]':
                    raise ValueError, trx
            else:
                cls = None
            db.insert(splits,
                      (sid, tid,
                       accounts[a2],
                       cls,
                       split.get('clr', None),
                       split.get('memo', None),
                       split['subtot']))
            sid += 1
        tid += 1



class CSVDB(object):
    def mktable(self, name):
        return csv.writer(open(name + ".csv", "wb"))

    def insert(self, t, row):
        t.writerow(row)


class NameTable(object, DictMixin):
    def __init__(self, name):
        self._name = name
        self._d = {}
        self._i = 1

    def open(self, db):
        self._db = db
        self._t = db.mktable(self._name)

    def __getitem__(self, k):
        d = self._d
        try:
            return d[k]
        except KeyError:
            v = self._i
            d[k] = v
            self._db.insert(self._t, (v, k))
            self._i += 1
            return v

    def keys(self):
        return self._d.keys()

    def __setitem__(self, k, v):
        raise RuntimeError

    def __delitem__(self, k):
        raise RuntimeError


def _test():
    import doctest
    doctest.testmod()
    
if __name__ == '__main__':
    import sys
    if '--test' in sys.argv: _test()
    else: main(sys.argv)
