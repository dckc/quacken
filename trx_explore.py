import json
import pprint

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer, String, Boolean
from bunch import Bunch

Base = declarative_base()


def explore(fp):
    data = json.load(fp)

    cols = set([k for item in data for k in item.keys()])
    print "columns"
    pprint.pprint(cols)

    #trxs = [Bunch.fromDict(o) for o in data]
    trxs = [mktrx(o) for o in data]                           

    trxs.sort(key=lambda(tx): tx.id)
    pprint.pprint(trxs)

    print "Labels:"
    pprint.pprint([(tx['id'], l['id'], l['name'])
                   for tx in data
                   for l in tx['labels']])

def mktrx(o):
    fields = dict([(str(k), v)  # **args can't be unicode
                   for k, v in o.iteritems()
                   if k != 'id' and k in MintTrx.__dict__.keys()])

    amount_num=int(o['amount'].replace('$', '').\
                   replace(',', '').replace('.', '')) \
                   * (-1 if o['isDebit'] == 'True' else 1)
                           
    
    return MintTrx(**dict(fields, id=int(o['id']), amount_num=amount_num))


def explore_db(fn):
    e = sqlalchemy.create_engine('sqlite:///' + fn)
    show_tables(e)


def show_tables(engine):
    meta = sqlalchemy.MetaData()
    meta.reflect(bind=engine)
    for t in meta.tables:
        print t


class MintTrx(Base):
    __tablename__ = 'minttrx'

    id = Column(Integer, primary_key=True)

    account = Column(String)
    amount = Column(String)
    amount_num = Column(Integer)  # assuming 100 denominator
    category = Column(String)
    categoryId = Column(String)
    date = Column(String)
    fi = Column(String)
    #inlineadviceid = Column(String)
    #isAfterFiCreationTime = Column(String)
    isCheck = Column(Boolean)
    isChild = Column(Boolean)
    isDebit = Column(Boolean)
    isDuplicate = Column(Boolean)
    isEdited = Column(Boolean)
    #isFirstDate = Column(String)
    #isLinkedToRule = Column(String)
    #isMatched = Column(String)
    isPending = Column(Boolean)
    #isSpending = Column(String)
    isTransfer = Column(Boolean)
    #labels = Column(String)
    #manualType = Column(String)
    mcategory = Column(String)
    merchant = Column(String)
    mmerchant = Column(String)
    note = Column(String)
    #numberMatchedByRule = Column(String)
    odate = Column(String)
    omerchant = Column(String)
    #ruleCategory = Column(String)
    #ruleCategoryId = Column(String)
    #ruleMerchant = Column(String)
    #txnType = Column(String)


def mk_cols():
    names = [u'account',
             u'amount',
             u'category',
             u'categoryId',
             u'date',
             u'fi',
             u'id',
             u'inlineadviceid',
             u'isAfterFiCreationTime',
             u'isCheck',
             u'isChild',
             u'isDebit',
             u'isDuplicate',
             u'isEdited',
             u'isFirstDate',
             u'isLinkedToRule',
             u'isMatched',
             u'isPending',
             u'isSpending',
             u'isTransfer',
             u'labels',
             u'manualType',
             u'mcategory',
             u'merchant',
             u'mmerchant',
             u'note',
             u'numberMatchedByRule',
             u'odate',
             u'omerchant',
             u'ruleCategory',
             u'ruleCategoryId',
             u'ruleMerchant',
             u'txnType']
    for n in names:
        print "    %s = Column(String)" % n

def main_(argv):
    dbfn = argv[1]
    print "dbfn:", dbfn
    explore_db(dbfn)

def main(argv):
    fn = argv[1]
    fp = open(fn)
    explore(fp)

if __name__ == '__main__':
    import sys
    main(sys.argv)
