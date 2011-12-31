'''trx_explore -- migrate Mint transactions to gnucash

.. todo:: migrate notes
.. todo:: migrate edited descriptions

Things about Mint that I'm likely to miss:
  - simple, comprehensive search
  - budget report showing difference
  - trends by month
    - not to mention 2d breakdowns from Quicken
'''

import json
import pprint
import logging
import datetime
import warnings

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer, String, Boolean, Date, DECIMAL

log = logging.getLogger(__name__)

Money = DECIMAL(precision=8, scale=2)
FreeText = String(250)
TagList = String(250)
Name = String(80)

Base = declarative_base()
Session = sqlalchemy.orm.sessionmaker()


def explore(fp):
    data = json.load(fp)
    pprint.pprint(data)
    #all_cols(data)
    #show_labels(data)


def load(fp, engine):
    data = json.load(fp)

    try:
        MintTrx.__table__.drop(bind=engine)
    except:
        pass

    try:
        MintTag.__table__.drop(bind=engine)
    except:
        pass

    Base.metadata.create_all(engine)
    s = Session(bind=engine)

    # parents may be repeated in data, so convert to dict
    for o in dict([(o['id'], o) for o in data]).values():
        s.add(mktrx(o))

    for trx, label, name in [(tx['id'], l['id'], l['name'])
                             for tx in data
                             for l in tx['labels']]:
        s.add(MintTag(trx=trx, label=label, name=name))

    s.commit()

    return s


def show_stats(s, limit=15):
    pprint.pprint(s.execute('''
        select count(*), merchant
        from minttrx
        group by merchant
        order by 1 desc
        ''').fetchmany(limit))
    pprint.pprint(s.execute('''
        select count(*), label, name
        from minttag
        group by label, name
        order by 1 desc
        ''').fetchmany(limit))



def show_labels(data):
    print "Labels:"
    pprint.pprint([(tx['id'], l['id'], l['name'])
                   for tx in data
                   for l in tx['labels']])


MONTHS = [datetime.date(2011, m, 1).strftime('%b') for m in range(1, 13)]

def mktrx(o):
    fields = dict([(str(k), v)  # **args can't be unicode
                   for k, v in o.iteritems()
                   if k in MintTrx.__dict__.keys()])

    amount=float(o['amount'].replace('$', '').replace(',', ''))

    this_year = datetime.date.today().year
    return MintTrx(**dict(fields,
                          date=mkdate(o['date'], this_year),
                          amount=amount,
                          children=len(o.get('children', [])) or None))


def mkdate(txt, this_year):
    '''
    >>> mkdate('Nov 21', 2011)
    datetime.date(2011, 11, 21)

    >>> mkdate('12/30/10', 2011)
    datetime.date(2010, 12, 30)

    >>> mkdate('12/30/56', 2011)
    datetime.date(1956, 12, 30)
    '''
    if txt[0].isdigit():
        m, d, yy = [int(numeral) for numeral in txt.split('/')]
        century = this_year - (this_year % 100) - (100 if yy > 50 else 0)
        y = century + yy
    else:
        y = this_year
        m = MONTHS.index(txt[:3]) + 1
        d = int(txt[4:])
    return datetime.date(y, m, d)


def explore_db(fn):
    e = sqlalchemy.create_engine('sqlite:///' + fn)
    show_tables(e)


def show_tables(engine):
    meta = sqlalchemy.MetaData()

    with warnings.catch_warnings():
        warnings.simplefilter("module")
        # "Did not recognize type 'BIGINT' of column .*")
        meta.reflect(bind=engine)
    for t in meta.tables:
        print t


class MintTrx(Base):
    __tablename__ = 'minttrx'

    id = Column(Integer, primary_key=True)

    account = Column(Name)
    amount = Column(Money, nullable=False)
    category = Column(Name, nullable=False)
    categoryId = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    fi = Column(Name)
    #inlineadviceid = Column(String)
    #isAfterFiCreationTime = Column(String)
    isCheck = Column(Boolean)
    isChild = Column(Boolean, nullable=False)
    parent = Column(Integer)
    children = Column(Integer)  # normalized a bit
    isDebit = Column(Boolean, nullable=False)
    isDuplicate = Column(Boolean, nullable=False)
    isEdited = Column(Boolean)
    #isFirstDate = Column(String)
    #isLinkedToRule = Column(String)
    #isMatched = Column(String)
    isPending = Column(Boolean)
    isSpending = Column(Boolean)
    isTransfer = Column(Boolean)
    #labels = Column(String)
    #manualType = Column(String)
    mcategory = Column(Name)
    merchant = Column(FreeText)
    mmerchant = Column(FreeText)
    note = Column(FreeText)
    #numberMatchedByRule = Column(String)
    odate = Column(Name)
    omerchant = Column(FreeText, nullable=False)
    #ruleCategory = Column(String)
    #ruleCategoryId = Column(String)
    #ruleMerchant = Column(String)
    #txnType = Column(String)


class MintAcct(Base):
    __tablename__ = 'mintacct'
    id = Column(Integer, primary_key=True)
    #kind = Column(Enum('A', 'L', 'I', 'E', 'Q'), primary_key=True)
    name = Column(Name)


class MintTag(Base):
    __tablename__ = 'minttag'
    id = Column(Integer, primary_key=True)
    trx = Column(Integer)  # ForeignKey...
    label = Column(Integer)  # ForeignKey...
    name = Column(Name)


def all_cols(data):
    cols = set([k for item in data for k in item.keys()])
    print "columns"
    pprint.pprint(cols)


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


