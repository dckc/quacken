from django.conf.urls.defaults import * #@@ ew import *

urlpatterns = patterns('',
    (r'^$', 'dm93data.qfm.views.accounts'),
    (r'^register/(?P<acct_id>\d+)', 'dm93data.qfm.views.register'),
)
