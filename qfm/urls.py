from django.conf.urls.defaults import patterns
from django.conf import settings

urlpatterns = patterns('',
    (r'^$', 'dm93data.qfm.views.accounts'),
    (r'^networth', 'dm93data.qfm.views.networth'),
    (r'^expenses', 'qfm.views.expenses'),
    (r'^register', 'dm93data.qfm.views.register'),
    (r'^register/(?P<acct>\d+)', 'dm93data.qfm.views.register'),
    (r'^export', 'dm93data.qfm.views.export'),
    (r'^api/categories/', 'dm93data.qfm.views.category_choices'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
