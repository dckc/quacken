'''budget_sync -- load GnuCash budget from google docs spreadsheet
'''

import csv
import logging

log = logging.getLogger(__name__)

MONEY_DENOM = 100


def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    infn = argv[1]

    def log_row(r):
        log.debug('insert: %s', r)

    budget_load(open(infn), log_row)


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

        monthly_num = money(row[monthly_col])
        for p in range(0, periods):
            amt = monthly_num + (money(row[period0_col + p])
                                 if period0_col + p < len(row)
                                 else 0)

            if amt > 0:
                insert_fn((None, budget_name, cat, subcat, acct_id, p,
                           amt, MONEY_DENOM))


def money(txt):
    '''
    >>> money('$8,454.00')
    845400
    '''
    amt = 0
    try:
        amt = int(txt.replace('$', '').replace(',', '').replace('.', ''))
    except ValueError:
        pass
    return amt


if __name__ == '__main__':
    import sys
    main(sys.argv)
