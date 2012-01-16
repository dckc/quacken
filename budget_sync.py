'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer, String, DECIMAL

Base = declarative_base()
Session = sqlalchemy.orm.sessionmaker()

log = logging.getLogger(__name__)

Money = DECIMAL(precision=8, scale=2)
Name = String(80)


def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    infn, engine_url = argv[1:3]

    engine = budget_setup(engine_url)
    def add_row(r):
        engine.execute(BudgetItem.__table__.insert(), r)
    budget_load(open(infn), add_row)


def budget_load(infp, insert_fn,
                budget_name='2012 H1',
                budget_start=(2012, 1), periods=6,
                monthly_header='Monthly 2012',
                period0_header='Jan 2012'):
    sheet = csv.reader(infp)
    schema = sheet.next()
    monthly_col = schema.index(monthly_header)
    period0_col = schema.index(period0_header)
    id_col = schema.index('id')

    for row in sheet:
        log.debug('input row: %s', row)
        if len(row) < monthly_col + 1:
            continue
        acct_id = row[id_col]
        if not acct_id:
            continue
        subcat = row[id_col - 1]
        cat = row[id_col - 2]

        monthly_money = money(row[monthly_col])
        for p in range(0, periods):
            amt = add_money(monthly_money, (money(row[period0_col + p])
                                            if period0_col + p < len(row)
                                            else (0, 1)))

            if amt[0] > 0:
                insert_fn(dict(id=None,
                               budget=budget_name,
                               cat=cat, subcat=subcat, acct_id=acct_id,
                               period=p,
                               amount_num=amt[0], amount_denom=amt[1]))


def budget_setup(engine_url):
    engine = sqlalchemy.create_engine(engine_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


class BudgetItem(Base):
    __tablename__ = 'gdocs_budget'
    id = Column(Integer, primary_key=True)
    budget = Column(Name)
    cat = Column(Name)
    subcat = Column(Name)
    acct_id = Column(Integer)
    period = Column(Integer)
    amount_num = Column(Integer)
    amount_denom = Column(Integer)


def money(txt):
    '''
    >>> money('$8,454.00')
    (8454, 1)
    >>> money('60')
    (60, 1)
    >>> money('256.69')
    (25669, 100)
    '''
    try:
        amt = int(float(txt.replace('$', '').replace(',', '')) * 100)
    except ValueError:
        return 0, 1

    if amt % 100 == 0:
        return amt / 100, 1
    else:
        return amt, 100

def add_money((xn, xd), (yn, yd)):
    if xd == yd:
        return xn + yn, xd
    else:
        n = xn * (100 / xd) + yn * (100 / yd)
        if n % 100 == 0:
            return n / 100, 1
        else:
            return n, 100


if __name__ == '__main__':
    import sys
    main(sys.argv)
