import logging
import pprint
from datetime import date
from decimal import Decimal

# "http://furius.ca/beancount
from beancount.ledger import Ledger, Account, Transaction, Posting, Wallet

from trxtsv import trxiter, isoDate

log = logging.getLogger(__name__)

USD = 'USD'
IMBALANCE_USD = 'Imbalance-USD'


def main(argv):
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    files = argv[1:]
    convert(files)


def convert(files):
    # based on Leger.parse_file in ledger.py
    #@@txs = list(trxiter(files))

    l = Ledger()
    #@@ get_accounts(l, txs)

    l.commodities.add(USD)

    for tx in trxiter(files):
        mktx(l, tx)

    # not sure what these do...
    l.build_postings_lists()
    l.complete_balances()
    l.compute_priced_map()
    l.complete_bookings()
    l.build_payee_lists()
    l.build_tag_lists()

    for trx in l.transactions:
        print trx.pretty()


def get_accounts(l, txs):
    for n in set([tx['trx']['acct'] for tx in txs]):
        l.get_account(n, create=True)

    for n in set([split['cat']
                  for tx in txs
                  for split in tx['splits'] if 'cat' in split]):
        l.get_account(n, create=True)

    log.debug('accounts:\n%s', pprint.pformat(l.accounts))


def mktx(l, obj):
    tx, splits = obj['trx'], obj['splits']
    txn = Transaction()
    txn.actual_date = txn.effective_date = mkdate(tx['date'])

    # txn.flag?
    # txn.code = ...?
    txn.payee = tx.get('payee', None)

    tot = 0
    for s in splits:
        anum = Decimal(s['subtot'].replace(',', ''))
        tot += anum
        post = mkposting(l, txn,
                         s.get('acct', s.get('cat', IMBALANCE_USD)),
                         anum,
                         flag=s.get('clr', None),
                         note=s.get('memo', None))

    mkposting(l, txn, tx['acct'], -tot, note=tx.get('memo', None))

    l.transactions.append(txn)


def mkposting(l, txn, acct_name, anum, flag=None, note=None):
    if not(acct_name):
        import pdb; pdb.set_trace()
    post = Posting(txn)
    txn.postings.append(post)
    post.account_name = acct_name
    post.account = l.get_account(acct_name, create=1)
    post.amount = post.cost = Wallet(USD, anum)
    return post


def mkdate(dt):
    """convert quicken date format to python date
    assume date between 1950 and 2050

    >>> mkdate("12/31/02")
    datetime.date(2002, 12, 31)

    >>> mkdate("12/31/96")
    datetime.date(1996, 12, 31)

    """

    mm, dd, yy = dt.split("/")
    yy = int(yy)
    if yy > 50:
        yy = 1900 + yy
    else:
        yy = 2000 + yy
    return date(yy, int(mm), int(dd))


if __name__ == '__main__':
    import sys
    main(sys.argv)
