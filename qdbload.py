from trxtsv import trxiter
from trxht import trxdetails

from UserDict import DictMixin

import csv

def main(args):
    fnames = args[1:]
    txs = trxiter(fnames)
    normalize(txs)

def normalize(txs):
    # running ids for transactions, splits
    tid = 1
    sid = 1

    txw = csv.writer(open("transactions.csv", "wb"))
    splits = csv.writer(open("splits.csv", "wb"))
    accounts = nametable("accounts")
    accounts.open()
    classes = nametable("classes")
    classes.open()

    for trx in trxdetails(txs):
        tx = trx['trx']
        txw.writerow((tid, accounts[tx['acct']],
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
            else:
                cls = None
            splits.writerow((sid, tid,
                             accounts[a2],
                             cls,
                             split.get('clr', None),
                             split.get('memo', None),
                             split['subtot']))
            sid += 1
        tid += 1


class nametable(object, DictMixin):
    def __init__(self, name):
        self._name = name
        self._d = {}
        self._i = 1

    def open(self):
        self._wr = csv.writer(open(self._name + ".csv", "wb"))

    def __getitem__(self, k):
        d = self._d
        try:
            return d[k]
        except KeyError:
            v = self._i
            d[k] = v
            self._wr.writerow((v, k))
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
