'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

from sqlalchemy import (MetaData, Table, Column,
                        select, func, text)
from sqlalchemy.types import String, Date, Integer
from sqlalchemy.engine.url import URL

from gckey import findMaker

log = logging.getLogger(__name__)

Name = String(80)


def main(argv, open_read, find_network_password_sync, create_engine,
         level=logging.DEBUG, host='localhost'):
    logging.basicConfig(level=level)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    gdoc_csv, db = argv[1:3]

    findcreds = findMaker(find_network_password_sync)
    log.info('getting keyring info for %s', db)
    creds = findcreds(db)
    engine = create_engine(URL(drivername='mysql', host=host, database=db,
                               username=creds['user'],
                               password=creds['password']))

    budget = Budget(engine)
    budget.load(open_read(gdoc_csv))

    budget.check_dups()
    budget.sync_accounts(dry_run='--accounts' not in argv)
    budget.sync_items()


GnuCashAux = MetaData()
BudgetItem = Table('gdocs_budget', GnuCashAux,
                   Column('budget_name', Name),
                   Column('t_lo', String(40)),
                   Column('lo', Date),  # date
                   Column('account_type', Name),
                   Column('code', Name),
                   Column('parent', Name),
                   Column('name', Name),
                   Column('budget', String(20)),
                   Column('amount_num', Integer),
                   Column('notes', String(200)))

BudgetTypeUpdate = text('''
 update gdocs_budget
 set lo = STR_TO_DATE(t_lo,'%m/%d/%Y'),
     amount_num = 100 * replace(replace(budget, '$', ''), ',', '')
 where code > '' and t_lo > ''
''')


class Budget(object):
    def __init__(self, engine):
        self._engine = engine

    def _prepare(self):
        log.info('dropping and creating %s',
                 [t.name for t in GnuCashAux.sorted_tables])
        GnuCashAux.drop_all(self._engine)
        GnuCashAux.create_all(self._engine)

    def load(self, infp):
        self._prepare()
        conn = self._engine.connect()
        sheet = csv.DictReader(infp)
        rows = list(sheet)
        log.info('inserting %d rows into %s', len(rows), BudgetItem)
        conn.execute(BudgetItem.insert(), rows)
        conn.execute(BudgetTypeUpdate)

    def sync_accounts(self, dry_run=True):
        conn = self._engine.connect()

        q = select_dups('''
(select distinct parent from gdocs_budget
where code > '' and t_lo > '') bi
left join accounts a
       on a.name=bi.parent
''',
                        key_cols=('parent', 'name'),
                        crit=func.count() != 1)
        missing_acct = conn.execute(q).fetchall()

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

        conn.execute('insert into accounts ' + missing_acct_q)

    def check_dups(self):
        conn = self._engine.connect()
        q = select_dups(BudgetItem.select().
                        where(BudgetItem.c.code > '').alias('bi'),
                        key_cols=('budget_name', 't_lo', 'code'))
        dups = conn.execute(q).fetchall()
        log.debug('dups: %d', len(dups))

        if dups:
            log.error('duplicate keys in budget spreadsheet: %s',
                      format_rows(dups))
            raise IOError

    def sync_items(self):
        # TODO: update, rather than delete all and re-insert
        conn = self._engine.connect()

        log.info('deleting budget_amounts...')
        result = conn.execute('''
delete
-- select *
from budget_amounts
where budget_guid in (
  select b.guid
  from budgets b
  where b.name in (
    select distinct budget_name from gdocs_budget)
)
''')
        log.info('deleted %d rows', result.rowcount)

        log.info('inserting budget_amounts ...')
        conn.execute('''
insert into budget_amounts
select -- distinct bi.t_lo, bi.code, bi.name
       null id,
         b.guid budget_guid,
       a.guid account_guid,
       mod(month(t_lo) - 1, 3) period_num,
       budget * 100 * (
         case a.account_type
           when 'INCOME' then 1
           when 'EXPENSE' then 1
           when 'LIABILITY' then -1
           else 1/0
         end
       ) amount_num,
       100 amount_denom
from (
 select budget_name,
        STR_TO_DATE(bi.t_lo,'%%m/%%d/%%Y') t_lo,
        account_type, bi.code, parent, bi.name,
        1 * replace(replace(budget, '$', ''), ',', '') budget
 from gdocs_budget bi
 where bi.code > ''
 ) bi
join budgets b
on b.name=bi.budget_name
join accounts a
on a.code=bi.code

-- and b.guid is null
-- order by bi.budget_name, bi.code, t_lo
''')
        log.info('inserted %d rows', result.rowcount)


def select_dups(from_obj, key_cols,
                crit=func.count() > 1):
    '''
    >>> print select_dups(from_obj='t', key_cols=('a', 'b', 'c'))
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT a, b, c, count(*) AS count_1
    FROM t GROUP BY a, b, c
    HAVING count(*) > :count_2
    '''
    return select(key_cols + (func.count(), ), from_obj=from_obj).\
        group_by(*key_cols).having(crit)


def format_rows(rows):
    return '\n'.join([str(row) for row in rows])


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
