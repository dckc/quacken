'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

from sqlalchemy import MetaData, Table, Column
from sqlalchemy.types import String
from sqlalchemy.engine.url import URL

from gckey import findMaker

log = logging.getLogger(__name__)

Name = String(80)


def main(argv, open_read, find_network_password_sync, create_engine):
    logging.basicConfig(level=logging.DEBUG)

    gdoc_csv, db = argv[1:3]

    engine = db_prepare(findMaker(find_network_password_sync),
                        create_engine, db)

    budget_load(open_read(gdoc_csv), engine)

    budget_sync_accounts(engine, dry_run='--accounts' not in argv)
    budget_sync_items(engine)


def db_prepare(findcreds, create_engine, db,
               host='localhost'):
    creds = findcreds(db)

    engine = create_engine(URL(drivername='mysql', host=host, database=db,
                               username=creds['user'],
                               password=creds['password']))

    log.info('dropping and creating %s',
             [t.name for t in GnuCashAux.sorted_tables])
    GnuCashAux.drop_all(engine)
    GnuCashAux.create_all(engine)

    return engine


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


def budget_sync_accounts(conn, dry_run=True):
    missing_acct = conn.execute('''
select bi.* from (
 select budget_name,
        STR_TO_DATE(bi.t_lo,'%%m/%%d/%%Y') t_lo,
        account_type, bi.code, parent, bi.name,
        1 * replace(replace(budget, '$', ''), ',', '') budget
 from budget_import bi
 where bi.code > '') bi
left join accounts a
on a.code=bi.code
where a.guid is null
''').fetchall()

    log.debug('missing_acct: %d', len(missing_acct))

    if missing_acct:
        log.warn('no such account code:\n%s',
                 format_rows(missing_acct))

    if dry_run:
        return

    raise NotImplemented


def format_rows(rows):
    return '\n'.join([str(row) for row in rows])


def budget_sync_items(conn):
    dups = conn.execute('''
select count(*), budget_name, t_lo, code
from budget_import
where code > ''
group by budget_name, t_lo, code
having count(*) > 1''').fetchall()
    log.debug('dups: %d', len(dups))

    if dups:
        log.error('duplicate keys in budget spreadsheet: %s',
                  format_rows(dups))
        raise IOError

    raise NotImplementedError


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
