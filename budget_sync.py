'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging
from pprint import pformat

from sqlalchemy import (MetaData, Table, Column,
                        select, func, text)
from sqlalchemy.types import String, Date, Integer
from sqlalchemy.engine.url import URL

from gckey import findMaker

log = logging.getLogger(__name__)

Name = String(80)


def main(argv, open_arg, engine_arg,
         level=logging.DEBUG):
    logging.basicConfig(level=level)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    gdoc_budget, engine = open_arg(1), engine_arg(2)

    budget = Budget(engine)
    if '--by-parent' in argv:
        log.info('subtots:\n%s', pformat(budget.compare_subtots()))
    elif '--by-type' in argv:
        log.info('subtots:\n%s', pformat(budget.compare_by_acct_type()))
    elif '--load' in argv:
        budget.load(gdoc_budget)
        budget.check_dups()
        budget.sync_accounts(dry_run='--accounts' not in argv)
    elif [arg for arg in argv
          if arg != '--acounts' and arg.startswith('--')]:
        raise SystemExit('unrecognized arguments:' + str(argv[1:]))
    else:
        budget.load(gdoc_budget)
        budget.check_dups()
        budget.sync_accounts(dry_run='--accounts' not in argv)
        budget.sync_items()


GnuCashAux = MetaData()
BudgetItem = Table('gdocs_budget', GnuCashAux,
                   Column('id', Integer),
                   Column('guid', String(32)),
                   Column('budget_name', Name),
                   Column('budget_guid', String(32)),
                   Column('t_lo', String(40)),
                   Column('lo', Date),  # date
                   Column('period_num', Integer),
                   Column('account_type', Name),
                   Column('code', Name),
                   Column('parent', Name),
                   Column('name', Name),
                   Column('account_guid', String(32)),
                   Column('budget', String(20)),
                   Column('amount_num', Integer),
                   Column('amount_sign', Integer),
                   Column('slot_9', Integer),
                   Column('slot_3', Integer),
                   Column('notes', String(200)))

BudgetMatchUpdate = text('''
 update gdocs_budget
 set budget_guid = (
   select guid from budgets b
   where b.name = budget_name
 )
''')

AccountMatchUpdate = text('''
 update gdocs_budget bi
 join accounts a on a.code = bi.code
 join (
   select replace(uuid(), '-', '') guid, budget_name, code
   from (
     select distinct budget_name, code from gdocs_budget
   ) each_acct_budget
 ) ea on ea.code = bi.code and ea.budget_name = bi.budget_name
 set account_guid = a.guid,
     amount_sign =
         case a.account_type
           when 'INCOME' then 1
           when 'EXPENSE' then 1
           when 'LIABILITY' then -1
           else 1/0
         end,
     bi.guid = ea.guid
 where bi.code > ''
''')

ItemMatchUpdate = text('''
 update gdocs_budget bi
 join budgets b on b.guid = bi.budget_guid
 join accounts a on a.guid = bi.account_guid
 join budget_amounts ba on ba.budget_guid = b.guid
              and ba.account_guid = a.guid
              and ba.period_num = bi.period_num
 set bi.id = ba.id
''')

SlotMatchUpdate = text('''
 update gdocs_budget bi
 join budgets b on b.guid = bi.budget_guid
 join accounts a on a.guid = bi.account_guid
 join slots s9 on s9.obj_guid = b.guid
              and s9.name = a.guid
              -- and s9.slot_type = 9
 join slots s3 on s3.obj_guid = s9.guid_val
              -- and s3.slot_type = 3
              and substr(s3.name, 34) = bi.period_num
 set bi.slot_9 = s9.id,
     bi.slot_3 = s3.id,
     bi.guid = s9.guid_val
''')

BudgetTypeUpdate = text('''
 update gdocs_budget
 set lo = STR_TO_DATE(t_lo,'%m/%d/%Y'),
     amount_num = 100 * replace(replace(budget, '$', ''), ',', '')
 where code > '' and t_lo > ''
''')

