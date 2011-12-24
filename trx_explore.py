import json
import pprint

import sqlalchemy
from bunch import Bunch

def explore(fp):
    data = json.load(fp)

    trxs = [Bunch.fromDict(o) for o in data]
    trxs.sort(key=lambda(tx): int(tx.id))
    pprint.pprint([(tx.id, tx.date,
                    (int(tx.amount.replace('$', '').\
                         replace(',', '').replace('.', '')) * (
                             -1 if tx.isDebit else 1), 100),
                    tx.amount, tx.isDebit) for tx in trxs])

    print "Labels:"
    pprint.pprint([(tx.id, l['id'], l['name'])
                   for tx in trxs
                   for l in tx.labels])

def explore_db(fn):
    e = sqlalchemy.create_engine('sqlite:///' + fn)
    show_tables(e)


def show_tables(engine):
    meta = sqlalchemy.MetaData()
    meta.reflect(bind=engine)
    for t in meta.tables:
        print t


def main(argv):
    dbfn = argv[1]
    print "dbfn:", dbfn
    explore_db(dbfn)
    #fn = argv[1]
    #fp = open(fn)
    #explore(fp)

if __name__ == '__main__':
    import sys
    main(sys.argv)
