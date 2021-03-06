# based on
# http://www.djangoproject.com/documentation/0.96/tutorial03/

# TODO: Use case: dining calendar. Fun:dining category in hCalendar with times

import datetime

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import loader, RequestContext
from django.utils import simplejson
from django import forms
from django.core.urlresolvers import reverse
from django.db import connection

from dm93data.qfm.models import Account, Transaction, Split
from widgets import AutoCompleteWidget

def accounts(request):
    accounts = Account.objects.filter(kind="AL") \
	.order_by('name')
    categories = Account.objects.filter(kind="IE") \
	.order_by('name')
    return render_to_response('accounts.html',
                              {'accounts': accounts,
			       'categories': categories,
			       'queries': connection.queries},
                              context_instance=media_too(request)
                              )


def networth(request):
    de = asDate(request.GET['date_end'])
    report = request.GET['report']
    acct_ids = [int(a) for a in request.GET.getlist('accts')]
    accounts = Account.objects.filter(pk__in = acct_ids) \
	.order_by('name')
    tot = 0
    for a in accounts:
	b = a.balance(de)
	a.bal = b
	tot += b
    return render_to_response('report.html',
                              {'date_end': de,
			       'report': report,
			       'accounts': accounts,
			       'total': tot,
			       'queries': connection.queries,
                               },
                              context_instance=media_too(request)
                              )

def expenses(request):
    report = request.GET['report']
    cat_ids = [int(c) for c in request.GET.getlist('cat')]
    ds, de = asDate(request.GET['date_start']), \
	asDate(request.GET['date_end'])

    cats = Account.objects.filter(pk__in = cat_ids)

    splits = Split.objects.filter(acct__in = cats,
				  trx__date__gte = ds,
				  trx__date__lt = de).order_by('trx__date')
    tot = sum([s.subtot for s in splits])

    return render_to_response('expenses.html',
                              {'date_start': ds,
			       'date_end': de,
			       'report': report,
			       'splits': splits,
			       'total': tot,
			       'queries': connection.queries,
                               },
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

def register(request):
    acct_id, ds, de = int(request.GET['acct']), \
	asDate(request.GET['date_start']), \
	asDate(request.GET['date_end'])
    account = Account.objects.get(id=acct_id)
    bal = account.balance(ds)
    transactions = account.transaction_set.filter(date__gte = ds,
						  date__lt = de)
    for t in transactions:
        splits = t.split_set.all()
        amount = sum([s.subtot for s in splits])
        bal += amount
        t.amount = amount
        t.balance = bal

    #@@ TODO: 'txform': TransactionForm()
    return render_to_response('register.html',
                              {'account': account,
                               'balance': bal,
                               'transactions': transactions,
			       'queries': connection.queries,
                               },
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
