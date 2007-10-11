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

def export(request):
    frm, to = asDate(request.GET['from']), asDate(request.GET['to'])
    transactions = Transaction.objects.filter(date__range=(frm, to)) \
                   .order_by('date')
    body = loader.render_to_string('export.tsv',
                                   {'transactions': transactions,
                                    'frm': frm,
                                    'to': to
                                    })
    return HttpResponse(body, mimetype="text/plain")

