# based on
# http://www.djangoproject.com/documentation/0.96/tutorial03/

import datetime

from django.shortcuts import render_to_response
from dm93data.qfm.models import Account, Transaction
from django.http import HttpResponse
from django.template import loader

def accounts(request):
    accounts = Account.objects.filter(kind="AL")
    for a in accounts:
        tx = a.transaction_set.latest('date')
        a.modified = tx.date
    def byDate(a):
        return a.modified
    accounts = sorted(accounts, key=byDate, reverse=True)
    return render_to_response('accounts.html',
                              {'accounts': accounts})

def register(request, acct_id):
    account = Account.objects.get(id=int(acct_id))
    transactions = account.transaction_set.all()
    bal = 0.0
    for t in transactions:
        splits = t.split_set.all()
        amount = sum([s.subtot for s in splits])
        bal += amount
        t.amount = amount
        t.balance = bal
    return render_to_response('register.html',
                              {'account': account,
                               'balance': bal,
                               'transactions': transactions})

def asDate(s):
    y = int(s[:4])
    m = int(s[5:7])
    d = int(s[8:10])
    return datetime.date(y, m, d)


def balances(frm, to):
    from django.db import connection
    cursor = connection.cursor()

    splitSum = "SELECT sum(qfm_Split.subtot) FROM qfm_Transaction, qfm_Split" \
                " WHERE qfm_Split.trx_id = qfm_Transaction.id "
    cursor.execute(splitSum +
                   " AND qfm_Transaction.date < %s", [frm])
    bal_in = cursor.fetchone()[0] or 0.0

    cursor.execute(splitSum +
                   " AND qfm_Transaction.date <= %s", [to])
    bal_out = cursor.fetchone()[0]

    cursor.execute(splitSum +
                   " AND qfm_Split.subtot > 0"
                   " AND qfm_Transaction.date >= %s"
                   " AND qfm_Transaction.date <= %s", [frm, to])
    inflows = cursor.fetchone()[0]

    cursor.execute(splitSum +
                   " AND qfm_Split.subtot < 0"
                   " AND qfm_Transaction.date >= %s"
                   " AND qfm_Transaction.date <= %s", [frm, to])
    outflows = cursor.fetchone()[0]

    return bal_in, inflows, outflows, bal_out


def export(request):
    frm, to = asDate(request.GET['from']), asDate(request.GET['to'])
    transactions = Transaction.objects.filter(date__range=(frm, to)) \
                   .order_by('date')

    bal_in, inflows, outflows, bal_out = balances(frm, to)

    body = loader.render_to_string('export.tsv',
                                   {'transactions': transactions,
                                    'frm_1': frm - datetime.timedelta(1),
                                    'frm': frm,
                                    'to': to,
                                    'bal_in': bal_in,
                                    'inflows': inflows,
                                    'outflows': outflows,
                                    'net': inflows + outflows,
                                    'bal_out': bal_out
                                    })
    return HttpResponse(body, mimetype="text/plain")

