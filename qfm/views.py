# based on
# http://www.djangoproject.com/documentation/0.96/tutorial03/

from django.shortcuts import render_to_response
from dm93data.qfm.models import Account, Transaction

def accounts(request):
    accounts = Account.objects.filter(kind="AL").order_by('name')
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
