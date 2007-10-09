# based on
# http://www.djangoproject.com/documentation/0.96/tutorial03/

from django.shortcuts import render_to_response
from dm93data.qfm.models import Account

def accounts(request):
    accounts = Account.objects.all().order_by('name')
    return render_to_response('accounts.html',
                              {'accounts': accounts})