def match(engine):
    with warnings.catch_warnings():
        #warnings.filterwarnings("once",
        #                        "Did not recognize type 'BIGINT' of column .*")
        warnings.simplefilter("ignore")
        Base.metadata.reflect(bind=engine)

    # TODO: consider matching on account id rather than name.

    engine.execute('drop table if exists acctmatch')
    engine.execute('''
    create table acctmatch as
    select sp.guid split_guid, tx.guid tx_guid, mtx.id mint_tx_id
         , mtx.amount_num, mtx.categoryId, mtx.category
    from splits sp
    join transactions tx on sp.tx_guid = tx.guid
    join accounts acct on sp.account_guid = acct.guid,
    minttrx mtx
    where mtx.account = acct.name
      and mtx.isChild = 0 and mtx.isDuplicate = 0
      and mtx.amount_num = sp.quantity_num
      and substr(tx.post_date, 5, 4) = mtx.date_yymm
    ''')
#      and substr(mtx.omerchant, 1, 20) = substr(tx.description, 1, 20)

    engine.execute('drop table if exists catmatch')
    engine.execute('''
    create table catmatch as
    select sp.guid split_guid, acct.guid account_guid, acctmatch.mint_tx_id
    from transactions tx
    join acctmatch on acctmatch.tx_guid = tx.guid
    join splits sp on sp.tx_guid = tx.guid
     and sp.quantity_num = -acctmatch.amount_num
    join accounts acct on acctmatch.category = acct.name
    ''')

    ans = engine.execute('''
        select count(*), split_guid
        from catmatch
        group by catmatch.split_guid
        having count(*) > 1
        ''')
    dups = ans.fetchall()
    log.warn('dups: %d\n %s', len(dups), pprint.pformat(dups))
    if len(dups) > 0:
        log.warn('catmatch:\n%s', pprint.pformat(
            engine.execute('''
                select mtx.*
                from minttrx mtx
                join catmatch on mtx.id = catmatch.mint_tx_id
                join (
                  select count(*), split_guid
                  from catmatch
                  group by catmatch.split_guid
                  having count(*) > 1) dups
                  on dups.split_guid = catmatch.split_guid
                order by mtx.id''') \
            .fetchall()))
        
    ans = engine.execute(
    '''
    select mtx.date, tx.post_date, tx.description, sp.quantity_num
         , acct_old.name, acct_new.name
    from catmatch
    join splits sp on sp.guid = catmatch.split_guid
    join transactions tx on sp.tx_guid = tx.guid
    join accounts acct_old on acct_old.guid = sp.account_guid
    join accounts acct_new on acct_new.guid = catmatch.account_guid
    join minttrx mtx on mtx.id = catmatch.mint_tx_id
    order by tx.post_date
    ''')
    rows = ans.fetchall()
    log.info('matches: %d\n %s', len(rows), pprint.pformat(rows))

    if len(dups) == 0:
        engine.execute('''
        update splits
        set account_guid = (
          select account_guid from catmatch
          where catmatch.split_guid = guid )
        where guid in (select split_guid from catmatch)
        ''')

    engine.execute('drop table if exists splitmatch')
    engine.execute('''
        create table splitmatch as
        select ms.date, tx.post_date
             , sp.quantity_num, mtx.amount_num, mtx.category
             , mtx.id mint_tx_id
             , sp.guid split_guid
             , tx.guid tx_guid
        from (
          select mtx.date, mtx.date_yymm, mtx.account, sum(mtx.amount_num) tot
          from minttrx mtx
          where mtx.isChild = 1
          group by account, date) ms

        join splits sp on sp.quantity_num = ms.tot
        join transactions tx on sp.tx_guid = tx.guid
         and substr(tx.post_date, 5, 4) = ms.date_yymm
        join accounts acct_old on acct_old.guid = sp.account_guid
        join minttrx mtx
          on mtx.date = ms.date
         and mtx.account = ms.account
         and mtx.isChild = 1
        ''')
    ans = engine.execute('''select * from splitmatch order by post_date''')
    log.warn('split matches:\n%s', pprint.pformat(ans.fetchall()))

    ans = engine.execute(
    '''
    select mtx.date,mtx.omerchant,mtx.category,mtx.amount
         , mtx.isChild, mtx.isTransfer, mtx.isPending
    from minttrx mtx
    left join catmatch on catmatch.mint_tx_id = mtx.id
    left join splitmatch on splitmatch.mint_tx_id = mtx.id
    where catmatch.split_guid is null
      and splitmatch.split_guid is null
      and mtx.category != 'Exclude From Mint'
      and mtx.isPending != 1 and mtx.isDuplicate != 1
    order by mtx.id
    ''')
    rows = ans.fetchall()
    log.warn('mismatches: %d\n %s', len(rows), pprint.pformat(rows))

    ans = engine.execute('''
        select distinct mtx.categoryId as id, mtx.category as name
        from minttrx mtx
        left join catmatch on catmatch.mint_tx_id = mtx.id
        left join splitmatch on splitmatch.mint_tx_id = mtx.id
        where catmatch.split_guid is null
          and splitmatch.split_guid is null
          and mtx.category != 'Exclude From Mint'
          and mtx.isPending != 1 and mtx.isDuplicate != 1
        order by mtx.category
        ''')
    log.warn('missing categories: %s', pprint.pformat(ans.fetchall()))


def main(argv):
    logging.basicConfig(level=logging.WARN)

    if '--explore' in argv:
        trxfn = argv[2]
        explore(open(trxfn))
    elif '--load' in argv:
        trxfn, dburl = argv[2:4]
        s = load(open(trxfn),
                 sqlalchemy.create_engine(dburl))
        show_stats(s)
    elif '--match' in argv:
        dbfn = argv[2]
        match(sqlalchemy.create_engine('sqlite:///' + dbfn))

if __name__ == '__main__':
    import sys
    main(sys.argv)
