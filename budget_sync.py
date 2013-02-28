'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

from sqlalchemy import MetaData, Table, Column, func
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
                   Column('parent', Name),
                   Column('name', Name),
                   Column('budget', String(20)),  # amount
                   Column('notes', String(200)))


def budget_sync_accounts(conn, dry_run=True):
    missing_acct = conn.execute(
'''
select bi.parent, a.name, count(*) from
(select distinct parent from gdocs_budget
where code > '' and t_lo > '') bi
left join accounts a
       on a.name=bi.parent
group by bi.parent, a.name
having count(*) != 1
''').fetchall()

    log.debug('parent mismatch: %d', len(missing_acct))

    if missing_acct:
        log.error('parent mismatch:\n%s',
                  format_rows(missing_acct))
        raise IOError

    missing_acct_q = '''
select replace(uuid(), '-', '') as guid
     , bi.name, bi.account_type
     , usd.guid as commodity_guid
     , usd.fraction as commodity_scu, 0 as non_std_scu
     , ap.guid as parent_guid
     , bi.code
     , '' as description, 0 as hidden, 0 as placeholder
from (
  select distinct account_type, parent, name, code
  from gdocs_budget
  where code > '' ) bi
join accounts ap on ap.name = bi.parent
join commodities usd on usd.mnemonic = 'USD'
left join accounts a on a.code = bi.code
where a.guid is null
'''
    missing_acct = conn.execute(missing_acct_q).fetchall()

    log.debug('missing_acct: %d', len(missing_acct))

    if missing_acct:
        log.log(logging.ERROR if dry_run else logging.WARN,
                'no such account code:\n%s',
                format_rows(missing_acct))

        if dry_run:
            raise IOError

    raise NotImplemented

'''
insert into accounts
select replace(uuid(), '-', '') as guid
     , bi.name, bi.account_type
     , usd.guid as commodity_guid
     , usd.fraction as commodity_scu, 0 as non_std_scu
     , ap.guid as parent_guid
     , bi.code
     , bi.notes as description, 0 as hidden, 0 as placeholder
from (
  select distinct account_type, parent, name, code
  from gdocs_budget
  where code > '' ) bi
left join accounts a on a.code = bi.code
left join accounts ap on ap.name = bi.parent
join commodities usd on usd.mnemonic = 'USD'
where a.guid is null
'''


def format_rows(rows):
    return '\n'.join([str(row) for row in rows])


def budget_sync_items(conn):
    key_cols = [BudgetItem.budget_name,
                BudgetItem.t_lo,
                BudgetItem.code]
    dups = conn.execute(
        BudgetItem.select(key_cols + [func.count()]).
        group_by(key_cols).having(func.count() > 1)).fetchall()
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
