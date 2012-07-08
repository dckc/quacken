'''gctomg -- convert GnuCash to moneyGuru
'''

import logging
from xml.etree import cElementTree as ElementTree

import sqlalchemy

log = logging.getLogger(__name__)


def main(argv):
    logging.basicConfig(level=logging.INFO)
    db_url = argv[1]
    e = sqlalchemy.create_engine(db_url)
    print ElementTree.tostring(convert(e))


def convert(e):
    guid = e.execute('select guid from books').fetchone()[0]
    f = mg_file(guid)
    # properties?
    f.extend(groups(e))
    f.extend(accounts(e))
    return f


def mg_file(uuid):
    return ElementTree.Element('moneyguru-file',
                               document_id=uuid)

TY = {'ROOT': None,
      'ASSET': 'asset',
      'BANK': 'asset',
      'CASH': 'asset',
      'RECEIVABLE': 'asset',
      'EQUITY': 'asset',  # hmm...
      'LIABILITY': 'liability',
      'CREDIT': 'liability',
      'PAYABLE': 'liability',
      'INCOME': 'income',
      'EXPENSE': 'expense'
      }


def groups(e):
    parents = e.execute('''select distinct p.name, p.account_type
                           from accounts p
                           join accounts ch
                           on ch.parent_guid = p.guid''').fetchall()

    # hmm... no subgroups
    return [ElementTree.Element('group',
                                {'name': acct[0],
                                 'type': TY[acct[1]], # TODO: just 4 types
                                 })
            for acct in parents if TY[acct[1]]]


def accounts(e):
    multi_currency_accounts = e.execute('''
        select count(*), account_guid, name
        from 

        (select distinct a.guid account_guid, a.name
              , cur.guid currency_guid, cur.mnemonic
        from accounts a
        join splits s on s.account_guid = a.guid
        join transactions tx on s.tx_guid = tx.guid
        join commodities cur on cur.guid = tx.currency_guid) t
        group by account_guid, name
          having count(*) > 1'''
                         ).fetchall()

    if multi_currency_accounts:
        raise LookupError(multi_currency_accounts)

    accounts = e.execute('''
        select distinct cur.mnemonic, a.name, a.account_type
             , p.name, p.account_type, ofx.string_val
        from accounts a
        join accounts p on a.parent_guid = p.guid
        left join slots ofx on ofx.name='online_id' and ofx.obj_guid = a.guid
        join splits s on s.account_guid = a.guid
        join transactions tx on s.tx_guid = tx.guid
        join commodities cur on cur.guid = tx.currency_guid'''
                         ).fetchall()
    for a in accounts:
        t = TY[a[2]]
        pt = TY[a[4]]
        if pt and t != pt:
            log.warn('account type mismatch: %s[%s] in %s[%s]',
                     a[1], t, a[3], pt)

    def ofxref(d, a):
        return dict(d, reference='||'.join(a[5].split())) if a[5] else d

    return [ElementTree.Element('account',
                                ofxref({'currency': a[0],
                                        'name': a[1],
                                        'group': a[3],
                                        'type': TY[a[2]]}, a))
            for a in accounts if TY[a[2]]]


if __name__ == '__main__':
    def _hide_sys():
        import sys
        return sys.argv
    main(_hide_sys())
