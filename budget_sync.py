'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

from sqlalchemy import MetaData, Table, Column
from sqlalchemy.types import String, DECIMAL
from sqlalchemy.engine.url import URL

from gckey import findMaker

log = logging.getLogger(__name__)

Money = DECIMAL(precision=8, scale=2)
Name = String(80)


def main(argv, open_read, find_network_password_sync, create_engine,
         host='localhost'):
    logging.basicConfig(level=logging.DEBUG)

    gdoc_csv, db = argv[1:3]

    creds = findMaker(find_network_password_sync)(db)

    engine = create_engine(URL(drivername='mysql', host=host, database=db,
                               username=creds['user'],
                               password=creds['password']))

    log.info('dropping and creating %s',
             [t.name for t in GnuCashAux.sorted_tables])
    GnuCashAux.drop_all(engine)
    GnuCashAux.create_all(engine)

    budget_load(open_read(gdoc_csv), engine)

    raise NotImplementedError


def budget_load(infp, conn):
    sheet = csv.DictReader(infp)
    rows = list(sheet)
    log.info('inserting %d rows into %s', len(rows), BudgetItem)
    conn.execute(BudgetItem.insert(), rows)


GnuCashAux = MetaData()
BudgetItem = Table('gdocs_budget', GnuCashAux,
                   Column('budget_name', Name),
                   Column('t_lo', String(40)),  # date
                   Column('account_type', Name),
                   Column('code', Name),
                   Column('name', Name),
                   Column('budget', String(20)),  # amount
                   Column('notes', String(200)))


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
    def _initial_caps():
        from sys import argv
        import gnomekeyring as gk
        from sqlalchemy import create_engine

        def open_read(n):
            return open(n)

        return dict(argv=argv,
                    find_network_password_sync=gk.find_network_password_sync,
                    create_engine=create_engine,
                    open_read=open_read)

    main(**_initial_caps())
