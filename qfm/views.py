# based on
# http://www.djangoproject.com/documentation/0.96/tutorial03/

# TODO: Use case: dining calendar. Fun:dining category in hCalendar with times

import datetime

from django.shortcuts import render_to_response
from dm93data.qfm.models import Account, Transaction
from django.http import HttpResponse
from django.template import loader, RequestContext
from django.utils import simplejson
from django import newforms as forms
from django.core.urlresolvers import reverse

from widgets import AutoCompleteWidget

def accounts(request):
    accounts = Account.objects.filter(kind="AL")
    for a in accounts:
        tx = a.transaction_set.latest('date')
        a.modified = tx.date
    def byDate(a):
        return a.modified
    accounts = sorted(accounts, key=byDate, reverse=True)
    return render_to_response('accounts.html',
                              {'accounts': accounts},
                              context_instance=media_too(request)
                              )


def media_too(request):
    # django 0.96 doesn't yet have django.core.context_processors.media
    # so we do it manually..

    from django.conf import settings
    return RequestContext(request, {"MEDIA_URL": settings.MEDIA_URL})

class TransactionForm(forms.Form):
    category = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        # cribbed from 
        w = self.fields['category'].widget = AutoCompleteWidget()
        w.lookup_url = reverse('dm93data.qfm.views.category_choices')
        w.schema = '["choices", "name"]' 

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
                               'transactions': transactions,
                               'txform': TransactionForm()},
                              context_instance=media_too(request)
                              )

def asDate(s):
    y = int(s[:4])
    m = int(s[5:7])
    d = int(s[8:10])
    return datetime.date(y, m, d)


def scalarq(query, params):
    """execute a query (e.g. SELECT sum(...) ...) and return the sole result
    """
    from django.db import connection
    cursor = connection.cursor()

    cursor.execute(query, params)
    return cursor.fetchone()[0]


def balances(frm, to):
    # Hmm... including the qfm_ prefix here seems ugly,
    # but I can't find any alternative in the Django Database API
    # http://www.djangoproject.com/documentation/db-api/
    splitSum = "SELECT sum(qfm_Split.subtot) FROM qfm_Transaction, qfm_Split" \
               " WHERE qfm_Split.trx_id = qfm_Transaction.id "
    bal_in = scalarq(splitSum +
                     " AND qfm_Transaction.date < %s", [frm]) or 0.0

    bal_out = scalarq(splitSum +
                      " AND qfm_Transaction.date <= %s", [to])

    inflows = scalarq(splitSum +
                      " AND qfm_Split.subtot > 0"
                      " AND qfm_Transaction.date >= %s"
                      " AND qfm_Transaction.date <= %s", [frm, to])

    outflows = scalarq(splitSum +
                       " AND qfm_Split.subtot < 0"
                       " AND qfm_Transaction.date >= %s"
                       " AND qfm_Transaction.date <= %s", [frm, to])

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

def category_choices(request):
    # http://www.djangosnippets.org/snippets/392/
    # http://developer.yahoo.com/yui/autocomplete/
    #http://superb-west.dl.sourceforge.net/sourceforge/yui/yui_2.3.1.zip
    hint = request.GET.get('query', '')
    accts = Account.objects.filter(kind="IE", name__istartswith = hint)
    return JsonResponse({'choices': [ {'id': a.id,
                                       'name': a.name}
                                      for a in accts]})


class JsonResponse(HttpResponse):
    # cribbed from http://www.djangosnippets.org/snippets/154/
    def __init__(self, object):
        content = simplejson.dumps(object)
        super(JsonResponse, self).__init__(content, mimetype='application/json')