BudgetPeriodUpdate = text('''
 update gdocs_budget
 set period_num = mod(month(lo) - 1, 3)
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
        conn.execute(BudgetMatchUpdate)
        conn.execute(BudgetTypeUpdate)
        conn.execute(BudgetPeriodUpdate)

    def sync_accounts(self, dry_run=True):
        conn = self._engine.connect()

        q = '''
select parent, name, count(name) from
(select distinct parent from gdocs_budget
where code > '' and t_lo > '') bi
left join accounts a
       on a.name=bi.parent
group by parent, name
having count(name) != 1
'''
        missing_acct = conn.execute(q).fetchall()

        log.debug('Ambiguous parents: %d', len(missing_acct))

        if missing_acct:
            log.error('Ambiguous parents:\n%s',
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

        log.info('inserting accounts...')
        result = conn.execute('insert into accounts ' + missing_acct_q)
        log.info('inserted %d rows', result.rowcount)

        conn.execute(AccountMatchUpdate)

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

    acct_type_q = '''select gcb.*, gdb.subtot,
      case when gcb.subtot = gdb.subtot then '' else 'MISMATCH' end ok
    from
    (select b.name budget_name, a.account_type,
    sum(ba.amount_num / ba.amount_denom) subtot
    from budgets b
    join budget_amounts ba on ba.budget_guid = b.guid
    join accounts a on a.guid = ba.account_guid
    where b.name in (%(budget_name)s)
    group by b.name, a.account_type) gcb
    join (
      select budget_name, account_type,
      sum(amount_num * amount_sign / 100.0) subtot
      from gdocs_budget bi
      where bi.code > ''
      and budget_name in (%(budget_name)s)
      group by budget_name, account_type
    ) gdb
      on gdb.budget_name = gcb.budget_name
      and gdb.account_type = gcb.account_type
    '''

    def compare_by_acct_type(self, budget_name='2013 Q2'):
        conn = self._engine.connect()
        ans = conn.execute(self.acct_type_q, budget_name=budget_name)
        return ans.fetchall()

    subtot_q = '''select gcb.*, gdb.subtot,
      case when gcb.subtot = gdb.subtot then '' else 'MISMATCH' end ok
    from
    (select b.name budget_name, a.account_type, p.name parent,
    sum(ba.amount_num / ba.amount_denom) subtot
    from budgets b
    join budget_amounts ba on ba.budget_guid = b.guid
    join accounts a on a.guid = ba.account_guid
    join accounts p on a.parent_guid = p.guid
    where b.name in (%(budget_name)s)
    group by b.name, a.account_type, p.name) gcb
    left join (
      select budget_name, account_type, parent,
      sum(amount_num * amount_sign / 100.0) subtot
      from gdocs_budget bi
      where bi.code > ''
      and budget_name in (%(budget_name)s)
      group by budget_name, account_type, parent
    ) gdb
      on gdb.budget_name = gcb.budget_name
      and gdb.account_type = gcb.account_type
      and gdb.parent = gcb.parent
    '''

    def compare_subtots(self):
        conn = self._engine.connect()
        ans = conn.execute(self.subtot_q, budget_name='2013 Q2')
        return ans.fetchall()

    def sync_items(self):
        # TODO: update, rather than delete all and re-insert
        conn = self._engine.connect()

        log.info('matching slots...')
        result = conn.execute(SlotMatchUpdate)
        log.info('updated %d rows', result.rowcount)

        log.info('matching budget items...')
        result = conn.execute(ItemMatchUpdate)
        log.info('updated %d rows', result.rowcount)

        unmatched = conn.execute('''
select * from gdocs_budget
where code > '' and (budget_guid is null
   or account_guid is null
   or id is null
   or slot_9 is null
   or slot_3 is null)
''').fetchall()
        if unmatched:
            log.info('unmatched: %s', format_rows(unmatched))

        log.info('deleting budget_amounts...')
        result = conn.execute('''
delete from budget_amounts where budget_guid in (
  select distinct budget_guid
  from gdocs_budget where account_guid is not null
)
''')
        log.info('deleted %d rows', result.rowcount)

        log.info('inserting budget_amounts ...')
        conn.execute('''
insert into budget_amounts
select -- distinct bi.t_lo, bi.code, bi.name
       id,
       budget_guid,
       account_guid,
       period_num,
       amount_num * amount_sign amount_num,
       100 amount_denom
from gdocs_budget bi
join accounts a on a.guid=bi.account_guid
''')
        log.info('inserted %d rows', result.rowcount)

        log.info('deleting budget slots...')
        result = conn.execute('''
delete s3
from gdocs_budget bi
join slots s9 on bi.budget_guid = s9.obj_guid
             and bi.account_guid = s9.name
join slots s3 on s3.obj_guid = s9.guid_val;
''')
        log.info('deleted %d rows', result.rowcount)
        result = conn.execute('''
delete s9
from gdocs_budget bi
join slots s9 on bi.budget_guid = s9.obj_guid
             and bi.account_guid = s9.name
''')
        log.info('deleted %d rows', result.rowcount)

        log.info('inserting budget slots type 9...')
        result = conn.execute('''
insert into slots (id, obj_guid, name, slot_type, guid_val)
select distinct slot_9, budget_guid, account_guid, 9, guid
from gdocs_budget bi
where bi.account_guid is not null
''')
        log.info('inserted %d rows', result.rowcount)

        log.info('inserting budget slots type 3...')
        result = conn.execute('''
insert into slots (id, obj_guid, name,
                   slot_type, numeric_val_num, numeric_val_denom)
select slot_3, guid, concat(account_guid, '/', period_num),
       3, amount_num * amount_sign, 100
from gdocs_budget bi
where bi.account_guid is not null
order by period_num
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
    def _initial_caps(host='localhost'):
        from sys import argv
        import gnomekeyring as gk
        from sqlalchemy import create_engine

        def open_arg(ix):
            return open(argv[ix])

        def engine_arg(ix):
            db = argv[ix]
            findcreds = findMaker(gk.find_network_password_sync)
            log.info('getting keyring info for %s', db)
            creds = findcreds(db)
            return create_engine(
                URL(drivername='mysql', host=host, database=db,
                    username=creds['user'],
                    password=creds['password']))

        return dict(argv=argv,
                    open_arg=open_arg,
                    engine_arg=engine_arg)

    main(**_initial_caps())
